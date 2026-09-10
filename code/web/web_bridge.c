/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "../client/client.h"
#include "web_bridge.h"
#include <emscripten.h>
#include <math.h>

/* Numeric allowlist only: browser UI cannot submit arbitrary console commands. */
static const char *webSettings[] = { "s_volume", "s_musicvolume", "sensitivity", "m_pitch", "cg_fov",
    "cg_drawCrosshair", "cg_crosshairSize", "cg_drawFPS", "handicap", "color1", "color2" };
static const double webMin[] = { 0, 0, 0.1, -0.1, 60, 0, 8, 0, 1, 1, 1 };
static const double webMax[] = { 1, 1, 30, 0.1, 140, 10, 64, 1, 100, 7, 7 };
static const char *webFilters[] = { "GL_NEAREST_MIPMAP_NEAREST", "GL_LINEAR_MIPMAP_NEAREST", "GL_LINEAR_MIPMAP_LINEAR" };
static const char *webActions[] = { "+forward", "+back", "+moveleft", "+moveright", "+moveup", "+movedown",
    "+speed", "+attack", "+zoom", "+scores", "weapprev", "weapnext", "+button2", "messagemode", "messagemode2",
    "weapon 1", "weapon 2", "weapon 3", "weapon 4", "weapon 5", "weapon 6", "weapon 7", "weapon 8", "weapon 9",
    "centerview", "+strafe", "+left", "+right", "+lookup", "+lookdown" };
static int webMenuOpen;
static int webInputBlocked;

static cg_ui_snapshot_t webHUD;
static unsigned int webHUDReadTime;
static int webHUDServerSequence;

static int WebHUDValid(void)
{
    return !webInputBlocked && clc.state == CA_ACTIVE && webHUD.valid &&
        webHUDServerSequence == clc.serverMessageSequence &&
        (unsigned int)Sys_Milliseconds() - webHUDReadTime <= 1000;
}

EMSCRIPTEN_KEEPALIVE int OG_WebHUDRefresh(void)
{
    memset(&webHUD, 0, sizeof(webHUD));
    if (webInputBlocked || !CL_CGameUISnapshot(&webHUD)) {
        CL_CGameUIHUD(qfalse);
        return 0;
    }
    webHUDServerSequence = clc.serverMessageSequence;
    webHUDReadTime = (unsigned int)Sys_Milliseconds();
    return 1;
}

EMSCRIPTEN_KEEPALIVE int OG_WebHUDEnabled(int enabled)
{
    if (enabled != 0 && enabled != 1) return 0;
    if (enabled && !WebHUDValid()) {
        CL_CGameUIHUD(qfalse);
        return 0;
    }
    CL_CGameUIHUD(enabled ? qtrue : qfalse);
    return 1;
}

EMSCRIPTEN_KEEPALIVE double OG_WebHUD(int field, int row)
{
    const cg_ui_score_t *score;
    if (!WebHUDValid()) return NAN;
    switch (field) {
    case CG_UI_HEALTH: return webHUD.health;
    case CG_UI_ARMOR: return webHUD.armor;
    case CG_UI_AMMO: return webHUD.ammo;
    case CG_UI_WEAPON: return webHUD.weapon;
    case CG_UI_WEAPONS: return webHUD.weapons;
    case CG_UI_TEAM: return webHUD.team;
    case CG_UI_SCORE: return webHUD.score;
    case CG_UI_TIME: return webHUD.time;
    case CG_UI_ELAPSED: return webHUD.elapsed;
    case CG_UI_PM_TYPE: return webHUD.pmType;
    case CG_UI_INTERMISSION: return webHUD.intermission;
    case CG_UI_SCORES_SHOWING: return webHUD.scoresShowing;
    case CG_UI_LOCAL_CLIENT: return webHUD.localClient;
    case CG_UI_GAMETYPE: return webHUD.gametype;
    case CG_UI_TEAM_SCORE1: return webHUD.teamScores[0];
    case CG_UI_TEAM_SCORE2: return webHUD.teamScores[1];
    case CG_UI_FRAGLIMIT: return webHUD.fraglimit;
    case CG_UI_TIMELIMIT: return webHUD.timelimit;
    case CG_UI_SCORE_COUNT: return webHUD.scoreCount;
    }
    if (row < 0 || row >= webHUD.scoreCount) return NAN;
    score = &webHUD.scores[row];
    switch (field) {
    case CG_UI_ROW_CLIENT: return score->client;
    case CG_UI_ROW_TEAM: return score->team;
    case CG_UI_ROW_SCORE: return score->score;
    case CG_UI_ROW_PING: return score->ping;
    case CG_UI_ROW_TIME: return score->time;
    default: return NAN;
    }
}

