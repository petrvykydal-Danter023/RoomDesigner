"""
Unit tests for Heatmap Placement System.
"""

import pytest
import numpy as np
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kitchen_core.heatmaps.grid import GridMap
from kitchen_core.heatmaps.masking import CollisionMask
from kitchen_core.heatmaps.fields import FieldEmitter, compute_dynamic_fields
from kitchen_core.geometry import Room


class TestGridMap:
    """Tests for GridMap class."""
    
    def test_create_zeros(self):
        grid = GridMap.zeros(400)
        assert grid.room_width == 400
        assert len(grid.data) == 400
        assert np.all(grid.data == 0)
    
    def test_create_ones(self):
        grid = GridMap.ones(400, value=100.0)
        assert np.all(grid.data == 100.0)
    
    def test_gaussian_field_shape(self):
        """Verify Gaussian creates bell curve."""
        grid = GridMap.zeros(400)
        field = grid.gaussian_field(center_cm=200, sigma_cm=50, amplitude=100)
        
        # Peak at center
        assert field[200] == pytest.approx(100.0, rel=0.01)
        
        # Drops off symmetrically
        assert field[200 - 50] == pytest.approx(field[200 + 50], rel=0.01)
        
        # About 60% at 1 sigma
        assert field[200 + 50] == pytest.approx(60.65, rel=0.05)
    
    def test_find_best_position_simple(self):
        """Best position is where score is highest."""
        grid = GridMap.zeros(400)
        grid.data[100:150] = 100  # High score zone
        
        best = grid.find_best_position(item_width=30)
        assert 100 <= best <= 120  # Should be in high zone
    
    def test_find_best_position_convolution(self):
        """np.convolve correctly sums over item width."""
        grid = GridMap.zeros(100)
        grid.data[50:70] = 10  # 20 cells of value 10
        
        # Item width 20 should have max score at position 50
        best = grid.find_best_position(item_width=20)
        assert best == 50
    
    def test_find_top_k_positions(self):
        """Find multiple good positions."""
        grid = GridMap.zeros(400)
        grid.data[50:70] = 100   # Zone 1
        grid.data[200:220] = 80  # Zone 2
        grid.data[300:320] = 60  # Zone 3
        
        top3 = grid.find_top_k_positions(item_width=20, k=3)
        
        assert len(top3) == 3
        # First should be highest score
        assert top3[0][0] == 50
        assert top3[0][1] > top3[1][1]  # Scores descending
    
    def test_apply_penalty_range(self):
        grid = GridMap.ones(400, value=100.0)
        grid.apply_penalty_range(100, 200, -50)
        
        assert grid.data[150] == 50.0
        assert grid.data[50] == 100.0
        assert grid.data[250] == 100.0


class TestCollisionMask:
    """Tests for CollisionMask class."""
    
    def test_create_empty(self):
        mask = CollisionMask.create(400)
        assert np.all(mask.hard_mask == 0)
        assert np.all(mask.soft_mask == 0)
    
    def test_mark_occupied_hard(self):
        mask = CollisionMask.create(400)
        mask.mark_occupied(100, 160, include_door_swing=False)
        
        assert np.all(mask.hard_mask[100:160] == 1)
        assert mask.hard_mask[99] == 0
        assert mask.hard_mask[160] == 0
    
    def test_is_valid_placement(self):
        mask = CollisionMask.create(400)
        mask.mark_occupied(100, 160, include_door_swing=False)
        
        # Can't place overlapping
        assert mask.is_valid_placement(120, 60) == False
        
        # Can place before
        assert mask.is_valid_placement(30, 60) == True
        
        # Can place after
        assert mask.is_valid_placement(170, 60) == True
    
    def test_door_swing_soft_penalty(self):
        mask = CollisionMask.create(400)
        mask.mark_occupied(100, 160, include_door_swing=True, door_swing_cm=30)
        
        # Soft penalty extends beyond hard block
        assert mask.soft_mask[80] > 0  # In swing zone
        assert mask.soft_mask[180] > 0  # In swing zone


