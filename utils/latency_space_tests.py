'''
    Run this file from main folder: 
    python -m unittest utils.latency_space_tests
'''
import unittest
import math
from utils.latency_space import Point, Space, SpringForce, GradientEstimate

class TestLatencySpace(unittest.TestCase):
    def test_point_not_none(self):
        point = Point()
        self.assertIsNotNone(point)
    
    def test_point_init_with_list(self):
        l = [0, 1, 2]
        point = Point(l)
        self.assertIsNotNone(point)
        for i in range(len(l)):
            self.assertEqual(point.coordinates[i], l[i])
    
    def test_new_space(self):
        space = Space(2)
        self.assertIsNotNone(space)

    def test_space_new_point(self):
        space = Space(2)
        l = [0, 1]
        ref_point = Point(l)
        point = space.new_point(l)
        for i in range(len(l)):
            self.assertEqual(point.coordinates[i], ref_point.coordinates[i])

    def test_space_difference1(self):
        space = Space(2)
        a = space.new_point([0, 0])
        b = space.new_point([1, 1])
        c = space.difference(a, b)        
        self.assertEqual(c.coordinates, [-1, -1])

    def test_space_difference2(self):
        space = Space(2)
        a = space.new_point([0, 0])
        b = space.new_point([1, 1])
        c = space.difference(b, a)        
        self.assertEqual(c.coordinates, [1, 1])

    def test_space_norm_1(self):
        space = Space(2)
        a = space.new_point([0, 0])
        norm = space.norm(a)        
        self.assertEqual(norm, 0)

    def test_space_norm_2(self):
        space = Space(2)
        a = space.new_point([1, 1])
        norm = space.norm(a)        
        self.assertAlmostEqual(norm, math.sqrt(2.0))

    def test_space_multiply_1(self):
        space = Space(2)
        a = space.new_point([0, 0])
        a10 = space.multiply(10, a)        
        self.assertEqual(a10.coordinates, [0, 0])

    def test_space_multiply_2(self):
        space = Space(2)
        a = space.new_point([1, 1])
        a10 = space.multiply(10, a)        
        self.assertEqual(a10.coordinates, [10, 10])

    def test_space_distance_1(self):
        space = Space(2)
        a = space.new_point([0, 0])
        b = space.new_point([1, 0])
        dist = space.distance(a, b)        
        self.assertEqual(dist, 1)

    def test_space_distance_2(self):
        space = Space(2)
        a = space.new_point([0, 0])
        b = space.new_point([1, 1])
        dist = space.distance(a, b)        
        self.assertAlmostEqual(dist, math.sqrt(2))

    def test_spring_force_is_not_none(self):
        space = Space(2)
        a = space.new_point([0, 0])
        b = space.new_point([1, 0])
        force = SpringForce(space, a, b)
        self.assertIsNotNone(force)

    def test_spring_force_init_1(self):
        space = Space(2)
        a = space.new_point([0, 0])
        b = space.new_point([1, 0])
        force = SpringForce(space, a, b)
        self.assertEqual(force.versor, [1, 0])
        self.assertEqual(force.magnitude, 1)
        
    def test_spring_force_init_2(self):
        space = Space(2)
        a = space.new_point([1, 0])
        b = space.new_point([0, 0])
        force = SpringForce(space, a, b)
        self.assertEqual(force.versor, [-1, 0])
        self.assertEqual(force.magnitude, 1)

    def test_spring_force_init_3(self):
        space = Space(2)
        a = space.new_point([0, 1])
        b = space.new_point([1, 0])
        force = SpringForce(space, a, b)
        self.assertEqual(force.versor, [0.5, -0.5])
        self.assertAlmostEqual(force.magnitude, math.sqrt(2.0))

    def test_spring_force_init_4(self):
        space = Space(2)
        a = space.new_point([10, 0])
        b = space.new_point([0, 10])
        force = SpringForce(space, a, b)
        self.assertEqual(force.versor, [-0.5, 0.5])
        self.assertAlmostEqual(force.magnitude, 10 * math.sqrt(2.0))

    def test_spring_force_init_5(self):
        space = Space(2)
        a = space.new_point([0, 0])
        b = space.new_point([1, 0])
        force = SpringForce(space, a, b, 10)
        self.assertEqual(force.versor, [1, 0])
        self.assertEqual(force.magnitude, 10)

    def test_spring_force_multiply(self):
        space = Space(2)
        a = space.new_point([1, 0])
        b = space.new_point([0, 1])
        force = SpringForce(space, a, b)
        self.assertAlmostEqual(force.magnitude, math.sqrt(2.0))
        c = 10
        force.multiply(c)
        self.assertAlmostEqual(force.magnitude, c * math.sqrt(2.0))

    def test_spring_force_add(self):
        space = Space(2)
        a = space.new_point([1, 0])
        b = space.new_point([0, 0])
        c = space.new_point([0, 1])
        force1 = SpringForce(space, a, b)
        force2 = SpringForce(space, c, b)

        force1.add(force2)
        self.assertEqual(force1.versor, [-0.5, -0.5])
        self.assertAlmostEqual(force1.magnitude, math.sqrt(2.0))

    def test_spring_force_move_point_1(self):
        space = Space(2)
        a = space.new_point([0, 0])
        b = space.new_point([1, 0])
        force = SpringForce(space, a, b)

        c = force.move_point(a, 0.1)
        self.assertEqual(c.coordinates, [0.1, 0.0])

    def test_spring_force_move_point_2(self):
        space = Space(2)
        a = space.new_point([0, 1])
        b = space.new_point([0, 0])
        force = SpringForce(space, a, b)

        c = force.move_point(a, 0.1)
        self.assertEqual(c.coordinates, [0.0, 0.9])

    def test_spring_force_move_point_3(self):
        space = Space(2)
        a = space.new_point([0, 0])
        b = space.new_point([1, 0])
        c = space.new_point([-1, 0])
        force1 = SpringForce(space, a, b)
        force2 = SpringForce(space, a, c)

        force1.add(force2)
        d = force1.move_point(a, 0.1)
        self.assertEqual(d.coordinates, [0.0, 0.0])

    def test_spring_force_move_point_4(self):
        space = Space(2)
        a = space.new_point([0, 0])
        b = space.new_point([0, 1])
        c = space.new_point([1, 0])
        force1 = SpringForce(space, a, b)
        force2 = SpringForce(space, a, c)

        force1.add(force2)
        d = force1.move_point(a, 1.0)
        for i in range(len(d.coordinates)):
            self.assertAlmostEqual(d.coordinates[i], math.sqrt(2)/2)

    def test_gradient_est_add_1(self):
        space = Space(2)
        a = space.new_point([0, 0])
        b = space.new_point([0, 1])
        g = GradientEstimate(space)
        g.add(a, b, 1.0)
        self.assertEqual(g.gradient, [0.0, 1.0])

    def test_gradient_est_add_2(self):
        space = Space(2)
        a = space.new_point([0, -1])
        b = space.new_point([0, 1])
        g = GradientEstimate(space)
        g.add(a, b, 1.0)
        g.add(b, a, 1.0)
        self.assertEqual(g.gradient, [0.0, 0.0])

    def test_gradient_est_add_3(self):
        space = Space(2)
        a = space.new_point([0, 0])
        b = space.new_point([0, 1])
        c = space.new_point([1, 0])
        g = GradientEstimate(space)
        g.add(a, b, 1.0)
        g.add(a, c, 1.0)
        self.assertEqual(g.gradient, [1, 1])

    def test_gradient_est_move_point_1(self):
        space = Space(2)
        a = space.new_point([0, 0])
        b = space.new_point([0, 1])
        g = GradientEstimate(space)
        g.add(a, b, 1.0)
        self.assertEqual(g.gradient, [0.0, 1.0])
        c = g.new_point_position(a, 10.0)
        self.assertEqual(c.coordinates, [0, 10.0])

if __name__ == '__main__':
    unittest.main()
