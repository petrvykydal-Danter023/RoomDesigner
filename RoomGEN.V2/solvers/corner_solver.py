from typing import List, Dict, Any, Literal
from core.room_parser import CornerNode, WallSegment

class CornerSolver:
    @staticmethod
    def solve(corner: CornerNode, budget: str = "standard") -> Dict[str, Any]:
        """
        Determines the corner module and updates adjacent walls.
        """
        if corner.type != 'inner':
            # Outer corners usually have no cabinets wrapping around, or special handling
            return {"type": "outer_corner_void"}

        # Inner Corner Strategy
        # Size: 65x65 (Blind) or 90x90 (Carousel)
        
        module_type = "blind_corner"
        size_a = 65.0 # Along wall_in (reversed? wait. Blind corner is usually 110x65)
        size_b = 65.0 # Along wall_out
        
        # Simplified logic for prototype:
        if budget == "high":
            module_type = "carousel_corner"
            size_a = 90.0
            size_b = 90.0
        else:
            # Standard Blind Corner
            # Occupies 110cm on one wall, 65cm on the other (void)
            # Let's assume symmetric 65x65 void for now for simpler filling, 
            # Or actually blind corner is a cabinet.
            # Let's implement the specific Blind Corner logic:
            # A 110cm cabinet placed in corner. 
            # One side is 65cm deep (void), the other is 110cm long.
            # For this Phase 3, let's treat it as a symmetric reservation of space
            # to keep it simple, or asymmetric if we want realism.
            
            # Let's go with symmetric 65x65 "Dead Corner" reservation
            # And then we place cabinets starting after 65cm.
            module_type = "blind_void"
            size_a = 65.0
            size_b = 65.0
            
        # Reserve space on walls
        # Wall In: Ends at corner. So end_reserved = size_a
        corner.wall_in.end_reserved = size_a
        
        # Wall Out: Starts at corner. So start_reserved = size_b
        corner.wall_out.start_reserved = size_b
        
        # Solution Dict
        solution = {
            "type": module_type,
            "size_in": size_a,
            "size_out": size_b,
            "visual_element": "corner_post" if module_type == "blind_void" else module_type
        }
        corner.module = solution
        return solution
