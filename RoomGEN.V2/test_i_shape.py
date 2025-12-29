import sys
import os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__)))

from core.room_parser import WallSegment
from solvers.wall_solver import WallSolver
from solvers.upper_cabinet_solver import UpperCabinetSolver
from reporting.bom import BOMGenerator
from exporters.glb_exporter import GlbExporter

def run_i_shape_test():
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          RoomGEN V2: I-Shape Kitchen Generator               ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    # ─────────────────────────────────────────────────────────────────────
    # ROOM CONFIG - Simple rectangular room with 4 walls
    # ─────────────────────────────────────────────────────────────────────
    room_config = {
        "width": 400,   # X dimension
        "depth": 300,   # Y dimension (cabinets at high Y, viewer at low Y)
        "height": 270,  # Z dimension
        "wall_thickness": 10,
        "features": {
            "back": [  # Wall where cabinets go
                {"type": "window", "x_start": 150, "width": 100, "sill_height": 90, "height": 120}
            ],
            "front": [],  # Transparent viewing wall
            "left": [],
            "right": [
                {"type": "door", "x_start": 100, "width": 90, "height": 210}
            ]
        }
    }
    
    print("\n┌─ ROOM ────────────────────────────────────────────────────────┐")
    print(f"│  Size: {room_config['width']} × {room_config['depth']} × {room_config['height']} cm")
    print("│  Back wall:  Window (150-250cm)")
    print("│  Right wall: Door")
    print("│  4 walls + floor, semi-transparent")
    print("└───────────────────────────────────────────────────────────────┘")

    # Solver
    wall = WallSegment((0, 0), (400, 0), 0)
    wall.features.append({"type": "window", "x_start": 150, "width": 100})
    
    required = ["fridge", "sink", "dishwasher", "stove"]
    base_items = WallSolver.solve(wall, required_items=required)
    upper_items = UpperCabinetSolver.solve(wall, base_items)
    all_items = base_items + upper_items
    
    print("\n┌─ LAYOUT ──────────────────────────────────────────────────────┐")
    for item in base_items:
        bar = "█" * (item['width'] // 10)
        print(f"│  {item['type']:18s} x={item['x_local']:3.0f}cm  {bar}")
    print("└───────────────────────────────────────────────────────────────┘")

    # Export
    glb_path = os.path.join(output_dir, f"kitchen_{timestamp}.glb")
    GlbExporter.export(all_items, glb_path, room_config=room_config)
    
    print(f"\n✅ Exported: {glb_path}")
    print("   Open in Windows 3D Viewer to see the full room!")

if __name__ == "__main__":
    run_i_shape_test()