EMSCRIPTEN_KEEPALIVE int OG_WebHUDText(int kind, int row, int index)
{
    if (!WebHUDValid() || index < 0) return -1;
    if (kind == CG_UI_TEXT_MAP && index < CG_UI_MAP_BYTES)
        return (unsigned char)webHUD.mapName[index];
    if (kind == CG_UI_TEXT_PLAYER && row >= 0 && row < webHUD.scoreCount && index < CG_UI_NAME_BYTES)
        return (unsigned char)webHUD.scores[row].name[index];
    return -1;
}

/* All command text is compile-time fixed. The reserved negative button identity
 * lets DOM respawn release its own attack without releasing a physical binding. */
EMSCRIPTEN_KEEPALIVE int OG_WebMatchAction(int action, int arg)
{
    static const char *teams[] = { "team free", "team red", "team blue", "team spectator" };
    if (action == 1 && arg == 0) {
        Cmd_ExecuteString("-attack -10042");
        return 1;
    }
    if (webInputBlocked || clc.state != CA_ACTIVE || !cgvm || clc.demoplaying) return 0;
    switch (action) {
    case 0:
        if (arg != 0 && arg != 1) return 0;
        Cmd_ExecuteString(arg ? "+scores" : "-scores");
        return 1;
    case 1:
        if (arg != 1 || !WebHUDValid() || webHUD.pmType != PM_DEAD || Key_GetCatcher()) return 0;
        Cmd_ExecuteString("+attack -10042");
        return 1;
    case 2:
        if (arg != 0) return 0;
        Cbuf_AddText("disconnect\n");
        return 1;
    case 3:
        if (arg != 0 || !com_sv_running || !com_sv_running->integer) return 0;
        Cbuf_AddText("map_restart 0\n");
        return 1;
    case 4:
        if (arg < 0 || arg >= (int)ARRAY_LEN(teams)) return 0;
        CL_AddReliableCommand(teams[arg], qfalse);
        return 1;
    default:
        return 0;
    }
}

int OG_WebMenuOpen(void) { return webMenuOpen || webInputBlocked; }

EMSCRIPTEN_KEEPALIVE int OG_WebUIState(void)
{
    if (webInputBlocked || !com_cl_running || !com_cl_running->integer || !uivm) return 0;
    if (clc.state == CA_DISCONNECTED) return 1;
    if (clc.state == CA_ACTIVE) return 2;
    return 3;
}

EMSCRIPTEN_KEEPALIVE double OG_WebSetting(int id)
{
    char value[64];
    int state = OG_WebUIState();
    if ((state != 1 && state != 2) || id < 0 || id >= ARRAY_LEN(webSettings)) return NAN;
    if (id >= 4 && id <= 7 && state != 2) return NAN;
    Cvar_VariableStringBuffer(webSettings[id], value, sizeof(value));
    return value[0] ? atof(value) : NAN;
}

EMSCRIPTEN_KEEPALIVE int OG_WebSetSetting(int id, double value)
{
    if (!isfinite(OG_WebSetting(id)) || !isfinite(value) || value < webMin[id] || value > webMax[id]) return 0;
    if (id == 3 && fabs(value) < 0.001) return 0;
    if (id >= 5 && value != floor(value)) return 0;
    Cvar_Set2(webSettings[id], va("%.6f", value), qfalse);
    return fabs(OG_WebSetting(id) - value) < 0.00001;
}

