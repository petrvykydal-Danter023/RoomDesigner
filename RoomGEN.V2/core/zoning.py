from typing import Dict, Any, Optional
from enum import Enum
from .geometry import GeometryEngine

class ZoneType(Enum):
    CIRCULATION = "circulation"
    DINING = "dining"
    WORKBENCH = "workbench"
    TALL_BANK = "tall_bank"
    FRIDGE = "fridge"

class Zone:
    def __init__(self, ztype: ZoneType, x: float, y: float, width: float, depth: float):
        self.type = ztype
        self.shape = GeometryEngine.create_rect(x, y, width, depth)
        self.bounds = (x, y, width, depth)

class WorkbenchZone(Zone):
    def __init__(self, x: float, y: float, length: float):
        # Standard depth 60cm
        super().__init__(ZoneType.WORKBENCH, x, y, length, 60)
        self.required_items = ["sink", "stove", "dishwasher"]

class DiningZone(Zone):
    def __init__(self, x: float, y: float, table_w: float, table_d: float):
        super().__init__(ZoneType.DINING, x, y, table_w, table_d)
        # Create buffer for chairs (60cm around)
        self.chair_zone = GeometryEngine.create_buffer(self.shape, 60)

class CirculationZone(Zone):
    def __init__(self, x: float, y: float, width: float, length: float):
        super().__init__(ZoneType.CIRCULATION, x, y, width, length)
        # Constraint: Min width 90-110cm usually enforced by solver or validator

class TallBankZone(Zone):
    def __init__(self, x: float, y: float, width: float):
        # Depth 60cm, Height usually max
        super().__init__(ZoneType.TALL_BANK, x, y, width, 60)

class FridgeZone(Zone):
    def __init__(self, x: float, y: float, width=60, depth=60):
        super().__init__(ZoneType.FRIDGE, x, y, width, depth)
