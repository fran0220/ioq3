"""Production q3_ui catalogue/launch policy against asymmetric VFS inputs."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PlayTest(unittest.TestCase):
    def test_validation_before_mutation_and_original_sp_route(self):
        source = r'''
#include <assert.h>
#include "code/q3_ui/ui_web.c"
static int writes, launches, missing;
static char commands[4096];
void QDECL Com_Printf(const char *fmt, ...) { (void)fmt; }
void QDECL Com_Error(int level, const char *fmt, ...) { (void)level; (void)fmt; abort(); }
int UI_GetNumArenas(void) { return 4; }
int UI_GetNumBots(void) { return 2; }
const char *UI_GetArenaInfoByNumber(int id) {
    static const char *arenas[] = {
        "\\map\\q3dm1\\longname\\Arena One\\type\\single ffa tourney",
        "\\map\\ctf_test\\type\\ctf team",
        "\\map\\evil;quit\\type\\ffa",
        "\\map\\missing\\type\\ffa"};
    return id >= 0 && id < 4 ? arenas[id] : NULL;
}
char *UI_GetBotInfoByNumber(int id) {
    return id == 0 ? "\\name\\Sarge" : id == 1 ? "\\name\\bad;quit" : NULL;
}
int UI_WebPlayerModels(void) { return 1; }
const char *UI_WebPlayerModelName(int id) { return id == 0 ? "models/players/sarge/icon_blue" : NULL; }
int trap_FS_FOpenFile(const char *path, fileHandle_t *file, fsMode_t mode) {
    assert(mode == FS_READ); *file = 0;
    if (strstr(path, "missing") || (missing && strstr(path, "upper"))) return -1;
    *file = 9; return 17;
}
void trap_FS_FCloseFile(fileHandle_t file) { assert(file == 9); }
void trap_Cvar_Set(const char *name, const char *value) { assert(name && value); writes++; }
void trap_Cvar_SetValue(const char *name, float value) { assert(name && value >= 0); writes++; }
float trap_Cvar_VariableValue(const char *name) { return strstr(name, "timelimit") ? 7 : 13; }
void trap_Cmd_ExecuteText(int when, const char *text) { assert(when == EXEC_APPEND); strcat(commands, text); }
void UI_ForceMenuOff(void) { }
void UI_SPArena_Start(const char *info) { assert(strstr(info, "q3dm1")); launches++; }
int main(void) {
    const ui_web_record_t *record;
    assert(!UI_WebCatalog(0, 0, 2, sizeof(ui_web_record_t)));
    assert(!UI_WebCatalog(0, 0, 1, sizeof(ui_web_record_t) - 1));
    assert(UI_WebEdit(UI_WEB_RESET, 0, 0) == 1);
    record = UI_WebCatalog(UI_WEB_MAP, 0, 1, sizeof(ui_web_record_t));
    assert(record && record->count == 4 && record->available);
    assert(record->modes == ((1 << GT_FFA) | (1 << GT_SINGLE_PLAYER) | (1 << GT_TOURNAMENT)));
    assert(!strcmp(record->displayName, "Arena One"));
    assert(!UI_WebCatalog(UI_WEB_MAP, 4, 1, sizeof(ui_web_record_t)));
    assert(!UI_WebCatalog(UI_WEB_MAP, 2, 1, sizeof(ui_web_record_t))->available);
    assert(UI_WebLaunch(2, 0, 3) == -3 && writes == 0);
    assert(UI_WebLaunch(3, 0, 3) == -3 && writes == 0);
    assert(UI_WebLaunch(0, 4, 3) == -2 && writes == 0);
    assert(UI_WebLaunch(0, 0, 0) == -2 && writes == 0);
    assert(UI_WebEdit(UI_WEB_BOT_SLOT, 8, 0) == -2);
    assert(UI_WebEdit(UI_WEB_BOT_SLOT, 0, 1) == -3);
    assert(UI_WebEdit(UI_WEB_BOT_SLOT, 7, 0) == 1);
    assert(UI_WebLaunch(0, GT_SINGLE_PLAYER, 3) == -2 && writes == 0);
    assert(UI_WebEdit(UI_WEB_LIMITS, 1000, 3) == -2);
    assert(UI_WebEdit(UI_WEB_LIMITS, 101, 3) == 1);
    assert(UI_WebLaunch(1, GT_CTF, 3) == -2 && writes == 0);
    assert(UI_WebEdit(UI_WEB_LIMITS, 5, 9) == 1);
    assert(UI_WebLaunch(1, GT_CTF, 4) == 1 && writes > 0);
    /* Reset the old reliable-command stream before loading a fresh match. */
    assert(strncmp(commands, "disconnect\nmap ctf_test\n", 24) == 0);
    assert(strstr(commands, "addbot Sarge 4 Blue\n"));
    assert(strstr(commands, "team Red\n"));
    assert(!strstr(commands, "quit"));
    UI_WebEdit(UI_WEB_RESET, 0, 0); writes = 0;
    assert(UI_WebLaunch(0, GT_SINGLE_PLAYER, 5) == 1 && launches == 1);
    writes = 0; missing = 1;
    assert(UI_WebEdit(UI_WEB_SELECT_MODEL, 0, 0) == -3 && writes == 0);
    missing = 0;
    assert(UI_WebEdit(UI_WEB_SELECT_MODEL, 0, 0) == 1 && writes == 4);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            cfile, binary = Path(tmp) / 'play.c', Path(tmp) / 'play'
            cfile.write_text(source)
            subprocess.run(['cc', '-std=c99', '-I', str(ROOT), str(cfile),
                            str(ROOT / 'code/qcommon/q_shared.c'), '-lm', '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    unittest.main()
