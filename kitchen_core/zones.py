from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Zone:
    type: str  # 'wet', 'cooking', 'prep', 'storage', 'fridge', 'pantry', 'filler'
    min_width: int
    max_width: int
    ideal_width: int
    compressibility: str  # 'hard', 'elastic', 'liquid'
    content: List[str] = field(default_factory=list) # List of item IDs or Types
    
    # Metadata for skinning (e.g. "has_sink", "has_hob")
    metadata: dict = field(default_factory=dict) 

class ZoneFactory:
    @staticmethod
    def create_wet_zone(sink_width=60, dw_width=60) -> 'Zone':
        # Hard zone. 
        # Typically Sink + DW.
        # But maybe Sink is alone?
        w = sink_width + dw_width
        return Zone(
            type='wet',
            min_width=w,
            max_width=w, # Hard
            ideal_width=w,
            compressibility='hard',
            content=['sink', 'dishwasher'] if dw_width > 0 else ['sink'],
            metadata={'has_water': True}
        )

    @staticmethod
    def create_cooking_zone(stove_width=60) -> 'Zone':
        return Zone(
            type='cooking',
            min_width=stove_width,
            max_width=stove_width,
            ideal_width=stove_width,
            compressibility='hard',
            content=['stove'],
            metadata={'has_heat': True}
        )

    @staticmethod
    def create_fridge_zone(width=60, height=215) -> 'Zone':
        return Zone(
            type='fridge',
            min_width=width,
            max_width=width + 5, # Slight tolerance?
            ideal_width=width,
            compressibility='hard',
            content=['fridge'],
            metadata={'height': height}
        )

    @staticmethod
    def create_prep_zone(ideal=90) -> 'Zone':
        # Elastic. Min 30, Max 120?
        return Zone(
            type='prep',
            min_width=40,
            max_width=150,
            ideal_width=ideal,
            compressibility='elastic',
            content=['drawers', 'cabinet'],
            metadata={'role': 'preparation'}
        )
        
    @staticmethod
    def create_filler_zone() -> 'Zone':
        return Zone(
            type='filler',
            min_width=1,
            max_width=30, # Max size for a filler before it should be a cabinet
            ideal_width=5,
            compressibility='liquid',
            content=[],
            metadata={}
        )
