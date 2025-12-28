"""
Premium Skin for Premium Kitchen Architecture V3.

Uses Layer Grid and Slice Composition for professional "půl milionu" look.
"""

from typing import List, Dict, Any
from .base import Skin
from ..layers import LayerSchema, get_dominant_layer_schema
from ..slices import SliceComposer, SliceSequence

class PremiumSkin(Skin):
    """
    Premium skin that generates cabinets with:
    - Consistent seam lines (Layer Grid)
    - Gola profiles (handleless)
    - Recessed plinths
    - Shadow gaps
    - End panels
    """
    
    def apply(self, skeleton: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert functional volumes into premium cabinet items with layer alignment.
        """
        volumes = skeleton['volumes']
        items = []
        
        # Determine dominant layer schema based on workbench width
        workbench_vols = [v for v in volumes if not v.get('metadata', {}).get('is_monolith')]
        monolith_vols = [v for v in volumes if v.get('metadata', {}).get('is_monolith')]
        
        # Calculate layer schema for workbench
        workbench_widths = [v['width'] for v in workbench_vols]
        layer_schema = get_dominant_layer_schema(workbench_widths)
        layer_heights = layer_schema.layer_heights
        
        print(f"  Layer Schema: {layer_schema.preset.value} -> Heights: {layer_heights}")
        
        # Track positions for end panel detection
        all_x_positions = sorted([v['x'] for v in volumes])
        leftmost_x = min(all_x_positions) if all_x_positions else 0
        rightmost_end = max(v['x'] + v['width'] for v in volumes) if volumes else 0
        
        # === PROCESS MONOLITH (Tall Block) - May be on Z axis for L-shape ===
        for i, vol in enumerate(monolith_vols):
            x = vol.get('x', 0)
            z = vol.get('z', 0)  # Z position for L-shape Arm B
            w = vol['width']
            func = vol['function']
            meta = vol.get('metadata', {})
            height = meta.get('height', 215)
            axis = meta.get('axis', 'X')  # 'X' for Arm A, 'Z' for Arm B
            
            # Determine if this is an edge item
            is_end = None
            if axis == 'X':
                if x == leftmost_x:
                    is_end = 'left'
                elif x + w >= rightmost_end - 1:
                    is_end = 'right'
            
            items.append({
                'type': func,
                'x': x,
                'z': z,  # Z position for Arm B
                'width': w,
                'height': height,
                'depth': 60,
                'is_end': is_end,
                'is_monolith': True,
                'axis': axis  # 'X' or 'Z' - tells generator which orientation
            })
        
        # === PROCESS WORKBENCH (Base Line) - handles both Arm A (X) and Arm B (Z) ===
        for i, vol in enumerate(workbench_vols):
            x = vol.get('x', 0)
            z = vol.get('z', 0)
            w = vol['width']
            func = vol['function']
            meta = vol.get('metadata', {})
            axis = meta.get('axis', 'X')  # Check if this is Arm B
            
            # For Arm B items, use z as position
            if axis == 'Z':
                # Arm B base cabinet - rotated orientation
                items.append({
                    'type': 'drawer_cabinet',
                    'x': 0,
                    'z': z,
                    'width': w,
                    'height': 85,
                    'depth': 60,
                    'axis': 'Z'
                })
                continue
            
            current_x = x
            remaining_w = w
            
            # Is this the first or last in workbench?
            is_first = (i == 0)
            is_last = (i == len(workbench_vols) - 1)
            
            # === ZONE-SPECIFIC LOGIC ===
            
            if func == 'wet':
                # Sink (80) + DW (60)
                if remaining_w >= 80:
                    is_end = 'left' if is_first and current_x == leftmost_x else None
                    items.append({
                        'type': 'sink_cabinet',
                        'x': current_x,
                        'width': 80,
                        'height': 85,
                        'depth': 60,
                        'layer_heights': [20, 20, 45],  # False drawer + door
                        'is_end': is_end
                    })
                    current_x += 80
                    remaining_w -= 80
                
                if remaining_w >= 60:
                    items.append({
                        'type': 'dishwasher',
                        'x': current_x,
                        'width': 60,
                        'height': 85,
                        'depth': 60
                    })
                    current_x += 60
                    remaining_w -= 60
            
            elif func == 'cooking':
                if remaining_w >= 60:
                    items.append({
                        'type': 'stove_cabinet',
                        'x': current_x,
                        'width': 60,
                        'height': 85,
                        'depth': 60,
                        'layer_heights': layer_heights
                    })
                    current_x += 60
                    remaining_w -= 60
                    
                    # Add hood above
                    items.append({
                        'type': 'hood',
                        'x': current_x - 60,
                        'width': 60,
                        'height': 40,
                        'depth': 35,
                        'y': 160
                    })
            
            # === FILL REMAINING WITH LAYER-ALIGNED CABINETS ===
            
            while remaining_w > 0:
                # Prefer 60cm for visual consistency
                if remaining_w >= 60:
                    cab_w = 60
                elif remaining_w >= 40:
                    cab_w = 40
                elif remaining_w >= 30:
                    cab_w = 30
                elif remaining_w >= 20:
                    cab_w = 20
                else:
                    # Filler
                    items.append({
                        'type': 'filler',
                        'x': current_x,
                        'width': remaining_w,
                        'height': 85,
                        'depth': 60
                    })
                    break
                
                # Determine end panel
                is_end = None
                if is_last and remaining_w - cab_w < 5:
                    if current_x + cab_w >= rightmost_end - 1:
                        is_end = 'right'
                
                items.append({
                    'type': 'drawer_cabinet',
                    'x': current_x,
                    'width': cab_w,
                    'height': 85,
                    'depth': 60,
                    'layer_heights': layer_heights,
                    'is_end': is_end
                })
                current_x += cab_w
                remaining_w -= cab_w
        
        return items
