import os
from typing import List, Dict, Any
from core.materials import get_material_for_item

class ObjExporter:
    @staticmethod
    def export(items: List[Dict[str, Any]], output_path: str):
        """
        Exports layout items to .obj and .mtl files.
        Generates simple box geometry for each item with vertex colors.
        """
        base_name = os.path.splitext(os.path.basename(output_path))[0]
        mtl_filename = f"{base_name}.mtl"
        obj_lines = []
        mtl_lines = []
        
        obj_lines.append(f"mtllib {mtl_filename}")
        obj_lines.append("")
        
        # 1. Generate Materials FIRST
        used_materials = {}
        for item in items:
            mat_info = get_material_for_item(item['type'])
            mat_name = mat_info['name']
            if mat_name not in used_materials:
                used_materials[mat_name] = mat_info['color']
                color = mat_info['color']
                mtl_lines.append(f"newmtl {mat_name}")
                mtl_lines.append(f"Ka {color[0]:.3f} {color[1]:.3f} {color[2]:.3f}")
                mtl_lines.append(f"Kd {color[0]:.3f} {color[1]:.3f} {color[2]:.3f}")
                mtl_lines.append(f"Ks 0.1 0.1 0.1")
                mtl_lines.append(f"Ns 100")
                mtl_lines.append(f"d 1.0")
                mtl_lines.append("")
        
        # 2. Generate Geometry - Each item as separate object
        vertex_offset = 1
        for idx, item in enumerate(items):
            x = item.get('x_local', 0) 
            w = item.get('width', 60)
            d = 60 # Depth
            h = 90 # Height for base
            
            # Upper cabinets are higher up and shallower
            if 'upper' in item['type'] or 'hood' in item['type'] or 'bridge' in item['type']:
                h = 70
                y_offset = 150 # Height from floor
                d = 35
            else:
                y_offset = 0 # Base cabinet on floor
            
            # Box vertices
            x_min, x_max = x, x + w
            y_min, y_max = 0, d
            z_min, z_max = y_offset, y_offset + h
            
            # Object name and material
            mat_name = get_material_for_item(item['type'])['name']
            obj_lines.append(f"o {item['type']}_{idx}")
            obj_lines.append(f"usemtl {mat_name}")
            
            # 8 Vertices (OBJ uses Y-up, so swap Y/Z)
            verts = [
                (x_min, z_min, -y_min), (x_max, z_min, -y_min), 
                (x_max, z_min, -y_max), (x_min, z_min, -y_max),
                (x_min, z_max, -y_min), (x_max, z_max, -y_min), 
                (x_max, z_max, -y_max), (x_min, z_max, -y_max)
            ]
            
            for v in verts:
                obj_lines.append(f"v {v[0]} {v[1]} {v[2]}")
            
            # Faces (quads) - using relative indices
            # Front, Back, Left, Right, Top, Bottom
            v = vertex_offset
            faces = [
                (v+0, v+1, v+2, v+3),  # Bottom
                (v+4, v+7, v+6, v+5),  # Top
                (v+0, v+4, v+5, v+1),  # Front
                (v+2, v+6, v+7, v+3),  # Back
                (v+1, v+5, v+6, v+2),  # Right
                (v+0, v+3, v+7, v+4),  # Left
            ]
            
            for f in faces:
                obj_lines.append(f"f {f[0]} {f[1]} {f[2]} {f[3]}")
                
            obj_lines.append("")
            vertex_offset += 8
            
        # Write OBJ
        with open(output_path, 'w') as f:
            f.write("\n".join(obj_lines))
            
        # Write MTL
        mtl_path = os.path.join(os.path.dirname(output_path), mtl_filename)
        with open(mtl_path, 'w') as f:
            f.write("\n".join(mtl_lines))
            
        return True
