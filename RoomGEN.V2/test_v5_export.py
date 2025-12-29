import sys
import os

# Add V2 to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from core.materials import get_material_for_item
from exporters.obj_exporter import ObjExporter

def run_test():
    print("----------------------------------------------------------------")
    print("🏗️  RoomGEN V2 Phase 5: 3D Export Test")
    print("----------------------------------------------------------------")

    # 1. Test Materials
    print("\n[1] Testing Material Mapping...")
    mat = get_material_for_item("sink")
    print(f"Sink -> {mat['name']} RGB{mat['color']}")
    if mat['name'] == 'wet_zone':
        print("✅ Material Correct")
    else:
        print("❌ Material Incorrect")

    # 2. Test OBJ Export
    print("\n[2] Testing OBJ Export...")
    items = [
        {"type": "sink", "x_local": 0, "width": 60, "wall_index": 0},
        {"type": "stove", "x_local": 60, "width": 60, "wall_index": 0},
        {"type": "upper_cabinet", "x_local": 0, "width": 60, "wall_index": 0},
        {"type": "hood", "x_local": 60, "width": 60, "wall_index": 0}
    ]
    
    out_dir = os.path.dirname(__file__)
    out_obj = os.path.join(out_dir, "test_layout.obj")
    
    ObjExporter.export(items, out_obj)
    
    if os.path.exists(out_obj):
        print(f"✅ Generated {out_obj}")
        # Verify content basic check
        with open(out_obj, 'r') as f:
            content = f.read()
        
        if "usemtl wet_zone" in content and "usemtl hot_zone" in content:
            print("✅ OBJ contains correct material references")
        else:
            print("❌ OBJ missing material references")
            
        mtl_path = out_obj.replace(".obj", ".mtl")
        if os.path.exists(mtl_path):
             print(f"✅ Generated {mtl_path}")
        else:
             print("❌ MTL file missing")
             
    else:
        print("❌ Failed to generate OBJ")

if __name__ == "__main__":
    run_test()
