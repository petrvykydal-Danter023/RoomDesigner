import math
import random
from typing import List, Dict, Any, Tuple
from core.room_parser import WallSegment

class LayoutSolver:
    @staticmethod
    def distribute_items(walls: List[WallSegment], required_items: List[str]) -> Dict[int, List[str]]:
        """
        Distributes required items across walls based on rules:
        - Tall items (Fridge, Pantry) at Ends ONLY.
        - Sink near Water.
        - Stove near Gas (or away from Sink).
        - No Tall items blocking Windows.
        - Buffers between Tall/Appliance and Sink/Stove.
        """
        
        # 1. Classification
        tall_types = ["fridge", "pantry", "fridge_tall", "pantry_tall"]
        utility_map = {
            "sink": ["water_point", "waste_point"],
            "stove": ["gas_point", "electrical_point_stove"]
        }
        
        # Parse Request
        talls = [i for i in required_items if i in tall_types]
        appliances = [i for i in required_items if i not in tall_types and i not in ["drawer_unit", "base_cabinet", "narrow_cabinet"]]
        
        # We need to assign specific items to specific walls
        wall_assignments: Dict[int, List[str]] = {w.index: [] for w in walls}
        
        # 2. Analyze Walls for Zones
        # Zones: Start (End), Middle, End (End). 
        # Check constraints for Ends (Corner reserved? Window?)
        
        wall_scores = {}
        for w in walls:
            has_water = any(f['type'] in ['water_point', 'waste_point'] for f in w.features)
            has_gas = any(f['type'] == 'gas_point' for f in w.features)
            
            # Check ends validity for Tall
            # Start: 0-60. End: Length-60 to Length.
            # Check Window overlap.
            
            start_ok = True
            end_ok = True
            
            # Corner Reservations block Ends?
            # If start_reserved > 0, Start is NOT an End, it's a corner interface!
            # Effectively, "End" means a free standing end, NOT a corner.
            if w.start_reserved > 10: start_ok = False
            if w.end_reserved > 10: end_ok = False
            
            # Window check
            for f in w.features:
                if f.get('type') == 'window':
                    ws = f['x_start']; we = ws + f['width']
                    # Check Start (0-60)
                    if max(0, ws) < min(60, we): start_ok = False
                    # Check End (Len-60, Len)
                    if max(w.length-60, ws) < min(w.length, we): end_ok = False
            
            wall_scores[w.index] = {
                "wall": w,
                "has_water": has_water,
                "has_gas": has_gas,
                "start_ok_tall": start_ok,
                "end_ok_tall": end_ok
            }

        # 3. Assign TALL items (Priority 1: Constraints are highest)
        # Strategy: Place Fridge at one valid end, Pantry at another.
        # Simple heuristic: Fill outer ends first.
        
        assigned_talls = []
        
        # Find all valid slots: (WallIndex, "start"|"end")
        valid_slots = []
        for wid, info in wall_scores.items():
            if info['start_ok_tall']: valid_slots.append((wid, "start"))
            if info['end_ok_tall']: valid_slots.append((wid, "end"))
            
        # Assign
        # Determine "Outer" ends of the L-Shape? 
        # Wall 0 Start is usually outer. Wall 1 End is outer. (If Wall 0 -> Corner -> Wall 1)
        # Let's try to prioritize Wall 0 Start, then Wall 1 End.
        
        # Sort slots preference?
        # If we have Fridge and Pantry:
        # Slot 1: Wall 0 Start (if valid)
        # Slot 2: Wall 1 End (if valid)
        
        # Helper to push to assignment list
        # We store them as explicit placement directives or just a sequential list?
        # LayoutSolver returns a SEQUENCE. We need to build the Sequence.
        
        # Let's build a "Left" and "Right" stack for each wall to sandwich the middle?
        wall_stacks = {w.index: {"left": [], "right": [], "middle": []} for w in walls}
        
        for tall in talls:
            # Pick best slot
            picked = None
             # Try Wall 0 Start
            if wall_scores[walls[0].index]['start_ok_tall'] and ("start", walls[0].index) not in assigned_talls:
                 wall_stacks[walls[0].index]["left"].insert(0, tall) # 0 is absolute start
                 assigned_talls.append(("start", walls[0].index))
                 # Mark used
                 wall_scores[walls[0].index]['start_ok_tall'] = False
                 continue
                 
            # Try Wall 1 End
            if len(walls) > 1 and wall_scores[walls[1].index]['end_ok_tall'] and ("end", walls[1].index) not in assigned_talls:
                 wall_stacks[walls[1].index]["right"].append(tall)
                 assigned_talls.append(("end", walls[1].index))
                 wall_scores[walls[1].index]['end_ok_tall'] = False
                 continue

            # Fallback: Wall 0 End (if not corner)
            if wall_scores[walls[0].index]['end_ok_tall']:
                 wall_stacks[walls[0].index]["right"].append(tall)
                 wall_scores[walls[0].index]['end_ok_tall'] = False
                 continue
                 
            # Fallback: Wall 1 Start (if not corner)
            if len(walls) > 1 and wall_scores[walls[1].index]['start_ok_tall']:
                 wall_stacks[walls[1].index]["left"].insert(0, tall)
                 wall_scores[walls[1].index]['start_ok_tall'] = False
                 continue
                 
            print(f"⚠️ Could not place tall item {tall} ideally!")
            # Force into middle? User said NO.
            # We skip? Or put in a 'buffer' list?
        
        # 4. Assign Utilities (Sink, Stove, Dishwasher)
        
        # Sink
        sink_wall_idx = walls[0].index # Default
        # Find wall with water
        for wid, info in wall_scores.items():
            if info['has_water']: sink_wall_idx = wid; break
            
        wall_stacks[sink_wall_idx]["middle"].append("sink")
        
        # Dishwasher (Next to Sink)
        if "dishwasher" in appliances:
            wall_stacks[sink_wall_idx]["middle"].append("dishwasher")
            
        if "stove" in required_items:
            stove_wall_idx = walls[1].index if len(walls) > 1 else walls[0].index
            # Find gas
            for wid, info in wall_scores.items():
                if info['has_gas']: stove_wall_idx = wid; break
            
            if stove_wall_idx != sink_wall_idx:
                 wall_stacks[stove_wall_idx]["middle"].append("stove")
            else:
                 # Same wall.
                 # Check if we have a buffer in between (dishwasher is good).
                 if "dishwasher" not in wall_stacks[sink_wall_idx]["middle"]:
                     # Need explicit buffer
                     wall_stacks[sink_wall_idx]["middle"].append("drawer_unit")
                 wall_stacks[sink_wall_idx]["middle"].append("stove")
             
        # Buffers for Ends
        # If Left stack has Tall, and Middle has Appliance -> Inject Buffer
        for wid, stack in wall_stacks.items():
            if stack["left"] and stack["middle"]:
                # Check first middle item
                first_mid = stack["middle"][0]
                if first_mid in ["sink", "stove", "dishwasher"]:
                    stack["left"].append("narrow_cabinet") # Buffer after Tall (30cm)
                    
            if stack["right"] and stack["middle"]:
                # Check last middle item
                last_mid = stack["middle"][-1]
                if last_mid in ["sink", "stove", "dishwasher"]:
                    stack["right"].insert(0, "narrow_cabinet") # Buffer before Tall (30cm)
                    
        
        # 5. Finalize Lists & Fill Gaps
        final_assignments = {}
        
        # Width Map (should match WallSolver)
        WIDTHS = {
            "fridge": 60, "pantry": 60, "sink": 60, "dishwasher": 60, "stove": 60,
            "drawer_unit": 60, "base_cabinet": 60, "narrow_cabinet": 30, "drawer_unit_90": 90
        }
        
        for wid, stack in wall_stacks.items():
            # Calculate Used Width
            # Note: We need to know specific cabinet widths.
            
            # Helper to get width
            def get_w(item): return WIDTHS.get(item, 60)
            
            # Current used
            used_w = sum(get_w(i) for i in stack["left"] + stack["middle"] + stack["right"])
            
            # Available Width
            # Wall Length - Reserves - Windows(if blocking base?)
            w_obj = next(w for w in walls if w.index == wid)
            
            # Simplified Available Space Calc (Assumes 1 segment for now)
            # Todo: Handle multiple segments if blocked.
            # Start Reserve + End Reserve
            reserved = w_obj.start_reserved + w_obj.end_reserved
            # Windows do not block base cabinets usually.
            
            available = w_obj.length - reserved
            remainder = available - used_w
            
            # FILLING STRATEGY:
            # If we have a Right Stack (End items), we must fill BEFORE it.
            # If no Right Stack, we fill AFTER Middle (WallSolver does this automatically, but we can be explicit).
            
            fillers = []
            while remainder >= 30:
                if remainder >= 90:
                     # RANDOM GAP FILLING (User Requested)
                     # Options:
                     # 1. Buffer 30 + Base 60
                     # 2. Buffer 30 + Drawer 60
                     # 3. Big Drawer 90
                     choice = random.choice([1, 2, 3])
                     if choice == 1:
                         fillers.append("narrow_cabinet")
                         fillers.append("base_cabinet")
                     elif choice == 2:
                         fillers.append("narrow_cabinet")
                         fillers.append("drawer_unit")
                     else:
                         fillers.append("drawer_unit_90")
                     
                     remainder -= 90
                     continue

                if remainder >= 60:
                    # Randomize 60cm filler too
                    if random.choice([True, False]):
                        fillers.append("drawer_unit")
                    else:
                        fillers.append("base_cabinet")
                    remainder -= 60
                else:
                    fillers.append("narrow_cabinet")
                    remainder -= 30
            
            # Injection Point
            # If Right Stack exists (Pantry/Fridge at end), fillers go BEFORE Right Stack.
            # If Left Stack exists (Fridge at start), fillers go AFTER Left (and Middle).
            # Generally: Left -> Middle -> FILLER -> Right.
            
            # Check Stove/Gas Alignment
            # If Stove is in Middle, does it align with Gas?
            # Gas Point - Start Reserve = Target Relative Position.
            # We might need to split fillers to nudge Stove?
            # For now, let's just solve the "Pantry at End" issue (Bulk Fill before Right).
            
            combined = stack["left"] + stack["middle"] + fillers + stack["right"]
            final_assignments[wid] = combined
            
        return final_assignments
