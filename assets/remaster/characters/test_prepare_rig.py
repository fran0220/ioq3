"""Blender test: restore split geometry without merging face-corner UVs."""
from pathlib import Path
import sys
import unittest

import bpy

sys.path.insert(0,str(Path(__file__).resolve().parent))
from prepare_rig import weld_uv_seams


class PrepareRigTests(unittest.TestCase):
    def test_geometry_weld_preserves_uv_islands_and_deform_weights(self):
        mesh = bpy.data.meshes.new('split-uv-test')
        mesh.from_pydata([(0,0,0),(2,0,0),(0,3,0),
                          (2,0,0),(2,3,0),(0,3,0)],[],[(0,1,2),(3,4,5)])
        obj = bpy.data.objects.new('split-uv-test',mesh)
        bpy.context.collection.objects.link(obj)
        group = obj.vertex_groups.new(name='ForeArm')
        group.add(list(range(6)),.375,'REPLACE')
        uv = mesh.uv_layers.new(name='UV')
        expected = [(0,0),(.2,0),(0,.3),(.8,.7),(1,1),(.7,1)]
        for corner,value in zip(uv.data,expected):
            corner.uv = value
        report = weld_uv_seams(mesh)
        self.assertEqual(report['vertices_after'],4)
        self.assertEqual(report['boundary_edges'],4)
        self.assertEqual(len(mesh.polygons),2)
        for actual,want in zip(mesh.uv_layers['UV'].data,expected):
            self.assertAlmostEqual(actual.uv.x,want[0],places=6)
            self.assertAlmostEqual(actual.uv.y,want[1],places=6)
        for vertex in mesh.vertices:
            self.assertAlmostEqual(group.weight(vertex.index),.375)
        bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.meshes.remove(mesh)


if __name__ == '__main__':
    unittest.main(argv=[__file__])
