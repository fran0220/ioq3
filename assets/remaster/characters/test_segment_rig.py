"""Run with Blender --python; synthetic math inputs are tests, never assets."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
from segment_rig import cut_triangle, globals_for, locals_for
from mathutils import Matrix, Vector


class SegmentTests(unittest.TestCase):
    def test_cut_preserves_area_and_tangent_contract(self):
        triangle = [{'position':p,'normal':[1,0,0],'tangent':[0,1,0,1],
                     'uv':uv,'influences':[[0,1]]}
                    for p,uv in [([2,-3,-1],[0,0]),([2,5,-1],[1,0]),([2,-3,7],[0,1])]]
        polygons = [cut_triangle(triangle,2,above) for above in (False,True)]
        areas = []
        for polygon in polygons:
            a = Vector(polygon[0]['position'])
            areas.append(sum((Vector(polygon[i]['position'])-a).cross(Vector(polygon[i+1]['position'])-a).length/2 for i in range(1,len(polygon)-1)))
            for v in polygon:
                self.assertAlmostEqual(Vector(v['normal']).dot(Vector(v['tangent'][:3])),0)
                self.assertAlmostEqual(sum(w for _,w in v['influences']),1)
        self.assertAlmostEqual(areas[0],19.5)
        self.assertAlmostEqual(areas[1],12.5)

    def test_relative_segment_roundtrip_nonidentity_parent(self):
        joints = [{'parent':-1},{'parent':0}]
        poses = [Matrix.Translation((2,-3,5)) @ Matrix.Rotation(.7,4,'Z'),
                 Matrix.Translation((9,4,2)) @ Matrix.Rotation(-.4,4,'X')]
        result = globals_for(joints,locals_for(joints,poses))
        for actual,expected in zip(result,poses):
            for i in range(4):
                for j in range(4):
                    self.assertAlmostEqual(actual[i][j],expected[i][j],places=5)


if __name__ == '__main__':
    unittest.main(argv=[__file__])
