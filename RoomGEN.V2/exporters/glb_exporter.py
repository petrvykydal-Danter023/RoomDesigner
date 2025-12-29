import os
from typing import List, Dict, Any
import numpy as np
import trimesh
from core.materials import get_material_for_item

class GlbExporter:
    """GLB exporter with correct room geometry and openings."""
    
    @staticmethod
    def export(items: List[Dict[str, Any]], output_path: str, 
               room_config: Dict[str, Any] = None):
        """Exports layout items + room to GLB format."""
        meshes = []
        
        W = room_config.get('width', 400) if room_config else 400
        D = room_config.get('depth', 300) if room_config else 300
        H = room_config.get('height', 270) if room_config else 270
        T = 8
        
        features = room_config.get('features', {}) if room_config else {}
        
        # ═══════════════════════════════════════════════════════════════
        # FLOOR
        # ═══════════════════════════════════════════════════════════════
        floor = trimesh.creation.box(extents=[W, 5, D])
        floor.apply_translation([W/2, -2.5, D/2])
        floor.visual.face_colors = [200, 180, 160, 255]
        meshes.append(floor)
        
        wall_color = [255, 255, 255, 80]
        
        # ═══════════════════════════════════════════════════════════════
        # BACK WALL with window cutout
        # ═══════════════════════════════════════════════════════════════
        back_feats = features.get('back', [])
        back_meshes = GlbExporter._create_wall_with_openings(
            wall_width=W, wall_height=H, wall_thickness=T,
            position=[0, 0, D - T],
            axis='x',
            openings=back_feats,
            wall_color=wall_color
        )
        meshes.extend(back_meshes)
        
        # ═══════════════════════════════════════════════════════════════
        # FRONT WALL (extra transparent, no openings usually)
        # ═══════════════════════════════════════════════════════════════
        front = trimesh.creation.box(extents=[W, H, T])
        front.apply_translation([W/2, H/2, T/2])
        front.visual.face_colors = [255, 255, 255, 30]
        meshes.append(front)
        
        # ═══════════════════════════════════════════════════════════════
        # LEFT WALL
        # ═══════════════════════════════════════════════════════════════
        left = trimesh.creation.box(extents=[T, H, D])
        left.apply_translation([T/2, H/2, D/2])
        left.visual.face_colors = wall_color
        meshes.append(left)
        
        # ═══════════════════════════════════════════════════════════════
        # RIGHT WALL with door cutout
        # ═══════════════════════════════════════════════════════════════
        right_feats = features.get('right', [])
        right_meshes = GlbExporter._create_wall_with_openings(
            wall_width=D, wall_height=H, wall_thickness=T,
            position=[W - T, 0, 0],
            axis='z',
            openings=right_feats,
            wall_color=wall_color
        )
        meshes.extend(right_meshes)
        
        # ═══════════════════════════════════════════════════════════════
        # FURNITURE
        # ═══════════════════════════════════════════════════════════════
        for item in items:
            x = item.get('x_local', 0)
            w = item.get('width', 60)
            d = 60
            h = 90
            y = 0
            
            if 'upper' in item['type'] or 'hood' in item['type'] or 'bridge' in item['type']:
                h = 70
                y = 150
                d = 35
            
            z_pos = D - T - d/2
            
            box = trimesh.creation.box(extents=[w, h, d])
            box.apply_translation([x + w/2, y + h/2, z_pos])
            
            mat = get_material_for_item(item['type'])
            rgb = [int(c * 255) for c in mat['color']]
            box.visual.face_colors = rgb + [255]
            meshes.append(box)
        
        scene = trimesh.Scene(meshes)
        scene.export(output_path, file_type='glb')
        return True
    
    @staticmethod
    def _create_wall_with_openings(wall_width, wall_height, wall_thickness,
                                    position, axis, openings, wall_color):
        """Creates wall segments around openings (windows/doors)."""
        meshes = []
        
        sorted_openings = sorted(openings, key=lambda o: o.get('x_start', 0))
        current_x = 0
        
        for opening in sorted_openings:
            o_start = opening.get('x_start', 0)
            o_width = opening.get('width', 80)
            o_type = opening.get('type', 'window')
            
            # Wall segment BEFORE opening
            if o_start > current_x:
                seg_w = o_start - current_x
                seg = GlbExporter._make_wall_segment(
                    seg_w, wall_height, wall_thickness, 
                    current_x, position, axis, wall_color
                )
                meshes.append(seg)
            
            # Process opening
            if o_type == 'window':
                sill = opening.get('sill_height', 90)
                o_height = opening.get('height', 120)
                
                # Wall BELOW window
                if sill > 0:
                    below = GlbExporter._make_wall_segment(
                        o_width, sill, wall_thickness,
                        o_start, position, axis, wall_color
                    )
                    meshes.append(below)
                
                # GLASS
                glass = GlbExporter._make_wall_segment(
                    o_width, o_height, wall_thickness/2,
                    o_start, [position[0], position[1] + sill, position[2]], 
                    axis, [135, 206, 250, 180]
                )
                meshes.append(glass)
                
                # Wall ABOVE window
                top = sill + o_height
                if top < wall_height:
                    above = GlbExporter._make_wall_segment(
                        o_width, wall_height - top, wall_thickness,
                        o_start, [position[0], position[1] + top, position[2]],
                        axis, wall_color
                    )
                    meshes.append(above)
                    
            elif o_type == 'door':
                o_height = opening.get('height', 210)
                
                # DOOR panel
                door = GlbExporter._make_wall_segment(
                    o_width, o_height, wall_thickness/2,
                    o_start, position, axis, [139, 90, 43, 220]
                )
                meshes.append(door)
                
                # Wall ABOVE door
                if o_height < wall_height:
                    above = GlbExporter._make_wall_segment(
                        o_width, wall_height - o_height, wall_thickness,
                        o_start, [position[0], position[1] + o_height, position[2]],
                        axis, wall_color
                    )
                    meshes.append(above)
            
            current_x = o_start + o_width
        
        # Wall segment AFTER last opening
        if current_x < wall_width:
            seg_w = wall_width - current_x
            seg = GlbExporter._make_wall_segment(
                seg_w, wall_height, wall_thickness,
                current_x, position, axis, wall_color
            )
            meshes.append(seg)
        
        # If no openings, create full wall
        if not openings:
            full = GlbExporter._make_wall_segment(
                wall_width, wall_height, wall_thickness,
                0, position, axis, wall_color
            )
            meshes.append(full)
        
        return meshes
    
    @staticmethod
    def _make_wall_segment(width, height, thickness, offset, position, axis, color):
        """Creates a single wall segment box."""
        if axis == 'x':  # Wall runs along X axis
            box = trimesh.creation.box(extents=[width, height, thickness])
            box.apply_translation([
                position[0] + offset + width/2,
                position[1] + height/2,
                position[2] + thickness/2
            ])
        else:  # axis == 'z', wall runs along Z axis
            box = trimesh.creation.box(extents=[thickness, height, width])
            box.apply_translation([
                position[0] + thickness/2,
                position[1] + height/2,
                position[2] + offset + width/2
            ])
        
        box.visual.face_colors = color
        return box
