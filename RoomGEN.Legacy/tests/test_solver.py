import unittest
from kitchen_core.geometry import Room, Slope
from kitchen_core.solver import KitchenSolver

class TestSolver(unittest.TestCase):
    def test_simple_layout(self):
        # Room 400x300x260, water at 100
        room = Room(400, 300, 260, [], {'water_x': 100})
        solver = KitchenSolver(room)
        
        wishlist = [
            {'type': 'sink_cabinet', 'width': 60},
            {'type': 'dishwasher', 'width': 60}
        ]
        
        # Result: {0: x1, 1: x2}
        result = solver.solve(wishlist)
        self.assertIsNotNone(result)
        
        sink_x = result[0]
        # sink center = sink_x + 30.
        # dist to water(100) <= 50 -> |sink_x + 30 - 100| <= 50 -> |sink_x - 70| <= 50.
        # sink_x in [20, 120]
        self.assertTrue(20 <= sink_x <= 120)
        
        dw_x = result[1]
        # Adjacent: dw_x + 60 == sink_x OR sink_x + 60 == dw_x
        self.assertTrue(dw_x + 60 == sink_x or sink_x + 60 == dw_x)

    def test_fridge_stove_distance(self):
        # Room 400
        room = Room(400, 300, 260, [], {})
        solver = KitchenSolver(room)
        
        wishlist = [
            {'type': 'fridge', 'width': 60, 'height': 200},
            {'type': 'stove_cabinet', 'width': 60}
        ]
        
        result = solver.solve(wishlist)
        self.assertIsNotNone(result)
        
        fx = result[0]
        sx = result[1]
        
        # distance >= 60
        # |fx - sx| >= 60? No, intervals: 
        # fx..fx+60 and sx..sx+60
        # dist(interval_f, interval_s) >= 60
        # if sx > fx: sx - (fx+60) >= 60 -> sx - fx >= 120
        # if fx > sx: fx - (sx+60) >= 60 -> fx - sx >= 120
        
        dist = abs(fx - sx)
        self.assertTrue(dist >= 120)

    def test_height_constraint_fail(self):
        # Slope very low. Fridge 200cm.
        # Slope starts at 0, angle 0 => height 0 (impossible room)
        slope = Slope('left', 50, 0) # height 50 everywhere
        room = Room(400, 300, 260, [slope], {})
        
        # Fridge needs 200
        wishlist = [{'type': 'fridge', 'width': 60, 'height': 200}]
        
        solver = KitchenSolver(room)
        result = solver.solve(wishlist)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
