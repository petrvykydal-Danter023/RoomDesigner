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
        
        # === PROCESS WORKBENCH (Base Line) - Direct item type pass-through ===
        # WorkflowSolver now provides actual item types (sink_cabinet, dishwasher, fridge, etc.)
        for i, vol in enumerate(workbench_vols):
            x = vol.get('x', 0)
            z = vol.get('z', 0)
            w = vol['width']
            func = vol['function']
            meta = vol.get('metadata', {})
            axis = meta.get('axis', 'X')
            height = meta.get('height', 85)
            
            # Determine if end panel is needed
            is_end = None
            if x == leftmost_x:
                is_end = 'left'
            elif x + w >= rightmost_end - 1:
                is_end = 'right'
            
            # Build item with actual function type
            item = {
                'type': func,
                'x': x,
                'z': z,
                'width': w,
                'height': height,
                'depth': 60,
                'axis': axis
            }
            
            # Add layer heights for drawer-type cabinets
            if func in ['drawer_cabinet', 'prep', 'landing', 'secondary', 'base_cabinet']:
                item['layer_heights'] = layer_heights
            
            # Add end panel info
            if is_end:
                item['is_end'] = is_end
            
            items.append(item)
        
        return items

