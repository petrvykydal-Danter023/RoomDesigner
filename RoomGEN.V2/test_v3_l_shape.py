import sys
import os

# Add V2 to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from core.room_parser import RoomParser
from solvers.corner_solver import CornerSolver
from solvers.wall_solver import WallSolver

def run_test():
    print("----------------------------------------------------------------")
    print("🏗️  RoomGEN V2 Phase 3: L-Shape Solver Test")
    print("----------------------------------------------------------------")

    # 1. Define L-Shape Room (Inner Corner at index 2 probably?)
    # (0,0) -> (300,0) -> (300,300) -> (0,300) is a square.
    # L-Shape:
    # A(0,200) -- B(100,200) (Inner corner?) No those are coords.
    # Let's trace a standard L-shape room CCW
    # S(0,0) -> R(300,0) -> Q(300,200) -> P(200,200) *INNER* -> O(200,300) -> N(0,300) -> S
    # Note: P is inner corner?
    # Wall QP (vector -100, 0)
    # Wall PO (vector 0, 100)
    # Angle? QP direction 180. PO direction 90.
    # Turn is Right? 180->90 is -90.
    # CCW system usually Left turns are inner. 
    # Let's try simple 2-wall segment logic manually first or just parse.
    
    # Let's define points that clearly make a 90 deg corner.
    # Wall 1: (0, 300) -> (0, 0) (Down)
    # Wall 2: (0, 0) -> (300, 0) (Right)
    # Corner at (0,0). Angle logic will tell.
    
    points = [ (0, 300), (0, 0), (300, 0) ] 
    # Technically an open string of walls, not closed room, but parser should handle it as segments.
    # Wall 0: (0,300)->(0,0). Vector (0, -300). Dir (0, -1). Angle 270.
    # Wall 1: (0,0)->(300,0). Vector (300, 0). Dir (1, 0). Angle 0.
    # Diff: 0 - 270 = -270. (180 - (-270)) % 360 = (450) % 360 = 90.
    # 90 deg -> Inner Corner.
    
    print("\n[1] Parsing Walls & Corners...")
    walls, corners = RoomParser.parse_polygon(points)
    print(f"Parsed {len(walls)} walls, {len(corners)} corners.") # Should be 2 walls, 1 corner (point 1)
    
    # Note: RoomParser currently loops back (i+1)%n. 
    # If we pass 3 points, it treats it as a triangle closed shape? 
    # Yes, parse_polygon assumes closed. 
    # If we want open, we need to ignore the last closing segment.
    # But let's assume valid room.
    
    corner = corners[0] # The one at index 0 (Wall 0 -> Wall 1)
    print(f"Corner 0: Type {corner.type} (Angle {corner.angle_deg:.1f})")
    
    if corner.type == 'inner':
        print("✅ Correctly identified Inner Corner")
    else:
        print(f"❌ Failed detection (Got {corner.type})")

    # 2. Solve Corner
    print("\n[2] Solving Corner (High Budget)...")
    sol = CornerSolver.solve(corner, budget="high")
    print(f"Solution: {sol['type']} | Side A: {sol['size_in']} | Side B: {sol['size_out']}")
    if sol['size_in'] == 90.0:
        print("✅ High Budget selected Carousel (90cm)")
    else:
        print("❌ Wrong module selected")
        
    print(f"Wall 0 Reserved End: {walls[0].end_reserved}")
    print(f"Wall 1 Reserved Start: {walls[1].start_reserved}")

    # 3. Solve Walls
    print("\n[3] Solving Wall 1 (Length: 300, Reserved Start: 90)...")
    # Usable: 300 - 90 = 210.
    # Fill with Sink, Stove.
    items = WallSolver.solve(walls[1], required_items=["sink", "stove"])
    print(f"Generated {len(items)} items:")
    total_w = 0
    for item in items:
        print(f" - {item['type']} (w={item['width']}, x={item['x_local']})")
        total_w += item['width']
        
    # Expected: Sink(60) at 90, Stove(60) at 150. Remainder 90 (60+30 cabinets). Total 210 space?
    # 90 + 60 = 150
    # 150 + 60 = 210
    # 210 + 60 (cabinet) = 270
    # 270 + 30 (narrow) = 300. Fits perfectly?
    
    if len(items) >= 2 and items[0]['type'] == 'sink':
        print("✅ Wall solved correctly with required items")
    else:
        print("❌ Wall solver issues")

if __name__ == "__main__":
    run_test()
