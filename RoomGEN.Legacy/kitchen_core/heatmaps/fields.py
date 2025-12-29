"""
Dynamic Field Emitters - Attractors and Repulsors between items.

Items emit fields that influence placement of other items:
- Attractors: Pull related items closer (sink <-> dishwasher)
- Repulsors: Push conflicting items apart (stove <-> fridge)
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
import numpy as np
from .grid import GridMap


# Predefined attraction relationships
# (source, target): {sigma_cm, amplitude}
ATTRACTIONS: Dict[Tuple[str, str], Dict[str, float]] = {
    # Sink attracts dishwasher strongly (plumbing efficiency)
    ('sink_cabinet', 'dishwasher'): {'sigma_cm': 60, 'amplitude': 150},
    ('sink', 'dishwasher'): {'sigma_cm': 60, 'amplitude': 150},
    
    # Stove attracts hood (must be above)
    ('stove_cabinet', 'hood'): {'sigma_cm': 30, 'amplitude': 200},
    ('stove', 'hood'): {'sigma_cm': 30, 'amplitude': 200},
    
    # Prep zone likes being near sink
    ('sink_cabinet', 'drawer_cabinet'): {'sigma_cm': 80, 'amplitude': 50},
    ('sink_cabinet', 'prep'): {'sigma_cm': 80, 'amplitude': 50},
    
    # Oven tower likes being near stove
    ('stove_cabinet', 'oven_tower'): {'sigma_cm': 100, 'amplitude': 40},
}


# Predefined repulsion relationships
# (source, target): {sigma_cm, amplitude} (amplitude should be negative)
REPULSIONS: Dict[Tuple[str, str], Dict[str, float]] = {
    # Stove repels fridge (heat damages compressor)
    ('stove_cabinet', 'fridge'): {'sigma_cm': 80, 'amplitude': -100},
    ('stove', 'fridge'): {'sigma_cm': 80, 'amplitude': -100},
    
    # Stove repels window (fire hazard, curtains, grease)
    ('stove_cabinet', 'window'): {'sigma_cm': 50, 'amplitude': -300},
    ('stove', 'window'): {'sigma_cm': 50, 'amplitude': -300},
    
    # Fridge repels stove (symmetrical)
    ('fridge', 'stove_cabinet'): {'sigma_cm': 80, 'amplitude': -100},
    ('fridge', 'stove'): {'sigma_cm': 80, 'amplitude': -100},
    
    # Tall items repel each other (visual balance)
    ('fridge', 'pantry'): {'sigma_cm': 60, 'amplitude': -30},
    ('fridge', 'oven_tower'): {'sigma_cm': 60, 'amplitude': -30},
}


@dataclass
class FieldEmitter:
    """
    Represents a placed item that emits influence fields.
    """
    position: int  # Center position in cm
    width: int  # Item width in cm
    item_type: str  # 'sink', 'stove', etc.
    
    @property
    def start(self) -> int:
        """Left edge of item."""
        return self.position
    
    @property
    def end(self) -> int:
        """Right edge of item."""
        return self.position + self.width
    
    @property
    def center(self) -> int:
        """Center of item."""
        return self.position + self.width // 2
    
    def get_attraction_for(self, target_type: str, room_width: int) -> Optional[GridMap]:
        """
        Generate attraction field for target item type.
        
        Returns:
            GridMap with attraction values, or None if no relationship
        """
        # Check both normalized names
        key1 = (self.item_type, target_type)
        key2 = (self._normalize_type(self.item_type), self._normalize_type(target_type))
        
        params = ATTRACTIONS.get(key1) or ATTRACTIONS.get(key2)
        if not params:
            return None
        
        grid = GridMap.zeros(room_width)
        grid.add_gaussian(
            center_cm=self.center,
            sigma_cm=params['sigma_cm'],
            amplitude=params['amplitude']
        )
        return grid
    
    def get_repulsion_for(self, target_type: str, room_width: int) -> Optional[GridMap]:
        """
        Generate repulsion field for target item type.
        
        Returns:
            GridMap with repulsion values, or None if no relationship
        """
        key1 = (self.item_type, target_type)
        key2 = (self._normalize_type(self.item_type), self._normalize_type(target_type))
        
        params = REPULSIONS.get(key1) or REPULSIONS.get(key2)
        if not params:
            return None
        
        grid = GridMap.zeros(room_width)
        grid.add_gaussian(
            center_cm=self.center,
            sigma_cm=params['sigma_cm'],
            amplitude=params['amplitude']  # Already negative
        )
        return grid
    
    def get_combined_field_for(self, target_type: str, room_width: int) -> GridMap:
        """
        Get combined attraction + repulsion field for target.
        
        Returns:
            GridMap with combined field values
        """
        grid = GridMap.zeros(room_width)
        
        attraction = self.get_attraction_for(target_type, room_width)
        if attraction:
            grid.data += attraction.data
        
        repulsion = self.get_repulsion_for(target_type, room_width)
        if repulsion:
            grid.data += repulsion.data
        
        return grid
    
    @staticmethod
    def _normalize_type(item_type: str) -> str:
        """Normalize item type for lookup (e.g., sink_cabinet -> sink)."""
        mappings = {
            'sink_cabinet': 'sink',
            'stove_cabinet': 'stove',
            'drawer_cabinet': 'prep',
            'base_cabinet': 'prep',
        }
        return mappings.get(item_type, item_type)


def compute_dynamic_fields(
    placed_emitters: List[FieldEmitter],
    target_type: str,
    room_width: int
) -> GridMap:
    """
    Compute combined dynamic field from all placed emitters for target item.
    
    Args:
        placed_emitters: List of already-placed items as FieldEmitters
        target_type: Type of item being placed
        room_width: Room width in cm
    
    Returns:
        Combined GridMap with all attraction/repulsion fields
    """
    grid = GridMap.zeros(room_width)
    
    for emitter in placed_emitters:
        field = emitter.get_combined_field_for(target_type, room_width)
        grid.data += field.data
    
    return grid
