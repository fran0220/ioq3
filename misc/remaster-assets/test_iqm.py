"""Independent numeric expectations and corrupt-byte tests; TEST ONLY geometry."""
import copy
import math
import struct
import unittest

from iqm_export import packed_weights, write_iqm
from iqm_validate import matrices, read_iqm, skin_positions


def pose(t, q=(0,0,0,1)):
    return {'translate': list(t), 'rotate': list(q), 'scale': [1,1,1]}


def fixture():
    joints = [dict(name='root', parent=-1, **pose((2,-3,1))),
              dict(name='arm', parent=0, **pose((4,0,2))),
              dict(name='tag_weapon', parent=1, **pose((0,3,1)))]
    half = math.sqrt(0.5)
    frames = [[pose((2,-3,1)), pose((4,0,2)), pose((0,3,1))],
              [pose((5,-1,2),(0,0,half,half)), pose((4,0,2),(half,0,0,half)), pose((0,3,1))]]
    def vertex(p, weights):
        return {'position': p, 'normal': [0,0,1], 'tangent': [1,0,0,1], 'uv': [p[0]/10,p[1]/10], 'influences': weights}
    mesh = {'name': 'asymmetric', 'material': 'models/remaster/test_iqm', 'vertices': [
        vertex([7,-3,3], [[1,1]]), vertex([6,-1,3], [[0,.2],[1,.8]]), vertex([6,-3,6], [[1,1]])], 'triangles': [[0,1,2]]}
    return {'schema_version': 1, 'coordinate_system': 'q3-x-forward-y-left-z-up', 'joints': joints, 'meshes': [mesh],
            'clips': [{'name': 'attack', 'fps': 20., 'loop': False, 'frames': frames},
                      {'name': 'idle', 'fps': 12., 'loop': True, 'frames': [frames[0]]}], 'attachments': ['tag_weapon']}


