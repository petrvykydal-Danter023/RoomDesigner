"""
Layer Grid System for Premium Kitchen Architecture V3.

Defines horizontal "seam lines" that all cabinet fronts must align to.
This creates the professional "expensive" look where drawer heights are consistent.
"""

from dataclasses import dataclass
from typing import List, Tuple
from enum import Enum

class LayerPreset(Enum):
    """Standard layer configurations used in premium kitchens."""
    EQUAL_3 = "equal_3"      # 3 equal drawers
    EQUAL_4 = "equal_4"      # 4 equal drawers
    GRADUATED = "graduated"   # Small top, larger bottom
    DOOR_2DRAWER = "door_2d" # Door + 2 drawers
    FULL_DOOR = "full_door"  # Single door

@dataclass
class LayerSchema:
    """
    Defines horizontal seam positions for a cabinet column.
    Heights are measured from cabinet bottom (0) to top (typically 85cm for base).
    """
    seam_heights: Tuple[int, ...]  # Heights where seams occur
    content_types: Tuple[str, ...]  # What's in each layer ('drawer', 'door', 'internals')
    preset: LayerPreset
    
    @property
    def num_layers(self) -> int:
        return len(self.seam_heights)
    
    @property
    def layer_heights(self) -> List[int]:
        """Returns the height of each layer."""
        heights = []
        prev = 0
        for h in self.seam_heights:
            heights.append(h - prev)
            prev = h
        return heights
    
    # === STANDARD PRESETS ===
    
    @classmethod
    def equal_3_drawer(cls, total_height: int = 85) -> 'LayerSchema':
        """3 equal drawers - most common premium look."""
        h = total_height // 3
        return cls(
            seam_heights=(h, h*2, total_height),
            content_types=('drawer', 'drawer', 'drawer'),
            preset=LayerPreset.EQUAL_3
        )
    
    @classmethod
    def equal_4_drawer(cls, total_height: int = 85) -> 'LayerSchema':
        """4 equal drawers - very modern look."""
        h = total_height // 4
        return cls(
            seam_heights=(h, h*2, h*3, total_height),
            content_types=('drawer', 'drawer', 'drawer', 'drawer'),
            preset=LayerPreset.EQUAL_4
        )
    
    @classmethod
    def graduated(cls, total_height: int = 85) -> 'LayerSchema':
        """Graduated: small top drawer, larger bottom drawers."""
        # 15cm top, then two equal below
        top = 15
        remaining = total_height - top
        mid = top + remaining // 2
        return cls(
            seam_heights=(top, mid, total_height),
            content_types=('drawer', 'drawer', 'drawer'),
            preset=LayerPreset.GRADUATED
        )
    
    @classmethod
    def door_with_2_drawers(cls, total_height: int = 85) -> 'LayerSchema':
        """Door on bottom, 2 drawers on top (under-sink style)."""
        drawer_h = 15
        return cls(
            seam_heights=(drawer_h, drawer_h * 2, total_height),
            content_types=('drawer', 'drawer', 'door'),
            preset=LayerPreset.DOOR_2DRAWER
        )
    
    @classmethod
    def full_door(cls, total_height: int = 85) -> 'LayerSchema':
        """Single full-height door."""
        return cls(
            seam_heights=(total_height,),
            content_types=('door',),
            preset=LayerPreset.FULL_DOOR
        )


def layers_compatible(schema_a: LayerSchema, schema_b: LayerSchema) -> bool:
    """
    Check if two layer schemas can be neighbors.
    For premium look, seam heights must align perfectly.
    """
    # Extract common seams (heights that appear in both)
    seams_a = set(schema_a.seam_heights)
    seams_b = set(schema_b.seam_heights)
    
    # For strict alignment: all seams must match
    # For flexible: at least key seams (e.g., 28cm line) must match
    
    # Strict mode for premium:
    return seams_a == seams_b


def get_dominant_layer_schema(cabinet_widths: List[int], total_height: int = 85) -> LayerSchema:
    """
    Determines the best layer schema for a row of cabinets.
    Wider cabinets (60-80cm) prefer 3-drawer.
    Narrow cabinets (20-40cm) prefer full door or 4-drawer.
    """
    avg_width = sum(cabinet_widths) / len(cabinet_widths) if cabinet_widths else 60
    
    if avg_width >= 60:
        return LayerSchema.equal_3_drawer(total_height)
    elif avg_width >= 40:
        return LayerSchema.graduated(total_height)
    else:
        return LayerSchema.equal_4_drawer(total_height)
