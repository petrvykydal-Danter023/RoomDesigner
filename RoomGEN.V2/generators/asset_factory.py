import trimesh
import numpy as np
import os
import shutil

class AssetFactory:
    """
    Generates static placeholder assets for the Hybrid Renderer.
    saves them to assets/ folder.
    """
    
    ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    
    @staticmethod
    @staticmethod
    def _generate_upper_corner_monolith(path):
        # Monolithic L-Shaped Open Shelf Unit (60x60)
        h, d, w = 70, 35, 60
        parts = []
        
        # 1. Back Panels (White)
        # Back Z (Along X-axis wall)
        back_z = trimesh.creation.box(extents=[w, h, 2])
        back_z.apply_translation([w/2, h/2, 1])
        parts.append(back_z)
        
        # Back X (Along Z-axis wall)
        back_x = trimesh.creation.box(extents=[2, h, w])
        back_x.apply_translation([1, h/2, w/2])
        parts.append(back_x)
        
        # 2. Side/End Panels (White)
        # End X (Far Right): At X=60
        end_x = trimesh.creation.box(extents=[2, h, d])
        end_x.apply_translation([w - 1, h/2, d/2])
        parts.append(end_x)
        
        # End Z (Far Front): At Z=60
        end_z = trimesh.creation.box(extents=[d, h, 2])
        end_z.apply_translation([d/2, h/2, w - 1])
        parts.append(end_z)
        
        # 3. Top/Bottom Panels (White)
        top1 = trimesh.creation.box(extents=[w, 2, d]); top1.apply_translation([w/2, h-1, d/2])
        top2 = trimesh.creation.box(extents=[d, 2, w]); top2.apply_translation([d/2, h-1, w/2])
        bot1 = trimesh.creation.box(extents=[w, 2, d]); bot1.apply_translation([w/2, 1, d/2])
        bot2 = trimesh.creation.box(extents=[d, 2, w]); bot2.apply_translation([d/2, 1, w/2])
        parts.extend([top1, top2, bot1, bot2])
        
        # Colorize White Parts
        for p in parts: p.visual.face_colors = [250, 250, 255, 255]
        
        # 4. Shelves (Wood, L-Shaped)
        shelf_color = [139, 69, 19, 255]
        for y in [15, 35, 55]:
             # S1 (X-run): 56 x 2 x 33. Center X=31, Z=18.5
             s1 = trimesh.creation.box(extents=[w-2-2, 2, d-2]); 
             s1.apply_translation([(w)/2 + 1, y, d/2 + 1])
             
             # S2 (Z-run): 33 x 2 x 56. Center X=18.5, Z=31
             s2 = trimesh.creation.box(extents=[d-2, 2, w-2-2])
             s2.apply_translation([d/2 + 1, y, (w)/2 + 1])
             
             s1.visual.face_colors = shelf_color
             s2.visual.face_colors = shelf_color
             parts.extend([s1, s2])
             
        mesh = trimesh.util.concatenate(parts)
        mesh.export(path)

    @staticmethod
    def _generate_upper_corner_open(path):
        # Base L-Corner (60x60, depth 35)
        # We REUSE the L-shape logic roughly
        h, d, thick = 70, 35, 2
        
        # 1. The Core L (60x60)
        # Z-arm (along Z axis): 60 deep. Width 35 (depth of other arm).
        # X-arm (along X axis): 60 wide. Depth 35.
        
        # Carcass parts
        # P1: 60x35 along X?
        # Let's frame it:
        # X-arm: Box [60, h, 35]. Pos [30, h/2, 17.5]
        # Z-arm: Box [35, h, 25]. Pos [17.5, h/2, 47.5] (60-35=25 remainder)
        # Union
        c1 = trimesh.creation.box(extents=[60, h, 35])
        c1.apply_translation([30, h/2, 17.5])
        
        c2 = trimesh.creation.box(extents=[35, h, 25])
        c2.apply_translation([17.5, h/2, 35 + 12.5])
        
        core = trimesh.util.concatenate([c1, c2])
        core.visual.face_colors = [255, 255, 255, 255]
        
        # Doors (Simple L)
        # D1 (X-face): Width 25 (60-35). Pos [35 + 12.5, h/2, 35+1].
        d1 = trimesh.creation.box(extents=[25, h-0.4, 2])
        d1.apply_translation([47.5, h/2, 36])
        
        # D2 (Z-face): Width 25. Pos [36, h/2, 47.5]. Rot 90.
        d2 = trimesh.creation.box(extents=[25, h-0.4, 2])
        d2.apply_translation([35+1, h/2, 47.5])
        d2.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0,1,0]))
        
        d1.visual.face_colors = [139, 69, 19, 255]
        d2.visual.face_colors = [139, 69, 19, 255]
        
        # 2. THE WINGS (Open Shelves)
        # Added to the "ends".
        # End 1: X-axis end. At X=60.
        # Shelf Unit: 20cm wide, 35cm deep, 70cm high.
        s1_w = 20
        shelf_unit_1 = AssetFactory._create_open_shelf(s1_w, h, d, color=[180, 190, 200, 255])
        # Position: Center X = 60 + 10 = 70. Z = 17.5.
        shelf_unit_1.apply_translation([60 + s1_w/2, 0, d/2]) # Y handled in create? No, create likely centered.
        # Let's make helper for shelf
        
        # End 2: Z-axis end. At Z=60.
        shelf_unit_2 = AssetFactory._create_open_shelf(s1_w, h, d, color=[180, 190, 200, 255], side_pos="left")
        # Position: X = 17.5. Center Z = 60 + 10 = 70.
        # Rotate -90 deg (Correct formatting: Back to Wall)
        shelf_unit_2.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2, [0,1,0]))
        # FIX: Align to Z-end (Center X=17.5, Z=70)
        shelf_unit_2.apply_translation([17.5, 0, 70])
        # Initial: [20, h, 35]. Center [0,0,0].
        # Rotated 90 around Y -> [35, h, 20].
        # Move to: X=17.5 (center of 35). Z=70.
        # Wait, create_open_shelf probably returns centered object.
        # Let's adjust manually.
        
        mesh = trimesh.util.concatenate([core, d1, d2, shelf_unit_1, shelf_unit_2])
        mesh.export(path)

    @staticmethod
    def _create_open_shelf(w, h, d, color, side_pos="right"):
        # Simple back + shelves + Side Panel
        # Back
        back = trimesh.creation.box(extents=[w, h, 2])
        back.apply_translation([0, h/2, -d/2 + 1])
        
        # Side Panel
        side = trimesh.creation.box(extents=[2, h, d])
        
        # Shelves (3)
        shelves = []
        
        if side_pos == "right":
             # Panel at +X
             side.apply_translation([w/2 - 1, h/2, 0])
             shelf_shift = -1
        else:
             # Panel at -X ("left")
             side.apply_translation([-(w/2 - 1), h/2, 0])
             shelf_shift = 1

        for i in range(3):
            s = trimesh.creation.box(extents=[w - 2, 2, d]) 
            s.apply_translation([shelf_shift, 15 + i*20, 0]) 
            shelves.append(s)
            
        mesh = trimesh.util.concatenate([back, side] + shelves)
        mesh.visual.face_colors = color
        return mesh

    @staticmethod
    def _generate_drawer_front(path):
        # 60cm wide, 24cm high (1/3 of 72)
        w, h, d = 60, 24, 2
        mesh = trimesh.creation.box(extents=[w, h, d])
        mesh.visual.face_colors = [139, 69, 19, 255] # Wood
        mesh.export(path)

    @staticmethod
    def _generate_pantry_door(path):
         # 60cm wide, 200cm high (Tall)
        w, h, d = 60, 200, 2
        mesh = trimesh.creation.box(extents=[w, h, d])
        mesh.visual.face_colors = [139, 69, 19, 255]
        mesh.export(path)

    @staticmethod
    def _generate_glass_door(path):
        # Frame + Glass
        w, h, d = 60, 70, 2
        fw = 5 
        f1 = trimesh.creation.box(extents=[fw, h, d]); f1.apply_translation([-(w/2 - fw/2), 0, 0])
        f2 = trimesh.creation.box(extents=[fw, h, d]); f2.apply_translation([(w/2 - fw/2), 0, 0])
        f3 = trimesh.creation.box(extents=[w - 2*fw, fw, d]); f3.apply_translation([0, (h/2 - fw/2), 0])
        f4 = trimesh.creation.box(extents=[w - 2*fw, fw, d]); f4.apply_translation([0, -(h/2 - fw/2), 0])
        frame = trimesh.util.concatenate([f1, f2, f3, f4])
        frame.visual.face_colors = [139, 69, 19, 255]
        glass = trimesh.creation.box(extents=[w - 2*fw, h - 2*fw, 0.5])
        glass.visual.face_colors = [200, 220, 255, 100] 
        mesh = trimesh.util.concatenate([frame, glass])
        mesh.export(path)

    @staticmethod
    def ensure_assets(force=False):
        """Generates all missing assets. Set force=True to regenerate."""
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        feature_map = {
            "handle_v1.glb": AssetFactory._generate_handle,
            "knob_v1.glb": AssetFactory._generate_knob, 
            "leg_v1.glb": AssetFactory._generate_leg,
            "sink_v1.glb": AssetFactory._generate_sink,
            "oven_v1.glb": AssetFactory._generate_oven,
            "hood_v1.glb": AssetFactory._generate_hood,
            "fridge_tall_v1.glb": AssetFactory._generate_fridge,
            "window_frame_v1.glb": AssetFactory._generate_window,
            "door_frame_v1.glb": AssetFactory._generate_door, # Changed from _generate_door_frame to _generate_door
            "corner_cabinet_l_v1.glb": AssetFactory._generate_corner_l_cabinet,
            "upper_corner_cabinet_l_v1.glb": AssetFactory._generate_upper_corner_l_cabinet,
            # NEW
            "drawer_front_v1.glb": AssetFactory._generate_drawer_front,
            "pantry_door_v1.glb": AssetFactory._generate_pantry_door,
            "glass_door_v1.glb": AssetFactory._generate_glass_door,
            "upper_corner_open_v1.glb": AssetFactory._generate_upper_corner_monolith
        }
        
        for name, func in feature_map.items():
            path = os.path.join(assets_dir, name)
            if force or not os.path.exists(path):
                print(f"Generating {name}...")
                func(path)
        print(f"✅ Assets check complete in {assets_dir}")

    @staticmethod
    def _generate_upper_corner_l_cabinet(path):
        # 60x60 Upper L-Shape
        # Depth 35
        # Height 70
        
        h = 70
        d = 35
        w = 60
        
        # Carcass
        # C1: X[0..35], Z[0..60] (Left run overlaps corner) - No.
        # Structure:
        # Leg 1 (Left): X[0..35], Z[35..60] ? 
        # Leg 2 (Right): X[35..60], Z[0..35] ?
        # Corner Box: X[0..35], Z[0..35]
        
        # Simpler: 
        # Box 1 (Left Wall): 35 wide (X), 60 deep (Z)? No.
        # Along Wall 1 (Z axis): X width is 35. Z length is 60.
        # Along Wall 2 (X axis): Z depth is 35. X length is 60.
        
        c1 = trimesh.creation.box(extents=[d, h, w]) # 35x70x60
        # Center: x=17.5, y=35, z=30
        c1.apply_translation([d/2, h/2, w/2])
        
        c2 = trimesh.creation.box(extents=[w - d, h, d]) # (60-35)=25 x 70 x 35
        # Center: x=35 + 12.5 = 47.5, y=35, z=17.5
        c2.apply_translation([d + (w-d)/2, h/2, d/2])
        
        carcass = trimesh.util.concatenate([c1, c2])
        carcass.visual.face_colors = [255, 255, 255, 255]
        
        # Doors (Bi-fold)
        # Door 1 (Facing +X, at X=35): Z goes 35..60. W=25.
        d1 = trimesh.creation.box(extents=[2, h, 25])
        d1.apply_translation([d + 1, h/2, d + 25/2]) # x=36, z=35+12.5=47.5
        
        # Door 2 (Facing +Z, at Z=35): X goes 35..60. W=25.
        d2 = trimesh.creation.box(extents=[25, h, 2])
        d2.apply_translation([d + 25/2, h/2, d + 1]) # x=47.5, z=36
        
        doors = trimesh.util.concatenate([d1, d2])
        doors.visual.face_colors = [139, 69, 19, 255]
        
        # Knobs
        k1 = trimesh.creation.cylinder(radius=1.5, height=2)
        k1.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 0, 1]))
        k1.apply_translation([37, 15, 40]) # Low knob
        
        k2 = trimesh.creation.cylinder(radius=1.5, height=2)
        k2.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
        k2.apply_translation([40, 15, 37])
        
        knobs = trimesh.util.concatenate([k1, k2])
        knobs.visual.face_colors = [50, 50, 50, 255]
        
        mesh = trimesh.util.concatenate([carcass, doors, knobs])
        mesh.export(path)

    # ... (Keep other generators) ...
    @staticmethod
    def _generate_handle(path):
        post1 = trimesh.creation.cylinder(radius=0.5, height=3)
        post1.apply_translation([0, -6, 1.5]) 
        post2 = trimesh.creation.cylinder(radius=0.5, height=3)
        post2.apply_translation([0, 6, 1.5]) 
        bar = trimesh.creation.cylinder(radius=0.4, height=14)
        rot = trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0])
        bar.apply_transform(rot)
        bar.apply_translation([0, 0, 3]) 
        mesh = trimesh.util.concatenate([post1, post2, bar])
        mesh.visual.face_colors = [200, 200, 200, 255]
        mesh.export(path)

    @staticmethod
    def _generate_knob(path):
        mesh = trimesh.creation.cylinder(radius=1.5, height=2)
        rot = trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0])
        mesh.apply_transform(rot)
        mesh.visual.face_colors = [50, 50, 50, 255] 
        mesh.export(path)

    @staticmethod
    def _generate_leg(path):
        base = trimesh.creation.cylinder(radius=2, height=1)
        stem = trimesh.creation.cylinder(radius=1, height=14)
        stem.apply_translation([0, 0, 7])
        base.apply_translation([0, 0, 0.5])
        mesh = trimesh.util.concatenate([base, stem])
        mesh.visual.face_colors = [20, 20, 20, 255] 
        rot = trimesh.transformations.rotation_matrix(-np.pi/2, [1, 0, 0])
        mesh.apply_transform(rot)
        mesh.export(path)
        
    @staticmethod
    def _generate_sink(path):
        rim = trimesh.creation.box(extents=[50, 2, 45])
        bowl = trimesh.creation.box(extents=[40, 15, 35])
        bowl.apply_translation([0, -8.5, 0]) 
        faucet_stem = trimesh.creation.cylinder(radius=1.5, height=20)
        rot = trimesh.transformations.rotation_matrix(-np.pi/2, [1, 0, 0])
        faucet_stem.apply_transform(rot)
        faucet_stem.apply_translation([0, 10, -18]) 
        faucet_spout = trimesh.creation.cylinder(radius=1.2, height=15)
        faucet_spout.apply_translation([0, 20, -10]) 
        mesh = trimesh.util.concatenate([rim, bowl, faucet_stem, faucet_spout])
        mesh.visual.face_colors = [200, 200, 210, 255] 
        mesh.export(path)

    @staticmethod
    def _generate_oven(path):
        face = trimesh.creation.box(extents=[59.5, 59.5, 2])
        face.visual.face_colors = [220, 220, 220, 255] # Silver
        window = trimesh.creation.box(extents=[45, 35, 2.5])
        window.apply_translation([0, 5, 0]) 
        window.visual.face_colors = [10, 10, 10, 255]
        handle = trimesh.creation.box(extents=[50, 2, 4])
        handle.apply_translation([0, 25, 2]) 
        handle.visual.face_colors = [180, 180, 180, 255]
        knob1 = trimesh.creation.cylinder(radius=2, height=3)
        knob1.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0])) 
        knob1.apply_translation([-20, 25, 2])
        knob2 = trimesh.creation.cylinder(radius=2, height=3)
        knob2.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
        knob2.apply_translation([20, 25, 2])
        mesh = trimesh.util.concatenate([face, window, handle, knob1, knob2])
        mesh.export(path)
        
    @staticmethod
    def _generate_hood(path):
        base = trimesh.creation.box(extents=[60, 5, 50])
        base.visual.face_colors = [200, 200, 200, 255]
        chimney = trimesh.creation.box(extents=[25, 40, 25])
        chimney.apply_translation([0, 22.5, -10]) 
        chimney.visual.face_colors = [180, 180, 180, 255]
        mesh = trimesh.util.concatenate([base, chimney])
        mesh.export(path)

    @staticmethod
    def _generate_fridge(path):
        body = trimesh.creation.box(extents=[60, 200, 60])
        body.apply_translation([0, 100, 0]) 
        body.visual.face_colors = [230, 230, 235, 255] 
        gap = trimesh.creation.box(extents=[60.5, 1, 60.5])
        gap.apply_translation([0, 80, 0])
        gap.visual.face_colors = [100, 100, 100, 255]
        h1 = trimesh.creation.box(extents=[2, 40, 2])
        h1.apply_translation([-25, 130, 31]) 
        h1.visual.face_colors = [150, 150, 150, 255]
        h2 = trimesh.creation.box(extents=[2, 30, 2])
        h2.apply_translation([-25, 50, 31]) 
        h2.visual.face_colors = [150, 150, 150, 255]
        mesh = trimesh.util.concatenate([body, gap, h1, h2])
        mesh.export(path)
        
    @staticmethod
    def _generate_window(path):
        outer_w = 100
        outer_h = 120
        thick = 10
        v1 = trimesh.creation.box(extents=[5, outer_h, thick])
        v1.apply_translation([-(outer_w/2 - 2.5), 0, 0])
        v2 = trimesh.creation.box(extents=[5, outer_h, thick])
        v2.apply_translation([(outer_w/2 - 2.5), 0, 0])
        h1 = trimesh.creation.box(extents=[outer_w, 5, thick])
        h1.apply_translation([0, (outer_h/2 - 2.5), 0])
        h2 = trimesh.creation.box(extents=[outer_w, 5, thick])
        h2.apply_translation([0, -(outer_h/2 - 2.5), 0])
        sill = trimesh.creation.box(extents=[outer_w + 10, 3, thick + 5])
        sill.apply_translation([0, -(outer_h/2 + 1.5), thick/2]) 
        cross_v = trimesh.creation.box(extents=[2, outer_h-10, thick-4])
        cross_h = trimesh.creation.box(extents=[outer_w-10, 2, thick-4])
        glass = trimesh.creation.box(extents=[outer_w-10, outer_h-10, 2])
        glass.visual.face_colors = [180, 220, 255, 120]
        
        frame_parts = [v1, v2, h1, h2, sill, cross_v, cross_h]
        for p in frame_parts: p.visual.face_colors = [255, 255, 255, 255]
        mesh = trimesh.util.concatenate(frame_parts + [glass])
        mesh.export(path)

    @staticmethod
    def _generate_door(path):
        v1 = trimesh.creation.box(extents=[5, 210, 10])
        v1.apply_translation([-42.5, 105, 0])
        v2 = trimesh.creation.box(extents=[5, 210, 10])
        v2.apply_translation([42.5, 105, 0])
        top = trimesh.creation.box(extents=[90, 5, 10])
        top.apply_translation([0, 207.5, 0])
        panel = trimesh.creation.box(extents=[80, 205, 4])
        panel.apply_translation([0, 102.5, 0])
        panel.visual.face_colors = [200, 200, 200, 100]
        mesh = trimesh.util.concatenate([v1, v2, top, panel])
        mesh.visual.face_colors = [139, 90, 43, 255] 
        mesh.export(path)

    @staticmethod
    def _generate_corner_l_cabinet(path):
        c1 = trimesh.creation.box(extents=[60, 72, 90])
        c1.apply_translation([30, 15 + 36, 45])
        c2 = trimesh.creation.box(extents=[30, 72, 60]) 
        c2.apply_translation([75, 15 + 36, 30])
        carcass = trimesh.util.concatenate([c1, c2])
        carcass.visual.face_colors = [255, 255, 255, 255]
        
        d1 = trimesh.creation.box(extents=[2, 72, 30])
        d1.apply_translation([61, 15 + 36, 75])
        d2 = trimesh.creation.box(extents=[30, 72, 2])
        d2.apply_translation([75, 15 + 36, 61])
        doors = trimesh.util.concatenate([d1, d2])
        doors.visual.face_colors = [139, 69, 19, 255] 
        
        k1 = trimesh.creation.cylinder(radius=1.5, height=2)
        k1.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 0, 1]))
        k1.apply_translation([63, 15 + 72 - 10, 65]) 
        k2 = trimesh.creation.cylinder(radius=1.5, height=2)
        k2.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
        k2.apply_translation([65, 15 + 72 - 10, 63])
        knobs = trimesh.util.concatenate([k1, k2])
        knobs.visual.face_colors = [50, 50, 50, 255]
        
        legs = []
        leg_pos = [[10, 10], [80, 10], [10, 80], [50, 50], [80, 50], [50, 80]]
        for lx, lz in leg_pos:
            leg = trimesh.creation.cylinder(radius=2, height=14)
            leg.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
            leg.apply_translation([lx, 7, lz])
            base = trimesh.creation.cylinder(radius=2, height=1)
            base.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
            base.apply_translation([lx, 0.5, lz])
            l_mesh = trimesh.util.concatenate([base, leg])
            l_mesh.visual.face_colors = [20, 20, 20, 255]
            legs.append(l_mesh)
        leg_mesh = trimesh.util.concatenate(legs)

        # Worktop (Concrete L-Shape)
        # Height: 15 (legs) + 72 (carcass) = 87 base. Thickness 3.
        # Bottom at 87. Center at 88.5.
        wt_y = 15 + 72 + 1.5
        
        # Part 1: Along Z wall (X width 63, Z length 90)
        # X: 0..63. Center 31.5. Z: 0..90. Center 45.
        w1 = trimesh.creation.box(extents=[63, 3, 90])
        w1.apply_translation([31.5, wt_y, 45])
        
        # Part 2: Along X wall (X remaining 63..90, Z width 63)
        # X: 63..90 (Width 27). Center 63 + 13.5 = 76.5.
        # Z: 0..63. Center 31.5.
        w2 = trimesh.creation.box(extents=[27, 3, 63])
        w2.apply_translation([76.5, wt_y, 31.5])
        
        worktop = trimesh.util.concatenate([w1, w2])
        worktop.visual.face_colors = [150, 150, 155, 255] # Concrete

        mesh = trimesh.util.concatenate([carcass, doors, knobs, leg_mesh, worktop])
        mesh.export(path)

if __name__ == "__main__":
    AssetFactory.ensure_assets(force=True)
