from ortools.sat.python import cp_model
from typing import List, Dict, Optional, Any
from .geometry import Room
from .zones import Zone, ZoneFactory

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
