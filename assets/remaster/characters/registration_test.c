/* Production cgame registration with a mock VFS/renderer, not a GL test.
 * cc -ffunction-sections -fdata-sections assets/remaster/characters/registration_test.c
 * code/qcommon/q_shared.c -Wl,--gc-sections -lm -o /tmp/character-registration
 */
#include <assert.h>
#include "../../../code/cgame/cg_players.c"

static int replacement;
static int registrationCount;
static char registered[MAX_QPATH];

int trap_FS_FOpenFile(const char *path, fileHandle_t *file, fsMode_t mode) {
    assert(file == NULL && mode == FS_READ);
    assert(strstr(path, ".iqm"));
    return replacement;
}

qhandle_t trap_R_RegisterModel(const char *path) {
    registrationCount++;
    Q_strncpyz(registered, path, sizeof(registered));
    return 73;
}

void QDECL Com_Error(int level, const char *fmt, ...) { abort(); }
void QDECL Com_Printf(const char *fmt, ...) { }

int main(void) {
    const char *parts[] = {"models/players/sarge/lower", "models/players/sarge/upper",
        "models/players/sarge/head", "models/players/characters/sarge/lower",
        "models/players/heads/sarge/sarge"};
    int i;
    for (i = 0; i < ARRAY_LEN(parts); i++) {
        char md3[MAX_QPATH], iqm[MAX_QPATH];
        Com_sprintf(md3, sizeof(md3), "%s.md3", parts[i]);
        Com_sprintf(iqm, sizeof(iqm), "%s.iqm", parts[i]);
        replacement = 128;
        registrationCount = 0;
        assert(CG_RegisterPlayerModel(md3) == 73);
        assert(registrationCount == 1 && !strcmp(registered, iqm));
        replacement = -1;
        assert(CG_RegisterPlayerModel(md3) == 73);
        assert(registrationCount == 2 && !strcmp(registered, md3));
        replacement = 0;
        assert(CG_RegisterPlayerModel(md3) == 73);
        assert(registrationCount == 3 && !strcmp(registered, md3));
    }
    puts("PASS: 5 player paths, IQM priority and missing/empty legacy fallback");
    return 0;
}
