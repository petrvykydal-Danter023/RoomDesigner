import trimesh
import numpy as np
import os
from pathlib import Path
from core.schema import CabinetItem

class HybridExporter:
    """
    Renders CabinetItems using a hybrid approach (Y-Up System).
    """
    
    def __init__(self):
        self.scene = trimesh.Scene()
        self.asset_cache = {}
        self.assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

    def load_asset(self, asset_id: str):
        if asset_id not in self.asset_cache:
            path = os.path.join(self.assets_dir, asset_id)
            if not path.endswith(".glb"):
                path += ".glb"
                
            if os.path.exists(path):
                try:
                    loaded = trimesh.load(path)
                    if isinstance(loaded, trimesh.Scene):
                        geoms = list(loaded.geometry.values())
                        if geoms:
                            self.asset_cache[asset_id] = geoms
                        else:
                            self.asset_cache[asset_id] = None
                    else:
                        self.asset_cache[asset_id] = [loaded]
                except Exception as e:
                    print(f"Failed to load asset {asset_id}: {e}")
                    self.asset_cache[asset_id] = None
            else:
                box = trimesh.creation.box(extents=[5, 5, 5])
                box.visual.face_colors = [255, 0, 0, 255]
                self.asset_cache[asset_id] = [box]
                
        return self.asset_cache[asset_id]

    def add_cabinet(self, cabinet: CabinetItem):
        # Global transformation for the cabinet
        # T_global: [x, y, z] -> [x, UP, z] ? 
        # CabinetFactory `global_pos` is [X, Y, Z] where Y is height.
        # So Translation is direct.
        T_global = trimesh.transformations.translation_matrix(cabinet.position)
        
        # Rotation around Y axis (Up)
        R_global = trimesh.transformations.rotation_matrix(np.radians(cabinet.rotation), [0, 1, 0])
        
        base_matrix = trimesh.transformations.concatenate_matrices(T_global, R_global)

        for comp in cabinet.components:
            meshes_to_add = []
            
            if comp.asset_id:
                assets = self.load_asset(comp.asset_id)
                if assets:
                    for a in assets:
                        meshes_to_add.append(a.copy())
            else:
                # Procedural Box
                # dims=[w, h, d] -> X, Y, Z
                mesh = trimesh.creation.box(extents=comp.dims)
                if comp.color:
                    mesh.visual.face_colors = comp.color
                meshes_to_add.append(mesh)

            # Local Transform
            T_local = trimesh.transformations.translation_matrix(comp.pos)
            
            R_local = np.eye(4)
            if comp.rotation:
                rx = trimesh.transformations.rotation_matrix(np.radians(comp.rotation[0]), [1, 0, 0])
                ry = trimesh.transformations.rotation_matrix(np.radians(comp.rotation[1]), [0, 1, 0])
                rz = trimesh.transformations.rotation_matrix(np.radians(comp.rotation[2]), [0, 0, 1])
                R_local = trimesh.transformations.concatenate_matrices(rx, ry, rz)
            
            final_comp_matrix = trimesh.transformations.concatenate_matrices(base_matrix, T_local, R_local)
            
            for m in meshes_to_add:
                self.scene.add_geometry(m, transform=final_comp_matrix)

    def export(self, filename: str):
        self.scene.export(filename)
        return True
