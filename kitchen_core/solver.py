from ortools.sat.python import cp_model
from typing import List, Dict, Optional, Any
from .geometry import Room
from .zones import Zone, ZoneFactory


class StorageValidator:
    """
    Storage Index (SI) - Professional validation for kitchen capacity.
    
    Rules:
    - 0.5 linear meters of cabinets per 1m² of room area
    - Minimum 3.0m base cabinets for standard family
    - Minimum 2.0m wall cabinets recommended
    """
    
    RATIO = 0.5  # linear meters per m² room
    MIN_BASE = 3.0  # meters (absolute minimum for base cabinets)
    MIN_WALL = 2.0  # meters (recommended wall cabinets)
    MIN_TOTAL = 3.0  # absolute minimum for any kitchen
    ISLAND_THRESHOLD = 15.0  # m² - rooms larger than this get Island suggestion
    
    def __init__(self, room: Room):
        self.room = room
        self.room_area_m2 = (room.width * room.length) / 10000  # cm² to m²
    
    def calculate_requirements(self) -> Dict[str, float]:
        """Calculate storage requirements based on room area."""
        target = max(self.room_area_m2 * self.RATIO, self.MIN_TOTAL)
        
        return {
            'room_area_m2': self.room_area_m2,
            'target_linear_m': target,
            'min_base_m': self.MIN_BASE,
            'min_wall_m': self.MIN_WALL,
            'suggest_island': self.room_area_m2 >= self.ISLAND_THRESHOLD
        }
    
    def evaluate_solution(self, skeleton: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate if the solution meets storage requirements."""
        requirements = self.calculate_requirements()
        
        # Sum widths of all units (convert cm to m)
        volumes = skeleton.get('volumes', [])
        wall_items = skeleton.get('wall_wishlist', [])
        
        base_m = sum(v.get('width', 0) for v in volumes) / 100
        wall_m = sum(v.get('width', 0) for v in wall_items) / 100
        total_m = base_m + wall_m
        
        target = requirements['target_linear_m']
        deficit = max(0, target - total_m)
        
        # Determine status
        if total_m >= target:
            status = 'OK'
            recommendation = None
        else:
            status = 'UNDER-STORAGE'
            recommendation = self._get_recommendation(requirements, deficit)
        
        return {
            'room_area_m2': requirements['room_area_m2'],
            'target_linear_m': round(target, 1),
            'actual_base_m': round(base_m, 1),
            'actual_wall_m': round(wall_m, 1),
            'actual_total_m': round(total_m, 1),
            'deficit_m': round(deficit, 1),
            'status': status,
            'recommendation': recommendation,
            'suggest_island': requirements['suggest_island']
        }
    
    def _get_recommendation(self, requirements: Dict, deficit: float) -> str:
        """Get remediation recommendation based on priority."""
        
        # Priority 1 for large rooms: ISLAND
        if requirements['suggest_island']:
            return f"Add Kitchen Island (+{deficit:.1f}m needed). Room is large enough for premium island design."
        
        # Priority 2: Wall Cabinets
        if deficit <= 2.0:
            return f"Add Wall Cabinets (+{deficit:.1f}m). Most cost-effective solution."
        
        # Priority 3: Expand shape
        if self.room.shape == 'I':
            return f"Expand to L-Shape (+{deficit:.1f}m needed). Second wall available."
        
        # Priority 4: Tall Bank
        return f"Add Tall Pantry Units (+{deficit:.1f}m needed). Maximize vertical storage."
    
    def print_report(self, evaluation: Dict[str, Any]):
        """Print storage validation report."""
        print("\n" + "="*50)
        print("[STORAGE INDEX REPORT]")
        print("="*50)
        print(f"  Room Area:        {evaluation['room_area_m2']:.1f} m2")
        print(f"  Target Capacity:  {evaluation['target_linear_m']:.1f} linear meters")
        print(f"  Actual Base:      {evaluation['actual_base_m']:.1f} m")
        print(f"  Actual Wall:      {evaluation['actual_wall_m']:.1f} m")
        print(f"  Actual Total:     {evaluation['actual_total_m']:.1f} m")
        print("-"*50)
        
        if evaluation['status'] == 'OK':
            print(f"  [OK] Storage requirements met!")
        else:
            print(f"  [WARNING] Status: {evaluation['status']}")
            print(f"  Deficit: {evaluation['deficit_m']:.1f} m")
            print(f"  Recommendation: {evaluation['recommendation']}")
        
        if evaluation['suggest_island']:
            print(f"  [ISLAND] Large room detected - Kitchen Island recommended!")
        
        print("="*50 + "\n")


class WishlistExpander:
    """
    Smart Fill - Automatic wishlist completion.
    
    Takes minimal user requirements and expands to a complete
    kitchen that satisfies all workflow and storage rules.
    
    SAFETY VALVE: Never adds items that would exceed room width.
    """
    
    # Mandatory zones - at least one item from each
    ZONE_REQUIREMENTS = {
        'storage': ['fridge', 'pantry'],
        'wet': ['sink_cabinet'],
        'hot': ['stove_cabinet'],
    }
    
    # Items that should auto-add based on other items
    AUTO_ADD_RULES = {
        'hood': {'requires': ['stove_cabinet'], 'is_wall': True},
    }
    
    # Default item specifications
    DEFAULT_ITEMS = {
        'fridge': {'width': 60, 'height': 215},
        'pantry': {'width': 45, 'height': 200},
        'sink_cabinet': {'width': 60, 'height': 85},
        'dishwasher': {'width': 60, 'height': 85},
        'stove_cabinet': {'width': 60, 'height': 85},
        'drawer_cabinet': {'width': 60, 'height': 85},
        'hood': {'width': 60, 'height': 40},
        'wall_cabinet': {'width': 60, 'height': 70},
    }
    
    # Buffer to prevent edge-case solver failures
    SAFETY_BUFFER = 30  # cm
    
    def __init__(self, room: Room):
        self.room = room
        self.room_width = int(room.width)
        self.room_area_m2 = (room.width * room.length) / 10000
    
    def expand(self, user_wishlist: List[Dict], user_wall_wishlist: List[Dict] = None) -> tuple:
        """
        Expand minimal wishlist to complete kitchen.
        
        Returns: (expanded_wishlist, expanded_wall_wishlist)
        """
        user_wall_wishlist = user_wall_wishlist or []
        
        expanded = [dict(item) for item in user_wishlist]  # Copy
        expanded_wall = [dict(item) for item in user_wall_wishlist]
        
        print("\n[WishlistExpander] Smart Fill...")
        print(f"  Input: {len(user_wishlist)} base, {len(user_wall_wishlist)} wall items")
        
        # Track what types we have
        base_types = {item['type'] for item in expanded}
        wall_types = {item['type'] for item in expanded_wall}
        
        # Step 1: Ensure mandatory zones have items
        expanded = self._ensure_zones(expanded, base_types)
        base_types = {item['type'] for item in expanded}
        
        # Step 2: Auto-add dependent items (e.g., hood for stove)
        expanded_wall = self._ensure_auto_items(expanded, expanded_wall, base_types, wall_types)
        
        # Step 3: Fill to meet Storage Index (with SAFETY VALVE)
        expanded = self._fill_storage_safe(expanded)
        
        print(f"  Output: {len(expanded)} base, {len(expanded_wall)} wall items")
        
        return expanded, expanded_wall
    
    def _ensure_zones(self, wishlist: List[Dict], existing_types: set) -> List[Dict]:
        """Ensure each mandatory zone has at least one item."""
        for zone, valid_items in self.ZONE_REQUIREMENTS.items():
            if not any(t in existing_types for t in valid_items):
                # Add default item for this zone
                default_type = valid_items[0]
                default_spec = self.DEFAULT_ITEMS.get(default_type, {'width': 60})
                
                print(f"  [AUTO] Adding {default_type} for {zone} zone")
                wishlist.append({
                    'type': default_type,
                    'width': default_spec.get('width', 60),
                    'height': default_spec.get('height', 85),
                    'auto': True
                })
        
        return wishlist
    
    def _ensure_auto_items(self, base_list: List[Dict], wall_list: List[Dict],
                           base_types: set, wall_types: set) -> List[Dict]:
        """Add items that depend on other items (e.g., hood requires stove)."""
        for item_type, rule in self.AUTO_ADD_RULES.items():
            # Check if required items are present
            required = rule.get('requires', [])
            if all(r in base_types for r in required):
                # Check if auto-item already exists
                target_types = wall_types if rule.get('is_wall') else base_types
                if item_type not in target_types:
                    spec = self.DEFAULT_ITEMS.get(item_type, {'width': 60})
                    print(f"  [AUTO] Adding {item_type} (requires {required})")
                    
                    new_item = {
                        'type': item_type,
                        'width': spec.get('width', 60),
                        'height': spec.get('height', 40),
                        'auto': True
                    }
                    
                    if rule.get('is_wall'):
                        wall_list.append(new_item)
                    # else would append to base_list
        
        return wall_list
    
    def _fill_storage_safe(self, wishlist: List[Dict]) -> List[Dict]:
        """
        Fill to meet Storage Index, WITH SAFETY VALVE.
        
        Never exceeds: room_width - SAFETY_BUFFER
        """
        # Calculate current width
        current_width = sum(item.get('width', 60) for item in wishlist)
        max_width = self.room_width - self.SAFETY_BUFFER
        
        # Calculate target (Storage Index)
        target_m = max(self.room_area_m2 * 0.5, 3.0)  # Min 3m
        target_width = target_m * 100  # Convert to cm
        
        # Calculate deficit
        deficit = target_width - current_width
        
        print(f"  Storage: current={current_width}cm, target={target_width:.0f}cm, max={max_width}cm")
        
        # SAFETY VALVE: Can we add anything?
        available_space = max_width - current_width
        
        if deficit <= 0:
            print(f"  [OK] Storage Index already met")
            return wishlist
        
        if available_space < 30:
            print(f"  [SAFETY] No room for more cabinets (only {available_space}cm available)")
            return wishlist
        
        # Fill with drawer cabinets
        filler_width = 60
        items_to_add = min(
            int(deficit / filler_width),  # Items needed for target
            int(available_space / filler_width)  # Items that fit (SAFETY)
        )
        
        if items_to_add > 0:
            print(f"  [FILL] Adding {items_to_add} x drawer_cabinet (60cm each)")
            for _ in range(items_to_add):
                wishlist.append({
                    'type': 'drawer_cabinet',
                    'width': filler_width,
                    'height': 85,
                    'auto': True
                })
        
        # Final check
        final_width = sum(item.get('width', 60) for item in wishlist)
        remaining_deficit = target_width - final_width
        
        if remaining_deficit > 0:
            print(f"  [WARNING] Still {remaining_deficit:.0f}cm short of Storage Index (room too small)")
        
        return wishlist


class WorkflowSolver:
    """
    Pro Workflow Zoning - Professional Kitchen Ergonomics.
    
    Implements the "Production Line" theory:
    Fridge -> Sink -> Prep -> Stove
    
    Key features:
    - Water anchor for WET zone
    - Polarity detection (Storage vs Hot placement)
    - Elastic PREP zone optimization
    - Secondary zone for overflow
    """
    
    def __init__(self, room: Room):
        self.room = room
        self.water_x = self._get_water_position()
    
    def _get_water_position(self) -> int:
        """Get water supply X position from room utilities."""
        for u in self.room.utilities:
            if u.get('type') == 'water':
                return int(u.get('x', self.room.width / 2))
        # Default to center if no water defined
        return int(self.room.width / 2)
    
    def solve_workflow(self, wishlist: List[Dict]) -> Dict[str, Any]:
        """
        Main workflow solving algorithm.
        
        Returns ordered zones with positions optimized for ergonomic flow.
        """
        from .zones import ZONE_CONSTRAINTS, ZoneType
        
        room_width = int(self.room.width)
        
        print(f"\n[Workflow Solver] Room: {room_width}cm, Water at: {self.water_x}cm")
        
        # === STEP 1: Determine what we have ===
        has_fridge = any(i['type'] == 'fridge' for i in wishlist)
        has_pantry = any(i['type'] == 'pantry' for i in wishlist)
        has_sink = any(i['type'] == 'sink_cabinet' for i in wishlist)
        has_dw = any(i['type'] == 'dishwasher' for i in wishlist)
        has_stove = any(i['type'] == 'stove_cabinet' for i in wishlist)
        
        # Get widths
        fridge_w = next((i['width'] for i in wishlist if i['type'] == 'fridge'), 0)
        pantry_w = next((i['width'] for i in wishlist if i['type'] == 'pantry'), 0)
        sink_w = next((i['width'] for i in wishlist if i['type'] == 'sink_cabinet'), 60)
        dw_w = next((i['width'] for i in wishlist if i['type'] == 'dishwasher'), 0)
        stove_w = next((i['width'] for i in wishlist if i['type'] == 'stove_cabinet'), 60)
        
        # === STEP 2: Calculate zone widths ===
        storage_w = fridge_w + pantry_w
        wet_w = sink_w + dw_w
        hot_w = stove_w
        landing_w = 30
        hot_padding = 15
        
        # === STEP 3: Determine polarity (sequence direction) ===
        # If water is on the left, put storage on the right (and vice versa)
        if self.water_x < room_width / 2:
            sequence = 'B'  # Storage on right: Landing-Hot-Prep-Wet-Landing-Storage
            storage_side = 'right'
            print(f"  Polarity: Water LEFT -> Storage RIGHT (Sequence B)")
        else:
            sequence = 'A'  # Storage on left: Storage-Landing-Wet-Prep-Hot-Landing
            storage_side = 'left'
            print(f"  Polarity: Water RIGHT -> Storage LEFT (Sequence A)")
        
        # === STEP 4: Calculate PREP (elastic zone) ===
        fixed_total = storage_w + 2*landing_w + wet_w + hot_w + hot_padding
        prep_available = room_width - fixed_total
        
        print(f"  Fixed zones: {fixed_total}cm, Prep available: {prep_available}cm")
        
        # Validate
        if prep_available < 60:
            print(f"  [CRITICAL] Prep zone too small ({prep_available}cm < 60cm)!")
            prep_w = max(30, prep_available)  # Emergency minimum
            secondary_w = 0
        elif prep_available > 140:
            prep_w = 110  # Ideal
            secondary_w = prep_available - 110
            print(f"  [OVERFLOW] Creating Secondary zone: {secondary_w}cm")
        else:
            prep_w = prep_available
            secondary_w = 0
        
        # === STEP 5: Build zone layout ===
        zones = []
        current_x = 0
        
        if sequence == 'A':
            # Storage-Landing-Wet-Prep-Hot-Landing
            if storage_w > 0:
                zones.append({'type': 'storage', 'x': current_x, 'width': storage_w, 
                             'content': ['fridge', 'pantry'] if has_pantry else ['fridge']})
                current_x += storage_w
            
            zones.append({'type': 'landing', 'x': current_x, 'width': landing_w})
            current_x += landing_w
            
            zones.append({'type': 'wet', 'x': current_x, 'width': wet_w,
                         'content': ['sink', 'dishwasher'] if has_dw else ['sink']})
            current_x += wet_w
            
            zones.append({'type': 'prep', 'x': current_x, 'width': prep_w})
            current_x += prep_w
            
            if secondary_w > 0:
                zones.append({'type': 'secondary', 'x': current_x, 'width': secondary_w})
                current_x += secondary_w
            
            zones.append({'type': 'hot', 'x': current_x, 'width': hot_w,
                         'content': ['stove']})
            current_x += hot_w
            
            # Final landing/padding
            if current_x < room_width:
                zones.append({'type': 'landing', 'x': current_x, 'width': room_width - current_x})
        
        else:  # Sequence B
            # Landing-Hot-Prep-Wet-Landing-Storage
            zones.append({'type': 'landing', 'x': current_x, 'width': hot_padding})
            current_x += hot_padding
            
            zones.append({'type': 'hot', 'x': current_x, 'width': hot_w,
                         'content': ['stove']})
            current_x += hot_w
            
            if secondary_w > 0:
                zones.append({'type': 'secondary', 'x': current_x, 'width': secondary_w})
                current_x += secondary_w
            
            zones.append({'type': 'prep', 'x': current_x, 'width': prep_w})
            current_x += prep_w
            
            zones.append({'type': 'wet', 'x': current_x, 'width': wet_w,
                         'content': ['sink', 'dishwasher'] if has_dw else ['sink']})
            current_x += wet_w
            
            zones.append({'type': 'landing', 'x': current_x, 'width': landing_w})
            current_x += landing_w
            
            if storage_w > 0:
                zones.append({'type': 'storage', 'x': current_x, 'width': storage_w,
                             'content': ['fridge', 'pantry'] if has_pantry else ['fridge']})
                current_x += storage_w
        
        # Print layout
        print(f"\n  Zone Layout:")
        for z in zones:
            print(f"    {z['type'].upper():10} {z['x']:4}-{z['x']+z['width']:<4} ({z['width']}cm)")
        
        # Build volumes by expanding zones into actual items from wishlist
        volumes = []
        
        # Map item types to zones
        zone_item_map = {
            'storage': ['fridge', 'pantry', 'oven_tower'],
            'wet': ['sink_cabinet', 'dishwasher'],
            'hot': ['stove_cabinet'],
            'prep': ['drawer_cabinet'],
            'landing': ['drawer_cabinet'],
            'secondary': ['drawer_cabinet', 'coffee_station', 'wine_rack'],
        }
        
        for z in zones:
            zone_type = z['type']
            zone_x = z['x']
            zone_w = z['width']
            
            # Get items that belong to this zone
            zone_items = [item for item in wishlist 
                         if item['type'] in zone_item_map.get(zone_type, [])]
            
            if zone_items:
                # Place actual items from wishlist
                item_x = zone_x
                for item in zone_items:
                    item_w = item.get('width', 60)
                    item_h = item.get('height', 85)
                    item_type = item['type']
                    
                    # Detect monolith (tall units)
                    is_monolith = item_type in ['fridge', 'pantry', 'oven_tower', 'pull_out_pantry'] or item_h > 150
                    
                    if item_x + item_w <= zone_x + zone_w + 5:  # Slight tolerance
                        volumes.append({
                            'x': item_x,
                            'width': item_w,
                            'function': item_type,  # Actual item type!
                            'metadata': {
                                'zone_type': zone_type,
                                'height': item_h,
                                'is_monolith': is_monolith
                            }
                        })
                        item_x += item_w
                
                # Fill remaining zone space with default
                remaining = zone_x + zone_w - item_x
                if remaining >= 20:
                    volumes.append({
                        'x': item_x,
                        'width': remaining,
                        'function': 'drawer_cabinet',
                        'metadata': {'zone_type': zone_type, 'auto_fill': True}
                    })
            else:
                # No specific items for this zone - use zone type as function
                volumes.append({
                    'x': zone_x,
                    'width': zone_w,
                    'function': zone_type,
                    'metadata': {'zone_type': zone_type}
                })
        
        return {
            'workflow_sequence': sequence,
            'zones': zones,
            'volumes': volumes,
            'prep_width': prep_w,
            'secondary_width': secondary_w,
            'storage_side': storage_side,
            'wishlist': wishlist  # Pass through for reference
        }


class KitchenSolver:
    def __init__(self, room: Room):
        self.room = room
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
    def create_zones_from_wishlist(self, wishlist: List[Dict]) -> List[Zone]:
        """
        Phase 1: Convert Item Wishlist into Functional Zones (Elastic Architecture).
        """
        zones = []
        
        # Analyze content
        counts = {}
        for item in wishlist:
            t = item['type']
            counts[t] = counts.get(t, 0) + 1
            
        # 1. Tall Zones (Fridge, Pantry) - Separate Zones
        # They usually anchor edges.
        for item in wishlist:
            if item['type'] == 'fridge':
                zones.append(ZoneFactory.create_fridge_zone(width=item['width'], height=item.get('height', 215)))
            elif item['type'] == 'pantry':
                z = ZoneFactory.create_fridge_zone(width=item['width'], height=item.get('height', 215))
                z.type = 'pantry'
                zones.append(z)
                
        # 2. Wet Zone (Sink + Dishwasher)
        has_sink = counts.get('sink_cabinet', 0) > 0
        has_dw = counts.get('dishwasher', 0) > 0
        
        if has_sink:
            sink_w = next(i['width'] for i in wishlist if i['type'] == 'sink_cabinet')
            dw_w = next(i['width'] for i in wishlist if i['type'] == 'dishwasher') if has_dw else 0
            zones.append(ZoneFactory.create_wet_zone(sink_w, dw_w))
            
        # 3. Cooking Zone (Stove)
        if counts.get('stove_cabinet', 0) > 0:
            stove_w = next(i['width'] for i in wishlist if i['type'] == 'stove_cabinet')
            zones.append(ZoneFactory.create_cooking_zone(stove_w))
            
        # 4. Prep / Storage Zones
        base_cabs = [i for i in wishlist if i['type'] == 'base_cabinet']
        for bc in base_cabs:
             # Map each requested base_cabinet to a Prep/Storage zone.
             z = ZoneFactory.create_prep_zone(ideal=bc['width'])
             zones.append(z)
             
        # 5. Fillers handled via elasticity
        
        return zones
    
    # ========== L-SHAPE SUPPORT ==========
    
    def detect_optimal_shape(self, wishlist: List[Dict]) -> str:
        """
        Auto-detect whether I-shape or L-shape is optimal.
        
        Rule: If total item width exceeds 90% of main wall, switch to L.
        """
        total_width = sum(item.get('width', 60) for item in wishlist)
        main_wall = int(self.room.width)
        
        # Leave 10% buffer for fillers/gaps
        if total_width <= main_wall * 0.9:
            return 'I'
        else:
            return 'L'
    
    def solve_l_shape(self, wishlist: List[Dict], wall_wishlist: List[Dict] = None,
                      corner_type: str = 'blind') -> Optional[Dict[str, Any]]:
        """
        Solve L-shape kitchen with CORRECT architecture:
        
        Real L-Kitchen Layout:
        - Corner module at intersection (65-90cm)
        - Arm A (back wall): base cabinets (85cm) - workbench
        - Arm B (side wall): base cabinets (85cm) - ends with Monolith
        - Monolith (fridge/pantry) at FAR END of Arm B, not at corner!
        
        ┌─────────────┐
        │   MONOLITH  │  ← Tall items at END
        │  (Fridge)   │
        ├─────────────┤
        │  Base Cabs  │  Arm B (85cm)
        ├─────────────┤
        │   CORNER    │──────────────────────┐
        │   MODULE    │    Base Cabinets     │ Arm A (85cm)
        └─────────────┴──────────────────────┘
        """
        from .geometry import CornerModule
        
        wall_wishlist = wall_wishlist or []
        self.validate_wishlist(wishlist, wall_wishlist)
        
        # Determine corner module
        if corner_type == 'carousel':
            corner = CornerModule.carousel()
        elif corner_type == 'diagonal':
            corner = CornerModule.diagonal()
        else:
            corner = CornerModule.blind()
        
        corner_size = corner.size
        
        # Calculate arm lengths
        arm_a_length = int(self.room.width) - corner_size  # Main wall (back)
        arm_b_length = int(self.room.wall_b_length or self.room.length) - corner_size  # Side wall
        
        print(f"  L-Shape: Corner={corner.type}({corner_size}cm)")
        print(f"  Arm A (back): {arm_a_length}cm, Arm B (side): {arm_b_length}cm")
        
        # Classify items
        tall_items = []
        base_items = []
        TALL_THRESHOLD = 150
        
        for item in wishlist:
            item_h = item.get('height', 85)
            if item_h > TALL_THRESHOLD or item['type'] in ['fridge', 'pantry', 'oven_tower']:
                tall_items.append(item)
            else:
                base_items.append(item)
        
        # Calculate Monolith width (at END of Arm B)
        monolith_width = sum(i.get('width', 60) for i in tall_items)
        
        # Arm B available for base cabinets (after reserving space for Monolith at end)
        arm_b_base_length = arm_b_length - monolith_width
        
        print(f"  Monolith: {monolith_width}cm (at end of Arm B)")
        print(f"  Arm B base zone: {arm_b_base_length}cm")
        
        # === SOLVE ARM A (Back Wall - Main Workbench) ===
        # Contains: Sink, Cooktop, DW, prep cabinets
        # === SOLVE ARM A (Back Wall - Main Workbench) ===
        # Contains: Sink, Cooktop, DW, prep cabinets
        
        # We need to place base_items into the available space on Arm A
        # Space available:
        arm_a_start = corner_size
        arm_a_end = corner_size + arm_a_length
        current_x = arm_a_start
        
        volumes = []
        
        # Simply place items sequentially for now (basic strategy)
        # TODO: Use WorkflowSolver logic here for true ergonomics on Arm A
        
        # Sort items by priority/flow if needed, or just take them as is
        # Workflow: Sink -> Prep -> Cook is ideal.
        
        # Let's try to order them: Sink, DW, Prep, Stove
        ordered_items = []
        
        # 1. Sink & DW
        sink_items = [i for i in base_items if i['type'] in ['sink_cabinet', 'dishwasher', 'wet']]
        other_items = [i for i in base_items if i not in sink_items]
        
        ordered_items.extend(sink_items)
        ordered_items.extend(other_items)
        
        for item in ordered_items:
            w = item.get('width', 60)
            if current_x + w <= arm_a_end:
                volumes.append({
                    'x': current_x,
                    'width': w,
                    'function': item['type'],
                    'metadata': {'height': item.get('height', 85)}
                })
                current_x += w
            else:
                print(f"  [WARNING] Item {item['type']} ({w}cm) does not fit on Arm A")
        
        # Fill remaining space with filler/prep
        remaining = arm_a_end - current_x
        if remaining >= 20:
             volumes.append({
                'x': current_x,
                'width': remaining,
                'function': 'drawer_cabinet', 
                'metadata': {'height': 85, 'auto_fill': True}
            })
            
        arm_a_skeleton = {'volumes': volumes, 'wall_wishlist': wall_wishlist}
        
        if arm_a_skeleton is None:
            return None
        
        # === BUILD ARM B (Side Wall) ===
        arm_b_volumes = []
        
        # 1. Base cabinets on Arm B (from corner to Monolith)
        if arm_b_base_length > 30:  # Only if there's meaningful space
            # Simple fill with base cabinets
            current_z = corner_size
            while current_z < corner_size + arm_b_base_length - 5:
                cab_width = min(60, corner_size + arm_b_base_length - current_z)
                if cab_width < 20:
                    break
                arm_b_volumes.append({
                    'x': 0,
                    'z': current_z,
                    'width': cab_width,
                    'function': 'storage',
                    'metadata': {'height': 85, 'arm': 'B', 'axis': 'Z'}
                })
                current_z += cab_width
        
        # 2. Monolith at END of Arm B (farthest from corner)
        monolith_z = corner_size + arm_b_base_length
        for item in tall_items:
            arm_b_volumes.append({
                'x': 0,
                'z': monolith_z,
                'width': item.get('width', 60),
                'function': item['type'],
                'metadata': {
                    'height': item.get('height', 215),
                    'arm': 'B',
                    'is_monolith': True,
                    'axis': 'Z'
                }
            })
            monolith_z += item.get('width', 60)
        
        # === BUILD SKELETON ===
        skeleton = {
            'shape': 'L',
            'corner': {
                'type': corner.type,
                'size': corner_size,
                'x': 0,
                'z': 0
            },
            'arm_a': {
                'start': corner_size,
                'end': corner_size + arm_a_length,
                'axis': 'X',
                'height': 85,
                'volumes': arm_a_skeleton['volumes']
            },
            'arm_b': {
                'start': corner_size,
                'end': corner_size + arm_b_length,
                'axis': 'Z',
                'height': 85,
                'monolith_start': corner_size + arm_b_base_length,
                'volumes': arm_b_volumes
            },
            'volumes': arm_a_skeleton['volumes'] + arm_b_volumes,
            'wall_wishlist': wall_wishlist
        }
        
        return skeleton
    def solve_masses(self, wishlist: List[Dict]) -> Dict[str, Any]:
        """
        Premium V3: Mass Allocation - separates kitchen into Monolith and Workbench.
        
        Monolith: Tall block (Fridge, Pantry, Oven Tower) - placed at room edge
        Workbench: Working line (Sink, Cooktop, Prep) - clean horizontal flow
        
        Returns:
            {
                'monolith': {'start': x, 'end': x, 'items': [...]},
                'workbench': {'start': x, 'end': x, 'items': [...]},
                'monolith_edge': 'left' or 'right'
            }
        """
        # Classify items by height
        tall_items = []
        base_items = []
        
        TALL_THRESHOLD = 150  # cm
        
        for item in wishlist:
            item_h = item.get('height', 85)
            if item_h > TALL_THRESHOLD or item['type'] in ['fridge', 'pantry', 'oven_tower']:
                tall_items.append(item)
            else:
                base_items.append(item)
        
        # Calculate required widths
        monolith_width = sum(i.get('width', 60) for i in tall_items)
        workbench_width = sum(i.get('width', 60) for i in base_items)
        room_width = int(self.room.width)
        
        # Decide Monolith edge (prefer left, unless windows block it)
        windows_on_left = any(
            w.get('wall') == 'back' and w.get('x', 0) < room_width / 2 
            for w in (self.room.windows or [])
        )
        
        if windows_on_left:
            monolith_edge = 'right'
        else:
            monolith_edge = 'left'
        
        # Calculate ranges
        if monolith_edge == 'left':
            monolith_start = 0
            monolith_end = monolith_width
            workbench_start = monolith_end + 2  # 2cm gap for visual separation
            workbench_end = room_width
        else:
            workbench_start = 0
            workbench_end = room_width - monolith_width - 2
            monolith_start = room_width - monolith_width
            monolith_end = room_width
        
        return {
            'monolith': {
                'start': monolith_start,
                'end': monolith_end,
                'width': monolith_width,
                'items': tall_items
            },
            'workbench': {
                'start': workbench_start,
                'end': workbench_end,
                'width': workbench_end - workbench_start,
                'items': base_items
            },
            'monolith_edge': monolith_edge
        }
    
    def solve_v3_premium(self, wishlist: List[Dict], wall_wishlist: List[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Premium V3 Solver with Mass Allocation.
        
        Pipeline:
        1. Mass Allocation (Monolith vs Workbench)
        2. Zone Solving within each mass
        3. Returns enhanced skeleton with mass info
        """
        wall_wishlist = wall_wishlist or []
        self.validate_wishlist(wishlist, wall_wishlist)
        
        # Phase 1: Mass Allocation
        masses = self.solve_masses(wishlist)
        print(f"  Mass Allocation: Monolith={masses['monolith']['width']}cm on {masses['monolith_edge']}")
        print(f"  Workbench zone: {masses['workbench']['start']}-{masses['workbench']['end']}cm")
        
        # Phase 2: Solve Workbench (using existing zone logic)
        workbench_zones = self.create_zones_from_wishlist(masses['workbench']['items'])
        
        # Solve zones within workbench range
        skeleton = self._solve_zones_in_range(
            workbench_zones, 
            masses['workbench']['start'], 
            masses['workbench']['end'],
            wall_wishlist
        )
        
        if skeleton is None:
            return None
        
        # Add Monolith items directly (they're rigid blocks)
        monolith_x = masses['monolith']['start']
        for item in masses['monolith']['items']:
            skeleton['volumes'].append({
                'x': monolith_x,
                'width': item.get('width', 60),
                'function': item['type'],
                'metadata': {'height': item.get('height', 215), 'is_monolith': True}
            })
            monolith_x += item.get('width', 60)
        
        # Attach mass info to skeleton
        skeleton['masses'] = masses
        
        return skeleton
    
    def _solve_zones_in_range(self, zones: List[Zone], start: int, end: int, wall_wishlist: List[Dict]) -> Optional[Dict[str, Any]]:
        """
        Solve zones constrained to a specific X range.
        """
        # Handle empty zones case
        if not zones:
            return {'volumes': [], 'wall_wishlist': wall_wishlist}
        
        model = cp_model.CpModel()
        zone_vars = {}
        range_width = end - start
        
        for i, z in enumerate(zones):
            w_var = model.NewIntVar(z.min_width, z.max_width, f'z_{i}_width')
            s_var = model.NewIntVar(0, range_width, f'z_{i}_start')
            e_var = model.NewIntVar(0, range_width, f'z_{i}_end')
            inv_var = model.NewIntervalVar(s_var, w_var, e_var, f'z_{i}_inv')
            
            zone_vars[i] = {
                'zone': z,
                'start': s_var,
                'end': e_var,
                'width': w_var,
                'interval': inv_var
            }
        
        # Constraints
        model.AddNoOverlap([v['interval'] for v in zone_vars.values()])
        for v in zone_vars.values():
            model.Add(v['end'] <= range_width)
        
        # Penalties
        penalties = []
        for i, v in zone_vars.items():
            z = v['zone']
            if z.compressibility != 'hard':
                diff = model.NewIntVar(0, range_width, f'diff_{i}')
                model.Add(diff >= v['width'] - z.ideal_width)
                model.Add(diff >= z.ideal_width - v['width'])
                penalties.append(diff * 10)
        
        # Gap minimization
        total_width = model.NewIntVar(0, range_width * 2, 'total_width')
        model.Add(total_width == sum(v['width'] for v in zone_vars.values()))
        gap = model.NewIntVar(0, range_width, 'gap')
        model.Add(gap == range_width - total_width)
        model.Add(total_width <= range_width)
        penalties.append(gap * 100)
        
        model.Minimize(sum(penalties))
        
        solver = cp_model.CpSolver()
        status = solver.Solve(model)
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            skeleton = {'volumes': []}
            for i, v in zone_vars.items():
                z = v['zone']
                skeleton['volumes'].append({
                    'x': start + solver.Value(v['start']),  # Offset by range start
                    'width': solver.Value(v['width']),
                    'function': z.type,
                    'metadata': z.metadata
                })
            skeleton['wall_wishlist'] = wall_wishlist
            return skeleton
        
        return None
        
    def validate_wishlist(self, wishlist: List[Dict], wall_wishlist: List[Dict]):
        """
        Enforce cardinality rules.
        """
        counts = {}
        for item in wishlist + (wall_wishlist or []):
            t = item['type']
            counts[t] = counts.get(t, 0) + 1
            
        one_of_a_kind = ['fridge', 'sink_cabinet', 'stove_cabinet', 'dishwasher']
        for t in one_of_a_kind:
            if counts.get(t, 0) > 1:
                raise ValueError(f"Validation Error: You can have at most ONE '{t}'. Found {counts[t]}.")
                
        stoves = counts.get('stove_cabinet', 0)
        hoods = counts.get('hood', 0)
        
        if stoves > 0 and hoods == 0:
            print("Warning: Stove present without Hood.")
        
        if hoods > stoves:
             raise ValueError(f"Found {hoods} hoods but only {stoves} stoves. Cannot have more hoods than stoves.")

    def solve(self, wishlist: List[Dict], wall_wishlist: List[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        New V2 Solve: Elastic Zones.
        Returns a 'Skeleton' dictionary describing functional volumes.
        """
        # Default behavior: Return optimal
        skeletons = self.solve_scenarios(wishlist, wall_wishlist, limit=1)
        return skeletons[0] if skeletons else None

    def solve_scenarios(self, wishlist: List[Dict], wall_wishlist: List[Dict], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Generates top N valid layout scenarios for evaluation.
        """
        wall_wishlist = wall_wishlist or []
        self.validate_wishlist(wishlist, wall_wishlist)
        base_zones = self.create_zones_from_wishlist(wishlist)
        
        return self.solve_zones_multiple(base_zones, wall_wishlist, limit)

    def _build_zone_model(self, base_zones, room_w):
        """
        Internal: Builds the CP Model for Zones.
        Returns (model, zone_vars, objective_expr)
        """
        model = cp_model.CpModel()
        zone_vars = {}
        
        # 0. Forbidden Zones
        forbidden_intervals = []
        features = (self.room.windows or []) + (self.room.doors or [])
        for f in features:
            if f.get('wall') == 'back':
                forbidden_intervals.append((f['x'], f['x'] + f['width'], f.get('y', 0)))

        # 1. Base Variables
        for i, z in enumerate(base_zones):
            # Width Variable
            w_var = model.NewIntVar(z.min_width, z.max_width, f'z_{i}_width')
            # Start/End Variables
            s_var = model.NewIntVar(0, room_w, f'z_{i}_start')
            e_var = model.NewIntVar(0, room_w, f'z_{i}_end')
            # Interval
            inv_var = model.NewIntervalVar(s_var, w_var, e_var, f'z_{i}_inv')
            
            zone_vars[i] = {
                'zone': z,
                'start': s_var,
                'end': e_var,
                'width': w_var,
                'interval': inv_var
            }
            
            # Forbidden Zone Checks (Hard constraints)
            if z.type in ['fridge', 'pantry']:
                for fx, f_end, sill in forbidden_intervals:
                     if z.metadata.get('height', 215) > sill:
                         before = model.NewBoolVar(f'z_{i}_before_{fx}')
                         after = model.NewBoolVar(f'z_{i}_after_{fx}')
                         model.Add(e_var <= int(fx)).OnlyEnforceIf(before)
                         model.Add(s_var >= int(f_end)).OnlyEnforceIf(after)
                         model.AddBoolOr([before, after])
        
        # 2. Constraints
        model.AddNoOverlap([v['interval'] for v in zone_vars.values()])
        for v in zone_vars.values():
            model.Add(v['end'] <= room_w)

        penalties = []

        # C. Ideal Width
        for i, v in zone_vars.items():
            z = v['zone']
            if z.compressibility != 'hard':
                diff = model.NewIntVar(0, room_w, f'diff_{i}')
                ideal = z.ideal_width
                model.Add(diff >= v['width'] - ideal)
                model.Add(diff >= ideal - v['width'])
                penalties.append(diff * 10) 
                
        # D. Gap Minimization
        total_width = model.NewIntVar(0, room_w * 2, 'total_width')
        model.Add(total_width == sum(v['width'] for v in zone_vars.values()))
        gap_total = model.NewIntVar(0, room_w, 'gap_total')
        model.Add(gap_total == room_w - total_width)
        model.Add(total_width <= room_w)
        penalties.append(gap_total * 100) 
        
        # E. Order / Grouping
        for i, v in zone_vars.items():
            z = v['zone']
            if z.type in ['fridge', 'pantry']:
                dist = model.NewIntVar(0, room_w, f'dist_edge_{i}')
                rem_space = model.NewIntVar(0, room_w, f'rem_{i}')
                model.Add(rem_space == room_w - v['end'])
                model.AddMinEquality(dist, [v['start'], rem_space])
                penalties.append(dist * 50)

        # Objective Variable
        total_penalty = model.NewIntVar(0, 1000000, 'total_penalty')
        model.Add(total_penalty == sum(penalties))
        
        return model, zone_vars, total_penalty

    def solve_zones_multiple(self, base_zones: List[Zone], wall_wishlist: List[Dict], limit: int) -> List[Dict[str, Any]]:
        room_w = int(self.room.width)
        model, zone_vars, objective_var = self._build_zone_model(base_zones, room_w)
        
        # Step 1: Solve for Optimal to define bounds
        solver_opt = cp_model.CpSolver()
        model.Minimize(objective_var)
        status = solver_opt.Solve(model)
        
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return []
            
        best_score = solver_opt.Value(objective_var)
        print(f"Optimal Score: {best_score}")
        
        # Step 2: Enumerate "Good" solutions (within 20% of best)
        # We need to Clear Objective to enumerate
        model.Proto().objective.Clear() 
        # Add constraint: score <= best * 1.5
        model.Add(objective_var <= int(best_score * 1.5))
        
        # Prepare enumeration
        solver_enum = cp_model.CpSolver()
        solver_enum.parameters.enumerate_all_solutions = True
        
        class SolutionCollector(cp_model.CpSolverSolutionCallback):
            def __init__(self, vars_map, limit, wall_wl):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self.vars_map = vars_map
                self.limit = limit
                self.wall_wl = wall_wl
                self.solutions = []

            def on_solution_callback(self):
                if len(self.solutions) >= self.limit:
                    self.StopSearch()
                    return
                
                # Extract solution
                skeleton = {'volumes': []}
                for i, v in self.vars_map.items():
                    z = v['zone']
                    skeleton['volumes'].append({
                        'x': self.Value(v['start']),
                        'width': self.Value(v['width']),
                        'function': z.type,
                        'metadata': z.metadata
                    })
                skeleton['wall_wishlist'] = self.wall_wl
                # Add score for reference?
                # score = self.Value(objective_var_ref) # Not accessible easily unless passed
                self.solutions.append(skeleton)
                
        collector = SolutionCollector(zone_vars, limit, wall_wishlist)
        solver_enum.Solve(model, collector)
        
        return collector.solutions

    # Legacy method for compatibility if needed, but we rerouted solve()
    def solve_zones(self, base_zones, wall_wishlist):
        return self.solve_zones_multiple(base_zones, wall_wishlist, 1)[0]
