import math
import struct
import unittest

from md3_static import normal_word, read_md3, write_md3


def vertex(position, uv=(0.25, 0.75), normal=(0, 0, 1)):
    return position, uv, normal


class StaticMD3Tests(unittest.TestCase):
    def setUp(self):
        self.triangle = [vertex((-3.25, 2, 0)), vertex((5, 1, 0)), vertex((0, 4.5, 8))]

    def test_binary_offsets_quantization_and_uv_without_reader_oracle(self):
        data = write_md3([self.triangle], "models/remaster/test")
        self.assertEqual(data[:8], b"IDP3\x0f\0\0\0")
        # qfiles.h: header108 + frame56; surface108 + tri12 + shader68 + uv24 + xyz24
        self.assertEqual(len(data), 400)
        self.assertEqual(struct.unpack_from("<9i", data, 72), (0, 1, 0, 1, 0, 108, 164, 164, 400))
        self.assertEqual(struct.unpack_from("<6f", data, 108), (-3.25, 1, 0, 5, 4.5, 8))
        self.assertEqual(struct.unpack_from("<3hH", data, 376), (-208, 128, 0, 0))
        self.assertEqual(struct.unpack_from("<2f", data, 352), (0.25, 0.75))
        self.assertEqual(struct.unpack_from("<3i", data, 272), (0, 1, 2))

    def test_normals_use_engine_256_step_table(self):
        self.assertEqual(normal_word((0, 0, 1)), 0)
        self.assertEqual(normal_word((0, 0, -1)), 128)
        self.assertEqual(normal_word((1, 0, 0)), 64)
        self.assertEqual(normal_word((0, 1, 0)), 64 << 8 | 64)
        decoded = read_md3(write_md3([self.triangle], "a"))
        self.assertEqual(decoded["surfaces"][0]["normals"][0], (0, 0, 1))

    def test_signed_short_boundary_and_nonfinite_fail(self):
        triangle = [vertex((-512, 0, 0)), vertex((32767/64, 0, 0)), vertex((0, 2, 0))]
        read_md3(write_md3([triangle], "a"))
        for value in [-512.001, 512, math.inf, math.nan]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                write_md3([[vertex((value, 0, 0)), *triangle[1:]]], "a")

    def test_uv_seams_split_vertices(self):
        other = [vertex(self.triangle[0][0], (0.9, 0.1)), *self.triangle[1:]]
        surface = read_md3(write_md3([self.triangle, other], "a"))["surfaces"][0]
        self.assertEqual(len(surface["positions"]), 4)
        self.assertEqual(surface["triangles"], [(0, 1, 2), (3, 1, 2)])

    def test_surface_split_preserves_all_triangles(self):
        # Each triangle has distinct UVs, forcing >4096 vertices even with shared XYZ.
        triangles = [[vertex(v[0], (index/1500, corner/3)) for corner, v in enumerate(self.triangle)] for index in range(1400)]
        surfaces = read_md3(write_md3(triangles, "a"))["surfaces"]
        self.assertEqual(len(surfaces), 2)
        self.assertEqual(sum(len(s["triangles"]) for s in surfaces), 1400)
        self.assertTrue(all(len(s["positions"]) <= 4096 for s in surfaces))

    def test_quantization_collapsed_face_and_corrupt_index_rejected(self):
        with self.assertRaisesRegex(ValueError, "collapses"):
            write_md3([[vertex((0, 0, 0)), vertex((0.001, 0, 0)), vertex((0, 0.001, 0))]], "a")
        bad = bytearray(write_md3([self.triangle], "a"))
        struct.pack_into("<i", bad, 272, 3)
        with self.assertRaisesRegex(ValueError, "index"):
            read_md3(bad)


if __name__ == "__main__":
    unittest.main()
