import unittest
from kitchen_core.geometry import Room, Slope

class TestGeometry(unittest.TestCase):
    def test_flat_room(self):
        room = Room(400, 300, 260, [], {})
        h = room.get_ceiling_height(100, 50)
        self.assertEqual(h, 260)
        
    def test_sloped_ceiling_left(self):
        # Slope starts at 120cm, 45 degrees, left wall
        # Height at x=0 should be 120.
        # Height at x=100 should be 120 + 100 * tan(45) = 220
        slope = Slope('left', 120, 45)
        room = Room(400, 300, 260, [slope], {})
        
        self.assertAlmostEqual(room.get_ceiling_height(0, 50), 120, delta=1)
        self.assertAlmostEqual(room.get_ceiling_height(100, 50), 220, delta=1)
        
        # Room max height
        self.assertEqual(room.get_ceiling_height(300, 50), 260)
        
    def test_valid_intervals(self):
        # Room: 400x300x260
        # Slope: Left, start 120, 45 deg.
        # At x=0, h=120. At x=100, h=220.
        # Fridge: 60x200.
        # Needs h >= 200.
        # 120 + x >= 200 => x >= 80.
        # So it should fit from x=80 to ...
        
        slope = Slope('left', 120, 45)
        room = Room(400, 300, 260, [slope], {})
        
        intervals = room.get_valid_x_intervals(item_width=60, item_height=200, item_depth=60)
        
        # Should start around 80.
        # Actually it checks 4 corners. 
        # (x, 0) and (x+60, 0)
        # For x=80:
        # Left edge (x=80) height = 200.
        # Right edge (x=140) height = 260.
        # So x=80 is valid.
        
        # What about x=79?
        # Left edge (x=79) height = 199 < 200. Invalid.
        
        self.assertTrue(len(intervals) > 0)
        self.assertEqual(intervals[0][0], 80)
        
    def test_impossible_height(self):
        # Giant fridge 300cm tall
        room = Room(400, 300, 260, [], {})
        intervals = room.get_valid_x_intervals(60, 300)
        self.assertEqual(len(intervals), 0)

if __name__ == '__main__':
    unittest.main()
