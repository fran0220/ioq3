#!/usr/bin/env python3
"""Execute production scalar GLSL math as float C, not a copied implementation.

This tests arithmetic only; browser execution remains a separate requirement.
"""
import ctypes
import math
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class MaterialMath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        path = Path(cls.temp.name)
        shader = (ROOT / 'code/renderergl2/glsl/lightall_fp.glsl').read_text()
        function = re.search(r'vec3 CalcSpecular\([^}]+\}', shader).group()
        # The calculation is componentwise: a scalar exercises each RGB lane.
        function = function.replace('vec3', 'float')
        function = re.sub(r'(?<![\w.])(\d+\.\d+)(?![\w.])', r'\1f', function)
        parser = (ROOT / 'code/renderergl2/tr_shader.c').read_text()
        conversion = re.search(r'// two values, metallic then smoothness\n([^}]+)', parser).group(1)
        source = '''#include <math.h>
#define EPSILON 0.00000001f
#define CLAMP(x,a,b) fminf(fmaxf((x),(a)),(b))
#define clamp CLAMP
''' + function + '''
void convert(float *values) {
    struct { float specularScale[4]; } data, *stage = &data;
    stage->specularScale[0] = values[0];
    stage->specularScale[1] = values[1];
''' + conversion + '''
    values[0] = stage->specularScale[0];
    values[1] = stage->specularScale[1];
}
'''
        (path / 'math.c').write_text(source)
        subprocess.run(['cc', '-std=c99', '-O2', '-shared', '-fPIC', str(path / 'math.c'),
                        '-lm', '-o', str(path / 'math.so')], check=True)
        cls.lib = ctypes.CDLL(str(path / 'math.so'))
        cls.lib.CalcSpecular.argtypes = [ctypes.c_float] * 4
        cls.lib.CalcSpecular.restype = ctypes.c_float
        cls.lib.convert.argtypes = [ctypes.POINTER(ctypes.c_float)]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_smooth_lobe_is_finite_and_matches_analytic_center(self):
        # Old production formula yields NaN at r=0, NH=1, and cancellation
        # error at small nonzero r. Independent double-precision center limit.
        for roughness in (0, 0.001, 0.044, 0.045, 0.046, 0.2, 1):
            effective = max(0.045, roughness)
            expected = 0.04 / (4 * effective**4 * (effective + 0.5 + 1e-8))
            actual = self.lib.CalcSpecular(0.04, 1, 1, roughness)
            self.assertTrue(math.isfinite(actual))
            self.assertAlmostEqual(actual / expected, 1, places=5)

    def test_off_axis_and_grazing_are_finite(self):
        for roughness in (0, 0.045, 0.33, 1):
            for nh in (0, 0.42, 0.999999, 1):
                for eh in (0, 0.63, 1):
                    value = self.lib.CalcSpecular(0.21, nh, eh, roughness)
                    self.assertTrue(math.isfinite(value) and value >= 0)
        center = self.lib.CalcSpecular(0.04, 1, 1, 0.3)
        side = self.lib.CalcSpecular(0.04, 0.7, 1, 0.3)
        self.assertGreater(center, side)

    def test_metallic_is_continuous_and_not_swapped(self):
        for metallic, smoothness in ((0.25, 0.8), (0.49, 0.13), (0.51, 0.92), (1, 0), (0, 1)):
            values = (ctypes.c_float * 2)(metallic, smoothness)
            self.lib.convert(values)
            self.assertAlmostEqual(values[0], smoothness, places=6)
            self.assertAlmostEqual(values[1], metallic, places=6)
        values = (ctypes.c_float * 2)(-0.1, 1.2)
        self.lib.convert(values)
        self.assertEqual(list(values), [1, 0])


if __name__ == '__main__':
    unittest.main()
