/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef IOQ3_WEB_BRIDGE_H
#define IOQ3_WEB_BRIDGE_H

/* Main thread only, after a submitted functional menu/game frame.
 * configChanged means a home config/state write has completed successfully.
 * Never infer playable from renderer or WASM initialization alone. */
void OG_WebFrame(int playable, int configChanged);
void OG_WebLoseFocus(void);
void OG_WebResumeAudio(void);

/* Main-thread UI only. State: 0 unavailable, 1 menu, 2 active, 3 connecting.
 * Numeric settings: volume, music, sensitivity, pitch, FOV. NaN = unavailable.
 * Set/Menu return 0 on rejection. Never invoke from an uninitialized runtime. */
int OG_WebUIState(void);
double OG_WebSetting(int id);
int OG_WebSetSetting(int id, double value);
/* 0 resumes active match; 1 opens DOM + engine menu; 2 returns to engine menu;
 * 3 detaches DOM ownership during failure, without invoking the UI VM.
 * SDL input must not recapture the canvas while OG_WebMenuOpen() is true. */
int OG_WebMenu(int open);
int OG_WebMenuOpen(void);

#endif
