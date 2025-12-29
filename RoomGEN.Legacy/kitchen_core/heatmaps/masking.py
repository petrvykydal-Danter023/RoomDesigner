"""
CollisionMask - Hard/Soft collision detection for placement validation.

Hard mask: Binary blocking (0=free, 1=occupied) - used for final validation
Soft mask: Float penalties (gradient) - used for optimization & debugging
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class CollisionMask:
    """
    Dual-layer collision detection system.
    
    - hard_mask: Binary, blocks placement completely
    - soft_mask: Float, adds penalties for near-collisions
    """
    hard_mask: np.ndarray  # Binary: 0=free, 1=blocked
    soft_mask: np.ndarray  # Float: penalty gradient
    room_width: int
    
    @classmethod
    def create(cls, room_width: int) -> 'CollisionMask':
        """Create empty collision mask for room."""
        return cls(
            hard_mask=np.zeros(room_width, dtype=np.int8),
            soft_mask=np.zeros(room_width, dtype=np.float64),
            room_width=room_width
        )
    
    def copy(self) -> 'CollisionMask':
        """Create deep copy of mask."""
        return CollisionMask(
            hard_mask=self.hard_mask.copy(),
            soft_mask=self.soft_mask.copy(),
            room_width=self.room_width
        )
    
    def mark_occupied(
        self, 
        start_cm: int, 
        end_cm: int, 
        include_door_swing: bool = True,
        door_swing_cm: int = 45,
        door_swing_penalty: float = 0.5
    ) -> 'CollisionMask':
        """
        Mark cells as occupied.
        
        Args:
            start_cm: Start position
            end_cm: End position
            include_door_swing: Whether to add soft penalty for door opening zone
            door_swing_cm: Door swing zone width
            door_swing_penalty: Penalty value for soft mask
        
        Returns:
            Self for chaining
        """
        # Clamp to valid range
        start = max(0, start_cm)
        end = min(self.room_width, end_cm)
        
        # Hard block the occupied cells
        self.hard_mask[start:end] = 1
        
        # Add soft penalty for door swing zone
        if include_door_swing:
            # Soft penalty extends beyond the item (door opens into room)
            # This is for TrafficLayer integration
            swing_start = max(0, start - door_swing_cm)
            swing_end = min(self.room_width, end + door_swing_cm)
            self.soft_mask[swing_start:swing_end] += door_swing_penalty
        
        return self
    
    def mark_utility_zone(self, center_cm: int, radius_cm: int) -> 'CollisionMask':
        """Mark utility (water, gas) zone - can be near but not on top."""
        start = max(0, center_cm - radius_cm)
        end = min(self.room_width, center_cm + radius_cm)
        # Don't hard-block, just soft penalty (can place near, better not on)
        self.soft_mask[start:end] += 0.3
        return self
    
    def is_valid_placement(self, start_cm: int, width: int) -> bool:
        """
        Check if placement is valid (no hard collision).
        
        Returns:
            True if no overlap with hard-blocked cells
        """
        end = start_cm + width
        if start_cm < 0 or end > self.room_width:
            return False
        return np.sum(self.hard_mask[start_cm:end]) == 0
    
    def get_penalty(self, start_cm: int, width: int) -> float:
        """
        Get soft penalty for placement.
        
        Returns:
            Sum of soft mask values in placement range
        """
        end = min(self.room_width, start_cm + width)
        start = max(0, start_cm)
        return float(np.sum(self.soft_mask[start:end]))
    
    def get_blocking_mask(self) -> np.ndarray:
        """Get binary mask for GridMap.apply_mask()."""
        return self.hard_mask