/* -1 reads current filter; 0..2 writes one of three engine-supported filters.
 * -2 means unavailable/custom. Existing textures update in R_BeginFrame. */
EMSCRIPTEN_KEEPALIVE int OG_WebTextureFilter(int choice)
{
    char value[64];
    int i, state = OG_WebUIState();
    if ((state != 1 && state != 2) || choice < -1 || choice >= (int)ARRAY_LEN(webFilters)) return -2;
    if (choice >= 0) Cvar_Set2("r_textureMode", webFilters[choice], qfalse);
    Cvar_VariableStringBuffer("r_textureMode", value, sizeof(value));
    for (i = 0; i < ARRAY_LEN(webFilters); i++) if (!Q_stricmp(value, webFilters[i])) return i;
    return -2;
}

static int WebKeyAllowed(int key)
{
    return (key >= 32 && key <= 126 && strchr(" ,-./0123456789;=[]\\'abcdefghijklmnopqrstuvwxyz", key)) || key == K_TAB || key == K_ENTER
        || key == K_BACKSPACE || key == K_CAPSLOCK || (key >= K_UPARROW && key <= K_F9)
        || (key >= K_KP_HOME && key <= K_MWHEELUP);
}

EMSCRIPTEN_KEEPALIVE int OG_WebKey(int index)
{
    static const int special[] = { K_TAB, K_ENTER, K_BACKSPACE, K_CAPSLOCK, K_UPARROW, K_DOWNARROW,
        K_LEFTARROW, K_RIGHTARROW, K_ALT, K_CTRL, K_SHIFT, K_INS, K_DEL, K_PGDN, K_PGUP, K_HOME, K_END,
        K_F1, K_F2, K_F3, K_F4, K_F5, K_F6, K_F7, K_F8, K_F9,
        K_MOUSE1, K_MOUSE2, K_MOUSE3, K_MOUSE4, K_MOUSE5, K_MWHEELDOWN, K_MWHEELUP,
        K_KP_HOME, K_KP_UPARROW, K_KP_PGUP, K_KP_LEFTARROW, K_KP_5, K_KP_RIGHTARROW, K_KP_END,
        K_KP_DOWNARROW, K_KP_PGDN, K_KP_ENTER, K_KP_INS, K_KP_DEL, K_KP_SLASH, K_KP_MINUS,
        K_KP_PLUS, K_KP_NUMLOCK, K_KP_STAR, K_KP_EQUALS };
    if (index >= 0 && index < 95) return index + 32;
    if (index < 95) return -1;
    index -= 95;
    return index >= 0 && index < ARRAY_LEN(special) ? special[index] : -1;
}

/* Read action id only; never expose/accept executable binding text. */
EMSCRIPTEN_KEEPALIVE int OG_WebBinding(int key)
{
    int i, state = OG_WebUIState();
    const char *binding;
    if ((state != 1 && state != 2) || !WebKeyAllowed(key)) return -3;
    binding = Key_GetBinding(key);
    if (!binding || !binding[0]) return -1;
    for (i = 0; i < ARRAY_LEN(webActions); i++) if (!Q_stricmp(binding, webActions[i])) return i;
    return -2;
}

/* Atomic slot change: reject stale old slot, custom commands and unresolved
 * conflicts before mutating either key. replace=1 explicitly displaces a known
 * action only. -1 old adds a binding; -1 next clears just the selected slot. */
