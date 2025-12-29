from typing import Dict, Tuple, Any

# Maps item type to (R, G, B) mapping (0-1 float)
ZONE_MATERIALS: Dict[str, Dict[str, Any]] = {
    # Wet Zone (Blue)
    'sink': {'color': (0.13, 0.59, 0.95), 'name': 'wet_zone'},
    'dishwasher': {'color': (0.13, 0.59, 0.95), 'name': 'wet_zone'},
    
    # Hot Zone (Orange)
    'stove': {'color': (1.0, 0.60, 0.0), 'name': 'hot_zone'},
    'oven': {'color': (1.0, 0.60, 0.0), 'name': 'hot_zone'},
    'hood': {'color': (1.0, 0.60, 0.0), 'name': 'hot_zone'},
    
    # Cold Zone (Purple)
    'fridge': {'color': (0.61, 0.15, 0.69), 'name': 'cold_zone'},
    'freezer': {'color': (0.61, 0.15, 0.69), 'name': 'cold_zone'},
    
    # Storage (Brown)
    'base_cabinet': {'color': (0.48, 0.33, 0.28), 'name': 'storage'},
    'upper_cabinet': {'color': (0.48, 0.33, 0.28), 'name': 'storage'},
    'narrow_cabinet': {'color': (0.48, 0.33, 0.28), 'name': 'storage'},
    'upper_narrow': {'color': (0.48, 0.33, 0.28), 'name': 'storage'},
    'pantry': {'color': (0.48, 0.33, 0.28), 'name': 'storage'},
    
    # Corner (Dark Gray)
    'blind_corner': {'color': (0.26, 0.26, 0.26), 'name': 'corner'},
    'corner_post': {'color': (0.26, 0.26, 0.26), 'name': 'corner'},
    'carousel_corner': {'color': (0.26, 0.26, 0.26), 'name': 'corner'},
}

def get_material_for_item(item_type: str) -> Dict[str, Any]:
    return ZONE_MATERIALS.get(item_type, {'color': (0.8, 0.8, 0.8), 'name': 'default'})
