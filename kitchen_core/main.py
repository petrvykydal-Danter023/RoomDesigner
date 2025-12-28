import json
import argparse
import sys
import os
from datetime import datetime
from kitchen_core.geometry import Room
from kitchen_core.solver import KitchenSolver
from kitchen_core.generator import OBJGenerator
from kitchen_core.skins.ikea_metod import IkeaSkin
from kitchen_core.ghost_chef import GhostChef
from kitchen_core.style_grammar import StyleCritic

def main():
    parser = argparse.ArgumentParser(description="Kitchen Generator V1")
    parser.add_argument("input_file", help="Path to input JSON file")
    args = parser.parse_args()
    
    with open(args.input_file, 'r') as f:
        data = json.load(f)
        
    room_data = data['room']
    room = Room.from_dict(room_data)
    
    wishlist = data['wishlist']
    wall_wishlist = data.get('wall_wishlist', [])
    
    print(f"Room: {room.width}x{room.length}x{room.height}")
    print(f"Items: Base={len(wishlist)}, Wall={len(wall_wishlist)}")
    
    solver = KitchenSolver(room)
    chef = GhostChef()
    critic = StyleCritic()
    
    # 1. Solve (Generate Candidates)
    print("Generating candidates...")
    candidates = solver.solve_scenarios(wishlist, wall_wishlist, limit=10)
    
    if not candidates:
        print("No valid layout found!")
        sys.exit(1)
        
    print(f"Found {len(candidates)} candidates. Tasting & Judging...")
    
    best_skeleton = None
    best_total_score = float('inf')
    
    for i, skeleton in enumerate(candidates):
        ergo_cost = chef.evaluate_skeleton(skeleton, room.width)
        style_cost = critic.evaluate(skeleton, room.width)
        
        # Weighted Combination (Ergonomics > Style)
        total_score = ergo_cost + (style_cost * 0.5)
        
        print(f"  Candidate {i}: Ergo={ergo_cost:.1f}, Style={style_cost:.1f} => Total={total_score:.1f}")
        
        if total_score < best_total_score:
            best_total_score = total_score
            best_skeleton = skeleton
            
    print(f"Winner: Total Score = {best_total_score:.1f}")
    skeleton = best_skeleton
    
    print("Applying Skin...")
    
    # 2. Skin (Items)
    skin = IkeaSkin()
    items = skin.apply(skeleton)
    
    # 3. Generate OBJ
    gen = OBJGenerator()
    gen.generate_room_shell(room) # Generate walls/floor
    
    placed_items = []
    
    # Base Items from Skin
    for item in items:
        # Smart Cutouts Logic (Back holes for utilities)
        cutouts = []
        cx = item['x']
        cw = item['width']
        # Simple collision check with utilities
        for u in room.utilities:
             ux = u.get('x')
             if ux is not None and cx <= ux <= cx + cw: # Utility behind cabinet
                 # Calculate relative pos
                 rel_x = ux - cx
                 cutouts.append((rel_x, u.get('y', 10), 50.0, 50.0))
        
        # Generate using specialized dispatcher
        gen.generate_item_by_type(
            item['type'],
            item['x'],
            0,  # y (base level)
            0,  # z (back wall)
            item['width'],
            item.get('height', 85),
            item.get('depth', 60)
        )
        
        placed_items.append({
            'type': item['type'],
            'x': item['x'],
            'width': item['width'],
            'height': item.get('height', 85),
            'depth': item.get('depth', 60)
        })
        
    # Generate Fillers - handled by Skin in V2, but we might want explicit visual fillers using generator?
    # IkeaSkin returns 'filler' items. Does gen.generate_cabinet handle 'filler' type?
    # Usually we need specific model for filler.
    # For now, if type is 'filler', generate_cabinet will try to load 'filler.obj'.
    # If not found, it generates box.
    
    # Wall Items (Skipped in V2 basics, but we can iterate wall_wishlist manually if needed)
    # skeleton['wall_wishlist'] exists.
    # For now, ignore wall to test base.
    
    # Generate Worktop
    if placed_items:
        min_x = min(i['x'] for i in placed_items)
        max_x = max(i['x'] + i['width'] for i in placed_items)
        
        # Identify holes (Sink/Stove)
        holes = []
        for i in placed_items:
            t = i['type']
            if 'sink' in t or 'stove' in t:
                # Hole inset 5cm?
                holes.append((i['x'] + 5, i['width'] - 10))
                
        gen.generate_worktop(min_x, max_x, 85, 60, holes)
    
    # Create output dir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("outputs", f"run_{timestamp}")
    os.makedirs(out_dir, exist_ok=True)
    
    # Save OBJ
    obj_path = os.path.join(out_dir, "layout.obj")
    gen.save(obj_path)
    
    # Save JSON
    json_path = os.path.join(out_dir, "layout.json")
    with open(json_path, 'w') as f:
        json.dump(placed_items, f, indent=4)
        
    # Save Input Copy
    with open(os.path.join(out_dir, "input_snapshot.json"), 'w') as f:
        json.dump(data, f, indent=4)
        
    print(f"Generated {obj_path} and {json_path}")

if __name__ == '__main__':
    main()
