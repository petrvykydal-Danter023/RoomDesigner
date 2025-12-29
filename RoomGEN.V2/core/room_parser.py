import math
from typing import List, Tuple, Dict, Optional, Literal

class WallSegment:
    def __init__(self, p1: Tuple[float, float], p2: Tuple[float, float], index: int):
        self.p1 = p1
        self.p2 = p2
        self.index = index
        self.length = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        self.vector = (p2[0] - p1[0], p2[1] - p1[1])
        # Vector normalized
        mag = math.sqrt(self.vector[0]**2 + self.vector[1]**2)
        if mag > 0:
            self.dir = (self.vector[0]/mag, self.vector[1]/mag)
        else:
            self.dir = (0, 0)
        
        # Available length for furniture (starts as full length)
        self.available_length = self.length
        self.start_reserved = 0.0 # From previous corner
        self.end_reserved = 0.0   # From next corner
        self.features: List[Dict[str, Any]] = [] # Windows, Doors, etc.

class CornerNode:
    def __init__(self, wall_in: WallSegment, wall_out: WallSegment):
        self.wall_in = wall_in
        self.wall_out = wall_out
        self.angle_deg = self._calculate_angle()
        self.type = self._determine_type()
        self.module: Optional[Dict] = None

    def _calculate_angle(self) -> float:
        # Vector A: wall_in (points to corner)
        # Vector B: wall_out (points away from corner)
        # However, wall_in struct points p1->p2. If p2 is corner, vector is correct.
        
        dx1, dy1 = self.wall_in.vector 
        dx2, dy2 = self.wall_out.vector
        
        # Angle of vector 1
        a1 = math.atan2(dy1, dx1)
        # Angle of vector 2
        a2 = math.atan2(dy2, dx2)
        
        diff = math.degrees(a2 - a1)
        # Wrap to [0, 360) or similar?
        # We want the interior angle.
        # This simple math might need adjustment based on polygon winding (CW vs CCW).
        # Assuming CCW winding for standard polygons usually.
        
        angle = (180 - diff) % 360 
        return angle

    def _determine_type(self) -> Literal['inner', 'outer', 'straight']:
        # Roughly: < 180 is inner, > 180 is outer (reflex)
        # But heavily depends on winding order.
        # For a standard room, 90 deg corners.
        # If we trace perimeter, a left turn (CCW) is usually an inner corner in a room? 
        # Actually usually room is defined by inner walls.
        
        # Let's simplify: 
        # If angle is approx 90 -> Inner (standard corner)
        # If angle is approx 270 -> Outer (projecting corner)
        
        ang = self.angle_deg
        if 80 <= ang <= 100:
            return 'inner'
        elif 260 <= ang <= 280:
            return 'outer'
        else:
            return 'straight' # or custom

class RoomParser:
    @staticmethod
    def parse_polygon(coords: List[Tuple[float, float]]) -> Tuple[List[WallSegment], List[CornerNode]]:
        walls = []
        n = len(coords)
        if coords[0] == coords[-1]:
            coords = coords[:-1] # Remove duplicate closing point if present
            n -= 1
            
        for i in range(n):
            p1 = coords[i]
            p2 = coords[(i+1) % n]
            walls.append(WallSegment(p1, p2, i))
            
        corners = []
        for i in range(n):
            w_in = walls[i]
            w_out = walls[(i+1) % n]
            corners.append(CornerNode(w_in, w_out))
            
        return walls, corners