EMSCRIPTEN_KEEPALIVE int OG_WebBind(int action, int old, int next, int replace)
{
    int target, state = OG_WebUIState();
    if ((state != 1 && state != 2) || action < 0 || action >= ARRAY_LEN(webActions)
        || (old == -1 && next == -1)
        || (replace != 0 && replace != 1) || (old != -1 && OG_WebBinding(old) != action)
        || (next != -1 && !WebKeyAllowed(next))) return 0;
    target = next == -1 ? -1 : OG_WebBinding(next);
    if (target == -2) return 3;
    if (target >= 0 && target != action && !replace) return 2;
    Key_ClearStates();
    if (old != -1 && old != next) Key_SetBinding(old, "");
    if (next != -1) Key_SetBinding(next, webActions[action]);
    return 1;
}

/* Numeric character transaction. No userinfo mutation until commit succeeds.
 * op 0 resets; 1 appends printable ASCII; 2 commits; 3 reads current char[index].
 * Names are 1..31 bytes, no color escapes or info/console delimiters. */
EMSCRIPTEN_KEEPALIVE int OG_WebName(int op, int value)
{
    static char pending[MAX_NAME_LENGTH];
    static int length, invalid;
    char current[MAX_NAME_LENGTH];
    int state = OG_WebUIState();
    if (state != 1 && state != 2) return -1;
    if (op == 3) {
        Cvar_VariableStringBuffer("name", current, sizeof(current));
        return value >= 0 && value < strlen(current) ? (unsigned char)current[value] : 0;
    }
    if (op == 0) { length = invalid = 0; pending[0] = 0; return 1; }
    if (op == 1) {
        if (value < 32 || value > 126 || value == '"' || value == ';' || value == '\\' || value == '^'
            || length >= sizeof(pending) - 1) { invalid = 1; return 0; }
        pending[length++] = value; pending[length] = 0; return 1;
    }
    if (op != 2 || invalid || !length || pending[0] == ' ' || pending[length - 1] == ' ' || strstr(pending, "    ")) return 0;
    Cvar_Set2("name", pending, qfalse);
    Cvar_VariableStringBuffer("name", current, sizeof(current));
    return !strcmp(current, pending);
}

EMSCRIPTEN_KEEPALIVE int OG_WebMenu(int open)
{
    /* Terminal failure releases menu ownership but blocks recapture until reload.
     * No VM invocation or attempts to revive a failed renderer/runtime. */
    if (open == 3) {
        webMenuOpen = 0;
        webInputBlocked = 1;
        Cmd_ExecuteString("-attack -10042");
        CL_CGameUIHUD(qfalse);
        memset(&webHUD, 0, sizeof(webHUD));
        return 1;
    }
    int state = OG_WebUIState();
    if ((state != 1 && state != 2) || open < 0 || open > 2) return 0;
    webMenuOpen = open == 1;
    Key_ClearStates();
    VM_Call(uivm, UI_SET_ACTIVE_MENU, open ? (state == 2 ? UIMENU_INGAME : UIMENU_MAIN) : UIMENU_NONE);
    return 1;
}

EM_JS(void, OG_WebFrame, (int playable, int configChanged), {
    if (Module['onEngineFrame']) {
        Module['onEngineFrame']({playable: !!playable, configChanged: !!configChanged});
    }
});

EMSCRIPTEN_KEEPALIVE void OG_WebLoseFocus(void)
{
    Cmd_ExecuteString("-attack -10042");
    Key_ClearStates();
    S_ClearSoundBuffer();
}

/* SDL2 and OpenAL are the two existing Emscripten audio backends. Resume only
 * from actual browser input; OG.userGesture alone is not transient activation. */
EM_JS(void, OG_ResumeBrowserAudio, (void), {
    var contexts = [];
    if (typeof SDL2 !== 'undefined' && SDL2.audioContext) contexts.push(SDL2.audioContext);
    if (typeof AL !== 'undefined') {
        for (var id in AL.contexts) {
            if (AL.contexts[id].audioCtx) contexts.push(AL.contexts[id].audioCtx);
        }
    }
    for (var context of contexts) {
        if (context.state === 'suspended') context.resume().catch(function() {});
    }
});

EMSCRIPTEN_KEEPALIVE void OG_WebResumeAudio(void)
{
    OG_ResumeBrowserAudio();
}
