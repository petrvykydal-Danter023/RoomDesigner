import sys
import os
import math
import numpy as np
import trimesh

sys.path.append(os.path.join(os.path.dirname(__file__)))

from core.room_parser import RoomParser
from solvers.corner_solver import CornerSolver
from solvers.wall_solver import WallSolver
from solvers.upper_cabinet_solver import UpperCabinetSolver
from solvers.cabinet_factory import CabinetFactory
from generators.asset_factory import AssetFactory
from exporters.hybrid_exporter import HybridExporter
from core.schema import CabinetItem, Component

from solvers.layout_solver import LayoutSolver

def run_master_validation():
    print("----------------------------------------------------------------")
    print("🚀 RoomGEN V2 Phase 9: Master Validation Protocol (Auto-Layout)")
    print("----------------------------------------------------------------")
    
    # Force new assets
    AssetFactory.ensure_assets(force=True)
    
    # 1. Define L-Shape Room
    polygon = [(0,300), (0,0), (300,0), (300,300)] 
    walls, corners = RoomParser.parse_polygon(polygon)
    kitchen_walls = walls[:2] # Wall 0 (Left), Wall 1 (Bottom)
    
    # ADD WINDOWS (Wall 0: Center Window)
    kitchen_walls[0].features.append({
        "type": "window", "x_start": 90, "width": 120
    })
    # Wall 1: Center Window (Re-added per user request)
    # Wall 1 Usable: 90 (Corner) to 300. Pantry at End (240-300).
    # Window Space: 90 to 240. Let's put it at 130-220 (Width 90).
    kitchen_walls[1].features.append({
        "type": "window", "x_start": 130, "width": 90
    })

    # ADD UTILITIES
    # Wall 0: Water/Waste
    kitchen_walls[0].features.append({"type": "water_point", "x_start": 150, "width": 10}) 
    kitchen_walls[0].features.append({"type": "waste_point", "x_start": 150, "width": 10})
    
    # Wall 1: Gas
    kitchen_walls[1].features.append({"type": "gas_point", "x_start": 200, "width": 10})
    
    # 2. Nexus (Corner)
    corner_node = None
    for c in corners:
        if c.wall_in == kitchen_walls[0] and c.wall_out == kitchen_walls[1]:
            corner_node = c
            break   
    if not corner_node: corner_node = corners[0]

    # Reserve Corner (90cm)
    CornerSolver.solve(corner_node, budget="high")
    
    # 3. AUTO-LAYOUT
    # User Rules: Tall at ends, Logic by utilities.
    # Required Furniture Pool
    required_pool = ["fridge", "pantry", "sink", "stove", "dishwasher"]
    
    print("\n[Auto-Layout] Distributing items...")
    layout_assignments = LayoutSolver.distribute_items(kitchen_walls, required_pool)
    
    print("Assignments:")
    for wid, items in layout_assignments.items():
        print(f"  Wall {wid}: {items}")

    detailed_cabinets = []
    exporter = HybridExporter()

    # PLACE L-CORNER ASSET (The anchor)
    corner_pos_3d = [corner_node.wall_in.p2[0], 0, corner_node.wall_in.p2[1]] # [0,0,0]
    
    # Base Corner
    detailed_cabinets.append(CabinetItem(
        id="corner_l_shape", type="corner_cabinet", position=corner_pos_3d, rotation=0,
        components=[Component(type="corner", dims=[], pos=[0,0,0], asset_id="corner_cabinet_l_v1")]
    ))
    # Upper Corner
    detailed_cabinets.append(CabinetItem(
        id="corner_upper_l_shape", type="upper_corner_cabinet", position=[corner_pos_3d[0], 150, corner_pos_3d[2]], rotation=0,
        components=[Component(type="corner_upper", dims=[], pos=[0,0,0], asset_id="upper_corner_cabinet_l_v1")]
    ))

    # Solve Loop
    for i, wall in enumerate(kitchen_walls):
        # Use Auto-Layout Assignments
        reqs = layout_assignments.get(wall.index, [])
        
        base_items = WallSolver.solve(wall, required_items=reqs)
        upper_items = UpperCabinetSolver.solve(wall, base_items)
        all_items = base_items + upper_items
        
        # Geometry calc
        wx = wall.p2[0] - wall.p1[0]; wy = wall.p2[1] - wall.p1[1]
        wall_len = math.sqrt(wx*wx + wy*wy)
        ux = wx / wall_len; uy = wy / wall_len
        nx, ny = -uy, ux 
        
        start_3d = np.array([wall.p1[0], 0, wall.p1[1]])
        vec_3d = np.array([ux, 0, uy])
        norm_3d = np.array([nx, 0, ny])
        n_angle = math.degrees(math.atan2(ny, nx))
        cabinet_rot = 90 - n_angle
        
        # ---------------------------------------------------------
        # UTILITY VISUALIZATION loop
        # ---------------------------------------------------------
        for feat in wall.features:
            ftype = feat.get("type", "")
            if ftype in ["water_point", "waste_point", "gas_point"]:
                # Position on wall line
                f_pos = feat.get("x_start", 0) # Use start as point
                pos_3d = start_3d + vec_3d * f_pos
                
                # Create Marker
                # Disk: Radius 5, Height 2.
                # Color: Blue (Water), Brown (Waste), Yellow (Gas)
                color = [200, 200, 200, 255]
                if ftype == "water_point": color = [0, 0, 255, 255] # Blue
                elif ftype == "waste_point": color = [100, 50, 0, 255] # Brown
                elif ftype == "gas_point": color = [255, 215, 0, 255] # Gold/Yellow
                
                marker = trimesh.creation.cylinder(radius=4, height=2)
                # Rotate to face normal (Cylinder is Z-up)
                # We want cylinder flat on wall -> Axis along Normal?
                # Wall Normal is 'norm_3d'.
                # Transform cylinder Z to align with 'norm_3d'
                
                # Default Cylinder is along Z.
                # Cross product Z with Normal -> Rotation Axis.
                z_axis = np.array([0, 0, 1])
                target_axis = norm_3d
                
                # Actually, simpler: just create sphere or box for robustness? 
                # Cylinder looks like a pipe fitting. Good.
                
                # Rotation matrix from Z to Target
                # Using trimesh align
                R = trimesh.geometry.align_vectors(z_axis, target_axis)
                
                # Apply Rotation
                marker.apply_transform(R)
                
                # Move to Position
                # Offset slightly out of wall? Or On Wall?
                # Wall is virtual line. 
                # Let's put slightly forward (0.1) so it doesn't Z-fight if we had a wall mesh
                marker.apply_translation(pos_3d + norm_3d * 1) 
                
                # Height: usually 50cm
                marker.apply_translation([0, 50, 0])
                if ftype == "waste_point": marker.apply_translation([0, -10, 0]) # Waste lower
                
                marker.visual.face_colors = color
                exporter.scene.add_geometry(marker)
        
        for item in all_items:
            dist = item['x_local'] + item['width']/2
            pos_on_line = start_3d + vec_3d * dist
            
            # Depth Offsets
            if "upper" in item['type'] or "hood" in item['type'] or "upper" in str(item.get('linked_to', '')):
                if item['type'] == 'upper_bridge': depth_offset = 60/2; height_offset = 200
                else: depth_offset = 35/2; height_offset = 150
            elif item['type'] == 'fridge_spacer': # Tall Unit
                 depth_offset = 60/2; height_offset = 0
            else:
                depth_offset = 60/2; height_offset = 0
            
            if item['type'] == 'fridge' or item['type'] == 'pantry': depth_offset = 60/2
            
            final_pos = pos_on_line + norm_3d * depth_offset
            final_pos[1] += height_offset 
            
            # Create
            cab = CabinetFactory.create(item, list(final_pos), rotation=cabinet_rot)
            
            # Tag wall index for later analysis
            cab.metadata = {"wall_index": wall.index, "x_local": item['x_local'], "width": item['width'], "type": item['type']}
            detailed_cabinets.append(cab)

    # -------------------------------------------------------------
    # POST-PROCESSING: CHECK ISOLATED CORNER
    # -------------------------------------------------------------
    # Corner connects Wall 0 (End) and Wall 1 (Start).
    # Wall 0 Length: Check upper items ending near 300 - 60 = 240.
    # Wall 1 Length: Check upper items starting near 60.
    
    has_neighbor_w0 = False
    has_neighbor_w1 = False
    
    # Wall 0 is kitchen_walls[0]. Length ~300.
    # Wall 1 is kitchen_walls[1].
    
    w0_idx = kitchen_walls[0].index
    w1_idx = kitchen_walls[1].index
    w0_len = kitchen_walls[0].length
    
    for cab in detailed_cabinets:
        if not hasattr(cab, 'metadata'): continue
        if "upper" not in cab.type and "hood" not in cab.type: continue # Only check uppers
        
        md = cab.metadata
        if not md: continue
        
        if md.get('wall_index') == w0_idx:
            # Check if ends near 240 (Corner Reservation 60)
            end_pos = md['x_local'] + md['width']
            # Reservation starts at w0_len - 60.
            limit = w0_len - 60
            if abs(end_pos - limit) < 5: # Tolerance
                has_neighbor_w0 = True
                
        elif md['wall_index'] == w1_idx:
            # Check if starts near 60
            start_pos = md['x_local']
            limit = 60
            if abs(start_pos - limit) < 5:
                has_neighbor_w1 = True

    if not has_neighbor_w0 and not has_neighbor_w1:
        print("🔍 Detected Isolated Corner! Swapping to Open Shelf Asset.")
        # Find upper corner cabinet
        for cab in detailed_cabinets:
            if cab.type == "upper_corner_cabinet":
                # Swap asset
                for comp in cab.components:
                    if comp.type == "corner_upper":
                        comp.asset_id = "upper_corner_open_v1"
                        # Adjust position?? 
                        # The asset includes Wings. It should physically occupy the empty space?
                        # Yes, visually. The origin remains 0,0,0 (Corner).
                        # Asset matches orientation.
                        break
    
    # Export
    output_path = os.path.join(os.path.dirname(__file__), "output", "hybrid_master_validation.glb")
    # exporter = HybridExporter() # Already init
    
    # Floor
    floor = trimesh.creation.box(extents=[400, 1, 400])
    floor.apply_translation([150, -0.5, 150])
    floor.visual.face_colors = [220, 220, 220, 100]
    exporter.scene.add_geometry(floor)
    
    # Windows - Dynamic Generation
    w_asset = exporter.load_asset("window_frame_v1")
    if w_asset:
        for wall in kitchen_walls:
            # Re-calculate wall geometry
            wx = wall.p2[0] - wall.p1[0]; wy = wall.p2[1] - wall.p1[1]
            wall_len = math.sqrt(wx*wx + wy*wy)
            ux = wx / wall_len; uy = wy / wall_len
            nx, ny = -uy, ux # Normal pointing IN
            
            start_3d = np.array([wall.p1[0], 0, wall.p1[1]])
            vec_3d = np.array([ux, 0, uy])
            norm_3d = np.array([nx, 0, ny])
            
            # Rotation of wall
            n_angle = math.degrees(math.atan2(ny, nx))
            # Window aligns with wall.
            # Asset orientation: Z-up? We need to check asset.
            # Existing code used R1 = rotation_matrix(np.pi/2, [0,1,0]) for Wall 0 (Vertical).
            # Wall 0 Angle: Normal is (1,0) -> 0 deg?
            # Wall 1 Angle: Normal is (0,1) -> 90 deg?
            
            # Hardcoded rotation fix based on wall Index/Direction
            # Wall 0 (Vertical): Needs 90 deg rotation around Y.
            # Wall 1 (Horizontal): Needs 0 deg (or 180) rotation around Y.
            
            # Calculate Rotation Matrix from Wall Vector
            angle = math.atan2(wy, wx) # Wall Vector Angle
            # Wall 0: (0,-300) -> -90 deg.
            # Wall 1: (300,0) -> 0 deg.
            
            # Asset is likely aligned to X-axis?
            # If Wall 0 requires 90deg, implying Asset X aligns with Wall Z?
            # Let's trust the math: Rotate around Y by -angle?
            
            w_rot = trimesh.transformations.rotation_matrix(-angle, [0, 1, 0])
            
            for feat in wall.features:
                if feat.get('type') == 'window':
                    # Feature Pos (Start)
                    fs = feat['x_start']
                    fw = feat['width']
                    center_dist = fs + fw/2
                    
                    # Global Position of Center
                    center_pos = start_3d + vec_3d * center_dist
                    
                    # Offset for Window Thickness/Position
                    # Start_3d is Wall Center Line.
                    # Move slightly outwards (-Normal * 5)?
                    # Wall 0 Normal (1,0). Outwards is (-1,0). Correct. (-5 X)
                    # Wall 1 Normal (0,1). Outwards is (0,-1). Correct. (-5 Z)
                    
                    final_pos = center_pos - norm_3d * 5
                    final_pos[1] = 150 # Window Center Height (Standard)
                    
                    T = trimesh.transformations.translation_matrix(final_pos)
                    M = trimesh.transformations.concatenate_matrices(T, w_rot)
                    
                    for m in w_asset: exporter.scene.add_geometry(m.copy(), transform=M)

    # Cabinets
    for cab in detailed_cabinets:
        exporter.add_cabinet(cab)
        
    exporter.export(output_path)
    print(f"✅ Master Validation Complete: {output_path}")

if __name__ == "__main__":
    run_master_validation()
