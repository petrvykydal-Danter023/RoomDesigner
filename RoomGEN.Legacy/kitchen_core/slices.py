"""
Slice Tile System for Premium Kitchen Architecture V3.

Implements WFC-inspired composition where cabinets are defined as vertical "slices"
with specific seam positions. Adjacent slices must have matching seam heights.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Set, Optional, Dict
from .layers import LayerSchema, LayerPreset
import random

@dataclass
class SliceTile:
    """
    A vertical slice representing one cabinet module with defined layer structure.
    """
    width: int  # 20, 30, 40, 60, 80
    layer_schema: LayerSchema
    function: str  # 'storage', 'sink', 'cooktop', 'appliance'
    
    # Content details
    has_internals: bool = True  # Shelves, drawers, etc.
    is_appliance_housing: bool = False  # Dishwasher, oven opening
    
    @property
    def seam_heights(self) -> Tuple[int, ...]:
        return self.layer_schema.seam_heights
    
    def compatible_with(self, other: 'SliceTile') -> bool:
        """Check if this tile can be placed next to another."""
        return self.seam_heights == other.seam_heights


# === TILE LIBRARY ===

def create_tile_library(layer_schema: LayerSchema) -> List[SliceTile]:
    """
    Creates a library of compatible tiles based on the given layer schema.
    All tiles in the library will have matching seam heights.
    """
    tiles = []
    
    # Standard widths
    for width in [20, 30, 40, 60, 80]:
        # Storage tile
        tiles.append(SliceTile(
            width=width,
            layer_schema=layer_schema,
            function='storage',
            has_internals=True
        ))
    
    # Dishwasher (60cm only, full height opening)
    dw_schema = LayerSchema.full_door(85)
    tiles.append(SliceTile(
        width=60,
        layer_schema=dw_schema,
        function='appliance',
        has_internals=False,
        is_appliance_housing=True
    ))
    
    return tiles


@dataclass
class SliceSequence:
    """
    A valid sequence of slice tiles that fill a zone.
    """
    tiles: List[SliceTile] = field(default_factory=list)
    
    @property
    def total_width(self) -> int:
        return sum(t.width for t in self.tiles)
    
    def is_seam_consistent(self) -> bool:
        """Check if all tiles have consistent seam heights."""
        if not self.tiles:
            return True
        reference = self.tiles[0].seam_heights
        return all(t.seam_heights == reference for t in self.tiles)


class SliceComposer:
    """
    WFC-inspired algorithm to fill a zone with compatible slice tiles.
    """
    
    def __init__(self, target_width: int, layer_schema: LayerSchema):
        self.target_width = target_width
        self.layer_schema = layer_schema
        self.tile_library = create_tile_library(layer_schema)
        
    def compose(self, required_functions: List[str] = None) -> Optional[SliceSequence]:
        """
        Fill the target width with compatible tiles.
        
        Args:
            required_functions: Functions that must be included (e.g., ['sink', 'cooktop'])
        """
        required_functions = required_functions or []
        sequence = SliceSequence()
        remaining_width = self.target_width
        
        # Phase 1: Place required function tiles first
        for func in required_functions:
            matching_tiles = [t for t in self.tile_library if t.function == func]
            if matching_tiles:
                tile = self._select_best_tile(matching_tiles, remaining_width)
                if tile:
                    sequence.tiles.append(tile)
                    remaining_width -= tile.width
        
        # Phase 2: Fill remaining space with storage tiles
        storage_tiles = [t for t in self.tile_library if t.function == 'storage']
        
        while remaining_width > 0:
            valid_tiles = [t for t in storage_tiles if t.width <= remaining_width]
            
            if not valid_tiles:
                # Can't fill exactly - need filler
                if remaining_width >= 5:
                    # Create custom filler tile
                    filler = SliceTile(
                        width=remaining_width,
                        layer_schema=self.layer_schema,
                        function='filler',
                        has_internals=False
                    )
                    sequence.tiles.append(filler)
                remaining_width = 0
                break
            
            # Prefer larger tiles for efficiency
            tile = max(valid_tiles, key=lambda t: t.width)
            sequence.tiles.append(tile)
            remaining_width -= tile.width
        
        return sequence if sequence.is_seam_consistent() else None
    
    def _select_best_tile(self, tiles: List[SliceTile], max_width: int) -> Optional[SliceTile]:
        """Select the best fitting tile from options."""
        valid = [t for t in tiles if t.width <= max_width]
        if not valid:
            return None
        # Prefer standard widths: 60 > 80 > 40 > others
        priority = {60: 0, 80: 1, 40: 2, 30: 3, 20: 4}
        return min(valid, key=lambda t: priority.get(t.width, 10))