class IQMTests(unittest.TestCase):
    def test_byte_contract_skinning_and_attachment_use_independent_expected_values(self):
        d = write_iqm(fixture()); h = struct.unpack_from('<27I', d, 16)
        self.assertEqual(d[:20], b'INTERQUAKEMODEL\0\x02\0\0\0')
        self.assertEqual((h[13],h[15],h[17],h[19]), (3,3,2,3))
        # Header/array descriptors inspected directly, independent of read_iqm.
        arrays = [struct.unpack_from('<5I',d,h[9]+i*20) for i in range(6)]
        self.assertEqual([(a[0],a[2],a[3]) for a in arrays], [(0,7,3),(1,7,2),(2,7,3),(3,7,4),(4,1,4),(5,1,4)])
        self.assertEqual(tuple(d[arrays[5][4]+4:arrays[5][4]+8]), (204,51,0,0))
        m = read_iqm(d)
        self.assertEqual(m['clips'], [{'name':'attack','first_frame':0,'num_frames':2,'fps':20.,'loop':False},
                                      {'name':'idle','first_frame':2,'num_frames':1,'fps':12.,'loop':True}])
        for actual, expected in zip(skin_positions(m,0), ([7,-3,3],[6,-1,3],[6,-3,6])):
            for a,b in zip(actual, expected): self.assertAlmostEqual(a,b,places=4)
        # Explicit root-Z90 + child-X90: arm-bound point goes to (5,4,4).
        for a,b in zip(skin_positions(m,1)[0], [5,4,4]): self.assertAlmostEqual(a,b,places=4)
        tag = matrices(m['joints'],m['frames'][1])[2]
        for a,b in zip([tag[i][3] for i in range(3)], [6,3,7]): self.assertAlmostEqual(a,b,places=4)
        self.assertEqual(m['meshes'][0]['material'], 'models/remaster/test_iqm')
        self.assertEqual(write_iqm(fixture()), d)

    def test_frame_quantization_and_quaternion_sign_continuity(self):
        f = fixture(); frame = copy.deepcopy(f['clips'][0]['frames'][0]); frame[0]['translate'][0] = 2.713
        frame[1]['rotate'] = [0,0,0,-1]
        f['clips'][0]['frames'].insert(1, frame)
        model = read_iqm(write_iqm(f))
        self.assertLess(abs(model['frames'][1][0]['translate'][0]-2.713), 3/65535)
        self.assertGreater(model['frames'][1][1]['rotate'][3], 0)
        for frame in range(4):
            for pos in skin_positions(model, frame):
                self.assertTrue(all(model['bounds'][frame][i] <= pos[i] <= model['bounds'][frame][i+3] for i in range(3)))

    def test_exact_vertex_and_index_runtime_boundaries_split(self):
        f = fixture(); mesh = f['meshes'][0]
        mesh['vertices'] = [copy.deepcopy(v) for _ in range(333) for v in mesh['vertices']]
        mesh['triangles'] = [[i,i+1,i+2] for i in range(0,999,3)]
        self.assertEqual(read_iqm(write_iqm(f))['meshes'][0]['vertices'],999)
        mesh['vertices'].append(copy.deepcopy(mesh['vertices'][0])); mesh['triangles'].append([999,1,2])
        self.assertEqual([m['vertices'] for m in read_iqm(write_iqm(f))['meshes']],[999,3])
        f = fixture(); f['meshes'][0]['triangles'] *= 1999
        self.assertEqual(len(read_iqm(write_iqm(f))['meshes']),1)
        f['meshes'][0]['triangles'].append([0,1,2])
        self.assertEqual([m['triangles'] for m in read_iqm(write_iqm(f))['meshes']], [1999,1])

    def test_128_joints_fit_129_rejected_without_dropping_attachment_bones(self):
        f=fixture()
        for clip in f['clips']:
            clip['frames'] = [copy.deepcopy(frame) for frame in clip['frames']]
        for i in range(3,128):
            f['joints'].append(dict(name='socket'+str(i),parent=0,**pose((0,0,0))))
            for clip in f['clips']:
                for frame in clip['frames']:
                    frame.append(pose((0,0,0)))
        f['attachments'].append('socket127')
        self.assertEqual(len(read_iqm(write_iqm(f))['joints']),128)
        f['joints'].append(dict(name='socket128',parent=0,**pose((0,0,0))))
        with self.assertRaisesRegex(ValueError,'128'): write_iqm(f)

    def test_invalid_rig_influence_scale_and_missing_attachment_fail(self):
        self.assertEqual(packed_weights([[0,.2],[1,.8]],2), ([1,0,0,0],[204,51,0,0]))
        for influences in ([], [[0,0]], [[0,-1]], [[2,1]], [[i,.2] for i in range(5)]):
            with self.assertRaises(ValueError): packed_weights(influences, 5 if len(influences)==5 else 2)
        for change in (lambda f: f['joints'][0].update(parent=1),
                       lambda f: f['joints'][1].update(scale=[2,1,1]),
                       lambda f: f.update(attachments=['TAG_WEAPON'])):
            f=fixture(); change(f)
            with self.assertRaises(ValueError): write_iqm(f)

    def test_corrupt_binary_rejected_not_merely_successful_roundtrip(self):
        d = write_iqm(fixture()); h = struct.unpack_from('<27I',d,16)
        arrays = [struct.unpack_from('<5I',d,h[9]+i*20) for i in range(6)]
        for offset, fmt, value in [(h[11],'<I',h[8]), (h[14]+4,'<i',1),
                                    (h[16]+4,'<I',1024), (h[9]+3*20,'<I',2),
                                    (arrays[4][4]+3,'<B',128), (arrays[5][4],'<B',0),
                                    (h[6]+12,'<I',1000), (h[18]+8,'<I',99),
                                    (16+20*4,'<I',h[20]+1)]:
            with self.subTest(offset=offset):
                bad=bytearray(d); struct.pack_into(fmt,bad,offset,value)
                with self.assertRaises(ValueError): read_iqm(bad)


if __name__ == '__main__':
    unittest.main()
