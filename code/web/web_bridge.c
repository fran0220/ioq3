/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "../client/client.h"
#include "web_bridge.h"
#include <emscripten.h>
#include <math.h>

/* Numeric allowlist only: browser UI cannot submit arbitrary console commands. */
static const char *webSettings[] = { "s_volume", "s_musicvolume", "sensitivity", "m_pitch", "cg_fov" };
static const double webMin[] = { 0, 0, 0.1, -0.1, 60 };
static const double webMax[] = { 1, 1, 30, 0.1, 140 };
static int webMenuOpen;
static int webInputBlocked;

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
    Cvar_VariableStringBuffer(webSettings[id], value, sizeof(value));
    return value[0] ? atof(value) : NAN;
}

EMSCRIPTEN_KEEPALIVE int OG_WebSetSetting(int id, double value)
{
    if (!isfinite(OG_WebSetting(id)) || !isfinite(value) || value < webMin[id] || value > webMax[id]) return 0;
    if (id == 3 && fabs(value) < 0.001) return 0;
    Cvar_Set2(webSettings[id], va("%.6f", value), qfalse);
    return fabs(OG_WebSetting(id) - value) < 0.00001;
}

EMSCRIPTEN_KEEPALIVE int OG_WebMenu(int open)
{
    /* Terminal failure releases menu ownership but blocks recapture until reload.
     * No VM invocation or attempts to revive a failed renderer/runtime. */
    if (open == 3) { webMenuOpen = 0; webInputBlocked = 1; return 1; }
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
