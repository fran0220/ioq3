"""Offline tests of Painter recovery and the actual cgame hand frame mapper."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from import_painter import import_image


class WeaponTests(unittest.TestCase):
    def test_import_is_idempotent_and_preserves_review(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / 'input.png'
            Image.new('RGB', (32, 24), (17, 83, 149)).save(image)
            manifest = {'asset_id': 'weapon-import-test', 'image_model': 'amp-painter',
                        'prototype_url': 'https://example.invalid/test-only'}
            work = root / 'work'
            first = import_image(manifest, work, image, 'first inspected review')
            state = (work / 'state.json').read_bytes()
            self.assertEqual(import_image(manifest, work, image, 'must not replace review'), first)
            self.assertEqual((work / 'state.json').read_bytes(), state)
            self.assertIsNone(json.loads(state)['stages']['image']['cost']['actual_usd'])
            Image.new('RGB', (32, 24), (149, 83, 17)).save(image)
            with self.assertRaisesRegex(ValueError, 'drift'):
                import_image(manifest, work, image, 'changed source')
            self.assertEqual((work / 'state.json').read_bytes(), state)

    def test_reject_non_painter_import(self):
        with self.assertRaisesRegex(ValueError, 'explicit Amp Painter'):
            import_image({'image_model': 'other'}, Path('/unused'), Path('/unused'), '')

    def test_production_mapper_boundaries_and_priority(self):
        root = Path(__file__).resolve().parents[3]
        source = (root / 'code/cgame/cg_weapons.c').read_text()
        start = source.index('static int CG_MapTorsoToWeaponFrame(')
        end = source.index('\n}\n', start) + 3
        program = '''
#include <assert.h>
enum { TORSO_DROP, TORSO_ATTACK, TORSO_ATTACK2 };
typedef struct { int firstFrame; } animation_t;
typedef struct { animation_t animations[3]; } clientInfo_t;
''' + source[start:end] + '''
int main(void) {
    clientInfo_t ci = {{{100}, {200}, {300}}};
    int i;
    assert(CG_MapTorsoToWeaponFrame(&ci, 99) == 0);
    for (i=0; i<9; ++i) assert(CG_MapTorsoToWeaponFrame(&ci, 100+i) == 6+i);
    assert(CG_MapTorsoToWeaponFrame(&ci, 109) == 0);
    assert(CG_MapTorsoToWeaponFrame(&ci, 199) == 0);
    assert(CG_MapTorsoToWeaponFrame(&ci, 299) == 0);
    for (i=0; i<6; ++i) {
        assert(CG_MapTorsoToWeaponFrame(&ci, 200+i) == 1+i);
        assert(CG_MapTorsoToWeaponFrame(&ci, 300+i) == 1+i);
    }
    assert(CG_MapTorsoToWeaponFrame(&ci, 206) == 0);
    assert(CG_MapTorsoToWeaponFrame(&ci, 306) == 0);
    ci.animations[TORSO_ATTACK].firstFrame = 102;
    assert(CG_MapTorsoToWeaponFrame(&ci, 102) == 8);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'mapper.c').write_text(program)
            subprocess.run(['cc', '-Wall', '-Werror', str(path / 'mapper.c'), '-o', str(path / 'mapper')], check=True)
            subprocess.run([str(path / 'mapper')], check=True)


if __name__ == '__main__':
    unittest.main()
