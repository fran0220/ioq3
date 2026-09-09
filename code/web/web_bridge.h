/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef IOQ3_WEB_BRIDGE_H
#define IOQ3_WEB_BRIDGE_H

/* Main thread only, after a submitted functional menu/game frame.
 * configChanged means a home config/state write has completed successfully.
 * Never infer playable from renderer or WASM initialization alone. */
void OG_WebFrame(int playable, int configChanged);
void OG_WebLoseFocus(void);
void OG_WebResumeAudio(void);

#endif
