"""
GridMap - Core heatmap data structure with NumPy operations.

Resolution: 1cm per cell for precise gradients.
Uses np.convolve for efficient width-based position scanning.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import numpy as np


@dataclass
class GridMap:
    """
    1D heatmap for kitchen placement scoring.
    
    Each cell represents 1cm. Higher values = better placement.
    """
    data: np.ndarray
    room_width: int  # Total width in cm
    
    @classmethod
    def create(cls, room_width: int, initial_value: float = 0.0) -> 'GridMap':
        """Create a new GridMap with given width and initial value."""
        return cls(
            data=np.full(room_width, initial_value, dtype=np.float64),
            room_width=room_width
        )
    
    @classmethod
    def zeros(cls, room_width: int) -> 'GridMap':
        """Create a zero-filled GridMap."""
        return cls.create(room_width, 0.0)
    
    @classmethod
    def ones(cls, room_width: int, value: float = 1.0) -> 'GridMap':
        """Create a GridMap filled with given value."""
        return cls.create(room_width, value)
    
    def copy(self) -> 'GridMap':
        """Create a deep copy of this GridMap."""
        return GridMap(data=self.data.copy(), room_width=self.room_width)
    
    def gaussian_field(self, center_cm: int, sigma_cm: float, amplitude: float) -> np.ndarray:
        """
        Generate Gaussian (bell curve) field centered at position.
        
        Args:
            center_cm: Center position in cm
            sigma_cm: Standard deviation (spread) in cm
            amplitude: Peak amplitude (positive = attractor, negative = repulsor)
        
        Returns:
            Array of field values to add to grid
        """
        indices = np.arange(self.room_width)
        return amplitude * np.exp(-0.5 * ((indices - center_cm) / sigma_cm) ** 2)
    
    def add_gaussian(self, center_cm: int, sigma_cm: float, amplitude: float) -> 'GridMap':
        """Add Gaussian field to this grid (in-place). Returns self for chaining."""
        self.data += self.gaussian_field(center_cm, sigma_cm, amplitude)
        return self
    
    def apply_penalty_range(self, start_cm: int, end_cm: int, value: float) -> 'GridMap':
        """Apply flat penalty/bonus to a range. Returns self for chaining."""
        start = max(0, start_cm)
        end = min(self.room_width, end_cm)
        self.data[start:end] += value
        return self
    
    def apply_mask(self, mask: np.ndarray, penalty: float = -10000) -> 'GridMap':
        """Apply binary mask (1 = blocked, 0 = free). Returns self for chaining."""
        self.data = np.where(mask > 0, penalty, self.data)
        return self
    
    def find_best_position(self, item_width: int) -> int:
        """
        Find best position for item of given width using np.convolve.
        
        Uses convolution with uniform kernel to sum scores across item width.
        O(n) vectorized operation - very fast.
        
        Returns:
            Best starting position in cm
        """
        if item_width >= self.room_width:
            return 0
        
        kernel = np.ones(item_width)
        scores = np.convolve(self.data, kernel, mode='valid')
        return int(np.argmax(scores))
    
    def find_top_k_positions(self, item_width: int, k: int = 3) -> List[Tuple[int, float]]:
        """
        Find top-k positions for item of given width.
        
        Returns:
            List of (position_cm, score) tuples, sorted by score descending
        """
        if item_width >= self.room_width:
            return [(0, float(np.sum(self.data)))]
        
        kernel = np.ones(item_width)
        scores = np.convolve(self.data, kernel, mode='valid')
        
        # Get indices of top-k scores
        if len(scores) <= k:
            top_indices = np.argsort(scores)[::-1]
        else:
            # Use argpartition for efficiency, then sort the top-k
            top_indices = np.argpartition(scores, -k)[-k:]
            top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
        
        return [(int(idx), float(scores[idx])) for idx in top_indices]
    
    def __add__(self, other: 'GridMap') -> 'GridMap':
        """Add two GridMaps together."""
        return GridMap(data=self.data + other.data, room_width=self.room_width)
    
    def __mul__(self, scalar: float) -> 'GridMap':
        """Scale GridMap by scalar."""
        return GridMap(data=self.data * scalar, room_width=self.room_width)
    
    def __rmul__(self, scalar: float) -> 'GridMap':
        """Scale GridMap by scalar (right multiply)."""
        return self.__mul__(scalar)


# Corner module sizes
CORNER_SIZES = {
    'blind': 65,
    'diagonal': 87,
    'carousel': 90,
}


@dataclass
class LShapeGridMap:
    """
    Dual 1D grids for L-shape kitchen placement.
    
    L-shape consists of:
    - Arm A: Back wall (horizontal, X axis)
    - Arm B: Side wall (vertical, Z axis)
    - Corner: Shared module at origin
    
    Layout:
        Arm A (width = room.width - corner_size)
    ┌─────────────────────────┐
    │ Corner                  │
    │   │                     │
    │   │ Arm B               │
    │   │ (height=room.wall_b)│
    └───┘                     │
    """
    arm_a: GridMap          # Back wall (starts after corner)
    arm_b: GridMap          # Side wall (starts after corner)
    corner_size: int        # 65, 87, or 90
    corner_type: str        # 'blind', 'diagonal', 'carousel'
    room_width: int         # Original room width
    wall_b_length: int      # Side wall length
    
    @classmethod
    def create(
        cls, 
        room_width: int, 
        wall_b_length: int,
        corner_type: str = 'blind',
        initial_value: float = 0.0
    ) -> 'LShapeGridMap':
        """Create L-shape grid with correct arm dimensions."""
        corner_size = CORNER_SIZES.get(corner_type, 65)
        
        # Arm A: from corner_size to room_width
        arm_a_width = room_width - corner_size
        arm_a = GridMap.create(arm_a_width, initial_value)
        
        # Arm B: from corner_size to wall_b_length
        arm_b_width = wall_b_length - corner_size
        arm_b = GridMap.create(arm_b_width, initial_value)
        
        return cls(
            arm_a=arm_a,
            arm_b=arm_b,
            corner_size=corner_size,
            corner_type=corner_type,
            room_width=room_width,
            wall_b_length=wall_b_length
        )
    
    @classmethod
    def zeros(cls, room_width: int, wall_b_length: int, corner_type: str = 'blind') -> 'LShapeGridMap':
        """Create zero-filled L-shape grid."""
        return cls.create(room_width, wall_b_length, corner_type, 0.0)
    
    @classmethod
    def ones(cls, room_width: int, wall_b_length: int, corner_type: str = 'blind', value: float = 100.0) -> 'LShapeGridMap':
        """Create L-shape grid filled with value."""
        return cls.create(room_width, wall_b_length, corner_type, value)
    
    def copy(self) -> 'LShapeGridMap':
        """Deep copy."""
        return LShapeGridMap(
            arm_a=self.arm_a.copy(),
            arm_b=self.arm_b.copy(),
            corner_size=self.corner_size,
            corner_type=self.corner_type,
            room_width=self.room_width,
            wall_b_length=self.wall_b_length
        )
    
    def get_arm(self, arm: str) -> GridMap:
        """Get grid for arm 'A' or 'B'."""
        if arm.upper() == 'A':
            return self.arm_a
        elif arm.upper() == 'B':
            return self.arm_b
        raise ValueError(f"Invalid arm: {arm}, expected 'A' or 'B'")
    
    def local_to_global_position(self, arm: str, local_pos: int) -> Tuple[int, int]:
        """
        Convert local arm position to global (x, z) coordinates.
        
        Arm A: local_pos -> (corner_size + local_pos, 0)
        Arm B: local_pos -> (0, corner_size + local_pos)
        """
        if arm.upper() == 'A':
            return (self.corner_size + local_pos, 0)
        else:
            return (0, self.corner_size + local_pos)
    
    def global_to_arm_position(self, x: int, z: int) -> Tuple[str, int]:
        """
        Determine which arm a global position belongs to.
        
        Returns: (arm_name, local_position)
        """
        if z == 0 and x >= self.corner_size:
            return ('A', x - self.corner_size)
        elif x == 0 and z >= self.corner_size:
            return ('B', z - self.corner_size)
        else:
            raise ValueError(f"Position ({x}, {z}) is in corner or invalid")

