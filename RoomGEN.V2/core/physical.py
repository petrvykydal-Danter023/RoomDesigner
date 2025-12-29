from typing import Dict, Any, List
from .geometry import GeometryEngine

class PhysicalRules:
    
    @staticmethod
    def apply_service_void(item: Dict[str, Any], gap: float = 5.0) -> Dict[str, Any]:
        """
        Shifts the cabinet body by 'gap' from the wall (y-axis relative).
        Assumes item['y'] is the wall position.
        The visual front remains at y + depth + gap? 
        Actually, usually cabinet back is at y=gap. 
        """
        # Create a copy to avoid mutating original if needed, 
        # but here we return specific checks or modified coords.
        # Simple implementation: shift Y by 5cm
        new_item = item.copy()
        new_item['y'] += gap
        new_item['service_void'] = gap
        return new_item

    @staticmethod
    def check_corner_guard(wall_a_items: List[Dict[str, Any]], wall_b_items: List[Dict[str, Any]], corner_size: float = 5.0) -> bool:
        """
        Checks if the first item on Wall A and first on Wall B leave enough space for corner guard.
        Assumption: Walls meet at (0,0).
        Wall A grows along X+, Wall B grows along Y+ (simplified L-shape).
        """
        # Find item closest to corner (0,0)
        # For Wall A (y=0, x varies), min x should be >= corner_size
        min_x_a = min((i['x'] for i in wall_a_items), default=0)
        
        # For Wall B (x=0, y varies), min y should be >= corner_size
        min_y_b = min((i['y'] for i in wall_b_items), default=0)

        return min_x_a >= corner_size and min_y_b >= corner_size

    @staticmethod
    def calculate_worktop_height(user_height: float) -> float:
        """
        Bio-Metric Tuning:
        Elbow height ~ 0.63 * user_height
        Worktop = Elbow - 15cm
        """
        elbow_height = user_height * 0.63
        return elbow_height - 15.0
