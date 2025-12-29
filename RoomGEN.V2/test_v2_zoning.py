import sys
import os
import json

# Add V2 to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from core.geometry import GeometryEngine, HAS_SHAPELY
from core.zoning import WorkbenchZone, DiningZone
from core.physical import PhysicalRules

def run_test():
    print("----------------------------------------------------------------")
    print("🏗️  RoomGEN V2 Phase 2: Zoning & Physical Rules Test")
    print("----------------------------------------------------------------")

    if not HAS_SHAPELY:
        print("⚠️  Shapely not found. Using Fallback Geometry Engine.")
    else:
        print("✅ Shapely detected.")

    # 1. Test Physical Rules (Service Void)
    print("\n[1] Testing Service Void...")
    cabinet = {"type": "base_cabinet", "x": 100, "y": 0, "width": 60, "depth": 60}
    shifted = PhysicalRules.apply_service_void(cabinet, gap=5.0)
    print(f"Original Y: {cabinet['y']}, Shifted Y: {shifted['y']}")
    if shifted['y'] == 5.0:
        print("✅ Service Void Applied Successfully (Y shifted by 5cm)")
    else:
        print(f"❌ Service Void Failed: Expected 5.0, got {shifted['y']}")

    # 2. Test Bio-Metric Tuning
    print("\n[2] Testing Bio-Metric Tuning...")
    user_h = 180 # cm
    # Elbow = 180 * 0.63 = 113.4
    # Worktop = 113.4 - 15 = 98.4
    recommended = PhysicalRules.calculate_worktop_height(user_h)
    print(f"User Height: {user_h}cm -> Recommended Worktop: {recommended:.1f}cm")
    if 98.0 <= recommended <= 99.0:
        print("✅ Bio-Metric Calculation Correct")
    else:
        print("❌ Bio-Metric Calculation Failed")

    # 3. Test Zoning & Collision
    print("\n[3] Testing Zoning & Buffer...")
    # Dining Table 100x200
    dining = DiningZone(x=200, y=200, table_w=200, table_d=100)
    # Workbench nearby
    workbench = WorkbenchZone(x=200, y=50, length=200) # y=50, depth=60 -> y_end=110

    print("Checking Table Chair Zone collisions...")
    # Chair zone is 60cm buffer. Table ends at y=300 (200+100). Buffer extends to y=360 and y=140.
    # Workbench ends at y=110. y=140 vs y=110 -> Gap is 30cm. No collision.
    
    collision = GeometryEngine.check_collision(dining.chair_zone, workbench.shape)
    if not collision:
        print("✅ No collision between Chair Zone and Workbench (Correct)")
    else:
        print("❌ Unexpected collision detected")

    # Create a colliding item (e.g. Island too close)
    # Table starts y=200. Buffer starts y=140.
    # Island at y=150 (inside buffer)
    island_shape = GeometryEngine.create_rect(x=200, y=150, width=100, depth=40)
    collision_island = GeometryEngine.check_collision(dining.chair_zone, island_shape)
    if collision_island:
         print("✅ Collision Detected with Obstacle in Chair Zone (Correct)")
    else:
         print("❌ Failed to detect collision")

if __name__ == "__main__":
    run_test()
