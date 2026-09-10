"""Exercise production VM copy, cgame capability gate and browser HUD cache."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class HUDBridgeTest(unittest.TestCase):
    def test_boundaries_fallback_and_cached_fields(self):
        vm = (ROOT / 'code/qcommon/vm.c').read_text()
        copy = re.search(r'^qboolean VM_CopyFromVM\(.*?^}', vm, re.M | re.S).group()
        client = (ROOT / 'code/client/cl_cgame.c').read_text()
        client = client[client.index('static qboolean cgUISupported;'):client.index('/*\n====================\nCL_GetGameState')]
        web = (ROOT / 'code/web/web_bridge.c').read_text()
        web = web[web.index('static cg_ui_snapshot_t webHUD;'):web.index('int OG_WebMenuOpen(')]
        prelude = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include "code/cgame/cg_ui_public.h"
typedef int qboolean;
#define qfalse 0
#define qtrue 1
#define CA_ACTIVE 8
#define CG_UI_SNAPSHOT 9
#define EMSCRIPTEN_KEEPALIVE
#define PM_DEAD 3
#define ARRAY_LEN(x) (sizeof(x)/sizeof((x)[0]))
typedef struct { int entryPoint; int dataMask; unsigned char *dataBase; } vm_t;
static unsigned char memory[16384];
static vm_t machine = {0, 16383, memory}, *cgvm = &machine;
static struct { int state, serverMessageSequence, demoplaying; } clc;
static struct { int integer; } running, *com_sv_running = &running;
static char command[128];
static int catcher;
static int Key_GetCatcher(void) { return catcher; }
static void Cmd_ExecuteString(const char *value) { strcpy(command, value); }
static void Cbuf_AddText(const char *value) { strcpy(command, value); }
static void CL_AddReliableCommand(const char *value, int disconnect) { assert(!disconnect); strcpy(command, value); }
static intptr_t returned = 32;
static int calls, now, hudCvar, webInputBlocked;
static int Sys_Milliseconds(void) { return now; }
static void Cvar_Set(const char *name, const char *value) {
    assert(!strcmp(name, "cg_webHUD")); hudCvar = value[0] - '0';
}
static intptr_t VM_Call(vm_t *vm, int call, int version, size_t size) {
    assert(vm == cgvm && call == CG_UI_SNAPSHOT && version == 1 && size == sizeof(cg_ui_snapshot_t));
    calls++; return returned;
}
'''
        checks = r'''
int main(void) {
    unsigned char result[8] = {0};
    memory[16380] = 73; memory[16383] = 91;
    assert(VM_CopyFromVM(&machine, result, 16380, 4));
    assert(result[0] == 73 && result[3] == 91);
    assert(!VM_CopyFromVM(&machine, result, 16380, 5));
    assert(!VM_CopyFromVM(&machine, result, -1, 1));
    assert(!VM_CopyFromVM(&machine, result, 16416, 1));
    assert(!VM_CopyFromVM(&machine, result, 0, 1));
    assert(!VM_CopyFromVM(&machine, result, 32, SIZE_MAX));
    assert(!VM_CopyFromVM(NULL, result, 32, 1));
    machine.entryPoint = 1;
    assert(VM_CopyFromVM(&machine, result, (intptr_t)"native", 7));
    assert(!strcmp((char *)result, "native")); machine.entryPoint = 0;

    cg_ui_snapshot_t fixture = {0}, output;
    fixture.version = 1; fixture.size = sizeof(fixture); fixture.valid = 1;
    fixture.health = 83; fixture.armor = 27; fixture.ammo = -1;
    fixture.scoreCount = 64; fixture.scores[63].score = -9;
    fixture.scores[63].client = 42; fixture.time = 12819; fixture.elapsed = 1917;
    memset(fixture.mapName, 'm', sizeof(fixture.mapName));
    memset(fixture.scores[63].name, 'n', sizeof(fixture.scores[63].name));
    memcpy(memory + 32, &fixture, sizeof(fixture));
    clc.state = CA_ACTIVE;
    assert(!CL_CGameUISnapshot(&output) && calls == 0); /* old VM */
    cgUISupported = 1;
    assert(CL_CGameUISnapshot(&output) && calls == 1);
    assert(output.mapName[63] == 0 && output.scores[63].name[63] == 0);
    assert(!memcmp(memory + 32, &fixture, sizeof(fixture))); /* readonly */
    assert(OG_WebHUDRefresh());
    int cachedCalls = calls;
    assert(OG_WebHUD(CG_UI_HEALTH, 0) == 83);
    assert(OG_WebHUD(CG_UI_ARMOR, 0) == 27);
    assert(OG_WebHUD(CG_UI_AMMO, 0) == -1);
    assert(OG_WebHUD(CG_UI_TIME, 0) == 12819);
    assert(OG_WebHUD(CG_UI_ELAPSED, 0) == 1917);
    assert(OG_WebHUD(CG_UI_ROW_SCORE, 63) == -9);
    assert(isnan(OG_WebHUD(CG_UI_ROW_SCORE, 64)));
    assert(isnan(OG_WebHUD(999, 0)));
    assert(OG_WebHUDText(CG_UI_TEXT_PLAYER, 63, 62) == 'n');
    assert(OG_WebHUDText(CG_UI_TEXT_PLAYER, 63, 63) == 0);
    assert(OG_WebHUDText(CG_UI_TEXT_PLAYER, 63, 64) == -1);
    assert(OG_WebHUDText(CG_UI_TEXT_MAP, 0, -1) == -1);
    assert(calls == cachedCalls);
    assert(OG_WebHUDEnabled(1) && hudCvar == 1);
    now = 1001;
    assert(!OG_WebHUDEnabled(1) && hudCvar == 0);
    assert(isnan(OG_WebHUD(CG_UI_HEALTH, 0)));
    assert(OG_WebHUDRefresh());
    assert(!OG_WebMatchAction(1, 1)); /* alive */
    webHUD.pmType = PM_DEAD;
    assert(OG_WebMatchAction(1, 1) && !strcmp(command, "+attack -10042"));
    catcher = 1; assert(!OG_WebMatchAction(1, 1)); catcher = 0;
    assert(OG_WebMatchAction(1, 0) && !strcmp(command, "-attack -10042"));
    assert(!OG_WebMatchAction(3, 0)); /* remote server */
    running.integer = 1;
    assert(OG_WebMatchAction(3, 0) && !strcmp(command, "map_restart 0\n"));
    assert(!OG_WebMatchAction(4, 4));
    assert(OG_WebMatchAction(4, 3) && !strcmp(command, "team spectator"));
    clc.demoplaying = 1; assert(!OG_WebMatchAction(4, 0)); clc.demoplaying = 0;
    assert(!OG_WebMatchAction(999, 0));
    clc.serverMessageSequence++;
    assert(isnan(OG_WebHUD(CG_UI_HEALTH, 0)));
    assert(OG_WebHUDRefresh());
    webInputBlocked = 1;
    assert(!OG_WebHUDRefresh() && hudCvar == 0); webInputBlocked = 0;
    fixture.scoreCount = 65; memcpy(memory + 32, &fixture, sizeof(fixture));
    assert(!CL_CGameUISnapshot(&output) && output.valid == 0);
    fixture.scoreCount = -1; memcpy(memory + 32, &fixture, sizeof(fixture));
    assert(!CL_CGameUISnapshot(&output));
    fixture.scoreCount = 0; fixture.version = 2; memcpy(memory + 32, &fixture, sizeof(fixture));
    assert(!CL_CGameUISnapshot(&output));
    returned = 16383; assert(!CL_CGameUISnapshot(&output));
    clc.state = 0; assert(!CL_CGameUISnapshot(&output));
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.c'
            path.write_text(prelude + copy + client + web + checks)
            binary = Path(tmp) / 'test'
            subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-I', str(ROOT), str(path), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    unittest.main()
