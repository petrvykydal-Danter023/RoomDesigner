from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Component(BaseModel):
    """
    A single part of a cabinet (e.g. Carcass, Door, Handle).
    """
    type: str  # "carcass", "door", "handle", "leg", "shelf", "panel"
    dims: List[float]  # [width, height, depth]
    pos: List[float]   # [x, y, z] relative to parent cabinet origin
    rotation: Optional[List[float]] = None # [rx, ry, rz] in degrees (optional)
    asset_id: Optional[str] = None # If set, load GLB. If None, generate box.
    color: Optional[List[int]] = None # [R, G, B, A]

class CabinetItem(BaseModel):
    """
    A complete furniture item composed of multiple components.
    """
    id: str
    type: str
    position: List[float] # Global position [x, y, z]
    rotation: float = 0.0 # Rotation around Z axis in degrees
    components: List[Component] # List of hybrid parts
    metadata: Optional[Dict[str, Any]] = None # Extra data for post-processing
