"""Actual Blender skinning versus independently decoded exported IQM."""
import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

from iqm_validate import matrices, read_iqm, skin_positions

HERE=Path(__file__).resolve().parent


@unittest.skipUnless(os.environ.get('RUN_BLENDER_TESTS')=='1','set RUN_BLENDER_TESTS=1')
class BlenderIQMTests(unittest.TestCase):
    def test_real_rig_multiframe_skinning_materials_uv_and_attachments(self):
        with tempfile.TemporaryDirectory(prefix='ioq3-iqm-test-') as directory:
            root=Path(directory)
            for script,args in [('blender_iqm_fixture.py',[str(root)]),
                                ('blender_iqm.py',[str(root/'fixture.blend'),str(root/'config.json'),str(root/'out')])]:
                result=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2',
                                       '--python-exit-code','1','--python',str(HERE/script),'--',*args],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-10000:])
            source=json.loads((root/'out/source.json').read_text())
            reference=json.loads((root/'blender-reference.json').read_text())
            contract=json.loads((root/'out/animation-contract.json').read_text())
            decoded=read_iqm((root/'out/model.iqm').read_bytes())
            self.assertEqual(len(decoded['frames']),5)
            self.assertEqual([c['first_frame'] for c in decoded['clips']],[0,3])
            self.assertEqual([m['material'] for m in decoded['meshes']],['models/remaster/iqm_test_cyan','models/remaster/iqm_test_orange'])
            self.assertEqual(contract['attachments'],['tag_weapon'])
            self.assertEqual(contract['clip_bindings'][0]['events'],[{'frame':1,'name':'test_event'}])
            self.assertTrue(contract['cgame_binding_required']); self.assertFalse(contract['runtime_accepted'])
            original_indices=[v['source_vertex'] for m in source['meshes'] for v in m['vertices']]
            self.assertEqual(len(original_indices),len(decoded['arrays'][0]))
            for frame, expected in enumerate(reference):
                for actual, index in zip(skin_positions(decoded,frame),original_indices):
                    for a,b in zip(actual,expected['positions'][index]):
                        self.assertAlmostEqual(a,b,delta=.003)
                tag=matrices(decoded['joints'],decoded['frames'][frame])[2]
                for r in range(3):
                    self.assertAlmostEqual(tag[r][3],expected['tag_origin'][r],delta=.003)
                    for c in range(3): self.assertAlmostEqual(tag[r][c],expected['tag_axis'][r][c],delta=.0001)
            # Source UV fixture starts (0,0); Q3 V is flipped, sign flips too.
            self.assertEqual(decoded['arrays'][1][0],(0,1))
            self.assertNotEqual(reference[0]['positions'][6],reference[2]['positions'][6])
            # Compile actual production ComputePoseMats / R_IQMLerpTag, not a
            # Python rewrite. This is not the full loader or a GL draw test.
            cflags=shlex.split(subprocess.check_output(['sdl2-config','--cflags'],text=True))
            compile_result=subprocess.run(['cc','-g','-O1','-ffunction-sections','-fdata-sections',*cflags,
                                           str(HERE/'iqm_pose_probe.c'),str(HERE.parents[1]/'code/qcommon/q_math.c'),
                                           '-Wl,--gc-sections','-lm','-o',str(root/'probe')],capture_output=True,text=True)
            self.assertEqual(compile_result.returncode,0,compile_result.stderr)
            output=subprocess.check_output([str(root/'probe'),str(root/'out/model.iqm')],text=True)
            engine=[json.loads(line) for line in output.splitlines()]
            for frame, expected in enumerate(reference):
                for actual,index in zip(engine[frame]['positions'],original_indices):
                    for a,b in zip(actual,expected['positions'][index]): self.assertAlmostEqual(a,b,delta=.003)
                for a,b in zip(engine[frame]['tag'],expected['tag_origin']): self.assertAlmostEqual(a,b,delta=.003)
            # Quarter of root translation .6m and 60-degree X rotation at
            # a 1.5m child socket: different from reversed 75% interpolation.
            for actual,expected in zip(engine[-1]['tag'],[6,60*math.cos(math.pi/12),40+60*math.sin(math.pi/12)]):
                self.assertAlmostEqual(actual,expected,delta=.003)


if __name__ == '__main__':
    unittest.main()
