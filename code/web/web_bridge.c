/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "../client/client.h"
#include "web_bridge.h"
#include <emscripten.h>

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
