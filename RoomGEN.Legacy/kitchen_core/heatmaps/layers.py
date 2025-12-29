"""
Static Layer Factories - Generate base heatmaps from room configuration.

Layers:
- Architecture: walls, doors, windows (hard constraints)
- Installation: utility proximity (water, gas, electrical)
- Ergonomics: safety & access patterns
- Traffic: movement paths between key points
- Light: natural light from windows
"""

from typing import List, Dict, Any, Optional
import numpy as np
from .grid import GridMap
from ..geometry import Room


def create_architecture_layer(room: Room) -> GridMap:
    """
    Architecture Layer - Hard constraints from room structure.
    
    + Walls baseline (+100)
    - Doors: complete blocking (-1000)
    - Windows: penalty for items like stove (-500)
    """
    grid = GridMap.ones(room.width, value=100.0)
    
    # Block door zones
    doors = room.doors or []
    for door in doors:
        if door.get('wall') == 'back':
            # Door on back wall - block placement
            door_x = door.get('x', 0)
            door_width = door.get('width', 90)
            grid.apply_penalty_range(door_x, door_x + door_width, -1100)  # Net negative
    
    # Penalty for window zones (not ideal for stoves/tall cabinets)
    windows = room.windows or []
    for window in windows:
        if window.get('wall') == 'back':
            win_x = window.get('x', 0)
            win_width = window.get('width', 80)
            grid.apply_penalty_range(win_x, win_x + win_width, -500)
    
    return grid


def create_installation_layer(room: Room, utility_type: str = 'water') -> GridMap:
    """
    Installation Layer - Proximity to utilities.
    
    Near utility = bonus (less installation cost)
    Far from utility = penalty (expensive pipe/wire runs)
    """
    grid = GridMap.zeros(room.width)
    
    # Find utilities of requested type
    for util in room.utilities:
        if util.get('type') == utility_type:
            util_x = util.get('x', 0)
            # Create Gaussian attractor around utility
            # Sigma ~50cm = strong bonus nearby, fades with distance
            grid.add_gaussian(center_cm=util_x, sigma_cm=50, amplitude=100)
    
    # If no utility found, return flat grid (no preference)
    if np.max(grid.data) == 0:
        return GridMap.ones(room.width, value=50.0)
    
    return grid


def create_ergonomics_layer(room: Room, item_type: str = 'generic') -> GridMap:
    """
    Ergonomics Layer - Safety and access patterns.
    
    + Center of wall: good access (+50)
    - Corners: restricted access (-50)
    - Edge bonus for tall items (fridge, pantry)
    """
    grid = GridMap.zeros(room.width)
    center = room.width // 2
    
    if item_type in ['fridge', 'pantry', 'oven_tower']:
        # Tall items prefer edges (start or end of run)
        edge_zone = 120  # First/last 120cm
        grid.apply_penalty_range(0, edge_zone, 80)
        grid.apply_penalty_range(room.width - edge_zone, room.width, 80)
        # Penalize center for tall items
        grid.add_gaussian(center_cm=center, sigma_cm=100, amplitude=-30)
    else:
        # Standard items prefer center access
        grid.add_gaussian(center_cm=center, sigma_cm=150, amplitude=50)
        # Penalize extreme corners
        corner_zone = 30
        grid.apply_penalty_range(0, corner_zone, -50)
        grid.apply_penalty_range(room.width - corner_zone, room.width, -50)
    
    return grid


def create_traffic_layer(room: Room) -> GridMap:
    """
    Traffic Layer - Movement path penalties.
    
    Calculates shortest path between doors and applies penalty
    to areas where cabinet doors would obstruct traffic.
    """
    grid = GridMap.zeros(room.width)
    
    # Find door positions
    door_positions = []
    doors = room.doors or []
    for door in doors:
        if door.get('wall') == 'back':
            door_x = door.get('x', 0) + door.get('width', 90) // 2
            door_positions.append(door_x)
        elif door.get('wall') == 'right':
            # Right wall door - traffic passes near end
            door_positions.append(room.width - 50)
        elif door.get('wall') == 'left':
            # Left wall door - traffic passes near start
            door_positions.append(50)
    
    # Apply traffic penalty near door paths
    for door_x in door_positions:
        # Traffic zone: 60cm on each side of door center
        grid.apply_penalty_range(door_x - 60, door_x + 60, -200)
    
    return grid


def create_light_layer(room: Room) -> GridMap:
    """
    Light Layer - Natural light from windows.
    
    Prep zones want light, storage doesn't care.
    """
    grid = GridMap.zeros(room.width)
    
    # Find windows and create light gradients
    windows = room.windows or []
    for window in windows:
        if window.get('wall') == 'back':
            win_x = window.get('x', 0)
            win_width = window.get('width', 80)
            win_center = win_x + win_width // 2
            
            # Light spreads from window center
            grid.add_gaussian(center_cm=win_center, sigma_cm=100, amplitude=80)
    
    return grid


def combine_layers(
    layers: Dict[str, GridMap],
    weights: Dict[str, float]
) -> GridMap:
    """
    Combine multiple layers with weights.
    
    Args:
        layers: Dict of layer name -> GridMap
        weights: Dict of layer name -> weight multiplier
    
    Returns:
        Combined GridMap
    """
    if not layers:
        raise ValueError("No layers to combine")
    
    room_width = list(layers.values())[0].room_width
    result = GridMap.zeros(room_width)
    
    for name, layer in layers.items():
        weight = weights.get(name, 1.0)
        result.data += layer.data * weight
    
    return result


# Default layer weights per item type
LAYER_WEIGHTS = {
    'sink_cabinet': {
        'architecture': 1.0,
        'installation_water': 1.0,
        'ergonomics': 0.5,
        'traffic': 0.3,
        'light': 0.8,
    },
    'stove_cabinet': {
        'architecture': 1.0,
        'installation_gas': 0.8,
        'ergonomics': 0.6,
        'traffic': 0.4,
        'light': 0.2,
    },
    'fridge': {
        'architecture': 1.0,
        'installation_water': 0.0,  # Doesn't need water
        'ergonomics': 0.8,  # Edge preference
        'traffic': 0.3,
        'light': 0.0,  # Doesn't need light
    },
    'dishwasher': {
        'architecture': 1.0,
        'installation_water': 0.9,  # Needs water nearby
        'ergonomics': 0.4,
        'traffic': 0.5,
        'light': 0.0,
    },
    'pantry': {
        'architecture': 1.0,
        'installation_water': 0.0,
        'ergonomics': 0.7,  # Edge preference
        'traffic': 0.2,
        'light': 0.0,  # Prefers dark/cool
    },
    'default': {
        'architecture': 1.0,
        'installation_water': 0.3,
        'ergonomics': 0.5,
        'traffic': 0.3,
        'light': 0.3,
    },
}


def get_layer_weights(item_type: str) -> Dict[str, float]:
    """Get layer weights for item type, with fallback to default."""
    return LAYER_WEIGHTS.get(item_type, LAYER_WEIGHTS['default'])
