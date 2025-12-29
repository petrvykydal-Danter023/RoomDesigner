import json
import argparse
import sys
import os
from datetime import datetime
from kitchen_core.geometry import Room
from kitchen_core.solver import KitchenSolver, StorageValidator, WorkflowSolver, WishlistExpander
from kitchen_core.generator import OBJGenerator
from kitchen_core.skins.premium import PremiumSkin
from kitchen_core.ghost_chef import GhostChef
from kitchen_core.style_grammar import StyleCritic
from kitchen_core.heatmaps import HeatmapSolver
from kitchen_core.heatmaps.visualize import export_combined_debug, export_placement_diagram

def main():
    parser = argparse.ArgumentParser(description="Kitchen Generator V3 - Premium Architecture")
    parser.add_argument("input_file", help="Path to input JSON file")
    parser.add_argument("--mode", choices=['standard', 'premium'], default='premium', 
                        help="Generation mode: standard (V2) or premium (V3)")
    parser.add_argument("--heatmaps", action="store_true",
                        help="Use heatmap-based placement solver (Beam Search)")
    parser.add_argument("--debug-maps", action="store_true",
                        help="Export heatmap debug PNG images")
    args = parser.parse_args()
    
    with open(args.input_file, 'r') as f:
        data = json.load(f)
        
    room_data = data['room']
    room = Room.from_dict(room_data)
    
    wishlist = data['wishlist']
    wall_wishlist = data.get('wall_wishlist', [])
    
    print(f"Room: {room.width}x{room.length}x{room.height}")
    print(f"Items: Base={len(wishlist)}, Wall={len(wall_wishlist)}")
    print(f"Mode: {args.mode.upper()}")
    print(f"Shape: {room.shape.upper()}")
    
    solver = KitchenSolver(room)
    chef = GhostChef()
    critic = StyleCritic()
    
    if args.mode == 'premium':
        # === V3 PREMIUM PIPELINE ===
        
        # === WISHLIST EXPANDER (Smart Fill) ===
        expander = WishlistExpander(room)
        wishlist, wall_wishlist = expander.expand(wishlist, wall_wishlist)
        
        # Auto-detect shape if needed
        actual_shape = room.shape
        if room.shape == 'auto':
            actual_shape = solver.detect_optimal_shape(wishlist)
            print(f"\n[Auto-Shape] Detected: {actual_shape}")
        
        if actual_shape == 'L':
            # === L-SHAPE PIPELINE ===
            if args.heatmaps:
                # L-Shape Heatmap Solver (Beam Search)
                print("\n[Phase 1] L-Shape Heatmap Placement (Beam Search)...")
                from kitchen_core.heatmaps.solver import LShapeHeatmapSolver
                lshape_solver = LShapeHeatmapSolver(room, corner_type='blind')
                lshape_result = lshape_solver.solve(wishlist)
                
                skeleton = {
                    'shape': 'L',
                    'corner': lshape_result['corner'],
                    'arm_a': lshape_result['arm_a'],
                    'arm_b': lshape_result['arm_b'],
                    'volumes': lshape_result['volumes'],
                    'wall_wishlist': wall_wishlist,
                    'heatmap_debug': lshape_result.get('debug', {})
                }
            else:
                # Original OR-Tools solver
                print("\n[Phase 1] L-Shape: Corner Nexus Strategy...")
                skeleton = solver.solve_l_shape(wishlist, wall_wishlist, corner_type='blind')
            
            if skeleton is None:
                print("No valid L-shape layout found!")
                sys.exit(1)
        else:
            # === I-SHAPE PIPELINE ===
            if args.heatmaps:
                # === HEATMAP SOLVER (Beam Search) ===
                print("\n[Phase 1] Heatmap Placement (Beam Search)...")
                heatmap_solver = HeatmapSolver(room)
                heatmap_result = heatmap_solver.solve(wishlist)
                
                skeleton = {
                    'shape': 'I',
                    'volumes': heatmap_result['volumes'],
                    'wall_wishlist': wall_wishlist,
                    'heatmap_debug': heatmap_result.get('debug', {})
                }
            else:
                # === PRO WORKFLOW ZONING (Default) ===
                print("\n[Phase 1] Pro Workflow Zoning...")
                workflow_solver = WorkflowSolver(room)
                workflow_result = workflow_solver.solve_workflow(wishlist)
                
                skeleton = {
                    'shape': 'I',
                    'workflow': workflow_result,
                    'volumes': workflow_result['volumes'],
                    'wall_wishlist': wall_wishlist
                }
            
            if skeleton is None:
                print("No valid layout found!")
                sys.exit(1)
        
        # === STORAGE INDEX VALIDATION ===
        storage_validator = StorageValidator(room)
        storage_eval = storage_validator.evaluate_solution(skeleton)
        storage_validator.print_report(storage_eval)
        
        # === AUTO-REMEDIATION: Add Island for large under-stored rooms ===
        island_config = None
        if storage_eval['status'] == 'UNDER-STORAGE' and storage_eval['suggest_island']:
            # Calculate Island size based on deficit
            deficit_m = storage_eval['deficit_m']
            island_width = min(max(120, deficit_m * 30), 240)  # 120-240cm based on need
            island_depth = 90
            
            # Center island in room
            island_x = room.width / 2
            island_z = room.length / 2 + 30  # Offset from center towards front
            
            island_config = {
                'x': island_x,
                'z': island_z,
                'width': island_width,
                'depth': island_depth,
                'has_cooktop': deficit_m > 4,  # Add cooktop if big deficit
                'has_seating': True
            }
            
            # Add island contribution to storage
            island_linear_m = island_width / 100
            print(f"  [AUTO] Adding Kitchen Island: {island_width}x{island_depth}cm (+{island_linear_m:.1f}m storage)")
            
            # Update skeleton with island
            skeleton['island'] = island_config
        
        # Score the solution
        ergo_cost = chef.evaluate_skeleton(skeleton, room.width)
        style_cost = critic.evaluate(skeleton, room.width)
        print(f"[Scoring] Ergo={ergo_cost:.1f}, Style={style_cost:.1f}")
        
        print("\n[Phase 2] Applying Premium Skin with Layer Grid...")
        skin = PremiumSkin()
        items = skin.apply(skeleton)
        
    else:
        # === V2 STANDARD PIPELINE ===
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
            total_score = ergo_cost + (style_cost * 0.5)
            print(f"  Candidate {i}: Ergo={ergo_cost:.1f}, Style={style_cost:.1f} => Total={total_score:.1f}")
            
            if total_score < best_total_score:
                best_total_score = total_score
                best_skeleton = skeleton
                
        print(f"Winner: Total Score = {best_total_score:.1f}")
        skeleton = best_skeleton
        
        print("Applying Standard Skin...")
        from kitchen_core.skins.ikea_metod import IkeaSkin
        skin = IkeaSkin()
        items = skin.apply(skeleton)
    
    # 3. Generate OBJ with Premium Geometry
    print("\n[Phase 3] Generating Premium Geometry...")
    gen = OBJGenerator()
    gen.generate_room_shell(room) # Generate walls/floor
    
    # Generate Corner Module for L-shape
    if skeleton.get('shape') == 'L' and skeleton.get('corner'):
        corner = skeleton['corner']
        print(f"  Generating corner module: {corner['type']} ({corner['size']}cm)")
        if corner['type'] == 'carousel':
            gen.generate_corner_carousel(0, 0, 0, corner['size'], 85, 60)
        else:
            gen.generate_corner_blind(0, 0, 0, corner['size'], 85, 60)
        
        # Generate L-shaped worktop connecting both arms
        arm_a = skeleton.get('arm_a', {})
        arm_b = skeleton.get('arm_b', {})
        corner_size = corner['size']
        worktop_y = 85  # Base cabinet height
        depth = 62  # Worktop depth with overhang
        
        print(f"  Generating L-worktop at y={worktop_y}cm")
        
        # Use generate_l_worktop if available
        gen.generate_l_worktop(
            arm_a_start=corner_size,
            arm_a_end=arm_a.get('end', 350),
            arm_b_end=arm_b.get('monolith_start', arm_b.get('end', 185)),  # Stop at Monolith
            y=worktop_y,
            depth=depth,
            corner_size=corner_size
        )
    
    # Generate Kitchen Island if configured
    if skeleton.get('island'):
        island = skeleton['island']
        gen.generate_island(
            x=island['x'],
            z=island['z'],
            width=island['width'],
            depth=island['depth'],
            has_cooktop=island.get('has_cooktop', False),
            has_seating=island.get('has_seating', True)
        )
    
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
        # Handle L-shape: Arm B items are on Z axis (perpendicular wall)
        item_axis = item.get('axis', 'X')
        item_z = item.get('z', 0)
        
        if item_axis == 'Z':
            # Arm B item: rotated 90° - placed along left wall
            # Use dedicated rotated generator
            gen.generate_item_rotated_z(
                item['type'],
                0,  # x = at left wall
                0,  # y (base level)
                item_z,  # z position along side wall
                item['width'],
                item.get('height', 85),
                item.get('depth', 60)
            )
        else:
            # Standard Arm A item: along back wall
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
            'z': item_z,
            'width': item['width'],
            'height': item.get('height', 85),
            'depth': item.get('depth', 60),
            'axis': item_axis
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
    
    # Export heatmap debug images if requested
    if args.heatmaps and args.debug_maps and 'heatmap_debug' in skeleton:
        debug_dir = os.path.join(out_dir, "debug")
        os.makedirs(debug_dir, exist_ok=True)
        
        # Export placement diagram
        export_placement_diagram(
            placed_items=placed_items,
            room_width=room.width,
            path=os.path.join(debug_dir, "placement.png")
        )
        print(f"  [Debug] Exported heatmap debug images to {debug_dir}/")
        
    print(f"Generated {obj_path} and {json_path}")

if __name__ == '__main__':
    main()
