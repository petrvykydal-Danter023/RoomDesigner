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

def run_l_shape_hybrid():
    print("----------------------------------------------------------------")
    print("🚀 RoomGEN V2 Phase 7: L-Shape Hybrid (Corner Asset)")
    print("----------------------------------------------------------------")
    
    # Force new assets
    AssetFactory.ensure_assets(force=True)
    
    # 1. Define L-Shape Room
    polygon = [(0,300), (0,0), (300,0), (300,300)] 
    walls, corners = RoomParser.parse_polygon(polygon)
    
    kitchen_walls = walls[:2] # First two
    
    # ADD WINDOW TO WALL 1
    # Wall 1 is 300 long.
    # Add window at 150cm (center), width 120 (including frame).
    kitchen_walls[0].features.append({
        "type": "window", 
        "x_start": 90, # 150 - 60 = 90
        "width": 120
    })

    # ADD WINDOW TO WALL 2
    # Wall 2 is 300 long.
    # Add window at 150cm (center), width 120.
    kitchen_walls[1].features.append({
        "type": "window", 
        "x_start": 90, 
        "width": 120
    })
    
    # 2. Nexus (Corner)
    corner_node = None
    for c in corners:
        if c.wall_in == kitchen_walls[0] and c.wall_out == kitchen_walls[1]:
            corner_node = c
            break
            
    if not corner_node: corner_node = corners[0]

    # USE HIGH BUDGET TO TRIGGER 90x90 Reservation if Solver supports it
    CornerSolver.solve(corner_node, budget="high") # Reserve 90cm on each side
    
    # 3. Solve Walls
    required = ["fridge", "sink", "stove", "dishwasher"]
    detailed_cabinets = []

    # PLACE L-CORNER ASSET
    # Asset 'corner_cabinet_l_v1' is generated at Origin (Back Corner).
    # Extends 90x90.
    # We just need to place it at the Corner Vertex (0,0) and rotate if needed.
    # Our corner is (0,0). Normals: +X and +Z.
    # Asset backs aligned with -X and -Z?
    # Asset gen: X[0..90], Z[0..90]. Back corner at 0,0.
    # So Asset occupies Quadrant +X, +Z.
    # If Corner Node is (0,0) and room is in +X, +Z (from (0,0) to (300,300)).
    # Then Asset fits perfectly without rotation.
    
    corner_pos_3d = [corner_node.wall_in.p2[0], 0, corner_node.wall_in.p2[1]] # [0,0,0]
    
    corner_cab = CabinetItem(
        id="corner_l_shape",
        type="corner_cabinet",
        position=corner_pos_3d,
        rotation=0, # Matches +X, +Z alignment
        components=[
            Component(type="corner", dims=[], pos=[0,0,0], asset_id="corner_cabinet_l_v1")
        ]
    )
    detailed_cabinets.append(corner_cab)

    # Upper Corner
    corner_upper = CabinetItem(
        id="corner_upper_l_shape",
        type="upper_corner_cabinet",
        position=[corner_pos_3d[0], 150, corner_pos_3d[2]], # Height 150
        rotation=0,
        components=[
             Component(type="corner_upper", dims=[], pos=[0,0,0], asset_id="upper_corner_cabinet_l_v1")
        ]
    )
    detailed_cabinets.append(corner_upper)

    
    for wall_idx, wall in enumerate(kitchen_walls):
        base_items = WallSolver.solve(wall, required_items=required)
        upper_items = UpperCabinetSolver.solve(wall, base_items)
        all_items = base_items + upper_items
        
        # Calculate Wall Coordinates
        wx = wall.p2[0] - wall.p1[0]; wy = wall.p2[1] - wall.p1[1]
        wall_len = math.sqrt(wx*wx + wy*wy)
        ux = wx / wall_len; uy = wy / wall_len
        nx, ny = -uy, ux 
        
        start_3d = np.array([wall.p1[0], 0, wall.p1[1]])
        vec_3d = np.array([ux, 0, uy])
        norm_3d = np.array([nx, 0, ny])
        
        # Normal Angle
        n_angle = math.degrees(math.atan2(ny, nx))
        
        # ROTATION CORRECTION
        cabinet_rot = 90 - n_angle
        
        for item in all_items:
            dist = item['x_local'] + item['width']/2
            pos_on_line = start_3d + vec_3d * dist
            
            if "upper" in item['type'] or "hood" in item['type']:
                if item['type'] == 'upper_bridge':
                    # Bridge over fridge: Starts high (200) and is deep (60)
                    depth_offset = 60/2
                    height_offset = 200
                else:
                    # Standard Upper
                    depth_offset = 35/2 
                    height_offset = 150
            else:
                depth_offset = 60/2; height_offset = 0
            
            if item['type'] == 'fridge': depth_offset = 60/2
            
            final_pos = pos_on_line + norm_3d * depth_offset
            final_pos[1] += height_offset 
            
            # Create
            cab = CabinetFactory.create(item, list(final_pos), rotation=cabinet_rot)
            
            # Color Coded Backs to verify Orientation
            # Add a back panel to every cabinet
            # Pos: -depth/2 (Back).
            # Cab origin is center.
            # Local Z is Front/Back.
            # Back is -Z.
            if item['type'] != 'fridge': # Fridge is simple block
                back_panel = Component(
                    type="panel",
                    dims=[item['width'], 72 if "upper" not in item['type'] else 70, 2],
                    pos=[0, 72/2+15 if "upper" not in item['type'] else 35, -30 if "upper" not in item['type'] else -17.5],
                    # Wait, Center Y. Center Z.
                    # Base: h=72, y=51. Back z=-30.
                    # This logic is tricky to inject here.
                    # Let's trust rotation formula.
                    color=[50, 50, 50, 255] # Dark Back
                )
                # cab.components.append(back_panel) 
                pass

            detailed_cabinets.append(cab)
            
            if item['type'] in required: required.remove(item['type'])

    # Export
    output_path = os.path.join(os.path.dirname(__file__), "output", "hybrid_l_shape_two_windows.glb")
    exporter = HybridExporter()
    
    # ---------------------------------------------------------
    # ROOM VISUALIZATION
    # ---------------------------------------------------------
    
    # Floor (Ghostly)
    floor = trimesh.creation.box(extents=[400, 1, 400])
    floor.apply_translation([150, -0.5, 150])
    floor.visual.face_colors = [220, 220, 220, 100]
    exporter.scene.add_geometry(floor)
    
    # Visualizing Openings
    w_asset = exporter.load_asset("window_frame_v1")
    if w_asset:
        # Window 1 (Wall 1): Pos (0, 150, 150). Face +X.
        T1 = trimesh.transformations.translation_matrix([-5, 150, 150]) 
        R1 = trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0])
        M1 = trimesh.transformations.concatenate_matrices(T1, R1)
        for m in w_asset:
            exporter.scene.add_geometry(m.copy(), transform=M1)
            
        # Window 2 (Wall 2): Pos (150, 150, 0). Face +Z.
        # Wall 2 is Y=0 line effectively in 2D? (0,0) to (300,0)?
        # Wall 2: (0,0) to (300,0). Y=0 (Z=0 in 3D).
        # Center is X=150. Z=0.
        # Normal is +Z?
        # vector (1,0) -> (-0, 1) normal? (0, 1) -> +Z.
        # So we want window at (150, 150, -5). Facing +Z.
        # Default window is Flat-Z?
        T2 = trimesh.transformations.translation_matrix([150, 150, -5])
        # If default is Flat-Z facing Z, no rotation needed?
        # Let's try identity rotation.
        M2 = T2
        for m in w_asset:
            exporter.scene.add_geometry(m.copy(), transform=M2)

    # Add Cabinets
    for cab in detailed_cabinets:
        exporter.add_cabinet(cab)
        
    exporter.export(output_path)
    print(f"✅ Exported Two Windows Hybrid: {output_path}")

if __name__ == "__main__":
    run_l_shape_hybrid()
