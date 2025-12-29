import sys
import os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__)))

from core.room_parser import WallSegment
from solvers.wall_solver import WallSolver
from solvers.upper_cabinet_solver import UpperCabinetSolver
from generators.asset_factory import AssetFactory
from exporters.hybrid_exporter import HybridExporter
from solvers.cabinet_factory import CabinetFactory

def run_hybrid_pipeline():
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("----------------------------------------------------------------")
    print("🚀 RoomGEN V2 Phase 7: Full Hybrid Pipeline")
    print("----------------------------------------------------------------")

    # 1. Assets
    print("[1] Ensuring Assets...")
    AssetFactory.ensure_assets()

    # 2. Solve Layout (Abstract)
    print("\n[2] Solving Abstract Layout...")
    wall = WallSegment((0, 0), (400, 0), 0)
    wall.features.append({"type": "window", "x_start": 150, "width": 100})
    
    required = ["fridge", "sink", "dishwasher", "stove"]
    base_items = WallSolver.solve(wall, required_items=required)
    upper_items = UpperCabinetSolver.solve(wall, base_items)
    
    all_abstract_items = base_items + upper_items
    print(f"   Generated {len(all_abstract_items)} abstract items.")

    # 3. Hydrate to Detailed Hybrid Schema
    print("\n[3] Hydrating with CabinetFactory...")
    detailed_cabinets = []
    
    # Room Depth for Y positioning
    room_depth = 300 
    wall_thickness = 10
    
    for item in all_abstract_items:
        # Calculate Global Position
        # Solver returns x_local along wall. 
        # For I-Shape on straight wall (y=0 in solver, but deep in room?)
        # Let's align with previous GLB exporter logic:
        # Cabinets are along Back Wall (Y=Depth).
        # Facing towards viewer (-Y).
        
        x_global = item['x_local'] + item['width']/2
        
        if "upper" in item['type'] or "hood" in item['type']:
            y_global = room_depth - wall_thickness - 35/2 # 35 deep
            z_global = 150 # Upper height
        else:
            y_global = room_depth - wall_thickness - 60/2 # 60 deep
            z_global = 0 # Floor
            
        # Rotation: 180 degrees (Facing Front/Viewer) if back wall is "North"
        # CabinetFactory assumes local Y+ is front?
        # If cabinet is against Back Wall, its Front should face -Y.
        
        # Let's verify CabinetFactory orientation.
        # Door pos Y = depth/2 + thick. This is +Y.
        # So Cabinet Front is +Y.
        # If Back Wall is at Y=TotalDepth, and we want cabinets to face Y=0...
        # We need to rotate them 180 degrees.
        
        rotation = 180
        
        cabinet = CabinetFactory.create(
            item_data=item, 
            global_pos=[x_global, y_global, z_global],
            rotation=rotation
        )
        detailed_cabinets.append(cabinet)
        
    print(f"   Created {len(detailed_cabinets)} detailed CabinetItems.")

    # 4. Export Hybrid GLB
    print("\n[4] Exporting Hybrid Scene...")
    exporter = HybridExporter()
    
    # Add Room Geometry (Procedural walls) - HybridExporter only adds cabinets currently?
    # Exporter.scene is a trimesh Scene. We can add room meshes manually.
    
    # Reuse GlbExporter room logic? Or recreate simply?
    # Let's recreate simple room walls in HybridExporter or here.
    import trimesh
    room_config = {"width": 400, "depth": 300, "height": 270}
    # Floor
    floor = trimesh.creation.box(extents=[400, 5, 300])
    floor.apply_translation([200, -2.5, 150])
    floor.visual.face_colors = [200, 180, 160, 255]
    exporter.scene.add_geometry(floor)
    
    # Wall (Back)
    back = trimesh.creation.box(extents=[400, 270, 10])
    back.apply_translation([200, 135, 300-5])
    back.visual.face_colors = [255, 255, 255, 100]
    exporter.scene.add_geometry(back)
    
    for cab in detailed_cabinets:
        exporter.add_cabinet(cab)
        
    output_path = os.path.join(output_dir, f"hybrid_kitchen_full_{timestamp}.glb")
    exporter.export(output_path)
    
    print(f"✅ Exported: {output_path}")
    print("   Includes detailed handles, legs, appliances, and walls.")

if __name__ == "__main__":
    run_hybrid_pipeline()