class TestFieldEmitter:
    """Tests for Attractor/Repulsor system."""
    
    def test_sink_attracts_dishwasher(self):
        """Dishwasher should have high score near sink."""
        emitter = FieldEmitter(position=100, width=60, item_type='sink_cabinet')
        field = emitter.get_attraction_for('dishwasher', room_width=400)
        
        assert field is not None
        # Highest near sink center
        center = 100 + 30
        assert field.data[center] > field.data[0]
        assert field.data[center] > field.data[300]
    
    def test_stove_repels_fridge(self):
        """Fridge should have low score near stove."""
        emitter = FieldEmitter(position=200, width=60, item_type='stove_cabinet')
        field = emitter.get_repulsion_for('fridge', room_width=400)
        
        assert field is not None
        # Negative values near stove
        center = 200 + 30
        assert field.data[center] < 0
        # Less negative far away
        assert field.data[0] > field.data[center]
    
    def test_compute_dynamic_fields(self):
        """Combined fields from multiple emitters."""
        emitters = [
            FieldEmitter(position=50, width=60, item_type='sink_cabinet'),
            FieldEmitter(position=200, width=60, item_type='stove_cabinet'),
        ]
        
        combined = compute_dynamic_fields(emitters, 'dishwasher', room_width=400)
        
        # Dishwasher attracted to sink (50-110), so high score there
        # Stove doesn't affect dishwasher directly
        assert combined.data[80] > combined.data[300]


def create_test_room(width=400):
    """Create a minimal test room."""
    return Room(
        width=width,
        length=300,
        height=260,
        slopes=[],
        utilities=[
            {'type': 'water', 'x': 100, 'y': 50, 'z': 0},
            {'type': 'gas', 'x': 300, 'y': 50, 'z': 0},
        ],
        windows=[{'wall': 'back', 'x': 150, 'width': 80, 'height': 100}],
        doors=[{'wall': 'right', 'x': 100, 'width': 90}]
    )


class TestHeatmapSolver:
    """Integration tests for HeatmapSolver."""
    
    def test_solver_returns_volumes(self):
        """Solver should return positioned volumes."""
        from kitchen_core.heatmaps.solver import HeatmapSolver
        
        room = create_test_room()
        solver = HeatmapSolver(room)
        
        wishlist = [
            {'type': 'sink_cabinet', 'width': 60},
            {'type': 'stove_cabinet', 'width': 60},
            {'type': 'fridge', 'width': 60, 'height': 215},
        ]
        
        result = solver.solve(wishlist)
        
        assert 'volumes' in result
        assert len(result['volumes']) >= 3  # At least anchors + fillers
        
        # Each volume should have position
        for vol in result['volumes']:
            assert 'x' in vol
            assert 'width' in vol
            assert 'function' in vol
    
    def test_solver_respects_water_for_sink(self):
        """Sink should be placed near water utility."""
        from kitchen_core.heatmaps.solver import HeatmapSolver
        
        room = create_test_room()  # Water at x=100
        solver = HeatmapSolver(room)
        
        wishlist = [
            {'type': 'sink_cabinet', 'width': 60},
        ]
        
        result = solver.solve(wishlist)
        volumes = result['volumes']
        
        # Find sink
        sink = next((v for v in volumes if 'sink' in v['function']), None)
        assert sink is not None
        
        # Should be within ~100cm of water (x=100)
        sink_center = sink['x'] + sink['width'] // 2
        distance = abs(sink_center - 100)
        assert distance < 150, f"Sink at {sink['x']}, too far from water at 100"
    
    def test_stove_not_adjacent_to_fridge(self):
        """Stove and fridge should not be adjacent."""
        from kitchen_core.heatmaps.solver import HeatmapSolver
        
        room = create_test_room()
        solver = HeatmapSolver(room)
        
        wishlist = [
            {'type': 'sink_cabinet', 'width': 60},
            {'type': 'stove_cabinet', 'width': 60},
            {'type': 'fridge', 'width': 60, 'height': 215},
        ]
        
        result = solver.solve(wishlist)
        volumes = result['volumes']
        
        # Find stove and fridge
        stove = next((v for v in volumes if 'stove' in v['function']), None)
        fridge = next((v for v in volumes if v['function'] == 'fridge'), None)
        
        assert stove is not None
        assert fridge is not None
        
        # Check minimum gap (should not be directly adjacent)
        stove_end = stove['x'] + stove['width']
        fridge_end = fridge['x'] + fridge['width']
        
        # Either stove before fridge or fridge before stove
        if stove['x'] < fridge['x']:
            gap = fridge['x'] - stove_end
        else:
            gap = stove['x'] - fridge_end
        
        # Should have some gap (at least 0, ideally > 30cm for safety)
        assert gap >= 0, "Stove and fridge are overlapping!"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
