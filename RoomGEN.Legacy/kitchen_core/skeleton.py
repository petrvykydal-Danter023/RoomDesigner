from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class FunctionalVolume:
    x: float
    width: float
    function: str # 'wet', 'cooking', 'prep', etc
    metadata: Dict[str, Any] = field(default_factory=dict)
