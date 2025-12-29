from typing import List, Dict, Any, Optional
from core.room_parser import WallSegment

class WallSolver:
    @staticmethod
    def solve(wall: WallSegment, required_items: List[str] = [], 
              layer: str = "base") -> List[Dict[str, Any]]:
        """
        Fills the available length of the wall with items.
        
        Args:
            layer: "base" or "upper" - windows only block upper layer
        """
        # Windows/doors block UPPER cabinets but NOT base cabinets
        # Base cabinets can go under windows (per blueprint)
        
        blockages = []
        
        # Corner reservations
        s_res = wall.start_reserved
        e_res = wall.end_reserved
        
        # CORNER ADAPTATION: Upper corners are usually 60x60, Base are 90x90.
        # If reservation is large (>= 90) and we are solving UPPER, reduce it to 60.
        if layer == "upper":
             if s_res >= 90: s_res = 60
             if e_res >= 90: e_res = 60
        
        if s_res > 0:
            blockages.append((0, s_res))
        if e_res > 0:
            blockages.append((wall.length - e_res, wall.length))
        
        # Features (windows/doors) - only block if layer == "upper" for windows
        for feat in wall.features:
            feat_type = feat.get('type', 'window')
            start = feat['x_start']
            end = start + feat['width']
            
            if feat_type == 'door':
                # Doors block everything
                blockages.append((start, end))
            elif feat_type == 'window' and layer == "upper":
                # Windows only block upper layer
                blockages.append((start, end))
            # For base layer, windows are NOT blockages
        
        blockages.sort(key=lambda x: x[0])
        
        # Calculate free segments
        free_segments = []
        current_x = 0
        for b_start, b_end in blockages:
            if b_start > current_x:
                free_segments.append((current_x, b_start))
            current_x = max(current_x, b_end)
        
        if current_x < wall.length:
            free_segments.append((current_x, wall.length))
        
        # If no blockages at all, entire wall is free
        if not blockages:
            free_segments = [(0, wall.length)]
        
        # Fill segments
        all_items = []
        remaining_req = required_items[:]
        
        width_map = {
            "sink": 60, "dishwasher": 60, "stove": 60,
            "fridge": 60, "base_cabinet": 60, "narrow_cabinet": 30,
            "pantry": 60, "drawer_unit": 60, "drawer_unit_90": 90
        }

        for seg_start, seg_end in free_segments:
            seg_len = seg_end - seg_start
            if seg_len < 30:
                continue
                
            current_seg_x = seg_start
            
            # Required items first
            
            conflicts = {
                "stove": ["sink", "dishwasher"],
                "sink": ["stove", "fridge", "pantry"],
                "dishwasher": ["stove"],
                "fridge": ["sink"],
                "pantry": ["sink"]
            }
            
            i = 0
            while i < len(remaining_req):
                req = remaining_req[i]
                w = width_map.get(req, 60)
                
                # Check Conflict with LAST item placed in this segment
                last_item_type = None
                if all_items:
                    last = all_items[-1]
                    if last['wall_index'] == wall.index and abs((last['x_local'] + last['width'] - current_seg_x)) < 1:
                        last_item_type = last['type']
                
                # Check logic
                needs_spacer = False
                if last_item_type:
                    # Strip suffix strictly for conflict check if needed? 
                    # "drawer_unit_90" -> "drawer_unit". Conflict map keys are standard.
                    # Drawer unit usually has no conflicts.
                    req_base = "drawer_unit" if "drawer_unit" in req else req
                    last_base = "drawer_unit" if "drawer_unit" in str(last_item_type) else last_item_type
                    
                    bad_neighbors = conflicts.get(req_base, [])
                    if last_base in bad_neighbors: needs_spacer = True
                    bad_neighbors_prev = conflicts.get(last_base, [])
                    if req_base in bad_neighbors_prev: needs_spacer = True
                
                # WINDOW CHECK For TALL items
                # Pantry, Fridge, FridgeSpacer are Tall (200cm). Window usually starts at 100cm. Collision!
                # Base cabinets (Sink, Dishwasher, Drawer) are ~90cm. OK under window.
                is_tall = req in ["fridge", "pantry", "fridge_spacer"]
                
                overlaps_window = False
                if is_tall:
                    item_start = current_seg_x
                    item_end = current_seg_x + w
                    for feat in wall.features:
                        if feat.get('type') == 'window':
                            w_start = feat['x_start']
                            w_end = w_start + feat['width']
                            # Check overlap
                            if max(item_start, w_start) < min(item_end, w_end):
                                overlaps_window = True
                                break
                
                if overlaps_window:
                    # Skip this item for this position
                    i += 1
                    continue

                # Try placing Spacer if needed
                if needs_spacer:
                    spacing_w = 30
                    if current_seg_x + spacing_w + w <= seg_end:
                        # Determine spacer type
                        spacer_type = "narrow_cabinet"
                        if "fridge" in [last_item_type, req]:
                             spacer_type = "fridge_spacer"
                        
                        # OVERRIDE: If Sink involved, Spacer MUST be Low (Base)
                        # Sink cannot be next to something tall (even a spacer).
                        if "sink" in [last_item_type, req]:
                            spacer_type = "narrow_cabinet"

                        # Validate Spacer vs Window (if Tall)
                        if spacer_type == "fridge_spacer":
                            s_start = current_seg_x; s_end = current_seg_x + spacing_w
                            for feat in wall.features:
                                if feat.get('type') == 'window':
                                    ws = feat['x_start']; we = ws + feat['width']
                                    if max(s_start, ws) < min(s_end, we):
                                        # Spacer hits window! Downgrade to base spacer.
                                        spacer_type = "narrow_cabinet"
                                        break
                                         
                        all_items.append({
                            "type": spacer_type, 
                            "x_local": current_seg_x,
                            "width": spacing_w,
                            "wall_index": wall.index,
                            "is_spacer": True
                        })
                        current_seg_x += spacing_w
                    else:
                        i += 1
                        continue
                
                # Place Item
                if current_seg_x + w <= seg_end:
                    final_type = req
                    if req == "drawer_unit_90": final_type = "drawer_unit"
                    
                    all_items.append({
                        "type": final_type,
                        "x_local": current_seg_x,
                        "width": w,
                        "wall_index": wall.index
                    })
                    current_seg_x += w
                    remaining_req.pop(i) 
                    i = 0 # Success! Restart scan to see if skipped items fit now
                else:
                    i += 1
            
            # Fill with cabinets
            while current_seg_x + 30 <= seg_end:
                if current_seg_x + 60 <= seg_end:
                    w, itype = 60, "base_cabinet"
                else:
                    w, itype = 30, "narrow_cabinet"
                
                all_items.append({
                    "type": itype,
                    "x_local": current_seg_x,
                    "width": w,
                    "wall_index": wall.index
                })
                current_seg_x += w
                
        return all_items
