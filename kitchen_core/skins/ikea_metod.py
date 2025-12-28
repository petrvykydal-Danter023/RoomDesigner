from typing import List, Dict, Any
from .base import Skin

class IkeaSkin(Skin):
    """
    IKEA Metod kitchen skin - translates functional zones into specific cabinet modules.
    Supports: base cabinets, drawers, sink, dishwasher, stove/cooktop, fridge, pantry, 
    corner cabinet, wall cabinets, hood, oven, and fillers.
    """
    
    # Standard IKEA Metod widths (cm)
    STANDARD_WIDTHS = [80, 60, 40, 30, 20]
    
    # Cabinet type preferences by zone function
    ZONE_CABINET_PRIORITY = {
        'prep': ['drawer_cabinet', 'base_cabinet'],
        'storage': ['base_cabinet', 'drawer_cabinet'],
        'wet': ['sink_cabinet', 'dishwasher'],
        'cooking': ['stove_cabinet', 'oven'],
        'fridge': ['fridge'],
        'pantry': ['pantry'],
    }
    
    def apply(self, skeleton: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split functional volumes into IKEA modules with intelligent type selection.
        """
        volumes = skeleton['volumes']
        items = []
        
        for vol in volumes:
            x = vol['x']
            w = vol['width']
            func = vol['function']
            meta = vol.get('metadata', {})
            
            current_x = x
            remaining_w = w
            
            # ========== ZONE-SPECIFIC LOGIC ==========
            
            if func == 'wet':
                # Wet Zone: Sink (60-80) + Dishwasher (60) + optional storage
                if remaining_w >= 80:
                    items.append({'type': 'sink_cabinet', 'width': 80, 'x': current_x, 'height': 85})
                    current_x += 80
                    remaining_w -= 80
                elif remaining_w >= 60:
                    items.append({'type': 'sink_cabinet', 'width': 60, 'x': current_x, 'height': 85})
                    current_x += 60
                    remaining_w -= 60
                
                if remaining_w >= 60:
                    items.append({'type': 'dishwasher', 'width': 60, 'x': current_x, 'height': 85})
                    current_x += 60
                    remaining_w -= 60
            
            elif func == 'cooking':
                # Cooking Zone: Stove/Cooktop (60-90) + optionally Oven (60)
                if remaining_w >= 90:
                    items.append({'type': 'stove_cabinet', 'width': 90, 'x': current_x, 'height': 85})
                    current_x += 90
                    remaining_w -= 90
                elif remaining_w >= 60:
                    items.append({'type': 'stove_cabinet', 'width': 60, 'x': current_x, 'height': 85})
                    current_x += 60
                    remaining_w -= 60
                
                # Add oven if space allows (built-in under cooktop requires tall cabinet)
                # For now, skip oven in base layer - would need separate tall unit logic
            
            elif func == 'fridge':
                # Fridge is a single tall unit
                fridge_h = meta.get('height', 200)
                items.append({'type': 'fridge', 'width': remaining_w, 'x': current_x, 'height': fridge_h, 'depth': 60})
                remaining_w = 0
            
            elif func == 'pantry':
                # Tall pantry unit
                pantry_h = meta.get('height', 200)
                items.append({'type': 'pantry', 'width': remaining_w, 'x': current_x, 'height': pantry_h, 'depth': 60})
                remaining_w = 0
            
            elif func == 'corner':
                # Corner cabinet (L-shaped, typical 90x90)
                items.append({'type': 'corner_cabinet', 'width': min(remaining_w, 90), 'x': current_x, 'height': 85, 'depth': 90})
                remaining_w = 0
            
            # ========== FILL REMAINING SPACE ==========
            
            while remaining_w > 0:
                placed = False
                
                # Try drawer cabinets for wider spaces (preferred for prep)
                if remaining_w >= 80:
                    items.append({'type': 'drawer_cabinet', 'width': 80, 'x': current_x, 'height': 85, 'num_drawers': 4})
                    current_x += 80
                    remaining_w -= 80
                    placed = True
                elif remaining_w >= 60:
                    # Alternate between drawers and cabinets for visual variety
                    item_type = 'drawer_cabinet' if len(items) % 2 == 0 else 'base_cabinet'
                    items.append({'type': item_type, 'width': 60, 'x': current_x, 'height': 85, 'num_drawers': 3})
                    current_x += 60
                    remaining_w -= 60
                    placed = True
                elif remaining_w >= 40:
                    items.append({'type': 'base_cabinet', 'width': 40, 'x': current_x, 'height': 85})
                    current_x += 40
                    remaining_w -= 40
                    placed = True
                elif remaining_w >= 30:
                    # Narrow pull-out (spice rack style)
                    items.append({'type': 'bottle_rack', 'width': 30, 'x': current_x, 'height': 85, 'num_drawers': 5})
                    current_x += 30
                    remaining_w -= 30
                    placed = True
                elif remaining_w >= 20:
                    items.append({'type': 'bottle_rack', 'width': 20, 'x': current_x, 'height': 85, 'num_drawers': 5})
                    current_x += 20
                    remaining_w -= 20
                    placed = True
                elif remaining_w >= 5:
                    # Small filler panel
                    items.append({'type': 'filler', 'width': remaining_w, 'x': current_x, 'height': 85})
                    current_x += remaining_w
                    remaining_w = 0
                    placed = True
                else:
                    # Tiny gap - ignore
                    remaining_w = 0
                    placed = True
        
        # ========== WALL ITEMS ==========
        
        wall_wishlist = skeleton.get('wall_wishlist', [])
        
        # Process wall items (simplified: place above corresponding base items)
        for wall_item in wall_wishlist:
            item_type = wall_item.get('type', 'wall_cabinet')
            width = wall_item.get('width', 60)
            
            if item_type == 'hood':
                # Hood goes above stove
                stove_items = [i for i in items if 'stove' in i.get('type', '')]
                if stove_items:
                    stove_x = stove_items[0]['x']
                    items.append({
                        'type': 'hood',
                        'width': width,
                        'x': stove_x + (stove_items[0]['width'] - width) / 2,  # Center above stove
                        'height': 40,
                        'depth': 35,
                        'y': 160  # Wall height
                    })
            else:
                # Generic wall cabinet - place in first available spot
                items.append({
                    'type': 'wall_cabinet',
                    'width': width,
                    'x': wall_item.get('x', 0),
                    'height': wall_item.get('height', 70),
                    'depth': 35,
                    'y': 145  # Standard wall cabinet height
                })
        
        return items
