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
/* Filter: -1 reads, 0..2 writes; -2 unavailable/custom. New setting IDs 5..10:
 * crosshair, crosshair size, FPS, handicap, color1, color2 (integers only). */
int OG_WebTextureFilter(int choice);
int OG_WebKey(int index);
/* Binding read: action id or -1 unbound/-2 custom/-3 invalid or unavailable.
 * Write: 1 applied/2 conflict/3 protected custom/0 invalid. Fixed commands only. */
int OG_WebBinding(int key);
int OG_WebBind(int action, int old, int next, int replace);
/* Name: 0 reset transaction, 1 append ASCII value, 2 commit, 3 read index.
 * Returns 1 success/0 rejected/-1 unavailable; read returns character or 0. */
int OG_WebName(int op, int value);
/* 0 resumes active match; 1 opens DOM + engine menu; 2 returns to engine menu;
 * 3 detaches DOM and terminally blocks input until reload, without invoking VM.
 * OG_WebMenuOpen covers both a visible DOM menu and a terminal failure page;
 * SDL input must not recapture the canvas while this predicate is true. */
int OG_WebMenu(int open);
int OG_WebMenuOpen(void);

#endif
