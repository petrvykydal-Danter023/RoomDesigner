"""
Heatmap Placement System for Kitchen Generator.

Uses NumPy-based utility maps with Beam Search for intelligent placement.
"""

from .grid import GridMap, LShapeGridMap, CORNER_SIZES
from .masking import CollisionMask
from .layers import (
    create_architecture_layer,
    create_installation_layer,
    create_ergonomics_layer,
    create_traffic_layer,
    create_light_layer,
)
from .fields import FieldEmitter, ATTRACTIONS, REPULSIONS
from .solver import HeatmapSolver, LShapeHeatmapSolver

__all__ = [
    'GridMap',
    'LShapeGridMap',
    'CORNER_SIZES',
    'CollisionMask',
    'HeatmapSolver',
    'LShapeHeatmapSolver',
    'FieldEmitter',
    'ATTRACTIONS',
    'REPULSIONS',
    'create_architecture_layer',
    'create_installation_layer',
    'create_ergonomics_layer',
    'create_traffic_layer',
    'create_light_layer',
]
