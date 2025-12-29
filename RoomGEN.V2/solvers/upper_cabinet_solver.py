from typing import List, Dict, Any
from core.room_parser import WallSegment

class UpperCabinetSolver:
    @staticmethod
    def solve(wall: WallSegment, base_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Solves upper cabinets by aligning with base items (grid) and respecting windows.
        Windows block upper cabinets!
        """
        upper_items = []
        
        mapping = {
            "base_cabinet": "upper_cabinet",
            "sink": "upper_cabinet",
            "dishwasher": "upper_cabinet",
            "stove": "hood",
            "narrow_cabinet": "upper_narrow",
            "drawer_unit": "glass_upper",
            "pantry": "none" # Tall unit has no upper
            # "fridge": "upper_bridge" # Disabled per user request
            # "fridge_spacer": Excluded (Tall)
        }
        
        # Get window ranges that block uppers
        blocked_ranges = []
        for feat in wall.features:
            if feat.get('type') == 'window':
                blocked_ranges.append((feat['x_start'], feat['x_start'] + feat['width']))
        
        for b_item in base_items:
            if b_item.get('wall_index') != wall.index:
                continue
                
            u_type = mapping.get(b_item['type'])
            if not u_type:
                continue
            
            item_start = b_item['x_local']
            item_end = item_start + b_item['width']
            
            # Check window collision
            is_blocked = False
            for b_start, b_end in blocked_ranges:
                if not (item_end <= b_start or item_start >= b_end):
                    is_blocked = True
                    break
            
            if not is_blocked:
                upper_items.append({
                    "type": u_type,
                    "x_local": item_start,
                    "width": b_item['width'],
                    "wall_index": wall.index,
                    "linked_to": b_item['type']
                })
                
                
        # GAP FILLING LOGIC (Start of Wall)
        # Check if we have a Corner Reservation (e.g. 90) but Upper Corner is only 60.
        # This leaves a gap from 60 to 90 (30cm).
        # We assume standard upper corner size is 60.
        
        # Sort items by position
        upper_items.sort(key=lambda x: x['x_local'])
        
        start_reservation = wall.start_reserved
        if start_reservation >= 90:
            # We likely have an Upper Corner (60cm)
            upper_corner_end = 60
            
            # Find where first item starts
            first_item_start = upper_items[0]['x_local'] if upper_items else wall.length
            
            gap = first_item_start - upper_corner_end
            if gap >= 29: # Tolerance for 30cm
                # Fill with narrow uppers (30cm)
                # How many fits?
                count = int(gap // 30)
                for i in range(count):
                    # Position: 60 + i*30
                    pos = upper_corner_end + i*30
                    # Check window collision for this gap filler!
                    item_start = pos
                    item_end = pos + 30
                    is_blocked = False
                    for b_start, b_end in blocked_ranges:
                         if not (item_end <= b_start or item_start >= b_end):
                            is_blocked = True
                            break
                    
                    if not is_blocked:
                        upper_items.append({
                            "type": "upper_narrow",
                            "x_local": pos,
                            "width": 30,
                            "wall_index": wall.index,
                            "linked_to": "gap_filler"
                        })
        
        # Re-sort
        upper_items.sort(key=lambda x: x['x_local'])
        
        # ---------------------------------------------------------
        # RULE: "Upper cabinets cannot be 2 buffers next to each other"
        # ---------------------------------------------------------
        # Strategy: Merge adjacent 'upper_narrow' (buffers) into 'upper_cabinet'.
        
        merged_items = []
        skip_indices = set()
        
        for i in range(len(upper_items)):
            if i in skip_indices: continue
            
            item = upper_items[i]
            
            # Look ahead for mergeable neighbor
            if item['type'] == 'upper_narrow':
                if i + 1 < len(upper_items):
                    next_item = upper_items[i+1]
                    # Check Type
                    if next_item['type'] == 'upper_narrow':
                        # Check Adjacency
                        # Tolerance 1cm
                        dist = next_item['x_local'] - (item['x_local'] + item['width'])
                        if abs(dist) < 1.0:
                            # MERGE!
                            # Create new Combined Cabinet
                            new_width = item['width'] + next_item['width'] # Should be 60
                            new_x = item['x_local']
                            
                            merged_items.append({
                                "type": "upper_cabinet", # Upgrade to standard
                                "x_local": new_x,
                                "width": new_width,
                                "wall_index": wall.index,
                                "linked_to": f"merged_{item.get('linked_to')}_{next_item.get('linked_to')}"
                            })
                            
                            skip_indices.add(i+1)
                            continue
            
            # If no merge happened, keep original
            merged_items.append(item)
            
        upper_items = merged_items
        
        # ---------------------------------------------------------
        # RULE: "At least two normal upper cabinets next to each other"
        # ---------------------------------------------------------
        # Corner cabinets don't count.
        # "Normal" = upper_cabinet, upper_narrow, glass_upper.
        # Hood, upper_bridge are NOT normal.
        
        normal_types = ["upper_cabinet", "upper_narrow", "glass_upper"]
        
        filtered_items = []
        
        # We need to identify "runs" of normal cabinets.
        # A run is unbroken by gaps or non-normal items.
        
        # Scan indices
        i = 0
        while i < len(upper_items):
            item = upper_items[i]
            itype = item['type']
            
            if itype in normal_types:
                # Start of a potential run
                run_indices = [i]
                
                # Look ahead
                j = i + 1
                while j < len(upper_items):
                    next_item = upper_items[j]
                    next_type = next_item['type']
                    
                    # Check types
                    if next_type not in normal_types:
                        break # End of run (type change)
                        
                    # Check Adjacency (gap check)
                    # prev_end = item['x_local'] + item['width']
                    # next_start = next_item['x_local']
                    # Tolerance 1cm
                    prev_item = upper_items[j-1]
                    prev_end = prev_item['x_local'] + prev_item['width']
                    next_start = next_item['x_local']
                    
                    if abs(next_start - prev_end) > 1.0:
                        break # End of run (gap)
                    
                    run_indices.append(j)
                    j += 1
                
                # Check Run Length
                if len(run_indices) >= 2:
                    # Keep valid run
                    for idx in run_indices:
                        filtered_items.append(upper_items[idx])
                else:
                    # Drop solitary item
                    # print(f"Dropped solitary upper at {item['x_local']}")
                    pass
                
                # Advance i to j
                i = j
            else:
                # Keep non-normal items (Hoods, Bridges, etc.) always?
                # "corner cabintes doestn count" -> assumes they stay?
                # "when the rule is not true it will not make any cabinet in that place"
                # This explicitly refers to the "normal" ones being dropped.
                # Other items (Hoods, Corners) should likely stay.
                filtered_items.append(item)
                i += 1
                
        return filtered_items
