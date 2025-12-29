from typing import List, Tuple, Union, Optional
try:
    from shapely.geometry import Polygon, Point, box
    from shapely.ops import unary_union
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False
    # Fallback or error handling if needed, but blueprint requires Shapely.
    # We will define dummy classes to avoid import errors during static analysis if shapely is missing,
    # but runtime will fail if used.
class SimpleBox:
    def __init__(self, x, y, x2, y2):
        self.bounds = (min(x, x2), min(y, y2), max(x, x2), max(y, y2))
    
    @property
    def minx(self): return self.bounds[0]
    @property
    def miny(self): return self.bounds[1]
    @property
    def maxx(self): return self.bounds[2]
    @property
    def maxy(self): return self.bounds[3]

    def intersects(self, other):
        return not (self.maxx <= other.minx or self.minx >= other.maxx or
                    self.maxy <= other.miny or self.miny >= other.maxy)

class GeometryEngine:
    @staticmethod
    def create_rect(x: float, y: float, width: float, depth: float) -> Union['Polygon', SimpleBox]:
        if HAS_SHAPELY:
            return box(x, y, x + width, y + depth)
        else:
            return SimpleBox(x, y, x + width, y + depth)

    @staticmethod
    def create_buffer(shape: Union['Polygon', SimpleBox], distance: float) -> Union['Polygon', SimpleBox]:
        if HAS_SHAPELY:
            return shape.buffer(distance)
        else:
            # Simple buffer for box = larger box
            if isinstance(shape, SimpleBox):
                return SimpleBox(shape.minx - distance, shape.miny - distance, 
                                 shape.maxx + distance, shape.maxy + distance)
            return shape # Should not happen in fallback mode

    @staticmethod
    def check_collision(shape1: Union['Polygon', SimpleBox], shape2: Union['Polygon', SimpleBox]) -> bool:
        if HAS_SHAPELY:
            return shape1.intersects(shape2)
        else:
            if hasattr(shape1, 'intersects'):
                return shape1.intersects(shape2)
            return False

    @staticmethod
    def get_union(shapes: List[Union['Polygon', SimpleBox]]) -> Union['Polygon', SimpleBox]:
        if HAS_SHAPELY:
            return unary_union(shapes)
        else:
            # Fallback union not implemented for complex shapes
            return shapes[0] if shapes else None
