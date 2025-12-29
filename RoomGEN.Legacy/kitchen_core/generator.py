from typing import List, Tuple, Dict
from .geometry import Room

class OBJGenerator:
    def __init__(self):
        self.vertices = []
        self.normals = [] # Not strictly needed for basic geo but good
        self.faces = [] # list of lists of vertex indices (1-based)
        
    def add_vertex(self, x: float, y: float, z: float) -> int:
        self.vertices.append((x, y, z))
        return len(self.vertices)
        
    def add_face(self, indices: List[int]):
        self.faces.append(indices)
        
    def add_box(self, x: float, y: float, z: float, w: float, h: float, d: float):
        """
        Adds a box at (x,y,z) with dimensions (w,h,d).
        (x,y,z) is bottom-front-left corner.
        """
        # 8 vertices
        # Bottom
        v1 = self.add_vertex(x, y, z)
        v2 = self.add_vertex(x + w, y, z)
        v3 = self.add_vertex(x + w, y, z + d)
        v4 = self.add_vertex(x, y, z + d)
        
        # Top
        v5 = self.add_vertex(x, y + h, z)
        v6 = self.add_vertex(x + w, y + h, z)
        v7 = self.add_vertex(x + w, y + h, z + d)
        v8 = self.add_vertex(x, y + h, z + d)
        
        # Faces (CCW winding)
        # Front
        self.add_face([v1, v2, v6, v5])
        # Back
        self.add_face([v3, v4, v8, v7])
        # Left
        self.add_face([v4, v1, v5, v8])
        # Right
        self.add_face([v2, v3, v7, v6])
        # Top
        self.add_face([v5, v6, v7, v8])
        # Bottom
        self.add_face([v4, v3, v2, v1])
    
    def add_box_rotated_z(self, x: float, y: float, z: float, w: float, h: float, d: float):
        """
        Adds a box rotated 90° around Y axis for Z-axis wall placement.
        Front face points towards X+ (into room) instead of Z+.
        
        For L-shape: items on left wall (perpendicular) need this.
        Parameters are in the item's local space:
        - w = item width (becomes depth along X)
        - d = item depth (becomes width along Z)
        """
        # Swap w and d, shift coordinates so front faces X+
        self.add_box(x, y, z, d, h, w)
        
    def generate_cabinet(self, x: float, y: float, z: float, width: float, height: float, depth: float, back_cutouts: List[Tuple[float, float, float, float]] = None):
        """
        Generates cabinet geometry.
        If back_cutouts is provided (local x, y, w, h), the back panel is generated with holes.
        """
        # Dimensions
        thick = 1.8 # cm
        base_h = 10.0 # legs
        
        # Legs (Simplification: Box at bottom)
        # self.add_box(x + 5, y, z + 5, 5, base_h, 5) ...
        # For now, simplistic box for body, BUT we need holes in back.
        # So we build panels.
        
        # Carcass Y start
        cy = y
        ch = height
        
        # Left Panel
        self.add_box(x, cy, z, thick, ch, depth)
        # Right Panel
        self.add_box(x + width - thick, cy, z, thick, ch, depth)
        # Bottom Panel (between sides)
        self.add_box(x + thick, cy, z, width - 2*thick, thick, depth)
        # Top Panel/Strip (between sides)
        self.add_box(x + thick, cy + ch - thick, z, width - 2*thick, thick, depth)
        
        # Back Panel (The smart part)
        # Position: Z (back) + gap? Usually inset or flush. Let's say flush at Z.
        # Thickness: 0.3 (sololit)
        back_z = z
        back_thick = 0.5
        
        # Back panel covers area:
        # Local X: thick to width-thick
        # Local Y: thick to height-thick (inside carcass)
        # Global X: x + thick
        # Global Y: cy + thick
        # Width: width - 2*thick
        # Height: ch - 2*thick
        
        bx = x + thick
        by = cy + thick
        bw = width - 2*thick
        bh = ch - 2*thick
        
        # Cutouts are relative to Cabinet Origin (x, y). 
        # Typically pipes are relative to Wall (Room coords). 
        # But we pass LOCAL cutouts to this func?
        # User said "generate_worktop... accept list of cutouts...".
        # For cabinet, let's assume `back_cutouts` are in Local Coords relative to (x, y).
        
        # Logic to split back panel rect (0, 0, bw, bh)
        # We need the Subtract method. 
        
        def subtract_rects(rects, hole):
            hx, hy, h_w, h_h = hole
            new_r = []
            for rx, ry, rw, rh in rects:
                # Check overlap
                if not (hx >= rx + rw or hx + h_w <= rx or hy >= ry + rh or hy + h_h <= ry):
                    # Overlap - Split
                     overlap_x1 = max(rx, hx)
                     overlap_x2 = min(rx + rw, hx + h_w)
                     
                     if overlap_x2 > overlap_x1:
                        # Bottom
                        if hy > ry:
                            new_r.append((rx, ry, rw, hy - ry)) 
                            # Wait, complex split logic for full 4-way?
                            # To keep it simple and robust (avoid overlaps):
                            # 1. Box Below Hole (Full width of rect)
                            # 2. Box Above Hole (Full width of rect)
                            # 3. Box Left of Hole (Between Y ranges)
                            # 4. Box Right of Hole (Between Y ranges)
                            
                        # Correct logic:
                        # Top
                        if hy + h_h < ry + rh:
                             new_r.append((rx, hy + h_h, rw, (ry + rh) - (hy + h_h)))
                        # Bottom
                        if hy > ry:
                             new_r.append((rx, ry, rw, hy - ry))
                        # Left (clamped vertical)
                        # Y range is max(ry, hy) to min(ry+rh, hy+hh)
                        y_start = max(ry, hy)
                        y_end = min(ry + rh, hy + h_h)
                        if y_end > y_start:
                             if hx > rx:
                                 new_r.append((rx, y_start, hx - rx, y_end - y_start))
                             if hx + h_w < rx + rw:
                                 new_r.append((hx + h_w, y_start, (rx + rw) - (hx + h_w), y_end - y_start))
                else:
                    new_r.append((rx, ry, rw, rh))
            return new_r

        # Start with full back panel (relative to bx, by)
        # Coordinates relative to bx, by
        curr_rects = [(0, 0, bw, bh)]
        
        if back_cutouts:
            for cx, cy_local, cw, ch_local in back_cutouts:
                # cx is relative to cabinet X.
                # we need relative to bx (which is x+thick)
                # rel_x = cx - thick
                # rel_y = cy_local - thick
                
                rel_x = cx - thick
                rel_y = cy_local - thick
                
                curr_rects = subtract_rects(curr_rects, (rel_x, rel_y, cw, ch_local))
                
        # Generate Geometry for rects
        for rx, ry, rw, rh in curr_rects:
            # Add back panel piece
            # box at global coords
            self.add_box(bx + rx, by + ry, back_z, rw, rh, back_thick)
            
        # Door (Overlay)
        self.add_box(x, y, z + depth, width, height, 1.8)
        # Handle
        self.add_box(x + width - 5, y + height - 10, z + depth + 1.8, 1, 5, 1)

    # ========== SPECIALIZED CABINET GENERATORS ==========
    
    def generate_drawer_cabinet(self, x: float, y: float, z: float, width: float, height: float = 85, depth: float = 60, num_drawers: int = 3):
        """
        Multi-drawer cabinet with individual drawer fronts, rails, and handles.
        """
        thick = 1.8
        
        # Carcass
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        self.add_box(x + thick, y, z, width - 2*thick, thick, depth)  # Bottom
        self.add_box(x + thick, y + height - thick, z, width - 2*thick, thick, depth)  # Top
        
        # Back Panel
        self.add_box(x + thick, y + thick, z, width - 2*thick, height - 2*thick, 0.5)
        
        # Drawers
        drawer_h = (height - thick) / num_drawers
        for i in range(num_drawers):
            dy = y + i * drawer_h
            
            # Drawer Front
            self.add_box(x, dy, z + depth, width, drawer_h - 0.3, 2.0)
            
            # Drawer Box (simplified inner)
            inner_depth = depth - 10
            inner_width = width - 2*thick - 2
            self.add_box(x + thick + 1, dy + 1, z + 5, inner_width, drawer_h - 3, inner_depth)
            
            # Handle (horizontal bar)
            handle_w = min(width * 0.6, 15)
            handle_x = x + (width - handle_w) / 2
            self.add_box(handle_x, dy + drawer_h/2 - 0.5, z + depth + 2.0, handle_w, 1, 2)
            
            # Rails (side guides)
            self.add_box(x + thick, dy + 2, z + 8, 1, 1, inner_depth)  # Left rail
            self.add_box(x + width - thick - 1, dy + 2, z + 8, 1, 1, inner_depth)  # Right rail
    
    def generate_sink_cabinet(self, x: float, y: float, z: float, width: float = 80, height: float = 85, depth: float = 60):
        """
        Sink cabinet with cutout for plumbing and false drawer front.
        """
        thick = 1.8
        
        # Carcass (no bottom center for plumbing)
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        
        # Partial bottom (strips at front and back for basin support)
        self.add_box(x + thick, y, z, width - 2*thick, thick, 10)  # Back strip
        self.add_box(x + thick, y, z + depth - 10, width - 2*thick, thick, 10)  # Front strip
        
        # Top Panel
        self.add_box(x + thick, y + height - thick, z, width - 2*thick, thick, depth)
        
        # Back Panel with plumbing cutout (simplified - just smaller panel)
        back_h = height - 2*thick
        pipe_cutout_y = 30
        pipe_cutout_h = 25
        # Lower section
        self.add_box(x + thick, y + thick, z, width - 2*thick, pipe_cutout_y - thick, 0.5)
        # Upper section
        self.add_box(x + thick, y + pipe_cutout_y + pipe_cutout_h, z, width - 2*thick, height - pipe_cutout_y - pipe_cutout_h - thick, 0.5)
        
        # False drawer front (top)
        self.add_box(x, y + height - 15, z + depth, width, 14, 2.0)
        self.add_box(x + width/2 - 7, y + height - 8, z + depth + 2.0, 14, 1, 2)  # Handle
        
        # Lower doors (double door)
        door_w = (width - 2) / 2
        door_h = height - 18
        # Left door
        self.add_box(x, y, z + depth, door_w, door_h, 2.0)
        self.add_box(x + door_w - 5, y + door_h/2 - 2, z + depth + 2.0, 1, 4, 2)  # Handle
        # Right door
        self.add_box(x + door_w + 2, y, z + depth, door_w, door_h, 2.0)
        self.add_box(x + door_w + 4, y + door_h/2 - 2, z + depth + 2.0, 1, 4, 2)  # Handle
        
        # Sink basin (stainless steel look - simplified box)
        basin_w = width - 20
        basin_d = depth - 15
        basin_h = 18
        self.add_box(x + 10, y + height - 3 - basin_h, z + 8, basin_w, basin_h, basin_d)
        
        # Faucet
        faucet_x = x + width/2
        faucet_z = z + 5
        self.add_box(faucet_x - 2, y + height - 3, faucet_z, 4, 35, 4)  # Base
        self.add_box(faucet_x - 1.5, y + height + 30, faucet_z, 3, 3, 25)  # Spout

    def generate_dishwasher(self, x: float, y: float, z: float, width: float = 60, height: float = 85, depth: float = 60):
        """
        Integrated dishwasher with panel front and controls.
        """
        # Body (stainless steel interior visible through gap)
        body_inset = 2
        self.add_box(x + body_inset, y, z + body_inset, width - 2*body_inset, height - 3, depth - body_inset)
        
        # Door panel (overlay front)
        self.add_box(x, y, z + depth, width, height - 3, 2.0)
        
        # Handle (long horizontal bar)
        handle_w = width - 10
        self.add_box(x + 5, y + height - 8, z + depth + 2.0, handle_w, 2, 3)
        
        # Control panel strip
        self.add_box(x, y + height - 3, z + depth - 5, width, 3, 7)
        # Control buttons
        for i in range(4):
            btn_x = x + 10 + i * 12
            self.add_box(btn_x, y + height - 2, z + depth - 3, 4, 1, 2)
        
        # Interior rack hint (visible at door bottom edge)
        self.add_box(x + 5, y + 10, z + 10, width - 10, 1, depth - 15)  # Lower rack
        self.add_box(x + 5, y + height/2, z + 10, width - 10, 1, depth - 15)  # Upper rack

    def generate_fridge(self, x: float, y: float, z: float, width: float = 60, height: float = 200, depth: float = 60):
        """
        Tall fridge/freezer with two compartments.
        """
        thick = 2.0
        
        # Outer shell
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        self.add_box(x + thick, y, z, width - 2*thick, thick, depth)  # Bottom
        self.add_box(x + thick, y + height - thick, z, width - 2*thick, thick, depth)  # Top
        self.add_box(x + thick, y + thick, z, width - 2*thick, height - 2*thick, thick)  # Back
        
        # Freezer compartment (top 1/4)
        freezer_h = height * 0.28
        fridge_h = height - freezer_h - thick
        
        # Divider
        self.add_box(x + thick, y + fridge_h, z + thick, width - 2*thick, thick, depth - thick)
        
        # Freezer door
        self.add_box(x, y + fridge_h + thick, z + depth, width, freezer_h - thick, 3.0)
        self.add_box(x + width - 8, y + fridge_h + freezer_h/2, z + depth + 3.0, 2, 15, 3)  # Handle
        
        # Fridge door
        self.add_box(x, y, z + depth, width, fridge_h, 3.0)
        self.add_box(x + width - 8, y + fridge_h - 25, z + depth + 3.0, 2, 20, 3)  # Handle
        
        # Internal shelves (fridge)
        num_shelves = 4
        shelf_gap = fridge_h / (num_shelves + 1)
        for i in range(1, num_shelves + 1):
            shelf_y = y + thick + i * shelf_gap
            self.add_box(x + thick + 2, shelf_y, z + thick + 3, width - 2*thick - 4, 1, depth - thick - 8)
        
        # Door shelf hints
        for i in range(3):
            self.add_box(x + 3, y + 15 + i * 25, z + depth - 8, width - 6, 8, 6)

    def generate_oven(self, x: float, y: float, z: float, width: float = 60, height: float = 60, depth: float = 55):
        """
        Built-in oven with glass door and control panel.
        """
        # Oven body
        self.add_box(x, y, z, width, height, depth)
        
        # Glass door (with frame)
        door_h = height - 12
        frame = 3
        # Frame
        self.add_box(x, y, z + depth, width, door_h, 2)
        # Glass (inset, darker material would be separate)
        self.add_box(x + frame, y + frame, z + depth + 1, width - 2*frame, door_h - 2*frame, 1)
        
        # Control panel
        self.add_box(x, y + door_h, z + depth - 5, width, height - door_h, 7)
        # Knobs
        for i in range(4):
            knob_x = x + 12 + i * 10
            self.add_box(knob_x, y + door_h + 5, z + depth + 2, 5, 5, 3)
        
        # Door handle
        self.add_box(x + width/2 - 15, y + door_h - 5, z + depth + 2, 30, 2, 3)
        
        # Interior cavity hint
        self.add_box(x + 3, y + 3, z + 3, width - 6, height - 18, depth - 8)
        # Rack
        self.add_box(x + 5, y + height/3, z + 5, width - 10, 1, depth - 12)

    def generate_cooktop(self, x: float, y: float, z: float, width: float = 60, depth: float = 52):
        """
        Induction/gas cooktop with burners.
        """
        # Glass/metal surface
        self.add_box(x, y, z, width, 5, depth)
        
        # Burners (4 burner layout)
        burner_positions = [
            (x + width*0.25, z + depth*0.3, 8),   # Front left - small
            (x + width*0.75, z + depth*0.3, 10),  # Front right - large
            (x + width*0.25, z + depth*0.7, 10),  # Back left - large
            (x + width*0.75, z + depth*0.7, 7),   # Back right - small
        ]
        
        for bx, bz, radius in burner_positions:
            # Simplified circular burner as octagon approximation
            self.add_box(bx - radius/2, y + 5, bz - radius/2, radius, 0.5, radius)
        
        # Control strip (front edge)
        self.add_box(x, y, z + depth, width, 3, 3)
        # Control knobs/touch
        for i in range(4):
            self.add_box(x + 8 + i * 12, y + 0.5, z + depth + 0.5, 4, 2, 2)

    def generate_hood(self, x: float, y: float, z: float, width: float = 60, height: float = 40, depth: float = 35):
        """
        Range hood with filters and lighting.
        """
        # Main housing (tapered shape simplified as box)
        housing_h = height * 0.6
        chimney_h = height - housing_h
        
        # Chimney/duct cover
        chimney_w = width * 0.4
        chimney_x = x + (width - chimney_w) / 2
        self.add_box(chimney_x, y + housing_h, z, chimney_w, chimney_h, depth * 0.6)
        
        # Main hood body
        self.add_box(x, y, z, width, housing_h, depth)
        
        # Filter grilles (2 filters)
        filter_w = (width - 10) / 2
        self.add_box(x + 3, y - 1, z + 3, filter_w, 1.5, depth - 6)
        self.add_box(x + filter_w + 7, y - 1, z + 3, filter_w, 1.5, depth - 6)
        
        # Light strip
        self.add_box(x + 5, y + 2, z + depth - 5, width - 10, 2, 3)
        
        # Control buttons
        for i in range(3):
            self.add_box(x + width/2 - 10 + i * 8, y + housing_h - 5, z + depth - 3, 4, 3, 2)

    def generate_wall_cabinet(self, x: float, y: float, z: float, width: float, height: float = 70, depth: float = 35):
        """
        Wall-mounted cabinet with lift-up or swing door.
        """
        thick = 1.6
        
        # Carcass
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        self.add_box(x + thick, y, z, width - 2*thick, thick, depth)  # Bottom
        self.add_box(x + thick, y + height - thick, z, width - 2*thick, thick, depth)  # Top
        
        # Back
        self.add_box(x + thick, y + thick, z, width - 2*thick, height - 2*thick, 0.5)
        
        # Internal shelf
        self.add_box(x + thick + 1, y + height/2, z + 2, width - 2*thick - 2, 1.5, depth - 4)
        
        # Door (single swing)
        self.add_box(x, y, z + depth, width, height, 1.8)
        
        # Handle
        self.add_box(x + width - 8, y + height/2 - 5, z + depth + 1.8, 2, 10, 2)

    def generate_pantry(self, x: float, y: float, z: float, width: float = 60, height: float = 200, depth: float = 60):
        """
        Tall pantry cabinet with pull-out shelving.
        """
        thick = 1.8
        
        # Carcass
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        self.add_box(x + thick, y, z, width - 2*thick, thick, depth)  # Bottom
        self.add_box(x + thick, y + height - thick, z, width - 2*thick, thick, depth)  # Top
        self.add_box(x + thick, y + thick, z, width - 2*thick, height - 2*thick, 0.5)  # Back
        
        # Pull-out shelf units (5 levels)
        num_shelves = 5
        usable_h = height - 2*thick
        shelf_gap = usable_h / num_shelves
        
        for i in range(num_shelves):
            shelf_y = y + thick + i * shelf_gap + 5
            # Shelf base
            self.add_box(x + thick + 2, shelf_y, z + 5, width - 2*thick - 4, 1.5, depth - 10)
            # Side rails
            self.add_box(x + thick + 2, shelf_y + 1.5, z + 5, 1, 8, depth - 10)
            self.add_box(x + width - thick - 3, shelf_y + 1.5, z + 5, 1, 8, depth - 10)
        
        # Door (full height)
        self.add_box(x, y, z + depth, width, height, 2.0)
        # Handle
        self.add_box(x + width - 6, y + height/2 - 10, z + depth + 2.0, 2, 20, 3)

    def generate_corner_cabinet(self, x: float, y: float, z: float, width: float = 90, height: float = 85, depth: float = 90):
        """
        L-shaped corner cabinet with lazy susan or carousel mechanism.
        """
        thick = 1.8
        
        # L-shaped carcass (two connected boxes forming corner)
        # Back walls (L shape)
        self.add_box(x, y, z, width, height, thick)  # Back along X
        self.add_box(x, y, z, thick, height, depth)  # Back along Z
        
        # Front faces (angled or straight)
        # Straight approach: diagonal front
        front_offset = 35  # How much to cut off corner
        
        # Left front panel (partial)
        self.add_box(x + width - thick, y, z, thick, height, depth - front_offset)
        # Right front panel (partial)  
        self.add_box(x, y, z + depth - thick, width - front_offset, height, thick)
        
        # Bottom
        self.add_box(x + thick, y, z + thick, width - 2*thick, thick, depth - 2*thick)
        # Top
        self.add_box(x + thick, y + height - thick, z + thick, width - 2*thick, thick, depth - 2*thick)
        
        # Lazy susan shelves (circular approximation)
        carousel_r = min(width, depth) * 0.35
        carousel_x = x + width/2
        carousel_z = z + depth/2
        
        # Bottom carousel
        self.add_box(carousel_x - carousel_r, y + 10, carousel_z - carousel_r, carousel_r*2, 2, carousel_r*2)
        # Top carousel
        self.add_box(carousel_x - carousel_r, y + height/2, carousel_z - carousel_r, carousel_r*2, 2, carousel_r*2)
        
        # Diagonal door (simplified as angled rectangle)
        door_w = front_offset * 1.4  # Approximate diagonal
        door_x = x + width - front_offset
        door_z = z + depth - front_offset
        self.add_box(door_x - 5, y, door_z + depth - 5, door_w, height, 2)

    # ========== EXPANDED MODEL LIBRARY ==========
    
    def generate_oven_tower(self, x: float, y: float, z: float, width: float = 60, height: float = 215, depth: float = 60):
        """
        Tall oven tower with built-in oven and storage above/below.
        """
        thick = 1.8
        oven_h = 60
        oven_y = 85  # Eye-level ergonomic placement
        
        # Carcass
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        self.add_box(x + thick, y, z, width - 2*thick, thick, depth)  # Bottom
        self.add_box(x + thick, y + height - thick, z, width - 2*thick, thick, depth)  # Top
        self.add_box(x, y + thick, z + depth - 0.5, width, height - 2*thick, 0.5)  # Back
        
        # Storage below oven (drawers)
        drawer_h = 25
        for i in range(3):
            dy = y + thick + i * drawer_h
            self.add_box(x + 2, dy, z - 2, width - 4, drawer_h - 1, 2)
        
        # Oven cavity
        self.add_box(x + thick + 2, oven_y, z + 3, width - 2*thick - 4, oven_h, depth - 6)
        # Oven door (glass look)
        self.add_box(x + 4, oven_y + 5, z - 2, width - 8, oven_h - 10, 3)
        # Oven handle
        self.add_box(x + 10, oven_y + oven_h - 8, z - 4, width - 20, 3, 2)
        
        # Storage above oven (cabinet)
        top_cab_y = oven_y + oven_h + 5
        top_cab_h = height - top_cab_y - thick
        self.add_box(x + 2, top_cab_y, z - 2, width - 4, top_cab_h, 2)  # Door
        
    def generate_microwave_cabinet(self, x: float, y: float, z: float, width: float = 60, height: float = 45, depth: float = 35):
        """
        Wall cabinet with built-in microwave space.
        """
        thick = 1.8
        micro_h = 30
        micro_w = width - 8
        
        # Cabinet shell
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        self.add_box(x + thick, y, z, width - 2*thick, thick, depth)  # Bottom
        self.add_box(x + thick, y + height - thick, z, width - 2*thick, thick, depth)  # Top
        self.add_box(x, y + thick, z + depth - 0.5, width, height - 2*thick, 0.5)  # Back
        
        # Microwave opening
        micro_y = y + thick + 5
        self.add_box(x + 4, micro_y, z + 2, micro_w, micro_h, depth - 4)
        # Microwave door
        self.add_box(x + 6, micro_y + 2, z - 2, micro_w - 4, micro_h - 4, 2)
        
    def generate_wine_rack(self, x: float, y: float, z: float, width: float = 30, height: float = 85, depth: float = 35):
        """
        Wine bottle storage rack with X-pattern dividers.
        """
        thick = 1.8
        cell_h = 10  # Height per bottle row
        cells_per_row = max(1, int(width / 10))
        num_rows = int((height - 20) / cell_h)
        
        # Frame
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        self.add_box(x + thick, y, z, width - 2*thick, thick, depth)  # Bottom
        self.add_box(x + thick, y + height - thick, z, width - 2*thick, thick, depth)  # Top
        
        # X-pattern dividers (simplified as grid)
        for row in range(num_rows):
            for col in range(cells_per_row):
                cy = y + 10 + row * cell_h
                cx = x + thick + col * (width - 2*thick) / cells_per_row
                # Horizontal divider
                self.add_box(cx, cy, z + 5, (width - 2*thick) / cells_per_row, 1, depth - 10)
                
    def generate_pull_out_pantry(self, x: float, y: float, z: float, width: float = 30, height: float = 200, depth: float = 55):
        """
        Narrow pull-out pantry with wire shelves.
        """
        thick = 1.8
        num_shelves = 6
        
        # Frame rails (sides)
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        
        # Back panel
        self.add_box(x, y, z + depth - thick, width, height, thick)
        
        # Pull-out cart (slightly set back)
        cart_x = x + thick + 2
        cart_w = width - 2*thick - 4
        cart_d = depth - 10
        
        # Shelf dividers
        shelf_gap = (height - 20) / num_shelves
        for i in range(num_shelves):
            shelf_y = y + 10 + i * shelf_gap
            # Wire shelf (grid pattern)
            self.add_box(cart_x, shelf_y, z + 3, cart_w, 1.5, cart_d)
            # Shelf front rail
            self.add_box(cart_x, shelf_y, z, cart_w, 3, 1)
        
        # Handle
        self.add_box(x + width/2 - 5, y + height/2, z - 3, 10, 20, 2)
        
    def generate_trash_cabinet(self, x: float, y: float, z: float, width: float = 45, height: float = 85, depth: float = 55):
        """
        Pull-out trash and recycling cabinet with dual bins.
        """
        thick = 1.8
        bin_w = (width - 3*thick) / 2
        
        # Cabinet shell
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        self.add_box(x + thick, y, z, width - 2*thick, thick, depth)  # Bottom
        self.add_box(x, y + thick, z + depth - thick, width, height - thick, thick)  # Back
        
        # Center divider
        self.add_box(x + width/2 - thick/2, y + thick, z + 5, thick, height - 20, depth - 10)
        
        # Trash bins (simplified as boxes)
        bin_h = height - 25
        # Left bin (trash)
        self.add_box(x + thick + 2, y + thick + 2, z + 5, bin_w - 4, bin_h, depth - 15)
        # Right bin (recycling)
        self.add_box(x + width/2 + thick/2 + 2, y + thick + 2, z + 5, bin_w - 4, bin_h, depth - 15)
        
        # Door with toe-kick trigger
        self.add_box(x + 2, y, z - 2, width - 4, height - 5, 2)
        
    def generate_coffee_station(self, x: float, y: float, z: float, width: float = 60, height: float = 85, depth: float = 60):
        """
        Coffee/breakfast station with appliance garage and storage.
        """
        thick = 1.8
        
        # Base cabinet
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        self.add_box(x + thick, y, z, width - 2*thick, thick, depth)  # Bottom
        self.add_box(x, y + thick, z + depth - thick, width, height - thick, thick)  # Back
        
        # Appliance shelf (raised platform)
        shelf_y = y + 30
        self.add_box(x + thick, shelf_y, z + thick, width - 2*thick, 2, depth - 2*thick)
        
        # Appliance garage door (roll-up style - closed)
        self.add_box(x + 2, shelf_y + 5, z - 2, width - 4, height - shelf_y - 10, 2)
        
        # Coffee machine placeholder
        machine_w = 25
        machine_d = 30
        machine_h = 35
        self.add_box(x + (width - machine_w)/2, shelf_y + 2, z + 5, machine_w, machine_h, machine_d)
        
        # Cup hooks/shelf above
        self.add_box(x + thick + 5, shelf_y + machine_h + 10, z + 5, width - 2*thick - 10, 2, depth/2)
        
    def generate_open_shelving(self, x: float, y: float, z: float, width: float = 80, height: float = 60, depth: float = 25):
        """
        Open floating shelves (no doors, industrial/modern look).
        """
        thick = 2.5
        num_shelves = 3
        shelf_gap = (height - thick) / num_shelves
        
        # Vertical supports (brackets)
        bracket_w = 3
        self.add_box(x, y, z + depth - 5, bracket_w, height, 5)  # Left
        self.add_box(x + width - bracket_w, y, z + depth - 5, bracket_w, height, 5)  # Right
        
        # Shelves
        for i in range(num_shelves):
            shelf_y = y + i * shelf_gap
            self.add_box(x, shelf_y, z, width, thick, depth)
            
    def generate_glass_cabinet(self, x: float, y: float, z: float, width: float = 60, height: float = 70, depth: float = 35):
        """
        Wall cabinet with glass doors for display.
        """
        thick = 1.8
        frame_w = 4
        
        # Cabinet frame
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        self.add_box(x + thick, y, z, width - 2*thick, thick, depth)  # Bottom
        self.add_box(x + thick, y + height - thick, z, width - 2*thick, thick, depth)  # Top
        self.add_box(x, y + thick, z + depth - thick, width, height - 2*thick, thick)  # Back
        
        # Glass door frame
        self.add_box(x + 2, y + 2, z - 2, frame_w, height - 4, 2)  # Left frame
        self.add_box(x + width - 2 - frame_w, y + 2, z - 2, frame_w, height - 4, 2)  # Right frame
        self.add_box(x + 2, y + 2, z - 2, width - 4, frame_w, 2)  # Bottom frame
        self.add_box(x + 2, y + height - 2 - frame_w, z - 2, width - 4, frame_w, 2)  # Top frame
        
        # Glass panel (thin)
        self.add_box(x + frame_w + 4, y + frame_w + 4, z - 1, width - 2*frame_w - 8, height - 2*frame_w - 8, 0.5)
        
        # Interior shelf
        shelf_y = y + height/2
        self.add_box(x + thick + 2, shelf_y, z + 3, width - 2*thick - 4, 1.5, depth - 6)
        
    def generate_spice_rack(self, x: float, y: float, z: float, width: float = 20, height: float = 40, depth: float = 10):
        """
        Narrow spice rack for door mounting or wall.
        """
        thick = 1.0
        num_shelves = 4
        shelf_gap = (height - 2*thick) / num_shelves
        
        # Frame
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        self.add_box(x + thick, y + height - thick, z, width - 2*thick, thick, depth)  # Top
        
        # Shelves with front rail
        for i in range(num_shelves):
            shelf_y = y + 3 + i * shelf_gap
            self.add_box(x + thick, shelf_y, z, width - 2*thick, thick, depth)
            # Front rail
            self.add_box(x + thick, shelf_y + thick, z - 1, width - 2*thick, 3, 1)
            
    def generate_appliance_garage(self, x: float, y: float, z: float, width: float = 45, height: float = 45, depth: float = 40):
        """
        Countertop appliance garage with tambour door.
        """
        thick = 1.8
        
        # Shell
        self.add_box(x, y, z, thick, height, depth)  # Left
        self.add_box(x + width - thick, y, z, thick, height, depth)  # Right
        self.add_box(x + thick, y, z, width - 2*thick, thick, depth)  # Bottom
        self.add_box(x + thick, y + height - thick, z, width - 2*thick, thick, depth)  # Top
        self.add_box(x, y + thick, z + depth - thick, width, height - 2*thick, thick)  # Back
        
        # Tambour door (roll-up, shown closed)
        self.add_box(x + 2, y + thick, z - 2, width - 4, height - 2*thick, 1.5)
        
        # Handle groove
        self.add_box(x + width/2 - 15, y + height/2 - 2, z - 3, 30, 4, 1)
        
    def generate_knife_block(self, x: float, y: float, z: float, width: float = 15, height: float = 25, depth: float = 12):
        """
        Countertop knife block accessory.
        """
        # Base block
        self.add_box(x, y, z, width, height, depth)
        
        # Knife slots (grooves)
        slot_gap = 2.5
        for i in range(5):
            slot_x = x + 3 + i * slot_gap
            self.add_box(slot_x, y + height - 15, z + 2, 0.5, 12, depth - 4)
            
    def generate_utensil_holder(self, x: float, y: float, z: float, diameter: float = 12, height: float = 18):
        """
        Cylindrical utensil holder (approximated as octagon).
        """
        # Simplified as square with beveled corners
        self.add_box(x, y, z, diameter, height, diameter)
        bevel = diameter * 0.15
        self.add_box(x - bevel/2, y, z + bevel, diameter + bevel, height, diameter - 2*bevel)

    def generate_item_by_type(self, item_type: str, x: float, y: float, z: float, width: float, height: float = 85, depth: float = 60, **kwargs):
        """
        Dispatcher: Routes to specialized generator based on item type.
        """
        generators = {
            # === BASE CABINETS ===
            'base_cabinet': lambda: self.generate_cabinet(x, y, z, width, height, depth),
            'drawers': lambda: self.generate_drawer_cabinet(x, y, z, width, height, depth, num_drawers=kwargs.get('num_drawers', 3)),
            'drawer_cabinet': lambda: self.generate_drawer_cabinet(x, y, z, width, height, depth, num_drawers=kwargs.get('num_drawers', 3)),
            'sink_cabinet': lambda: self.generate_sink_cabinet(x, y, z, width, height, depth),
            'dishwasher': lambda: self.generate_dishwasher(x, y, z, width, height, depth),
            'corner_cabinet': lambda: self.generate_corner_cabinet(x, y, z, width, height, depth),
            'trash_cabinet': lambda: self.generate_trash_cabinet(x, y, z, width, height, depth),
            'coffee_station': lambda: self.generate_coffee_station(x, y, z, width, height, depth),
            
            # === COOKING ===
            'stove_cabinet': lambda: self.generate_cooktop(x, y + height, z + 4, width, depth - 8),
            'cooktop': lambda: self.generate_cooktop(x, y, z, width, depth),
            'oven': lambda: self.generate_oven(x, y, z, width, kwargs.get('oven_height', 60), depth),
            'hood': lambda: self.generate_hood(x, y, z, width, kwargs.get('hood_height', 40), kwargs.get('hood_depth', 35)),
            
            # === TALL UNITS (MONOLITH) ===
            'fridge': lambda: self.generate_fridge(x, y, z, width, height, depth),
            'pantry': lambda: self.generate_pantry(x, y, z, width, height, depth),
            'oven_tower': lambda: self.generate_oven_tower(x, y, z, width, height, depth),
            'pull_out_pantry': lambda: self.generate_pull_out_pantry(x, y, z, width, height, depth),
            
            # === WALL CABINETS ===
            'wall_cabinet': lambda: self.generate_wall_cabinet(x, y, z, width, height, depth),
            'microwave_cabinet': lambda: self.generate_microwave_cabinet(x, y, z, width, height, depth),
            'glass_cabinet': lambda: self.generate_glass_cabinet(x, y, z, width, height, depth),
            'open_shelving': lambda: self.generate_open_shelving(x, y, z, width, height, depth),
            
            # === SPECIALTY ===
            'wine_rack': lambda: self.generate_wine_rack(x, y, z, width, height, depth),
            'bottle_rack': lambda: self.generate_wine_rack(x, y, z, width, height, depth),
            'spice_rack': lambda: self.generate_spice_rack(x, y, z, width, height, depth),
            'appliance_garage': lambda: self.generate_appliance_garage(x, y, z, width, height, depth),
            
            # === ACCESSORIES ===
            'knife_block': lambda: self.generate_knife_block(x, y, z, width, height, depth),
            'utensil_holder': lambda: self.generate_utensil_holder(x, y, z, width, height),
            
            # === FILLERS ===
            'filler': lambda: self.add_box(x, y, z, width, height, depth - 2),
            'landing': lambda: self.generate_drawer_cabinet(x, y, z, width, height, depth, num_drawers=2),
            'prep': lambda: self.generate_drawer_cabinet(x, y, z, width, height, depth, num_drawers=3),
            'storage': lambda: self.generate_cabinet(x, y, z, width, height, depth),
            'secondary': lambda: self.generate_drawer_cabinet(x, y, z, width, height, depth, num_drawers=4),
        }
        
        generator = generators.get(item_type, lambda: self.generate_cabinet(x, y, z, width, height, depth))
        generator()

    def generate_item_rotated_z(self, item_type: str, x: float, y: float, z: float, width: float, height: float = 85, depth: float = 60, **kwargs):
        """
        Generate item rotated 90° for placement on perpendicular wall (Z axis).
        Item faces X+ direction instead of Z+.
        
        For L-shape Arm B: cabinets on left wall facing into room.
        """
        # For rotated items, we need to:
        # 1. Swap width and depth in the geometry
        # 2. Generate at correct position
        
        # Simple approach: generate with swapped dimensions
        # The item's "width" becomes its depth (into room along X)
        # The item's "depth" becomes its width (along wall on Z)
        
        if item_type == 'fridge':
            self._generate_fridge_rotated(x, y, z, width, height, depth)
        elif item_type == 'pantry':
            self._generate_pantry_rotated(x, y, z, width, height, depth)
        else:
            # Generic rotation: just swap width/depth and use basic cabinet
            self.generate_cabinet(x, y, z, depth, height, width)
    
    def _generate_fridge_rotated(self, x: float, y: float, z: float, width: float, height: float, depth: float):
        """Fridge rotated 90° - door faces X+ direction."""
        thick = 2.0
        # Swap w/d for rotated placement
        w = depth  # Width along X (into room)
        d = width  # Depth along Z (item's original width)
        
        # Outer shell
        self.add_box(x, y, z, thick, height, d)  # Left (now back)
        self.add_box(x + w - thick, y, z, thick, height, d)  # Right (now front-ish)
        self.add_box(x + thick, y, z, w - 2*thick, thick, d)  # Bottom
        self.add_box(x + thick, y + height - thick, z, w - 2*thick, thick, d)  # Top
        self.add_box(x, y + thick, z, w, height - 2*thick, thick)  # Back
        
        # Freezer/Fridge compartments
        freezer_h = height * 0.28
        fridge_h = height - freezer_h - thick
        
        # Divider
        self.add_box(x + thick, y + fridge_h, z + thick, w - 2*thick, thick, d - thick)
        
        # Doors face X+ (front of room)
        # Freezer door
        self.add_box(x + w, y + fridge_h + thick, z, 3.0, freezer_h - thick, d)
        self.add_box(x + w + 3.0, y + fridge_h + freezer_h/2, z + d - 8, 3, 15, 2)  # Handle
        
        # Fridge door
        self.add_box(x + w, y, z, 3.0, fridge_h, d)
        self.add_box(x + w + 3.0, y + fridge_h - 25, z + d - 8, 3, 20, 2)  # Handle
        
        # Internal shelves
        num_shelves = 4
        shelf_gap = fridge_h / (num_shelves + 1)
        for i in range(1, num_shelves + 1):
            shelf_y = y + thick + i * shelf_gap
            self.add_box(x + thick + 2, shelf_y, z + thick + 3, w - 2*thick - 4, 1, d - thick - 8)
    
    def _generate_pantry_rotated(self, x: float, y: float, z: float, width: float, height: float, depth: float):
        """Pantry cabinet rotated 90° - door faces X+ direction."""
        thick = 1.8
        # Swap w/d for rotated placement
        w = depth  # Width along X
        d = width  # Depth along Z
        
        # Carcass
        self.add_box(x, y, z, thick, height, d)  # Left (back wall)
        self.add_box(x + w - thick, y, z, thick, height, d)  # Right
        self.add_box(x + thick, y, z, w - 2*thick, thick, d)  # Bottom
        self.add_box(x + thick, y + height - thick, z, w - 2*thick, thick, d)  # Top
        self.add_box(x, y + thick, z, w - thick, height - 2*thick, 0.5)  # Back
        
        # Shelves
        num_shelves = 5
        usable_h = height - 2*thick
        shelf_gap = usable_h / num_shelves
        
        for i in range(num_shelves):
            shelf_y = y + thick + i * shelf_gap + 5
            self.add_box(x + thick + 2, shelf_y, z + 5, w - 2*thick - 4, 1.5, d - 10)
        
        # Door (faces X+)
        self.add_box(x + w, y, z, 2.0, height, d)
        # Handle
        self.add_box(x + w + 2.0, y + height/2 - 10, z + d - 6, 3, 20, 2)

    def generate_worktop(self, x_start: float, x_end: float, y: float, depth: float, holes: List[Tuple[float, float]] = None):
        """
        Generates a worktop from x_start to x_end.
        holes: list of (hole_start_x, hole_width)
        """
        thickness = 3.0
        overhang = 2.0
        
        real_depth = depth + overhang
        
        if not holes:
            self.add_box(x_start, y, 0, x_end - x_start, thickness, real_depth)
            return

        # Sort holes
        holes.sort(key=lambda item: item[0])
        
        current_x = x_start
        
        for h_start, h_width in holes:
            # Segment before hole
            if h_start > current_x:
                self.add_box(current_x, y, 0, h_start - current_x, thickness, real_depth)
            
            # Hole Area: We can add strips front/back if needed, but for sink/stove 
            # usually there is a strip at the back and front.
            # Let's add simple front/back rails
            rail_depth = 5.0
            # Back rail
            self.add_box(h_start, y, 0, h_width, thickness, rail_depth) # assuming z=0 is wall
            # Front rail
            self.add_box(h_start, y, real_depth - rail_depth, h_width, thickness, rail_depth)
            
            current_x = h_start + h_width
            
        # Final segment
        if current_x < x_end:
            self.add_box(current_x, y, 0, x_end - current_x, thickness, real_depth)
            
    def generate_room_shell(self, room: Room):
        """
        Generates the static geometry of the room: Floor, Ceiling (optional), Walls.
        Handles windows/doors by generating wall segments around them (basic rectangular subdivision).
        """
        w, l, h = room.width, room.length, room.height
        
        # Floor
        self.add_box(0, -10, 0, w, 10, l) # 10cm thick floor below 0
        
        # Helper to generate a wall plane with holes
        # Wall local coords: u (horizontal), v (vertical).
        # We need to transform to global coords.
        
        def build_wall_segments(wall_w, wall_h, holes):
            # holes: list of (u, v, w, h)
            # Naive approach: Just subtract? 
            # Better: a grid or quadtree?
            # Simple approach: If no holes, 1 quad.
            # If 1 hole, 4 quads (left, right, top, bottom).
            # If multiple? Overlap checking is hard.
            # Let's assume non-overlapping holes.
            
            # If no holes, return [(0, 0, wall_w, wall_h)]
            if not holes:
                return [(0, 0, wall_w, wall_h)]
            
            # For multiple holes, doing full CSG is hard.
            # Let's just draw the "Window/Door Frame" on top of the wall? 
            # User might want to see through.
            # Let's try to punch out the first hole.
            # For this MVP, let's just generate the wall *as is* (solid) 
            # and draw a "Window Glass" box *inside* it (maybe slightly indented)
            # effectively blocking it but distinguishing it.
            # Creating true geometric holes for arbitrary windows is complex.
            # Wait, user asked for "make walls windows".
            # Let's try to make at least 1 hole work.
            
            # Let's stick to: Solid wall + "Window/Door" geometry that is *visible*.
            # For "Door", we might want to see through.
            # Let's just make the wall segments for "Back" wall (where kitchen usually is).
            return [(0, 0, wall_w, wall_h)]

        # Walls - Thickness
        t = 10.0
        
        # Back Wall (Z=l if we look from front? Or Z=0?)
        # Standard: X is width, Z is depth.
        # "Back" is usually Z=0 or Z=L. 
        # Kitchen items usually at Z=0 (if depth=60 goes to Z=60).
        # So Back Wall is at Z=0? Or Z=-t?
        # Let's say Back Wall is at Z=0 coord, extending to Z=-t.
        
        # Let's define walls:
        # Back: X=0..W, Y=0..H, Z=0. Normal +Z.
        # Left: X=0, Y=0..H, Z=0..L. Normal +X.
        # Right: X=W, Y=0..H, Z=0..L. Normal -X.
        # Front: Z=L.
        
        # We generate "Shell" which is Outside the room volume?
        # Or Just boundary planes.
        
        # Back Wall (The main wall)
        # Check windows on 'back'
        back_feats = [f for f in (room.windows or []) + (room.doors or []) if f.get('wall') == 'back']
        # If back wall has features, we should try to split it.
        # For simplicity, I will implement a "Simple Subdivision" for 1 feature.
        # If multiple, it gets tricky.
        
        # General algo: List of Rects. Start with 1 full wall.
        # For each hole, split intersecting rects.
        
        def subtract_hole(rects, hole):
            hx, hy, hw, hh = hole
            new_rects = []
            for rx, ry, rw, rh in rects:
                # Check overlap
                if not (hx >= rx + rw or hx + hw <= rx or hy >= ry + rh or hy + hh <= ry):
                    # Overlap. Split rect.
                    # 1. Left of hole
                    if rx < hx:
                        new_rects.append((rx, ry, hx - rx, rh))
                    # 2. Right of hole
                    if rx + rw > hx + hw:
                        new_rects.append((hx + hw, ry, (rx + rw) - (hx + hw), rh))
                    # 3. Below hole (spanning hole width)
                    # We need to clamp to the hole vertical range relative to rect?
                    # Be careful not to create overlaps.
                    # A robust way: 
                    # Top slab (above hole top)
                    if ry + rh > hy + hh:
                        # width is constrained to overlap? No, full rect width?
                        # Using 4-way split is easier:
                        # L, R are full height? Or L, R are middle?
                        # Let's say: L and R are full height of rect?
                        # No, simpler:
                        # Top rect (full width of intersection)
                        # Bottom rect (full width of intersection)
                        # Left rect (middle height)
                        # Right rect (middle height)
                        pass
                    
                    # SIMPLER: Just 4 rects
                    # Left
                    if hx > rx:
                        new_rects.append((rx, ry, hx - rx, rh))
                    # Right
                    if hx + hw < rx + rw:
                        new_rects.append((hx + hw, ry, (rx + rw) - (hx + hw), rh))
                    # Bottom (clamped to hole horizontal)
                    # overlap_x_start = max(rx, hx)
                    # overlap_x_end = min(rx+rw, hx+hw)
                    # if overlap_x_end > overlap_x_start: ...
                    
                    # To avoid overlaps:
                    # R1 (Left): rx to hx
                    # R2 (Right): hx+hw to rx+rw
                    # R3 (Bottom): max(rx, hx) to min(rx+rw, hx+hw), ry to hy
                    # R4 (Top): max(rx, hx) to min(rx+rw, hx+hw), hy+hh to ry+rh
                    
                    overlap_x1 = max(rx, hx)
                    overlap_x2 = min(rx + rw, hx + hw)
                    
                    if overlap_x2 > overlap_x1:
                        # Bottom
                        if hy > ry:
                            new_rects.append((overlap_x1, ry, overlap_x2 - overlap_x1, hy - ry))
                        # Top
                        if hy + hh < ry + rh:
                             new_rects.append((overlap_x1, hy + hh, overlap_x2 - overlap_x1, (ry + rh) - (hy + hh)))
                             
                else:
                    new_rects.append((rx, ry, rw, rh))
            return new_rects

        # Walls generation
        walls_config = [
            # name, width, height, z_pos, is_x_wall (False=Z wall), invert_ext
            ('back', w, h, 0, False, -1),
            ('front', w, h, l, False, 1),
            ('left', l, h, 0, True, -1),
            ('right', l, h, w, True, 1) # placed at x=w, traversing z
        ]
        
        for name, ww, wh, pos, is_lateral, ext_dir in walls_config:
            # 1. Gather holes
            feats = [f for f in (room.windows or []) + (room.doors or []) if f.get('wall') == name]
            holes = []
            for f in feats:
                # x is along the wall width.
                # For lateral walls, 'x' in json implies distance along that wall (which is Z room coord)
                fx = f.get('x', 0)
                fy = f.get('y', 0)
                fw = f.get('width', 0)
                fh = f.get('height', 0)
                holes.append((fx, fy, fw, fh))
            
            # 2. Compute segments
            rects = [(0, 0, ww, wh)]
            for hole in holes:
                rects = subtract_hole(rects, hole)
                
            # 3. Generate Boxes for rects
            for rx, ry, rwidth, rheight in rects:
                if is_lateral:
                    # Wall along Z axis.
                    # x is fixed at `pos`.
                    # local x (rx) maps to Z??
                    # "Left" wall starts at z=0?
                    # Let's say: rx is Z coord.
                    # If wall is Left (x=0), Z goes 0..L.
                    # Thickness implies x goes from 0 to -10 (ext_dir=-1)
                    
                    # Box params: x, y, z, w, h, d
                    if ext_dir == -1: # Left
                        self.add_box(-t, ry, rx, t, rheight, rwidth)
                    else: # Right
                        self.add_box(pos, ry, rx, t, rheight, rwidth)
                else:
                    # Wall along X axis.
                    # rx is X coord.
                    # pos is Z coord.
                    if ext_dir == -1: # Back (Z=0), expand to -10
                         self.add_box(rx, ry, -t, rwidth, rheight, t)
                    else: # Front (Z=L), expand to L+10
                         self.add_box(rx, ry, pos, rwidth, rheight, t)

    def generate_forbidden_zones(self, room: Room):
        """
        Visualized low ceiling areas as red wireframes or boxes.
        We scan the room and if height < 200, we draw a box.
        """
        step = 20 # resolution
        w = int(room.width)
        d = int(room.length) # Or generic 60cm depth check
        
        # We only really care about the kitchen run depth (e.g. 0-60)
        # Let's scan x along the wall
        for x in range(0, w, step):
             # check height at wall and at depth 60
             h1 = room.get_ceiling_height(x, 0)
             h2 = room.get_ceiling_height(x + step, 0)
             
             if h1 < 200 or h2 < 200:
                 # Draw a "marker" box here
                 # height is room height? Or just a red box on floor?
                 # Let's draw a box up to the ceiling
                 self.add_box(x, 0, 0, step, min(h1, h2), 60)
                 
    def generate_fillers(self, placed_items, room):
        """
        Generates filler panels for gaps between cabinets to create a built-in look.
        Respects Room Geometry (Slopes) and Forbidden Zones (Windows).
        """
        # 1. Group by Layer (Base vs Wall)
        base_items = []
        wall_items = []
        
        for item in placed_items:
            if item['y'] < 100:
                base_items.append(item)
            else:
                wall_items.append(item)
                
        # Gather Windows on Back Wall
        windows = [f for f in (room.windows or []) if f.get('wall') == 'back']
        
        # Helper to process a layer
        def process_layer(items, default_h, default_d, layer_y):
            if not items: return
            
            # Sort by X
            items.sort(key=lambda i: i['x'])
            
            # Combined list of occupied intervals
            intervals = [(i['x'], i['x'] + i['width']) for i in items]
            
            # Check gaps
            current_x = 0
            
            # Add dummy end to force check of last gap
            intervals.append((room.width, room.width))
            
            for start, end in intervals:
                if start > current_x + 1: # 1cm tolerance
                    gap_start = current_x
                    gap_width = start - current_x
                    gap_end = start
                    gap_center = (gap_start + gap_end) / 2
                    
                    # 1. Check Slope / Ceiling Height
                    # We check ceiling height at the center of the gap (simplified)
                    # Or check min height across gap.
                    ceil_h = room.get_ceiling_height(gap_center, default_d)
                    
                    # If Box Top (layer_y + h) > ceil_h, we have a collision.
                    # Action: Clamp height or Skip?
                    # Profi: Clamp height to ceiling.
                    
                    real_h = default_h
                    if layer_y + real_h > ceil_h:
                        real_h = max(0, ceil_h - layer_y)
                        
                    if real_h < 1: 
                        # Too small/clipping
                        current_x = max(current_x, end)
                        continue
                        
                    # 2. Check Window Collision
                    # If this gap overlaps a window, we need to respect it.
                    blocked_by_window = False
                    
                    for w in windows:
                        wx, wy, ww, wh = w['x'], w['y'], w['width'], w['height']
                        # Intersection of [gap_start, gap_end] and [wx, wx+ww]
                        overlap = max(0, min(gap_end, wx + ww) - max(gap_start, wx))
                        
                        if overlap > 1: # Significant overlap
                            # Collision Logic
                            # If Wall Layer: Window blocks 100%.
                            if layer_y > 100: 
                                blocked_by_window = True
                                break
                            # If Base Layer: Allow if under window (sill check)
                            else:
                                if layer_y + real_h > wy:
                                    # Overlap in height too
                                    # Clamp height to window sill?
                                    # Ideally yes, let's make a low filler.
                                    real_h = max(0, wy - layer_y)
                                    if real_h < 1:
                                        blocked_by_window = True
                                    pass
                                    
                    if not blocked_by_window:
                        self.add_box(gap_start, layer_y, 0, gap_width, real_h, default_d - 2)
                    
                current_x = max(current_x, end)

        # Process Base
        process_layer(base_items, 85, 58, 0)
        
        # Process Wall
        process_layer(wall_items, 70, 33, 145)

    # ========== PREMIUM GEOMETRY V3 ==========
    
    def generate_gola_profile(self, x: float, y: float, z: float, width: float, depth: float, position: str = 'top'):
        """
        Generate handleless Gola profile - negative groove for finger grip.
        Creates the premium "floating door" look without visible handles.
        
        Args:
            position: 'top' (under worktop), 'between' (between drawers), 'bottom' (above plinth)
        """
        groove_height = 4.0
        groove_depth = 2.5
        inset_from_front = 1.5  # Groove is slightly behind door face
        
        # The groove is a horizontal channel cut into the cabinet
        # It's positioned at the specified height
        if position == 'top':
            groove_y = y + 85 - groove_height  # Just under worktop
        elif position == 'bottom':
            groove_y = y + 10  # Just above plinth
        else:
            groove_y = y  # Caller specifies exact position
        
        # Create the groove (negative space effect via colored/shadowed box)
        # In real CSG we'd subtract this. Here we add it as darker geometry
        self.add_box(x + 0.5, groove_y, z + depth - groove_depth - inset_from_front, 
                     width - 1, groove_height, groove_depth)
    
    def generate_recessed_plinth(self, x: float, z: float, width: float, depth: float, 
                                  plinth_height: float = 10, setback: float = 8):
        """
        Generate recessed toe kick that creates a floating effect.
        The plinth is set back from the cabinet face, creating shadow.
        
        Args:
            setback: How far back the plinth is from cabinet face (8-10cm typical)
        """
        # Plinth panel (recessed)
        plinth_depth = depth - setback
        self.add_box(x, 0, z + setback, width, plinth_height, plinth_depth)
        
        # Floor shadow strip (darker area where plinth is recessed)
        # This is optional visual enhancement
        shadow_height = 0.5
        self.add_box(x, 0, z, width, shadow_height, setback)
    
    def generate_end_panel(self, x: float, y: float, z: float, height: float, depth: float, 
                           side: str = 'left', panel_width: float = 2.0, include_plinth: bool = True):
        """
        Generate decorative end panel that covers exposed cabinet sides.
        Creates framed, finished look on kitchen ends.
        
        Args:
            side: 'left' or 'right'
            panel_width: Thickness of panel (typically 2cm)
            include_plinth: Whether to extend panel to floor
        """
        plinth_height = 10 if include_plinth else 0
        panel_height = height + plinth_height
        panel_y = 0 if include_plinth else y
        
        if side == 'left':
            panel_x = x - panel_width
        else:  # right
            panel_x = x
            
        self.add_box(panel_x, panel_y, z, panel_width, panel_height, depth)
    
    def generate_shadow_gap(self, x: float, y: float, z: float, gap_width: float = 0.2, 
                            height: float = 85, depth: float = 2):
        """
        Generate thin vertical shadow gap between doors/drawers.
        Creates visual separation and modern grid look.
        """
        # Shadow gap is a thin recessed line between cabinet modules
        self.add_box(x - gap_width/2, y, z, gap_width, height, depth)
    
    def generate_premium_drawer(self, x: float, y: float, z: float, width: float, 
                                 drawer_height: float, depth: float = 60, 
                                 with_gola: bool = True, gap: float = 0.2):
        """
        Generate a single premium drawer with Gola profile and shadow gaps.
        """
        thick = 1.8
        
        # Drawer front (slightly inset for shadow gap effect)
        front_inset = gap
        self.add_box(x + front_inset, y + front_inset, z + depth, 
                     width - 2*front_inset, drawer_height - 2*front_inset, 2.0)
        
        # Gola groove at top of drawer
        if with_gola:
            groove_h = 3.5
            groove_d = 2.0
            self.add_box(x + front_inset + 0.5, y + drawer_height - groove_h - front_inset, 
                         z + depth - groove_d, width - 2*front_inset - 1, groove_h, groove_d)
        
        # Inner drawer box
        inner_w = width - 2*thick - 4
        inner_h = drawer_height - 4
        inner_d = depth - 12
        self.add_box(x + thick + 2, y + 2, z + 6, inner_w, inner_h, inner_d)
        
        # Soft-close rail hints
        rail_w = 1.5
        self.add_box(x + thick, y + 3, z + 8, rail_w, 1, inner_d)
        self.add_box(x + width - thick - rail_w, y + 3, z + 8, rail_w, 1, inner_d)
    
    def generate_premium_cabinet(self, x: float, y: float, z: float, width: float, 
                                  height: float = 85, depth: float = 60,
                                  layer_heights: List[int] = None,
                                  with_gola: bool = True,
                                  is_end: str = None):  # 'left', 'right', or None
        """
        Generate a complete premium cabinet with:
        - Recessed plinth
        - Layer-aligned drawer fronts
        - Gola profiles
        - Shadow gaps
        - End panel if at edge
        """
        plinth_h = 10
        cabinet_y = y + plinth_h
        cabinet_h = height - plinth_h
        
        # Default layer heights (3 equal drawers)
        if layer_heights is None:
            layer_heights = [25, 25, cabinet_h - 50]  # Three sections
        
        thick = 1.8
        
        # === CARCASS ===
        
        # Side panels (from plinth height up)
        self.add_box(x, cabinet_y, z, thick, cabinet_h, depth)  # Left
        self.add_box(x + width - thick, cabinet_y, z, thick, cabinet_h, depth)  # Right
        
        # Bottom panel
        self.add_box(x + thick, cabinet_y, z, width - 2*thick, thick, depth)
        
        # Top panel/rail
        self.add_box(x + thick, cabinet_y + cabinet_h - thick, z, width - 2*thick, thick, depth)
        
        # Back panel
        self.add_box(x + thick, cabinet_y + thick, z, width - 2*thick, cabinet_h - 2*thick, 0.5)
        
        # === RECESSED PLINTH ===
        self.generate_recessed_plinth(x, z, width, depth, plinth_h, setback=8)
        
        # === DRAWER FRONTS (LAYER ALIGNED) ===
        current_y = cabinet_y
        for i, layer_h in enumerate(layer_heights):
            # Drawer front with shadow gap
            self.generate_premium_drawer(x, current_y, z, width, layer_h, depth, 
                                          with_gola=(i == 0))  # Gola only on top drawer
            current_y += layer_h
        
        # === END PANEL ===
        if is_end:
            self.generate_end_panel(x if is_end == 'left' else x + width, 
                                     cabinet_y, z, cabinet_h, depth, is_end)
    
    def generate_premium_item_by_type(self, item_type: str, x: float, y: float, z: float,
                                       width: float, height: float = 85, depth: float = 60,
                                       layer_heights: List[int] = None, is_end: str = None,
                                       **kwargs):
        """
        Premium dispatcher that routes to appropriate premium generator.
        """
        if item_type in ['drawer_cabinet', 'base_cabinet', 'drawers', 'storage']:
            self.generate_premium_cabinet(x, y, z, width, height, depth, 
                                           layer_heights, with_gola=True, is_end=is_end)
        elif item_type == 'sink_cabinet':
            # Sink cabinet: door on bottom, Gola stripped
            self.generate_sink_cabinet(x, y, z, width, height, depth)
            self.generate_recessed_plinth(x, z, width, depth)
        elif item_type == 'dishwasher':
            self.generate_dishwasher(x, y, z, width, height, depth)
            self.generate_recessed_plinth(x, z, width, depth)
        elif item_type == 'fridge':
            self.generate_fridge(x, y, z, width, height, depth)
        elif item_type == 'pantry':
            self.generate_pantry(x, y, z, width, height, depth)
        elif item_type == 'stove_cabinet':
            # Cooktop on top, drawers below
            self.generate_premium_cabinet(x, y, z, width, height, depth, 
                                           layer_heights, with_gola=True, is_end=is_end)
            self.generate_cooktop(x, y + height, z + 4, width, depth - 8)
        elif item_type == 'hood':
            self.generate_hood(x, y, z, width, kwargs.get('hood_height', 40), depth)
        elif item_type == 'wall_cabinet':
            self.generate_wall_cabinet(x, y, z, width, height, depth)
        elif item_type == 'filler':
            # Premium filler with shadow gaps
            self.add_box(x + 0.2, y, z, width - 0.4, height, depth - 2)
        else:
            # Fallback to standard
            self.generate_item_by_type(item_type, x, y, z, width, height, depth, **kwargs)

    # ========== L-SHAPE GEOMETRY ==========
    
    def generate_corner_blind(self, x: float, y: float, z: float, size: float = 65, height: float = 85, depth: float = 60):
        """
        Generate blind corner cabinet (65cm standard).
        L-shaped carcass with door on one face.
        """
        thick = 1.8
        plinth_h = 10
        cab_y = y + plinth_h
        cab_h = height - plinth_h
        
        # L-shaped back walls
        self.add_box(x, cab_y, z, size, cab_h, thick)  # Back along X
        self.add_box(x, cab_y, z, thick, cab_h, size)  # Back along Z
        
        # Front edges
        accessible_w = 30  # Front panel width
        self.add_box(x + size - thick, cab_y, z, thick, cab_h, size - accessible_w)
        self.add_box(x, cab_y, z + size - thick, size - accessible_w, cab_h, thick)
        
        # Bottom and top
        self.add_box(x + thick, cab_y, z + thick, size - 2*thick, thick, size - 2*thick)
        self.add_box(x + thick, cab_y + cab_h - thick, z + thick, size - 2*thick, thick, size - 2*thick)
        
        # Door (on front accessible face)
        self.add_box(x + size - accessible_w, cab_y, z + size, accessible_w, cab_h, 2)
        
        # Shelf (half-moon style)
        self.add_box(x + 5, cab_y + cab_h/2, z + 5, size - 10, 1.5, size - 10)
        
        # Plinth
        self.add_box(x + 8, 0, z + 8, size - 16, plinth_h, size - 16)
    
    def generate_corner_carousel(self, x: float, y: float, z: float, size: float = 90, height: float = 85, depth: float = 60):
        """
        Generate carousel corner cabinet (90cm premium) with lazy susan.
        """
        thick = 1.8
        plinth_h = 10
        cab_y = y + plinth_h
        cab_h = height - plinth_h
        
        # L-shaped back walls
        self.add_box(x, cab_y, z, size, cab_h, thick)  # Back X
        self.add_box(x, cab_y, z, thick, cab_h, size)  # Back Z
        
        # Diagonal front (simplified as two angled panels)
        front_offset = 35
        self.add_box(x + size - thick, cab_y, z, thick, cab_h, size - front_offset)
        self.add_box(x, cab_y, z + size - thick, size - front_offset, cab_h, thick)
        
        # Diagonal door section
        diag_w = front_offset * 1.4
        self.add_box(x + size - front_offset, cab_y, z + size - front_offset, diag_w, cab_h, 2)
        
        # Bottom and top
        self.add_box(x + thick, cab_y, z + thick, size - 2*thick, thick, size - 2*thick)
        self.add_box(x + thick, cab_y + cab_h - thick, z + thick, size - 2*thick, thick, size - 2*thick)
        
        # Carousel shelves (circular approximation)
        carousel_r = size * 0.35
        carousel_cx = x + size/2
        carousel_cz = z + size/2
        
        # Lower carousel
        self.add_box(carousel_cx - carousel_r, cab_y + 10, carousel_cz - carousel_r, carousel_r*2, 2, carousel_r*2)
        # Upper carousel
        self.add_box(carousel_cx - carousel_r, cab_y + cab_h/2, carousel_cz - carousel_r, carousel_r*2, 2, carousel_r*2)
        
        # Plinth
        self.add_box(x + 8, 0, z + 8, size - 16, plinth_h, size - 16)
    
    def generate_l_worktop(self, arm_a_start: float, arm_a_end: float, arm_b_end: float,
                           y: float, depth: float = 62, corner_size: float = 65):
        """
        Generate L-shaped worktop that flows through corner.
        """
        thickness = 3.0
        overhang = 2.0
        real_depth = depth + overhang
        
        # Arm A worktop (along X axis, from corner to end)
        self.add_box(corner_size, y, 0, arm_a_end - corner_size, thickness, real_depth)
        
        # Arm B worktop (along Z axis, from corner down)
        self.add_box(0, y, corner_size, real_depth, thickness, arm_b_end - corner_size)
        
        # Corner piece (square at intersection)
        self.add_box(0, y, 0, corner_size + overhang, thickness, corner_size + overhang)
        
        # Mitered edge detail (diagonal cut appearance)
        # This creates the professional 45° joint look
        miter_size = 5
        self.add_box(corner_size - miter_size, y + thickness, corner_size - miter_size, 
                     miter_size * 2, 0.5, miter_size * 2)
    
    def generate_l_shape_item(self, item: Dict, arm: str = 'A'):
        """
        Generate item with correct orientation for L-shape arm.
        Arm A = along X axis (standard)
        Arm B = along Z axis (rotated 90°)
        """
        x = item['x']
        width = item['width']
        height = item.get('height', 85)
        depth = item.get('depth', 60)
        item_type = item['type']
        
        if arm == 'A':
            # Standard orientation (along back wall)
            self.generate_item_by_type(item_type, x, 0, 0, width, height, depth)
        else:
            # Rotated for side wall (swap X and Z logic)
            # Items on Arm B are placed along Z axis
            z_pos = x  # x in Arm B context is actually Z position
            self.generate_item_by_type(item_type, 0, 0, z_pos, width, height, depth)

    # ========== KITCHEN ISLAND ==========
    
    def generate_island(self, x: float, z: float, width: float = 180, depth: float = 90, 
                        height: float = 90, has_cooktop: bool = False, has_seating: bool = True):
        """
        Generate premium kitchen island.
        
        Args:
            x, z: Center position of island
            width: Length along X axis (default 180cm)
            depth: Depth along Z axis (default 90cm)
            height: Counter height (default 90cm - bar height)
            has_cooktop: Add cooktop on island
            has_seating: Add overhang for bar stools
        """
        thick = 1.8
        plinth_h = 10
        
        # Calculate actual position (center to corner)
        ix = x - width/2
        iz = z - depth/2
        
        cab_y = plinth_h
        cab_h = height - plinth_h - 3  # Leave space for countertop
        
        print(f"  Generating Island: {width}x{depth}cm at ({x}, {z})")
        
        # === BASE CABINET STRUCTURE ===
        # Front panel (facing into room)
        self.add_box(ix, cab_y, iz, width, cab_h, thick)
        # Back panel
        self.add_box(ix, cab_y, iz + depth - thick, width, cab_h, thick)
        # Left side
        self.add_box(ix, cab_y, iz + thick, thick, cab_h, depth - 2*thick)
        # Right side
        self.add_box(ix + width - thick, cab_y, iz + thick, thick, cab_h, depth - 2*thick)
        
        # Bottom
        self.add_box(ix + thick, cab_y, iz + thick, width - 2*thick, thick, depth - 2*thick)
        
        # === INTERNAL DIVIDERS (creates 3 sections) ===
        section_w = (width - 4*thick) / 3
        for i in range(1, 3):
            div_x = ix + thick + i * (section_w + thick)
            self.add_box(div_x, cab_y + thick, iz + thick, thick, cab_h - 2*thick, depth - 2*thick)
        
        # === DRAWERS (premium look) ===
        drawer_front_depth = 2.0
        gap = 0.3
        
        for i in range(3):
            drawer_x = ix + thick + gap + i * (section_w + thick)
            # 3 drawers per section
            drawer_heights = [20, 20, cab_h - 42]
            current_y = cab_y + gap
            
            for dh in drawer_heights:
                self.add_box(drawer_x, current_y, iz - drawer_front_depth, 
                            section_w - 2*gap, dh - gap, drawer_front_depth)
                # Drawer handle (Gola style groove)
                self.add_box(drawer_x + 2, current_y + dh - 4, iz - drawer_front_depth - 0.5,
                            section_w - 4 - 2*gap, 3, 0.5)
                current_y += dh
        
        # === COUNTERTOP ===
        counter_thickness = 3.0
        overhang_front = 5 if has_seating else 2
        overhang_back = 2
        overhang_sides = 2
        
        # Seating overhang (one side extends more)
        seating_overhang = 30 if has_seating else 0
        
        self.add_box(
            ix - overhang_sides,
            height - counter_thickness,
            iz - overhang_front - seating_overhang,
            width + 2*overhang_sides,
            counter_thickness,
            depth + overhang_front + overhang_back + seating_overhang
        )
        
        # === PLINTH ===
        plinth_inset = 8
        self.add_box(
            ix + plinth_inset,
            0,
            iz + plinth_inset,
            width - 2*plinth_inset,
            plinth_h,
            depth - 2*plinth_inset
        )
        
        # === OPTIONAL COOKTOP ===
        if has_cooktop:
            cooktop_w = 60
            cooktop_d = 50
            cooktop_x = ix + (width - cooktop_w) / 2
            cooktop_z = iz + depth - cooktop_d - 10
            self.generate_cooktop(cooktop_x, height, cooktop_z, cooktop_w, cooktop_d)
        
        # === BAR STOOL POSITIONS (visual markers) ===
        if has_seating:
            stool_spacing = 60
            num_stools = int(width / stool_spacing)
            for i in range(num_stools):
                stool_x = ix + 30 + i * stool_spacing
                stool_z = iz - seating_overhang - 40
                # Simple stool representation
                self.add_box(stool_x, 0, stool_z, 40, 65, 40)

    def save(self, filename: str):
        with open(filename, 'w') as f:
            f.write("# KitchenCore Generator Output\n")
            for v in self.vertices:
                f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
            
            for face in self.faces:
                f_str = " ".join([str(idx) for idx in face])
                f.write(f"f {f_str}\n")
