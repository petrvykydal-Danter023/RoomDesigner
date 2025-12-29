from typing import List, Dict, Any
from core.schema import CabinetItem, Component

class CabinetFactory:
    """
    Converts abstract item definitions (type, width) into detailed CabinetItem schemas.
    COORDINATE SYSTEM: Y-UP (Standard 3D)
    """
    
    @staticmethod
    def create(item_data: Dict[str, Any], global_pos: List[float], rotation: float = 0) -> CabinetItem:
        itype = item_data.get('type', 'base_cabinet')
        width = item_data.get('width', 60)
        
        depth = 60
        height = 72 # Carcass height
        leg_height = 15
        door_thick = 2
        
        # Center of Carcass Y
        carcass_y = leg_height + height/2
        
        comps = []
        
        # GAP SETTINGS
        gap = 0.4 # Total reduction (0.2 per side)
        
        # ---------------------------------------------------------------------
        # BASE CABINETS
        # ---------------------------------------------------------------------
        if itype in ["base_cabinet", "narrow_cabinet", "sink", "dishwasher", "drawer_unit"]:
            
            # Legs & Carcass (Standard)
            # if itype != "dishwasher": # REMOVED: Dishwasher needs carcass for surface
            if True:
                leg_x = width/2 - 5
                leg_z = depth/2 - 5
                comps.extend([
                    Component(type="leg", dims=[], pos=[leg_x, 0, -leg_z], asset_id="leg_v1", rotation=[0,0,0]), 
                    Component(type="leg", dims=[], pos=[-leg_x, 0, -leg_z], asset_id="leg_v1", rotation=[0,0,0]),
                    Component(type="leg", dims=[], pos=[leg_x, 0, leg_z], asset_id="leg_v1", rotation=[0,0,0]),
                    Component(type="leg", dims=[], pos=[-leg_x, 0, leg_z], asset_id="leg_v1", rotation=[0,0,0]),
                ])
                comps.append(Component(
                    type="carcass", dims=[width, height, depth], pos=[0, carcass_y, 0], color=[255, 255, 255, 255]
                ))

            # Worktop (Common for all base units)
            # Carcass: 60 deep (-30 to 30).
            # Door: 2 thick (30 to 32).
            # Worktop: Overhang front by 2cm (Cover door). Back flush.
            # Depth: 60 (carcass) + 2 (door) + 1 (overhang) = 63cm
            # Z range: -30 to 33. Center: 1.5.
            wt_thick = 3
            wt_y = leg_height + height + wt_thick/2
            
            # Add Worktop (Concrete)
            comps.append(Component(
                type="worktop", dims=[width, wt_thick, 63], pos=[0, wt_y, 1.5], color=[150, 150, 155, 255]
            ))

            # Specifics
            if itype == "drawer_unit":
                # Stacks of 3 drawers
                # Height 72. 3x 24cm.
                # Drawers
                for i in range(3):
                    # y pos: bottom of drawer?
                    # 0..24, 24..48, 48..72
                    # Center Y: 12, 36, 60
                    dy = carcass_y - height/2 + 12 + i*24
                    
                    comps.append(Component(
                         type="drawer", dims=[width - gap, 24 - gap, door_thick],
                         pos=[0, dy, depth/2 + door_thick/2], # Use asset or box? 
                         # Use generated asset for better detail if we used it, but box is fine for flat front
                         # Actually we made asset drawer_front_v1. Let's use it? 
                         # But asset has fixed size 60x24. If width is different, scaling needed.
                         # Dimensions in Component DO NOT scale the asset automatically unless we implement scaling.
                         # Our Exporter scales 'cabinet_doors' if dims provided? No, it uses dims for box creation if no asset_id.
                         # If asset_id provided, it uses asset.
                         # Let's use asset "drawer_front_v1" and hope scale applies?
                         # Exporter logic: "if comp.asset_id: load asset. Apply scale = dims / asset_dims?"
                         # Current exporter likely mostly does Identity scale for assets or User defined scale.
                         # Let's stick to BOX generation (like door) for now to support variable widths, 
                         # unless we update Exporter to Scale.
                         # Since we just added drawer_front_v1 asset but maybe Exporter ignores it?
                         # Let's use simple Box with Gap for now to be safe and consistent with Doors.
                         # We'll use color Wood.
                         color=[139, 69, 19, 255]
                    ))
                    # Handle
                    comps.append(Component(
                        type="handle", dims=[], pos=[0, dy + 8, depth/2 + door_thick], 
                        asset_id="handle_v1", rotation=[0,0,90] # Horizontal handle
                    ))
            
            elif itype == "sink":
                # Door (With Gap)
                comps.append(Component(
                    type="door", dims=[width - gap, height - gap, door_thick], 
                    pos=[0, carcass_y, depth/2 + door_thick/2], color=[139, 69, 19, 255]
                ))
                # Sink Asset (On top of worktop)
                comps.append(Component(
                   type="sink", dims=[], pos=[0, leg_height + height + wt_thick, 0], asset_id="sink_v1", rotation=[0, 0, 0]
                ))
                 # Handle (Lowered)
                comps.append(Component(
                    type="handle", dims=[], pos=[width/2 - 5, carcass_y + height/2 - 10, depth/2 + door_thick], 
                    asset_id="handle_v1", rotation=[0,0,0] 
                ))
            
            elif itype == "dishwasher":
                # Full Door (Integrated)
                d_h = height + leg_height
                comps.append(Component(
                    type="door", dims=[width - gap, d_h - gap, door_thick], 
                    pos=[0, d_h/2, depth/2 + door_thick/2], color=[139, 69, 19, 255] # Integrated Wood
                ))
                 # Handle
                comps.append(Component(
                    type="handle", dims=[], pos=[0, d_h - 10, depth/2 + door_thick], asset_id="handle_v1", rotation=[0,0,90]
                ))
                
            else: # Standard Base (With Gap)
                 # Base Cabinet
                comps.append(Component(
                    type="door", dims=[width - gap, height - gap, door_thick], 
                    pos=[0, carcass_y, depth/2 + door_thick/2], color=[139, 69, 19, 255]
                ))
                # Handle (Lowered to avoid Worktop collision)
                comps.append(Component(
                    type="handle", dims=[], pos=[width/2 - 5, carcass_y + height/2 - 10, depth/2 + door_thick], 
                    asset_id="handle_v1", rotation=[0,0,0] 
                ))

        # ---------------------------------------------------------------------
        # TALL APPLIANCES & SPACERS
        # ---------------------------------------------------------------------
        elif itype == "pantry":
            # Tall unit. Height 200.
            p_height = 200
            # Carcass
            comps.append(Component(
                type="carcass", dims=[width, p_height, depth], pos=[0, p_height/2, 0], color=[255, 255, 255, 255]
            ))
            # Door (Tall)
            comps.append(Component(
                type="door", dims=[width - gap, p_height - gap, door_thick],
                pos=[0, p_height/2, depth/2 + door_thick/2], color=[139, 69, 19, 255]
            ))
            # Handle (Vertical, centered height?)
            comps.append(Component(
                type="handle", dims=[], pos=[width/2 - 5, 100, depth/2 + door_thick], 
                asset_id="handle_v1", rotation=[0,0,0]
            ))
            # Legs? Yes.
            leg_x = width/2 - 5; leg_z = depth/2 - 5
            comps.extend([
                Component(type="leg", dims=[], pos=[leg_x, 0, -leg_z], asset_id="leg_v1", rotation=[0,0,0]),
                Component(type="leg", dims=[], pos=[-leg_x, 0, -leg_z], asset_id="leg_v1", rotation=[0,0,0]),
                Component(type="leg", dims=[], pos=[leg_x, 0, leg_z], asset_id="leg_v1", rotation=[0,0,0]),
                Component(type="leg", dims=[], pos=[-leg_x, 0, leg_z], asset_id="leg_v1", rotation=[0,0,0]),
            ])

        elif itype == "fridge_spacer":
            # "Tin Shelf all the way up" -> Tall Open Metal Shelf
            # Height: 200 (Match Fridge). Depth: 60.
            # Visual: Brushed Metal / Tin.
            s_height = 200
            
            # 1. Back Panel
            comps.append(Component(
                type="panel", dims=[width, s_height, 2], pos=[0, s_height/2, -depth/2 + 1], color=[160, 170, 180, 255] # Tin color
            ))
            # 2. Side Panels? Frame.
            # Left
            comps.append(Component(
                type="panel", dims=[2, s_height, depth], pos=[-width/2 + 1, s_height/2, 0], color=[160, 170, 180, 255]
            ))
            # Right
            comps.append(Component(
                type="panel", dims=[2, s_height, depth], pos=[width/2 - 1, s_height/2, 0], color=[160, 170, 180, 255]
            ))
            # 3. Shelves (Every 40cm?)
            for i in range(5):
                sy = 10 + i * 45
                comps.append(Component(
                    type="shelf", dims=[width - 4, 2, depth - 2], pos=[0, sy, 0], color=[200, 200, 210, 255] # Lighter metal
                ))
        
        elif itype == "fridge":
            # Just the Asset
            comps.append(Component(
                type="appliance", dims=[], pos=[0, 0, 0], asset_id="fridge_tall_v1", rotation=[0, 0, 0]
            ))

        elif itype == "stove":
            # Oven Carcass
            comps.append(Component(
                type="carcass", dims=[width, height, depth], pos=[0, carcass_y, 0], color=[255, 255, 255, 255]
            ))
            
            # Worktop for Stove too
            wt_thick = 3
            wt_y = leg_height + height + wt_thick/2
            comps.append(Component(
                type="worktop", dims=[width, wt_thick, 63], pos=[0, wt_y, 1.5], color=[150, 150, 155, 255]
            ))

            # Legs
            leg_x = width/2 - 5; leg_z = depth/2 - 5
            comps.extend([
                Component(type="leg", dims=[], pos=[leg_x, 0, -leg_z], asset_id="leg_v1", rotation=[0,0,0]),
                Component(type="leg", dims=[], pos=[-leg_x, 0, -leg_z], asset_id="leg_v1", rotation=[0,0,0]),
                Component(type="leg", dims=[], pos=[leg_x, 0, leg_z], asset_id="leg_v1", rotation=[0,0,0]),
                Component(type="leg", dims=[], pos=[-leg_x, 0, leg_z], asset_id="leg_v1", rotation=[0,0,0]),
            ])
            # Asset Face (Oven usually has its own front, but if we had a cabinet door below?)
            # Oven typically is the front. No door change needed here.
            comps.append(Component(
                type="oven", dims=[], pos=[0, carcass_y, depth/2], asset_id="oven_v1", rotation=[0,0,0]
            ))

        # ---------------------------------------------------------------------
        # UPPER
        # ---------------------------------------------------------------------
        elif "upper" in itype or itype == "hood":
            
            if itype == "upper_bridge":
                # Over-Fridge Cabinet: Deep (60) and Short (35)
                u_height = 35
                u_depth = 60
                # Carcass
                comps.append(Component(
                    type="carcass", dims=[width, u_height, u_depth], pos=[0, u_height/2, 0], color=[255, 255, 255, 255]
                ))
                # Door (With Gap)
                comps.append(Component(
                    type="door", dims=[width - gap, u_height - gap, door_thick], 
                    pos=[0, u_height/2, u_depth/2 + door_thick/2], color=[139, 69, 19, 255]
                ))
                 # Handle (Horizontal on bottom?)
                comps.append(Component(
                    type="handle", dims=[], pos=[width/2, 5, u_depth/2 + door_thick], 
                    asset_id="handle_v1", rotation=[0,0,90]
                ))

            elif itype == "hood":
                comps.append(Component(
                    type="hood", dims=[], pos=[0, 0, 0], asset_id="hood_v1", rotation=[0, 0, 0]
                ))
            
            elif itype == "glass_upper":
                # Standard Upper dims
                u_height = 70; u_depth = 35
                # Carcass
                comps.append(Component(
                    type="carcass", dims=[width, u_height, u_depth], pos=[0, u_height/2, 0], color=[255, 255, 255, 255]
                ))
                # Glass Door Asset
                # Asset is 60x70. If width!=60, this might look weird if not scaled.
                # Assuming 60cm wide.
                comps.append(Component(
                    type="door_glass", dims=[], pos=[0, u_height/2, u_depth/2 + door_thick/2], 
                    asset_id="glass_door_v1", rotation=[0,0,0]
                ))
                # Handle
                comps.append(Component(
                    type="handle", dims=[], pos=[width/2 - 5, 10, u_depth/2 + door_thick], 
                    asset_id="handle_v1", rotation=[0,0,0]
                ))

            else:
                # Standard Upper
                u_height = 70; u_depth = 35
                # Carcass
                comps.append(Component(
                    type="carcass", dims=[width, u_height, u_depth], pos=[0, u_height/2, 0], color=[255, 255, 255, 255]
                ))
                # Door (With Gap)
                comps.append(Component(
                    type="door", dims=[width - gap, u_height - gap, door_thick], 
                    pos=[0, u_height/2, u_depth/2 + door_thick/2], color=[139, 69, 19, 255]
                ))
                comps.append(Component(
                    type="handle", dims=[], pos=[width/2 - 5, 10, u_depth/2 + door_thick], 
                    asset_id="handle_v1", rotation=[0,0,0]
                ))

        return CabinetItem(
            id=f"{itype}_{int(global_pos[0])}",
            type=itype,
            position=global_pos,
            rotation=rotation,
            components=comps
        )
