"""Synthetic fixtures only: no commercial assets in tests or repository."""
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import wave
import zipfile

from inventory import coverage, dependencies, inspect, scan, sha, tokens
from md3_static import write_md3


def bsp():
    lumps = [b''] * 17
    lumps[0] = b'{"classname" "worldspawn" "message" ""}\n{"classname" "misc_model" "model" "models/test.md3" "origin" "8 -16 40"}\0'
    lumps[1] = struct.pack('<64s2i', b'textures/test', 0, 0)
    lumps[7] = struct.pack('<6f4i', -80, -12, 4, 160, 60, 100, 0, 0, 0, 0)
    offset, header = 144, b'IBSP' + struct.pack('<i', 46)
    for lump in lumps:
        header += struct.pack('<2i', offset, len(lump)); offset += len(lump)
    return header + b''.join(lumps)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        triangle = [((0, 0, 0), (0, 0), (0, 0, 1)), ((2, 0, 0), (1, 0), (0, 0, 1)), ((0, 3, 0), (0, 1), (0, 0, 1))]
        self.files = {'maps/test.bsp': bsp(), 'maps/test.aas': b'EAAS' + struct.pack('<i', 5),
                      'models/test.md3': write_md3([triangle], 'textures/test'),
                      'scripts/test.shader': b'textures/test { { map textures/test.tga } { map $lightmap } }',
                      'textures/test.tga': b'TEST ONLY texture bytes'}

    def archive(self, name, files):
        path = self.base / name
        with zipfile.ZipFile(path, 'w') as z:
            for name, data in files.items():
                z.writestr(name, data)
        return {'path': path.name, 'sha256': sha(path.read_bytes()), 'provenance': 'TEST ONLY synthetic'}

    def scan(self, *archives):
        return scan({'scope': 'demo', 'authorization': 'fixture', 'archives': list(archives)}, self.base)

    def test_map_model_shader_texture_closure_and_asymmetric_bounds(self):
        inv = self.scan(self.archive('a.pk3', self.files))
        self.assertEqual(inv['warnings'], [])
        meta = next(f['metadata'] for f in inv['files'] if f['path'].endswith('.bsp'))
        self.assertEqual(meta['model_bounds'][0]['size_q3'], [240, 72, 96])
        self.assertEqual(meta['entities'][0]['message'], '')
        self.assertEqual(meta['entities'][1]['origin'], '8 -16 40')
        graph = dependencies(inv, ['maps/test.bsp'])
        self.assertEqual(set(graph['nodes']), set(self.files) | {'shader:textures/test'})
        self.assertEqual(graph['unresolved'], [])

    def test_vfs_override_and_missing_are_not_full_coverage(self):
        first = self.archive('a.pk3', self.files)
        second = self.archive('z.pk3', {'textures/test.tga': b'replacement'})
        inv = self.scan(first, second)
        texture = next(f for f in inv['files'] if f['path'] == 'textures/test.tga')
        self.assertEqual(texture['sha256'], sha(b'replacement'))
        self.assertEqual(len(texture['versions']), 2)
        mapping = {'inventory_sha256': sha(json.dumps(inv, sort_keys=True).encode()), 'replacements': []}
        result = coverage(inv, mapping)
        self.assertFalse(result['full_game_complete'])
        self.assertEqual(result['accepted_files'], 0)
        mapping['replacements'] = [{'source_path': texture['path'], 'source_sha256': texture['sha256'], 'asset_id': 'new',
                                    'gates': {'visual': {'passed': True}}}]
        self.assertIn('visual', coverage(inv, mapping)['replacements'][texture['path']]['missing_gates'])
        mapping['inventory_sha256'] = 'wrong'
        with self.assertRaises(ValueError): coverage(inv, mapping)

    def test_material_extension_shader_lookup_does_not_capture_sound(self):
        files = dict(self.files)
        files['models/test.skin'] = b'body,textures/test.tga\n'
        files['scripts/test.shader'] += b' sound/miss1 { { map textures/test.tga } }'
        files['sound/miss1.tga'] = b'not sound'
        # Replace the model entity reference with a missing sound with same stem
        # as both a shader and an image; neither is a valid WAV dependency.
        files['maps/test.bsp'] = bsp().replace(b'"model" "models/test.md3"', b'"noise" "sound/miss1.wav"')
        # Keep the BSP byte layout intact using equal-length replacement above.
        self.assertEqual(len(files['maps/test.bsp']), len(bsp()))
        inv = self.scan(self.archive('a.pk3', files))
        skin = next(e for e in inv['dependencies'] if e['from'] == 'models/test.skin')
        self.assertEqual(skin['targets'], ['shader:textures/test'])
        noise = next(e for e in inv['dependencies'] if e['reason'] == 'entity-noise')
        self.assertEqual(noise['status'], 'missing')

    def test_bad_hash_zip_paths_case_collision_and_corrupt_bsp(self):
        source = self.archive('a.pk3', self.files); source['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'): self.scan(source)
        for files in ({'../evil': b'x'}, {'X.TGA': b'x', 'x.tga': b'y'}):
            with self.assertRaises(ValueError): self.scan(self.archive('bad.pk3', files))
        inv = self.scan(self.archive('bad.pk3', {'maps/bad.bsp': bsp()[:150]}))
        self.assertEqual(len(inv['warnings']), 1)

    def test_shader_animation_sky_missing_and_duplicate_definitions(self):
        script = b'textures/test { skyparms env/sky 512 - { animMap 2 textures/a.tga textures/b.jpg rgbGen identity } }'
        inv = self.scan(self.archive('a.pk3', {'scripts/a.shader': script, 'scripts/b.shader': script,
                                              'textures/a.jpg': b'test', 'textures/b.jpg': b'test'}))
        self.assertTrue(inv['warnings'])
        refs = inv['dependencies']
        self.assertEqual(sum(e['reason'] == 'sky' for e in refs), 12)
        self.assertTrue(all(e['status'] == 'resolved' for e in refs if e['reason'] == 'animmap'))
        self.assertTrue(any(e['status'] == 'ambiguous' for e in refs))
        self.assertEqual(tokens('"http://test" /* ignored */ "" // ignored\n{}'), ['http://test', '', '{', '}'])

    def test_tag_only_md3_and_iqm_animation_header(self):
        header = struct.pack('<4si64s9i', b'IDP3', 15, b'fixture', 0, 1, 1, 0, 0, 108, 164, 276, 276)
        tag = struct.pack('<64s12f', b'tag_weapon', *([0.] * 12))
        meta, _ = inspect('models/hand.md3', header + bytes(56) + tag)
        self.assertEqual(meta['tags'], ['tag_weapon']); self.assertEqual(meta['surfaces'], [])
        text = b'mesh\0textures/test\0run\0'
        h = [0] * 27
        h[0] = 2; h[1] = 124 + len(text) + 24 + 20
        h[3:7] = [len(text), 124, 1, 124 + len(text)]
        h[13] = 8; h[17:20] = [1, 124 + len(text) + 24, 12]
        data = struct.pack('<16s27I', b'INTERQUAKEMODEL\0', *h) + text
        data += struct.pack('<6I', 0, 5, 0, 3, 0, 1) + struct.pack('<3IfI', 19, 3, 9, 24, 1)
        meta, refs = inspect('models/test.iqm', data)
        self.assertEqual(refs, [('textures/test', 'iqm-material')])
        self.assertEqual(meta['joints'], 8)
        self.assertEqual(meta['animations'], [{'name': 'run', 'first': 3, 'frames': 9, 'fps': 24., 'loop': True}])

    def test_skin_wav_and_animation_cfg(self):
        _, refs = inspect('models/players/a/lower.skin', b'tag_torso,\nbody,textures/body\n')
        self.assertEqual(refs, [('textures/body', 'skin-material')])
        out = io.BytesIO()
        with wave.open(out, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050); w.writeframes(bytes(20))
        self.assertEqual(inspect('sound/test.wav', out.getvalue())[0]['frames'], 10)
        meta, _ = inspect('models/players/a/animation.cfg', b'sex m\n0 12 4 15 // run\n')
        self.assertEqual(meta['animation_rows_first_count_loop_fps'], [[0, 12, 4, 15]])


if __name__ == '__main__':
    unittest.main()
