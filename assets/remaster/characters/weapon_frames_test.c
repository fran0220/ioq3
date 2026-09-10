/* Actual cgame metadata parser/endpoint mapper with read-only VFS mocks. */
#include <assert.h>
#include "../../../code/cgame/cg_players.c"

static const char *config;
int trap_FS_FOpenFile(const char *path, fileHandle_t *file, fsMode_t mode) {
    assert(mode == FS_READ && file);
    *file = config ? 1 : 0;
    return config ? strlen(config) : -1;
}
void trap_FS_Read(void *buffer, int length, fileHandle_t file) { memcpy(buffer, config, length); }
void trap_FS_FCloseFile(fileHandle_t file) { assert(file == 1); }
void QDECL Com_Error(int level, const char *fmt, ...) { abort(); }
void QDECL Com_Printf(const char *fmt, ...) { }

int main(void) {
    clientInfo_t ci = {0}, copy = {0};
    const char *bad[] = {"5", "5 -1", "5 1.5", "5 2147483648", "5 2147483600",
        "999 2", "-1 2", "0 2", "5 153 5 154", "5 153junk", "5 153 2"};
    int i;
    ci.animations[TORSO_GESTURE].firstFrame = 90;
    ci.animations[TORSO_STAND2].firstFrame = 152;
    ci.animations[TORSO_STAND2].numFrames = 1;
    config = "// independent hand placement, shared animation time\n2 0\n5 153\n";
    assert(CG_ParseWeaponFrames("weapon_frames.cfg", &ci));
    assert(ci.torsoWeaponFrameOffset[WP_MACHINEGUN] == 0);
    assert(ci.torsoWeaponFrameOffset[WP_ROCKET_LAUNCHER] == 153);
    // Both sides of the death/living boundary, tested per interpolation endpoint.
    assert(CG_WeaponTorsoFrame(&ci, WP_ROCKET_LAUNCHER, 89) == 89);
    assert(CG_WeaponTorsoFrame(&ci, WP_ROCKET_LAUNCHER, 90) == 243);
    assert(CG_WeaponTorsoFrame(&ci, WP_ROCKET_LAUNCHER, 151) == 304);
    assert(CG_WeaponTorsoFrame(&ci, WP_ROCKET_LAUNCHER, 147) == 300);
    assert(CG_WeaponTorsoFrame(&ci, WP_MACHINEGUN, 147) == 147);
    assert(CG_WeaponTorsoFrame(&ci, WP_NUM_WEAPONS, 151) == 151);
    assert(CG_WeaponTorsoFrame(&ci, -1, 151) == 151);
    assert(CG_WeaponTorsoFrame(&ci, WP_ROCKET_LAUNCHER, INT_MAX) == INT_MAX);
    CG_CopyClientInfoModel(&ci, &copy);
    assert(!memcmp(copy.torsoWeaponFrameOffset, ci.torsoWeaponFrameOffset, sizeof(ci.torsoWeaponFrameOffset)));
    for (i = 0; i < ARRAY_LEN(bad); i++) {
        config = bad[i];
        assert(!CG_ParseWeaponFrames("weapon_frames.cfg", &ci));
        assert(ci.torsoWeaponFrameOffset[WP_ROCKET_LAUNCHER] == 153); // no partial parse
    }
    config = "";
    assert(CG_ParseWeaponFrames("weapon_frames.cfg", &ci));
    assert(ci.torsoWeaponFrameOffset[WP_ROCKET_LAUNCHER] == 0);
    config = NULL;
    assert(CG_ParseWeaponFrames("weapon_frames.cfg", &ci));
    assert(CG_WeaponTorsoFrame(&ci, WP_ROCKET_LAUNCHER, 151) == 151);
    puts("PASS: weapon offset parser, invalid integers/overflow, per-endpoint death boundary, copy and legacy zero");
    return 0;
}
