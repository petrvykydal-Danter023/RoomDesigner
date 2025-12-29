import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__)))

from core.schema import CabinetItem, Component
from generators.asset_factory import AssetFactory
from exporters.hybrid_exporter import HybridExporter

def run_hybrid_test():
    print("----------------------------------------------------------------")
    print("🏗️  RoomGEN V2 Phase 7: Hybrid Renderer Test")
    print("----------------------------------------------------------------")

    # 1. Generate Assets
    print("\n[1] Generating Assets...")
    AssetFactory.ensure_assets()
    
    # 2. Define a detailed Cabinet using Schema
    print("\n[2] Constructing Pydantic Schema...")
    
    # Standard 60cm Base Cabinet
    # Carcass: 60w x 72h x 56d
    # Legs: 15cm high
    # Door: 60w x 72h x 2d
    # Handle: attached to top-left of door
    
    cab_width = 60
    cab_height = 72
    cab_depth = 56
    leg_height = 15
    door_thick = 2
    
    # Global Z for carcass center = leg_height + cab_height/2 = 15 + 36 = 51
    # Global Y for carcass center (assuming 0 is back wall) = 56/2 = 28
    
    # Actually, let's define components relative to Cabinet Origin (0,0,0) which is on floor, back-left corner?
    # Or center?
    # HybridExporter assumes 'pos' is center of component relative to cabinet origin.
    # Let's say Cabinet Origin is center of bottom footprint on floor.
    
    # Carcass Center relative to floor center:
    # Z = leg_height + cab_height/2
    carcass_z = leg_height + cab_height/2
    
    cabinet = CabinetItem(
        id="cab_001",
        type="base_cabinet",
        position=[100, 30, 0], # X=100 global, Y=30 (depth/2), Z=0 (floor)
        rotation=0,
        components=[
            # CARCASS (White Box)
            Component(
                type="carcass",
                dims=[cab_width, cab_depth, cab_height], # Trimesh box extents
                pos=[0, 0, carcass_z],
                color=[240, 240, 240, 255]
            ),
            # DOOR (Brown Slab) - Front of carcass
            # Y pos = +cab_depth/2 + door_thick/2
            Component(
                type="door",
                dims=[cab_width, door_thick, cab_height],
                pos=[0, cab_depth/2 + door_thick/2, carcass_z],
                color=[139, 69, 19, 255]
            ),
            # LEGS (Assets)
            # 4 legs
            Component(type="leg", dims=[], pos=[-25, -20, 0], asset_id="leg_v1"),
            Component(type="leg", dims=[], pos=[25, -20, 0], asset_id="leg_v1"),
            Component(type="leg", dims=[], pos=[-25, 20, 0], asset_id="leg_v1"),
            Component(type="leg", dims=[], pos=[25, 20, 0], asset_id="leg_v1"),
            
            # HANDLE (Asset)
            # Attached to door front
            # Pos relative to cabinet:
            # Y = cab_depth/2 + door_thick
            # X = 20 (right side)
            # Z = carcass_z + 30 (top)
            Component(
                type="handle", 
                dims=[], 
                pos=[20, cab_depth/2 + door_thick, carcass_z + 25],
                asset_id="handle_v1",
                rotation=[0, 0, 90] # Rotate to be vertical? Handle asset is horizontal bar.
                # Asset handle_v1: Bar along Y axis (generated code says so).
                # We want it vertical -> Rotate 90 deg around X? 
                # Let's trust visual check.
            )
        ]
    )
    
    print(f"Created CabinetItem: {cabinet.id} with {len(cabinet.components)} components")

    # 3. Export
    print("\n[3] Exporting Hybrid Scene...")
    exporter = HybridExporter()
    exporter.add_cabinet(cabinet)
    
    output_path = os.path.join(os.path.dirname(__file__), "hybrid_kitchen_test.glb")
    exporter.export(output_path)
    
    print(f"✅ Exported: {output_path}")
    print("Open in 3D Viewer to see: 1 Cabinet, 4 Legs (asset), 1 Handle (asset)")

if __name__ == "__main__":
    run_hybrid_test()
