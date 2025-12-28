from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import math

@dataclass
class Vector3:
    x: float
    y: float
    z: float

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        return cls(d.get('x', 0), d.get('y', 0), d.get('z', 0))

    def dist(self, other: 'Vector3') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)

class GhostChef:
    def __init__(self):
        self.workflows = {
            "make_pasta": ["fridge", "wet", "cooking", "wet", "cooking", "serving"],
            "morning_coffee": ["pantry", "wet", "cooking", "serving"],
            "unload_groceries": ["serving", "fridge", "pantry"] 
            # 'serving' is usually an entry point or table. Let's assume X=RoomWidth/2 for entry if not defined.
        }
        
    def evaluate_skeleton(self, skeleton: Dict[str, Any], room_width: float) -> float:
        """
        Simulates workflows on the skeleton layout and returns a 'Cost' (lower is better).
        Cost is primarily travel distance.
        """
        volumes = skeleton['volumes']
        # Map function to center position
        zone_map = {}
        for v in volumes:
            func = v['function']
            center = Vector3(v['x'] + v['width']/2, 0, v['metadata'].get('depth', 60)) # Approximate Z
            
            # Handle multiple zones of same type? (e.g. 2 prep zones)
            # For simplicity, keep list
            if func not in zone_map:
                zone_map[func] = []
            zone_map[func].append(center)
            
        # Helper to get closest zone of type
        def get_pos(func_name: str, current_pos: Vector3) -> Vector3:
            if func_name == "serving":
                # Assume Door/Entry. Let's fake it as Center of Room for now, or X=0
                return Vector3(room_width / 2, 0, 150) # Middle of room
                
            candidates = zone_map.get(func_name)
            if not candidates:
                # Fallback mapping
                if func_name == "pantry": candidates = zone_map.get("fridge") # Fallback to fridge
                if func_name == "serving": candidates = [Vector3(0,0,0)]
                
            if not candidates:
                return current_pos # Stay put if missing (penalty?)
                
            # Return closest
            return min(candidates, key=lambda p: p.dist(current_pos))

        total_distance = 0.0
        
        for name, routine in self.workflows.items():
            # Start at entry
            pos = Vector3(room_width/2, 0, 150) 
            
            for step in routine:
                target = get_pos(step, pos)
                dist = pos.dist(target)
                total_distance += dist
                pos = target
                
        return total_distance
