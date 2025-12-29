
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

def run_ishape_validation():
    print("----------------------------------------------------------------")
    print("🚀 RoomGEN V2 Phase 10: I-Shape Validation Protocol")
    print("----------------------------------------------------------------")
    
    # Force new assets
    AssetFactory.ensure_assets(force=True)
    
    # 1. Define I-Shape Room (Linear 400cm Wall)
    # Just a simple box, we pick the bottom wall.
    polygon = [(0,400), (0,0), (400,0), (400,400)] 
    walls, corners = RoomParser.parse_polygon(polygon)
    
    # Select just ONE wall (Wall 1: Bottom 0,0 -> 400,0)
    # Direction: P1(0,0) -> P2(400,0). Normal is (0,1). Interior is +Y.
    target_wall = walls[1]
    
    # ADD WINDOW?
    # Let's add a window to test obstruction in I-Shape
    target_wall.features.append({
        "type": "window", "x_start": 250, "width": 100
    })

    # ADD UTILITIES
    # Water/Waste for Sink (Start of line?)
    target_wall.features.append({"type": "water_point", "x_start": 80, "width": 10})
    target_wall.features.append({"type": "waste_point", "x_start": 80, "width": 10})
    
    # Requirements for Single Wall
    # Fridge -> Pantry -> Sink -> Dishwasher -> Stove -> Drawers
    required_items = ["fridge", "pantry", "sink", "dishwasher", "stove", "drawer_unit"]
    
    detailed_cabinets = []
    exporter = HybridExporter()

    # NO CORNER SOLVER NEEDED
    
    # Solve Loop (Single Wall)
    print(f"Solving Wall {target_wall.index} Length: {target_wall.length}")
    base_items = WallSolver.solve(target_wall, required_items=required_items)
    upper_items = UpperCabinetSolver.solve(target_wall, base_items)
    all_items = base_items + upper_items
    
    # Geometry calc
    wx = target_wall.p2[0] - target_wall.p1[0]; wy = target_wall.p2[1] - target_wall.p1[1]
    wall_len = math.sqrt(wx*wx + wy*wy)
    ux = wx / wall_len; uy = wy / wall_len
    nx, ny = -uy, ux 
    
    start_3d = np.array([target_wall.p1[0], 0, target_wall.p1[1]])
    vec_3d = np.array([ux, 0, uy])
    norm_3d = np.array([nx, 0, ny])
    n_angle = math.degrees(math.atan2(ny, nx))
    cabinet_rot = 90 - n_angle
    
    # generate cabinets
    for item in all_items:
        dist = item['x_local'] + item['width']/2
        pos_on_line = start_3d + vec_3d * dist
        
        # Depth Offsets (Same logic as V9)
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
        
        cab = CabinetFactory.create(item, list(final_pos), rotation=cabinet_rot)
        cab.metadata = {"wall_index": target_wall.index, "x_local": item['x_local'], "width": item['width'], "type": item['type']}
        detailed_cabinets.append(cab)

    # Export
    output_path = os.path.join(os.path.dirname(__file__), "output", "hybrid_ishape_validation.glb")

    # Floor
    floor = trimesh.creation.box(extents=[500, 1, 500])
    floor.apply_translation([200, -0.5, 200])
    floor.visual.face_colors = [220, 220, 220, 100]
    exporter.scene.add_geometry(floor)
    
    # Windows Visualization
    w_asset = exporter.load_asset("window_frame_v1")
    if w_asset:
        # Wall 1 Window (At 250)
        # Pos = Start(0,0) + Vec(1,0)*250 = (250,0). Normal (0,1).
        # Win Pos 3D = (250, 150, 0)
        # Rotation: Align with Wall Normal.
        T = trimesh.transformations.translation_matrix([250, 150, -5])
        for m in w_asset: exporter.scene.add_geometry(m.copy(), transform=T)

    # Cabinets
    for cab in detailed_cabinets:
        exporter.add_cabinet(cab)
        
    exporter.export(output_path)
    print(f"✅ I-Shape Validation Complete: {output_path}")

if __name__ == "__main__":
    run_ishape_validation()
