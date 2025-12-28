from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

@dataclass
class Slope:
    wall: str  # 'left', 'right', 'back'
    start_height: float
    angle: float  # degrees

    def get_height_at(self, x: float, z: float, room_width: float, room_length: float, room_height: float) -> float:
        """
        Calculates the ceiling height at a specific (x, z) point caused by this slope.
        Returns the height limitation imposed by this slope. Use room_height as default if not limited.
        """
        import math
        
        # Calculate distance from the wall where the slope starts
        dist = 0.0
        if self.wall == 'left':
            dist = x
        elif self.wall == 'right':
            dist = room_width - x
        elif self.wall == 'back':
            dist = z 
        # Note: 'front' wall usually doesn't have slope in this context, or it's z=0
        
        # Calculate height increase from start_height based on angle
        # tan(angle) = dy / dx  => dy = dx * tan(angle)
        # height = start_height + dist * tan(angle)
        rad = math.radians(self.angle)
        slope_h = self.start_height + dist * math.tan(rad)
        
        # The actual ceiling is the minimum of room height and the slope height
        return slope_h

@dataclass
class Room:
    width: float
    length: float
    height: float
    slopes: List[Slope]
    utilities: List[Dict] # [{'type': 'water', 'x': 150, 'y': 50, 'z': 0, 'radius': 5}]
    # Enhancements
    windows: List[Dict] = None 
    doors: List[Dict] = None

    @classmethod
    def from_dict(cls, data: dict):
        slopes_data = data.get('slopes', [])
        slopes = [Slope(s['wall'], s['start_height'], s['angle']) for s in slopes_data]
        return cls(
            width=data['width'],
            length=data.get('length', data.get('depth')), # Handle 'depth' alias
            height=data['height'],
            slopes=slopes,
            utilities=data.get('utilities', []),
            windows=data.get('windows', []),
            doors=data.get('doors', [])
        )

    def get_ceiling_height(self, x: float, z: float) -> float:
        """
        Returns the lowest ceiling height at (x, z) considering all slopes.
        """
        current_min = self.height
        for slope in self.slopes:
            h = slope.get_height_at(x, z, self.width, self.length, self.height)
            if h < current_min:
                current_min = h
        return current_min

    def get_valid_x_intervals(self, item_width: float, item_height: float, item_depth: float = 60.0) -> List[Tuple[int, int]]:
        """
        Returns a list of (start_x, end_x) intervals where the item fits vertically.
        We check height at the item's corners along the wall (assuming depth is towards center).
        Kitchen items are usually placed against a wall (Z=Length or Z=0? Prompt implies lines).
        
        Let's assume a "Left-to-Right" placement along the BACK wall (Z = Length) or similar.
        The prompt says "X position for each requested item".
        Usually kitchen runs are linear. Let's assume standard placement along the Z=Length wall (Back wall) or Z=0.
        However, if slopes are 'left' or 'right', X varies.
        
        Let's scan X from 0 to Room Width - Item Width.
        """
        valid_intervals = []
        
        # We assume standard placement at Z = 0 (or Z=Length). Let's pick Z=0 as "back wall" reference for now, 
        # or ask user? The utils are at 'water_x', 'gas_x', implying a 1D placement line.
        # Let's assume the installation depth is `item_depth`.
        # We need to check height at (x, 0) and (x + width, 0) and potentially (x, depth) and (x+width, depth)
        # if the slope comes from the back.
        # But usually slopes are "attic" style.
        
        # Let's use a step size for scanning (e.g. 1cm) or analytical if simple.
        # Scanning 1cm is safe and fast enough for 400cm.
        
        # We need to find contiguous ranges of valid start positions.
        
        room_w_int = int(self.width)
        width_int = int(item_width)
        
        current_start = -1
        
        # Check Z at the wall (e.g., 0) and at the front of the cabinet (depth).
        # We'll assume the wall is at Z=RoomLength (Back) or Z=0. 
        # Prompt utils: water_x=150.
        # Let's assume items are placed along the wall at Z=RoomLength (typical for "Back" wall view).
        # Actually usually cabinets are against the wall.
        # Let's assume the main run is along the wall at Z=0 or Z=Length.
        # If the slope is "back", it changes with Z.
        # If the slope is "left/right", it changes with X.
        
        # Let's assume placement is along Z=0 for simplicity (Front view) or Z=Length.
        # Given "Back" wall slope, let's assume items are against Z=0 (Front) or Z=Length (Back).
        # Let's assume Z positions are fixed (e.g., against a wall).
        # We will check height at Z=0 (wall) and Z=depth (front of cabinet).
        
        # WAIT: If utilities are given as X, it's a 1D problem.
        # Let's assume placement is along a single wall (e.g. the Back wall at Z=Length? or Z=0?).
        # Standard convention: Viewer looking at wall.
        # Let's default to checking Z from 0 to depth. (Wait, if slope is at 'back' wall, height might be lowest there).
        
        # Let's assume the wall line is at Z=0.
        z_wall = 0.0
        z_front = item_depth
        
        for x in range(0, room_w_int - width_int + 1):
            # Check 4 corners of the volumes
            # (x, z_wall), (x+w, z_wall), (x, z_front), (x+w, z_front)
            
            h1 = self.get_ceiling_height(x, z_wall)
            h2 = self.get_ceiling_height(x + item_width, z_wall)
            h3 = self.get_ceiling_height(x, z_front)
            h4 = self.get_ceiling_height(x + item_width, z_front)
            
            min_h = min(h1, h2, h3, h4)
            
            if min_h >= item_height:
                if current_start == -1:
                    current_start = x
            else:
                if current_start != -1:
                    valid_intervals.append((current_start, x - 1))
                    current_start = -1
                    
        if current_start != -1:
             valid_intervals.append((current_start, room_w_int - width_int))
             
        return valid_intervals
