import sys
import os
import math
import numpy as np
import trimesh

sys.path.append(os.path.join(os.path.dirname(__file__)))

from core.room_parser import RoomParser
# Corners not needed for I-Shape
from solvers.wall_solver import WallSolver
from solvers.upper_cabinet_solver import UpperCabinetSolver
from solvers.cabinet_factory import CabinetFactory
from generators.asset_factory import AssetFactory
from exporters.hybrid_exporter import HybridExporter
from core.schema import CabinetItem, Component

def run_i_shape_hybrid():
    print("----------------------------------------------------------------")
    print("🚀 RoomGEN V2 Phase 8: I-Shape Hybrid")
    print("----------------------------------------------------------------")
    
    # Force new assets (ensure updated worktops/handles are used)
    AssetFactory.ensure_assets(force=True)
    
    # 1. Define I-Shape Room (Single Wall Focus)
    # We define a box, but we only use Wall 1 (Bottom, long)
    polygon = [(0,300), (0,0), (400,0), (400,300)]  # 400cm long wall at Bottom (Wall 1: 0,0 -> 400,0)
    walls, corners = RoomParser.parse_polygon(polygon)
    
    # Select Wall 1 (Bottom Wall: 0,0 to 400,0) as the Kitchen Wall
    kitchen_walls = [walls[1]] # Wall index 1 is usually the second segment? 
    # Let's verify: 
    # p1=(0,300), p2=(0,0) -> Wall 0 (Left)
    # p1=(0,0), p2=(400,0) -> Wall 1 (Bottom) -> THIS ONE
    
    main_wall = kitchen_walls[0]
    
    # ADD WINDOW
    # Wall is 400 long. Window at center (200).
    main_wall.features.append({
        "type": "window", 
        "x_start": 140, # 200 center - 60 = 140
        "width": 120
    })
    
    # 2. Nexus (Corner) - SKIPPED for I-Shape
    
    # 3. Solve Wall
    required = ["fridge", "sink", "stove", "dishwasher"]
    detailed_cabinets = []

    # Corner Asset - SKIPPED
    
    # Solve
    base_items = WallSolver.solve(main_wall, required_items=required)
    upper_items = UpperCabinetSolver.solve(main_wall, base_items)
    all_items = base_items + upper_items
    
    # Calculate Wall Coordinates
    wx = main_wall.p2[0] - main_wall.p1[0]; wy = main_wall.p2[1] - main_wall.p1[1]
    wall_len = math.sqrt(wx*wx + wy*wy)
    ux = wx / wall_len; uy = wy / wall_len
    nx, ny = -uy, ux 
    
    start_3d = np.array([main_wall.p1[0], 0, main_wall.p1[1]])
    vec_3d = np.array([ux, 0, uy])
    norm_3d = np.array([nx, 0, ny])
    
    # Normal Angle
    n_angle = math.degrees(math.atan2(ny, nx))
    
    # ROTATION
    cabinet_rot = 90 - n_angle
    
    for item in all_items:
        dist = item['x_local'] + item['width']/2
        pos_on_line = start_3d + vec_3d * dist
        
        if "upper" in item['type'] or "hood" in item['type']:
            if item['type'] == 'upper_bridge':
                depth_offset = 60/2
                height_offset = 200
            else:
                depth_offset = 35/2 
                height_offset = 150
        else:
            depth_offset = 60/2; height_offset = 0
        
        if item['type'] == 'fridge': depth_offset = 60/2
        
        final_pos = pos_on_line + norm_3d * depth_offset
        final_pos[1] += height_offset 
        
        # Create
        cab = CabinetFactory.create(item, list(final_pos), rotation=cabinet_rot)
        detailed_cabinets.append(cab)

    # Export
    output_path = os.path.join(os.path.dirname(__file__), "output", "hybrid_i_shape.glb")
    exporter = HybridExporter()
    
    # ---------------------------------------------------------
    # ROOM VISUALIZATION
    # ---------------------------------------------------------
    
    # Floor
    floor = trimesh.creation.box(extents=[500, 1, 400])
    floor.apply_translation([200, -0.5, 150])
    floor.visual.face_colors = [220, 220, 220, 100]
    exporter.scene.add_geometry(floor)
    
    # Window Vis
    w_asset = exporter.load_asset("window_frame_v1")
    if w_asset:
        # Wall 1: (0,0) to (400,0). Normal +Z (0,1).
        # Center X=200, Z=0.
        # Window at 200, 150, -5 (slightly back).
        T = trimesh.transformations.translation_matrix([200, 150, -5])
        # Default is Flat-Z. Matches Wall Normal. No rot needed.
        for m in w_asset:
            exporter.scene.add_geometry(m.copy(), transform=T)

    # Add Cabinets
    for cab in detailed_cabinets:
        exporter.add_cabinet(cab)
        
    exporter.export(output_path)
    print(f"✅ Exported I-Shape Hybrid: {output_path}")

if __name__ == "__main__":
    run_i_shape_hybrid()
