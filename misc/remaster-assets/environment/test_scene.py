import unittest

from build_scene import fit, rotated_bounds


class SceneFitTests(unittest.TestCase):
    def test_asymmetric_center_and_limiting_axis(self):
        origin, scale, bounds = fit([-1, -2, 0, 3, 4, 8], [[10, 20, 30], [30, 50, 70]], .8)
        self.assertEqual(origin, [16, 31, 34])
        self.assertEqual(scale, 4)
        self.assertEqual(bounds, [[12, 23, 34], [28, 47, 66]])

    def test_grounding_uses_decoded_minimum_not_assumed_zero_or_center(self):
        origin, scale, bounds = fit([-1, -2, -1, 3, 4, 7], [[10, 20, 30], [30, 50, 90]], .8, True)
        self.assertEqual(scale, 4)
        self.assertEqual(origin, [16, 31, 34])
        self.assertEqual(bounds, [[12, 23, 30], [28, 47, 62]])

    def test_closed_seams_and_missing_face_are_distinguished(self):
        from package_statue import topology
        points = [(0, 0, 0), (3, 0, 0), (0, 5, 0), (0, 0, 7)]
        faces = [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]
        surfaces = [{'positions': [points[i] for i in face], 'triangles': [(0, 1, 2)]} for face in faces]
        self.assertEqual(topology({'surfaces': surfaces})['boundary_edges'], 0)
        self.assertEqual(topology({'surfaces': surfaces[:-1]})['boundary_edges'], 3)
        self.assertEqual(topology({'surfaces': surfaces + surfaces[:1]})['nonmanifold_edges'], 3)

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

    def test_glow_preserves_opaque_and_expands_bounds(self):
        from lamp_glow import append_glow, SHADER
        from md3_static import read_md3, write_md3
        source = write_md3([[((0, 0, 0), (0, 0), (0, 1, 0)),
                             ((0, 0, 5), (0, 1), (0, 1, 0)),
                             ((3, 0, 0), (1, 0), (0, 1, 0))]], 'models/remaster/test')
        result, report = append_glow(source, False)
        model = read_md3(result)
        self.assertEqual(model['surfaces'][0], read_md3(source)['surfaces'][0])
        self.assertEqual(model['surfaces'][-1]['shader'], SHADER)
        self.assertEqual(model['bounds'], [-10, -4.078125, 0, 10, 0, 55])
        self.assertEqual(len(model['surfaces'][-1]['triangles']), 2)
        self.assertTrue(report['opaque_surface_bytes_identical'])
        for floor in [False, True]:
            derived, _ = append_glow(source, floor)
            surface = read_md3(derived)['surfaces'][-1]
            for a, b, c in surface['triangles']:
                p, q, r = [surface['positions'][i] for i in (a, b, c)]
                u = [q[i]-p[i] for i in range(3)]
                v = [r[i]-p[i] for i in range(3)]
                cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
                self.assertLess(sum(x*n for x, n in zip(cross, surface['normals'][a])), 0)


if __name__ == '__main__':
    unittest.main()
