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

    def test_dom_hud_gate_preserves_state_and_native_pixels(self):
        root = Path(__file__).resolve().parents[3]
        source = (root / 'code/cgame/cg_weapons.c').read_text()
        start = source.index('void CG_DrawWeaponSelect( void )')
        end = source.index('\n}\n', start) + 3
        program = '''
#include <assert.h>
#include <stddef.h>
#define STAT_HEALTH 0
#define STAT_WEAPONS 1
#define WEAPON_SELECT_TIME 1400
#define MAX_WEAPONS 16
#define BIGCHAR_WIDTH 16
#define SCREEN_WIDTH 640
typedef struct { int stats[2], ammo[16]; } ps_t;
struct { ps_t ps; } snapshot;
struct { ps_t predictedPlayerState; int weaponSelectTime, itemPickupTime, weaponSelect;
         __typeof__(snapshot) *snap; } cg;
struct { int integer; } cg_webHUD;
struct { struct { int selectShader, noammoShader; } media; } cgs;
struct item { char *pickup_name; };
struct { int weaponIcon; struct item *item; } cg_weapons[16];
static int pixels, colors, fades, registers, expired;
float *CG_FadeColor(int time, int duration) { static float color[4];
    assert(time==123); assert(duration==1400); fades++; return expired ? NULL : color; }
void trap_R_SetColor(float *color) { colors++; }
void CG_RegisterWeapon(int i) { registers++; }
void CG_DrawPic(int x,int y,int w,int h,int shader) { pixels++; }
int CG_DrawStrlen(char *s) { return 1; }
void CG_DrawBigStringColor(int x,int y,char *s,float *color) { pixels++; }
''' + source[start:end] + '''
int main(void) {
    cg.snap=&snapshot; cg.predictedPlayerState.stats[STAT_HEALTH]=100;
    cg.weaponSelectTime=123; cg.weaponSelect=2; cg.itemPickupTime=456;
    snapshot.ps.stats[STAT_WEAPONS]=(1<<2)|(1<<5); snapshot.ps.ammo[2]=7;
    cg_webHUD.integer=1; CG_DrawWeaponSelect();
    assert(cg.itemPickupTime==0 && cg.weaponSelectTime==123 && cg.weaponSelect==2);
    assert(pixels==0 && colors==0 && fades==1);
    cg_webHUD.integer=0; cg.itemPickupTime=789; CG_DrawWeaponSelect();
    assert(cg.itemPickupTime==0 && pixels==4 && colors==2 && registers==2);
    expired=1; cg.itemPickupTime=222; CG_DrawWeaponSelect();
    assert(cg.itemPickupTime==222 && pixels==4 && colors==2);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'hud.c').write_text(program)
            subprocess.run(['cc', '-Wall', '-Werror', str(path / 'hud.c'), '-o', str(path / 'hud')], check=True)
            subprocess.run([str(path / 'hud')], check=True)

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
