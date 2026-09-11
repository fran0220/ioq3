import unittest

from build_scene import fit, rotated_bounds


class SceneFitTests(unittest.TestCase):
    def test_asymmetric_center_and_limiting_axis(self):
        origin, scale, bounds = fit([-1, -2, 0, 3, 4, 8], [[10, 20, 30], [30, 50, 70]], .8)
        self.assertEqual(origin, [16, 31, 34])
        self.assertEqual(scale, 4)
        self.assertEqual(bounds, [[12, 23, 34], [28, 47, 66]])

    def test_yaw_direction_and_off_center_pivot(self):
        for yaw, expected in [(90, [-4, -1, 0, 2, 3, 8]), (-90, [-2, -3, 0, 4, 1, 8])]:
            with self.subTest(yaw=yaw):
                actual = rotated_bounds([-1, -2, 0, 3, 4, 8], yaw)
                for value, wanted in zip(actual, expected):
                    self.assertAlmostEqual(value, wanted)

    def test_rotated_corner_not_only_min_max(self):
        from math import sqrt
        bounds = rotated_bounds([-2, -1, 0, 2, 1, 1], 45)
        self.assertAlmostEqual(bounds[0], -3 / sqrt(2))
        self.assertAlmostEqual(bounds[4], 3 / sqrt(2))

    def test_envelope_margin_and_degenerate_rejection(self):
        for margin in [0, 1, -1, 1.1]:
            with self.subTest(margin=margin), self.assertRaises(ValueError):
                fit([0, 0, 0, 1, 2, 3], [[0, 0, 0], [4, 5, 6]], margin)
        with self.assertRaises(ValueError):
            fit([0, 0, 0, 0, 2, 3], [[0, 0, 0], [4, 5, 6]], .9)
        with self.assertRaises(ValueError):
            fit([0, 0, 0, 1, 2, 3], [[0, 0, 0], [0, 5, 6]], .9)


if __name__ == '__main__':
    unittest.main()
