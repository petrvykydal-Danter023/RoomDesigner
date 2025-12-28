import unittest
import os
from kitchen_core.generator import OBJGenerator
from kitchen_core.geometry import Room

class TestGenerator(unittest.TestCase):
    def test_obj_creation(self):
        gen = OBJGenerator()
        gen.add_box(0, 0, 0, 10, 10, 10)
        
        filename = "test_output.obj"
        gen.save(filename)
        
        self.assertTrue(os.path.exists(filename))
        with open(filename, 'r') as f:
            content = f.read()
            self.assertIn("v 0.0000 0.0000 0.0000", content)
            self.assertIn("f", content)
            
        os.remove(filename)

    def test_worktop_holes(self):
        gen = OBJGenerator()
        # Worktop 0 to 200. Hole at 50, width 60.
        gen.generate_worktop(0, 200, 85, 60, holes=[(50, 60)])
        
        # We expect multiple boxes
        # 0-50: Box
        # 50-110: Rails
        # 110-200: Box
        
        # Check if vertices created
        self.assertTrue(len(gen.vertices) > 8)

if __name__ == '__main__':
    unittest.main()
