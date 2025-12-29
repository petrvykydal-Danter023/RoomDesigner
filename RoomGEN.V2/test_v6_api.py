import sys
import os

# Add V2 to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from reporting.bom import BOMGenerator
# Import API (will run imports, verify structure)
from api import main

def run_test():
    print("----------------------------------------------------------------")
    print("🏗️  RoomGEN V2 Phase 6: API & Reporting Test")
    print("----------------------------------------------------------------")

    # 1. Test BOM Generator
    print("\n[1] Testing BOM Generator...")
    layout_items = [
        {"type": "base_cabinet", "width": 60},
        {"type": "sink", "width": 60},
        {"type": "base_cabinet", "width": 60}
    ]
    # Expected:
    # base_cabinet (60cm): 2
    # sink (60cm): 1
    # Legs: 3 items (base/sink) -> 3 packs
    # Handles/Hinges: 2 cabinets -> 2 pairs + 2 handles
    
    bom = BOMGenerator.generate_bom(layout_items)
    print("Generated BOM:")
    for row in bom:
        print(f" - {row['item_name']}: {row['quantity']}")
        
    legs = next((r for r in bom if "Legs" in r['item_name']), None)
    if legs and legs['quantity'] == 3:
        print("✅ Legs calculated correctly (Hidden Items added)")
    else:
        print("❌ Legs calculation failed")
        
    # Export CSV
    csv_path = os.path.join(os.path.dirname(__file__), "test_bom.csv")
    if BOMGenerator.export_csv(bom, csv_path):
        print(f"✅ CSV Export successful: {csv_path}")
    else:
        print("❌ CSV Export failed")

    # 2. Test API imports
    print("\n[2] Testing API Structure...")
    if hasattr(main.app, 'post'):
        print("✅ FastAPI app instance found")
    else:
        print("❌ FastAPI app not initialized correctly")
        
    # Mock Request
    # We can't easily run async code in this sync script without asyncio loop,
    # but we can verify the function exists.
    if hasattr(main, 'solve_layout'):
        print("✅ Endpoint 'solve_layout' defined")
    else:
        print("❌ Endpoint missing")

if __name__ == "__main__":
    run_test()
