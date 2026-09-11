"""Offline tests of Painter recovery and the actual cgame hand frame mapper."""
import json
import re
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from import_painter import import_image
from iqm_validate import read_iqm, matrices


class WeaponTests(unittest.TestCase):
    def test_actual_damage_and_knockback_rules(self):
        root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as directory:
            team = Path(directory) / 'team.o'
            executable = Path(directory) / 'damage-rules'
            subprocess.run(['cc', '-ffunction-sections', '-fdata-sections',
                            '-DTeam_CheckHurtCarrier=Discarded_Team_CheckHurtCarrier',
                            '-c', str(root / 'code/game/g_team.c'), '-o', str(team)], check=True)
            subprocess.run(['cc', '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
                            str(root / 'misc/remaster-assets/weapons/damage_rules.c'), str(team),
                            str(root / 'code/qcommon/q_math.c'), '-lm', '-o', str(executable)], check=True)
            subprocess.run([str(executable)], check=True)

    def test_actual_shared_weapon_rules(self):
        root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / 'fire-rules'
            subprocess.run(['cc', '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
                            str(root / 'misc/remaster-assets/weapons/fire_rules.c'),
                            str(root / 'code/game/bg_misc.c'), str(root / 'code/qcommon/q_shared.c'),
                            str(root / 'code/qcommon/q_math.c'), '-lm', '-o', str(executable)], check=True)
            subprocess.run([str(executable)], check=True)

    def test_shotgun_fit_scales_socket_with_mesh_and_keeps_unit_axes(self):
        root = Path(__file__).resolve().parents[3]
        with zipfile.ZipFile(root / 'assets/remaster/runtime/weapon-shotgun-v1-candidate.pk3') as archive:
            model = read_iqm(archive.read('models/remaster/weapons/shotgun/weapon.iqm'))
        index = next(i for i, joint in enumerate(model['joints']) if joint['name'] == 'tag_flash')
        socket = matrices(model['joints'], model['frames'][0])[index]
        # Independent measured socket minus grip, .8 authored fit, 40 units/m.
        for axis, expected in enumerate((25.664, 0, 4.48)):
            self.assertAlmostEqual(socket[axis][3], expected, delta=.001)
            for other in range(3):
                self.assertAlmostEqual(socket[axis][other], int(axis == other), places=6)

    def test_partial_pack_keeps_reference_view_parts_together(self):
        source = (Path(__file__).resolve().parents[3] / 'code/cgame/cg_weapons.c').read_text()
        start = source.index('\tcg_remasterHands[weaponNum] = qfalse;')
        end = source.index('\n\tswitch ( weaponNum )', start)
        registration = source[start:end]
        assignments = '\n'.join(re.search(r'\b' + part + r'\.hModel = [^;]+;', source).group()
                                for part in ('gun', 'barrel', 'flash'))
        program = '''
#include <assert.h>
#include <string.h>
#define qfalse 0
#define qtrue 1
static int mask;
int CG_RemasterWeaponModel(int n, const char *part) {
    int bit=!strcmp(part,"hands")?2:!strcmp(part,"barrel")?4:8;
    return mask&bit ? 100+bit : 0;
}
int trap_R_RegisterModel(const char *s) { return 11; }
int main(void) {
    int view;
    for(mask=0;mask<16;mask++) for(view=0;view<2;view++) {
        int cg_remasterHands[1]={0}, cg_referenceViewWeapon[1]={0};
        int cg_referenceViewBarrel[1]={0}, cg_referenceViewFlash[1]={0};
        int weaponNum=0, remaster, remasterBody=mask&1?100:0;
        int *ps=view?&view:0;
        struct { const char *world_model[1]; } itemData={{"reference"}}, *item=&itemData;
        struct { int weaponModel, handsModel, barrelModel, flashModel; }
            data={remasterBody?100:11,12,14,13}, *weaponInfo=&data, *weapon=&data;
        struct { int hModel; } gun, barrel, flash;
''' + registration + assignments + '''
        int useNew=(mask&1) && (!view || (mask&2));
        assert(gun.hModel == (useNew?100:11));
        assert(barrel.hModel == (useNew && (mask&4)?104:14));
        assert(flash.hModel == (useNew && (mask&8)?108:13));
    }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'parts.c').write_text(program)
            subprocess.run(['cc', '-Wall', '-Werror', str(path / 'parts.c'), '-o', str(path / 'parts')], check=True)
            subprocess.run([str(path / 'parts')], check=True)

    def test_generated_hand_clip_socket_and_boundaries(self):
        root = Path(__file__).resolve().parents[3]
        with zipfile.ZipFile(root / 'assets/remaster/runtime/weapon-hands-v1-candidate.pk3') as archive:
            model = read_iqm(archive.read('models/remaster/weapons/rocket/hands.iqm'))
        self.assertEqual(len(model['frames']), 15)
        index = next(i for i, joint in enumerate(model['joints']) if joint['name'] == 'tag_weapon')
        expected = {0: (18,-6,-14), 1: (16.8,-6,-14.3), 6: (18,-6,-14),
                    10: (18,-6,-26), 11: (18,-6,-26), 14: (18,-6,-14)}
        for frame, origin in expected.items():
            socket = matrices(model['joints'], model['frames'][frame])[index]
            for axis in range(3):
                self.assertAlmostEqual(socket[axis][3], origin[axis], delta=.001)
                for other in range(3):
                    self.assertAlmostEqual(socket[axis][other], int(axis == other), places=6)

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
