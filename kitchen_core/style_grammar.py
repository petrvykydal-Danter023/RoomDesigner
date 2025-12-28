from typing import Dict, Any, List
import math
import statistics

class StyleCritic:
    def __init__(self):
        # Weights for different style aspects
        self.weights = {
            'symmetry': 1.0,
            'rhythm': 2.0,      # Consistency of widths
            'alignment': 1.5    # Alignment to grid (e.g. 15cm steps)
        }
        
    def evaluate(self, skeleton: Dict[str, Any], room_width: float) -> float:
        """
        Returns a 'Style Cost' (lower is better, 0 is perfect).
        """
        cost = 0.0
        
        volumes = skeleton['volumes']
        widths = [v['width'] for v in volumes]
        xs = [v['x'] for v in volumes]
        
        # 1. Rhythm (Variance of Widths)
        # We prefer fewer unique widths. e.g. [60, 60, 60] is better than [45, 60, 20]
        # Calculate standard deviation relative to mean? 
        # Or count unique width buckets (snapped to 5cm)?
        if widths:
            # Bucket widths to nearest 10cm to group similar ones
            buckets = set([round(w / 10) * 10 for w in widths])
            # Penalty for high number of unique buckets
            cost += (len(buckets) - 1) * 100 * self.weights['rhythm']
            
            # Variance
            if len(widths) > 1:
                stdev = statistics.stdev(widths)
                cost += stdev * self.weights['rhythm']

        # 2. Alignment (Grid Snap)
        # Check if starts/widths are multiples of standard increments (e.g. 10cm or 5cm)
        grid_step = 10
        alignment_misses = 0
        for x in xs:
            if x % grid_step != 0:
                alignment_misses += 1
        for w in widths:
            if w % grid_step != 0:
                alignment_misses += 1
                
        cost += alignment_misses * 50 * self.weights['alignment']
        
        # 3. Symmetry (Center Mass)
        # Calculate center of mass of volumes
        # If room is symmetric, we might want CoM at room_center
        # This is a weak rule for functional kitchens but "Divine" ones are symmetric.
        # Let's assess symmetry of the *Zone Sequence*.
        
        return cost
