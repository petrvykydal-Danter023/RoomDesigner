"""
HeatmapSolver - Beam Search placement engine.

Uses heatmaps for anchor items (Sink, Stove, Fridge, Tall).
Filler items (prep cabinets) are computed classically to fill gaps.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from .grid import GridMap
from .masking import CollisionMask
from .layers import (
    create_architecture_layer,
    create_installation_layer,
    create_ergonomics_layer,
    create_traffic_layer,
    create_light_layer,
    combine_layers,
    get_layer_weights,
)
from .fields import FieldEmitter, compute_dynamic_fields
from ..geometry import Room


# Anchor items that get heatmap placement
ANCHOR_TYPES = {'sink_cabinet', 'sink', 'stove_cabinet', 'stove', 'fridge', 'pantry', 'oven_tower'}

# Filler items that fill gaps between anchors
FILLER_TYPES = {'drawer_cabinet', 'base_cabinet', 'prep', 'landing', 'dishwasher'}


@dataclass
class PlacementCandidate:
    """A potential placement position for an item."""
    position: int  # cm from left
    score: float
    item_type: str
    width: int


@dataclass
class PartialSolution:
    """A partial solution in beam search."""
    placements: List[PlacementCandidate]
    total_score: float
    collision_mask: CollisionMask
    emitters: List[FieldEmitter]
    
    def copy(self) -> 'PartialSolution':
        """Deep copy for branching."""
        return PartialSolution(
            placements=self.placements.copy(),
            total_score=self.total_score,
            collision_mask=self.collision_mask.copy(),
            emitters=self.emitters.copy()
        )


class HeatmapSolver:
    """
    Beam Search placement solver using heatmaps.
    
    Algorithm:
    1. Build static layers from room
    2. Separate items into ANCHORS vs FILLERS
    3. Place anchors using beam search with heatmaps
    4. Fill gaps with filler cabinets classically
    """
    
    BEAM_WIDTH = 50  # Keep top-N partial solutions
    CANDIDATES_PER_ITEM = 3  # Top-K candidates per item
    
    def __init__(self, room: Room, beam_width: int = 50, candidates_per_item: int = 3):
        self.room = room
        self.BEAM_WIDTH = beam_width
        self.CANDIDATES_PER_ITEM = candidates_per_item
        
        # Pre-compute static layers
        self._static_layers = {
            'architecture': create_architecture_layer(room),
            'installation_water': create_installation_layer(room, 'water'),
            'installation_gas': create_installation_layer(room, 'gas'),
            'ergonomics': create_ergonomics_layer(room),
            'traffic': create_traffic_layer(room),
            'light': create_light_layer(room),
        }
        
        # Debug storage
        self.debug_data: Dict[str, Any] = {}
    
    def solve(self, wishlist: List[Dict], skip_fillers: bool = False) -> Dict[str, Any]:
        """
        Solve placement for wishlist items.
        
        Args:
            wishlist: Items to place
            skip_fillers: If True, don't add filler cabinets (for monolith-only zones)
        
        Returns:
            Dict with 'volumes' (positioned items) and 'debug' data
        """
        # Separate anchors and fillers
        anchors = [item for item in wishlist if item.get('type') in ANCHOR_TYPES]
        fillers = [item for item in wishlist if item.get('type') in FILLER_TYPES]
        
        # Sort anchors by priority
        anchor_priority = ['sink_cabinet', 'sink', 'stove_cabinet', 'stove', 'fridge', 'pantry', 'oven_tower']
        anchors.sort(key=lambda x: anchor_priority.index(x['type']) if x['type'] in anchor_priority else 99)
        
        print(f"  [Heatmap] Anchors: {[a['type'] for a in anchors]}")
        print(f"  [Heatmap] Fillers: {[f['type'] for f in fillers]}")
        
        # Initialize beam with empty solution
        initial_mask = CollisionMask.create(self.room.width)
        initial_solution = PartialSolution(
            placements=[],
            total_score=0.0,
            collision_mask=initial_mask,
            emitters=[]
        )
        beam = [initial_solution]
        
        # Place each anchor using beam search
        for item in anchors:
            beam = self._expand_beam(beam, item)
            print(f"  [Heatmap] Placed {item['type']}: beam size = {len(beam)}")
        
        # Get best solution
        if not beam:
            print("  [Heatmap] WARNING: No valid placement found!")
            return {'volumes': [], 'debug': self.debug_data}
        
        best = max(beam, key=lambda s: s.total_score)
        anchor_volumes = self._candidates_to_volumes(best.placements)
        
        # Fill gaps with fillers (unless skip_fillers is True)
        if skip_fillers:
            all_volumes = anchor_volumes
        else:
            filler_volumes = self._fill_gaps_classical(anchor_volumes, fillers)
            all_volumes = anchor_volumes + filler_volumes
        
        all_volumes.sort(key=lambda v: v['x'])
        
        self.debug_data['beam_final_size'] = len(beam)
        self.debug_data['best_score'] = best.total_score
        
        return {
            'volumes': all_volumes,
            'debug': self.debug_data
        }
    
    def _expand_beam(
        self, 
        beam: List[PartialSolution], 
        item: Dict
    ) -> List[PartialSolution]:
        """Expand beam by adding candidates for new item."""
        item_type = item['type']
        item_width = item.get('width', 60)
        
        new_solutions = []
        
        for solution in beam:
            candidates = self._generate_candidates(
                item_type=item_type,
                item_width=item_width,
                mask=solution.collision_mask,
                emitters=solution.emitters
            )
            
            for cand in candidates:
                # Clone solution and add candidate
                new_sol = solution.copy()
                new_sol.placements.append(cand)
                new_sol.total_score += cand.score
                
                # Update collision mask
                new_sol.collision_mask.mark_occupied(
                    cand.position, 
                    cand.position + cand.width,
                    include_door_swing=True
                )
                
                # Add emitter for dynamic fields
                new_sol.emitters.append(FieldEmitter(
                    position=cand.position,
                    width=cand.width,
                    item_type=cand.item_type
                ))
                
                new_solutions.append(new_sol)
        
        # Prune to beam width
        new_solutions.sort(key=lambda s: s.total_score, reverse=True)
        return new_solutions[:self.BEAM_WIDTH]
    
    def _generate_candidates(
        self,
        item_type: str,
        item_width: int,
        mask: CollisionMask,
        emitters: List[FieldEmitter]
    ) -> List[PlacementCandidate]:
        """Generate top-K candidates for item."""
        # Build combined heatmap from static layers
        weights = get_layer_weights(item_type)
        
        # Start with architecture (always weight 1.0)
        combined = self._static_layers['architecture'].copy()
        
        # Add other layers with weights
        for layer_name, weight in weights.items():
            if layer_name in self._static_layers and weight > 0:
                combined.data += self._static_layers[layer_name].data * weight
        
        # Add dynamic fields from placed items
        if emitters:
            dynamic = compute_dynamic_fields(emitters, item_type, self.room.width)
            combined.data += dynamic.data
        
        # Apply collision mask (hard block occupied cells)
        combined.apply_mask(mask.get_blocking_mask(), penalty=-10000)
        
        # Subtract soft collision penalties
        combined.data -= mask.soft_mask * 100
        
        # Find top-K positions
        top_positions = combined.find_top_k_positions(item_width, k=self.CANDIDATES_PER_ITEM)
        
        # Filter out invalid positions (negative scores indicate blocked)
        candidates = []
        for pos, score in top_positions:
            if mask.is_valid_placement(pos, item_width) and score > -5000:
                candidates.append(PlacementCandidate(
                    position=pos,
                    score=score,
                    item_type=item_type,
                    width=item_width
                ))
        
        return candidates
    
    def _candidates_to_volumes(self, placements: List[PlacementCandidate]) -> List[Dict]:
        """Convert PlacementCandidates to volume dicts."""
        volumes = []
        for p in placements:
            height = 215 if p.item_type in ['fridge', 'pantry', 'oven_tower'] else 85
            is_monolith = p.item_type in ['fridge', 'pantry', 'oven_tower']
            
            volumes.append({
                'x': p.position,
                'width': p.width,
                'function': p.item_type,
                'metadata': {
                    'height': height,
                    'is_monolith': is_monolith,
                    'heatmap_score': p.score
                }
            })
        
        return volumes
    
    def _fill_gaps_classical(
        self, 
        anchors: List[Dict], 
        fillers: List[Dict]
    ) -> List[Dict]:
        """
        Fill gaps between anchors with filler cabinets.
        
        Uses classical sequential filling, not heatmaps.
        """
        if not anchors:
            return []
        
        # Sort anchors by position
        anchors_sorted = sorted(anchors, key=lambda a: a['x'])
        
        filled = []
        
        # Fill gap at start (before first anchor)
        first_x = anchors_sorted[0]['x']
        if first_x > 30:
            filled.extend(self._fill_range(0, first_x, fillers))
        
        # Fill gaps between anchors
        for i in range(len(anchors_sorted) - 1):
            curr = anchors_sorted[i]
            next_anchor = anchors_sorted[i + 1]
            
            gap_start = curr['x'] + curr['width']
            gap_end = next_anchor['x']
            gap_width = gap_end - gap_start
            
            if gap_width >= 30:  # Minimum cabinet width
                filled.extend(self._fill_range(gap_start, gap_end, fillers))
        
        # Fill gap at end (after last anchor)
        last = anchors_sorted[-1]
        last_end = last['x'] + last['width']
        if self.room.width - last_end > 30:
            filled.extend(self._fill_range(last_end, self.room.width, fillers))
        
        return filled
    
    def _fill_range(
        self, 
        start: int, 
        end: int, 
        available_fillers: List[Dict]
    ) -> List[Dict]:
        """Fill a range with filler cabinets."""
        filled = []
        current_x = start
        gap_remaining = end - start
        
        # Prioritize dishwasher if in fillers and near sink
        dishwasher = next((f for f in available_fillers if f['type'] == 'dishwasher'), None)
        
        # Use standard cabinet widths: 60, 45, 30
        standard_widths = [60, 45, 30]
        
        while gap_remaining >= 30:
            # Find best fitting width
            chosen_width = None
            for w in standard_widths:
                if w <= gap_remaining:
                    chosen_width = w
                    break
            
            if chosen_width is None:
                break
            
            # Use dishwasher first if available
            if dishwasher and chosen_width == 60:
                filled.append({
                    'x': current_x,
                    'width': 60,
                    'function': 'dishwasher',
                    'metadata': {'height': 85, 'is_monolith': False}
                })
                dishwasher = None  # Only place once
            else:
                filled.append({
                    'x': current_x,
                    'width': chosen_width,
                    'function': 'drawer_cabinet',
                    'metadata': {'height': 85, 'is_monolith': False}
                })
            
            current_x += chosen_width
            gap_remaining -= chosen_width
        
        # Handle tiny gaps with fillers
        if 0 < gap_remaining < 30:
            filled.append({
                'x': current_x,
                'width': gap_remaining,
                'function': 'filler',
                'metadata': {'height': 85, 'is_monolith': False}
            })
        
        return filled
    
    def get_static_layers(self) -> Dict[str, GridMap]:
        """Get static layers for debugging/visualization."""
        return self._static_layers


# =============================================================================
# L-SHAPE HEATMAP SOLVER
# =============================================================================

# Item distribution preferences for L-shape
ARM_PREFERENCES = {
    # Monolith items prefer end of Arm B
    'fridge': 'B_END',
    'pantry': 'B_END',
    'oven_tower': 'B_END',
    # Wet zone near water utility
    'sink_cabinet': 'WATER',
    'sink': 'WATER',
    'dishwasher': 'WATER',
    # Hot zone near gas utility
    'stove_cabinet': 'GAS',
    'stove': 'GAS',
}


class LShapeHeatmapSolver:
    """
    Beam Search placement solver for L-shape kitchens.
    
    Uses dual 1D grids (Arm A + Arm B) with corner module at origin.
    
    Algorithm:
    1. Create corner module (fixed position)
    2. Distribute items between arms based on rules
    3. Run Beam Search per arm
    4. Combine results with axis metadata
    """
    
    BEAM_WIDTH = 50
    CANDIDATES_PER_ITEM = 3
    
    def __init__(
        self, 
        room: Room, 
        corner_type: str = 'blind',
        beam_width: int = 50
    ):
        self.room = room
        self.corner_type = corner_type
        self.BEAM_WIDTH = beam_width
        
        from .grid import LShapeGridMap, CORNER_SIZES
        self.corner_size = CORNER_SIZES.get(corner_type, 65)
        
        # Arm dimensions
        self.arm_a_length = room.width - self.corner_size
        self.arm_b_length = (room.wall_b_length or room.length) - self.corner_size
        
        # Create separate I-shape solvers for each arm
        # We'll create mock rooms for each arm
        self._arm_a_solver = self._create_arm_solver('A')
        self._arm_b_solver = self._create_arm_solver('B')
        
        self.debug_data: Dict[str, Any] = {}
    
    def _create_arm_solver(self, arm: str) -> HeatmapSolver:
        """Create HeatmapSolver for a single arm with adjusted room."""
        from ..geometry import Room as RoomClass
        
        if arm == 'A':
            # Arm A is along X axis (back wall after corner)
            arm_width = self.arm_a_length
            # Utilities on Arm A: those with x > corner_size
            utilities = [
                u for u in self.room.utilities 
                if u.get('x', 0) >= self.corner_size
            ]
            # Adjust utility x positions relative to arm start
            adjusted_utilities = [
                {**u, 'x': u.get('x', 0) - self.corner_size} 
                for u in utilities
            ]
        else:
            # Arm B is along Z axis (side wall after corner)
            arm_width = self.arm_b_length
            # Utilities on Arm B: those with z > corner_size (or near z=0 for side wall)
            # For simplicity, assume utilities with small x are on Arm B
            utilities = [
                u for u in self.room.utilities 
                if u.get('x', 0) < self.corner_size
            ]
            adjusted_utilities = utilities  # Use as-is or transform
        
        # Create mock room for arm
        mock_room = RoomClass(
            width=arm_width,
            length=self.room.length,
            height=self.room.height,
            slopes=[],
            utilities=adjusted_utilities,
            windows=self.room.windows or [],
            doors=self.room.doors or [],
            shape='I'
        )
        
        return HeatmapSolver(mock_room, self.BEAM_WIDTH, self.CANDIDATES_PER_ITEM)
    
    def solve(self, wishlist: List[Dict]) -> Dict[str, Any]:
        """
        Solve L-shape placement.
        
        Returns dict with:
        - volumes: All placed items with global coordinates
        - corner: Corner module info
        - arm_a/arm_b: Per-arm placement info
        """
        print(f"  L-Shape Heatmap: Corner={self.corner_type}({self.corner_size}cm)")
        print(f"  Arm A: {self.arm_a_length}cm, Arm B: {self.arm_b_length}cm")
        
        # Distribute items between arms
        arm_a_items, arm_b_items = self._distribute_items(wishlist)
        
        print(f"  [Arm A] Items: {[i['type'] for i in arm_a_items]}")
        print(f"  [Arm B] Items: {[i['type'] for i in arm_b_items]}")
        
        # Solve each arm
        # Arm A: normal placement with fillers
        arm_a_result = self._arm_a_solver.solve(arm_a_items, skip_fillers=False)
        # Arm B: monolith zone - no fillers needed
        arm_b_result = self._arm_b_solver.solve(arm_b_items, skip_fillers=True)
        
        # Transform arm results to global coordinates
        arm_a_volumes = self._transform_arm_a_volumes(arm_a_result['volumes'])
        arm_b_volumes = self._transform_arm_b_volumes(arm_b_result['volumes'])
        
        # Combine all volumes
        all_volumes = arm_a_volumes + arm_b_volumes
        
        return {
            'volumes': all_volumes,
            'corner': {
                'type': self.corner_type,
                'size': self.corner_size
            },
            'arm_a': {
                'start': self.corner_size,
                'end': self.room.width,
                'volumes': arm_a_volumes
            },
            'arm_b': {
                'start': self.corner_size,
                'end': self.room.wall_b_length or self.room.length,
                'volumes': arm_b_volumes
            },
            'debug': {
                'arm_a_debug': arm_a_result.get('debug', {}),
                'arm_b_debug': arm_b_result.get('debug', {}),
            }
        }
    
    def _distribute_items(self, wishlist: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Distribute items between Arm A and Arm B based on rules.
        
        Rules:
        - Monolith (fridge, pantry, oven_tower) -> Arm B end
        - Wet zone (sink, dishwasher) -> arm with water utility
        - Hot zone (stove) -> arm with gas utility OR Arm A (default for work zone)
        - Others -> balance between arms
        """
        arm_a: List[Dict] = []
        arm_b: List[Dict] = []
        
        # Determine which arm has water/gas
        water_on_a = any(
            u.get('type') == 'water' and u.get('x', 0) >= self.corner_size
            for u in self.room.utilities
        )
        gas_on_a = any(
            u.get('type') == 'gas' and u.get('x', 0) >= self.corner_size
            for u in self.room.utilities
        )
        gas_on_b = any(
            u.get('type') == 'gas' and u.get('x', 0) < self.corner_size
            for u in self.room.utilities
        )
        # If no gas defined at all, default stove to Arm A (work zone convention)
        no_gas_defined = not gas_on_a and not gas_on_b
        
        for item in wishlist:
            item_type = item.get('type', '')
            preference = ARM_PREFERENCES.get(item_type, 'BALANCE')
            
            if preference == 'B_END':
                # Monolith at end of Arm B
                arm_b.append(item)
            elif preference == 'WATER':
                if water_on_a:
                    arm_a.append(item)
                else:
                    arm_b.append(item)
            elif preference == 'GAS':
                # Stove: prefer Arm A if no gas defined (standard work zone)
                if gas_on_a or no_gas_defined:
                    arm_a.append(item)
                else:
                    arm_b.append(item)
            else:
                # Balance: prefer arm with more space
                arm_a_used = sum(i.get('width', 60) for i in arm_a)
                arm_b_used = sum(i.get('width', 60) for i in arm_b)
                
                if self.arm_a_length - arm_a_used > self.arm_b_length - arm_b_used:
                    arm_a.append(item)
                else:
                    arm_b.append(item)
        
        return arm_a, arm_b
    
    def _transform_arm_a_volumes(self, volumes: List[Dict]) -> List[Dict]:
        """Transform Arm A local positions to global coordinates."""
        transformed = []
        for vol in volumes:
            new_vol = vol.copy()
            # Arm A: add corner offset to x, z stays 0
            new_vol['x'] = vol['x'] + self.corner_size
            new_vol['z'] = 0
            new_vol['metadata'] = vol.get('metadata', {}).copy()
            new_vol['metadata']['axis'] = 'X'
            new_vol['metadata']['arm'] = 'A'
            transformed.append(new_vol)
        return transformed
    
    def _transform_arm_b_volumes(self, volumes: List[Dict]) -> List[Dict]:
        """Transform Arm B local positions to global (rotated) coordinates."""
        transformed = []
        for vol in volumes:
            new_vol = vol.copy()
            # Arm B: x becomes 0, local position becomes z
            new_vol['x'] = 0
            new_vol['z'] = vol['x'] + self.corner_size  # Local x -> global z
            new_vol['metadata'] = vol.get('metadata', {}).copy()
            new_vol['metadata']['axis'] = 'Z'
            new_vol['metadata']['arm'] = 'B'
            transformed.append(new_vol)
        return transformed

