/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef IOQ3_WEB_BRIDGE_H
#define IOQ3_WEB_BRIDGE_H

/* Main thread only, after a submitted functional menu/game frame.
 * configChanged means a home config/state write has completed successfully.
 * Never infer playable from renderer or WASM initialization alone. */
void OG_WebFrame(int playable, int configChanged);
void OG_WebLoseFocus(void);
void OG_WebResumeAudio(void);

/* Production cgame snapshot; field IDs in cgame/cg_ui_public.h. Refresh once
 * per DOM update, then read that cached snapshot. Invalid number = NaN, invalid
 * text index = -1, text terminator = 0. Enable only after DOM is mounted;
 * refresh + enable each update renews the 1-second original-HUD fallback lease. */
int OG_WebHUDRefresh(void);
double OG_WebHUD(int field, int row);
int OG_WebHUDText(int kind, int row, int index);
int OG_WebHUDEnabled(int enabled);
/* Fixed actions: 0 scores (arg 1 down/0 up), 1 respawn attack (1 down/0 up),
 * 2 disconnect (0), 3 local-server restart (0), 4 team (0 free/1 red/2 blue/3
 * spectator). 1 means accepted for normal engine processing, not server success.
 * Release respawn on pointerup/keyup/cancel/blur; never enable it while alive. */
int OG_WebMatchAction(int action, int arg);

/* Explicit catalogue refresh returns a generation and clears staged launch
 * options. kind=0 map/1 bot/2 modelskin. Value fields=id/mode bits/available;
 * text fields=internal name/display name. Fixed numeric ids only, no command
 * text. Mutations: 1 accepted, 0 unavailable, -1 stale, -2 input, -3 missing. */
int OG_WebCatalogRefresh(void);
int OG_WebCatalogCount(int kind);
double OG_WebCatalogValue(int kind, int id, int field);
int OG_WebCatalogText(int kind, int id, int field, int index);
int OG_WebPlayBot(int generation, double slot, double botId);
int OG_WebPlayLimits(int generation, double limit, double time);
int OG_WebPlay(int generation, double mapId, double mode, double skill);
int OG_WebSelectModel(int generation, double id);

/* Main-thread UI only. State: 0 unavailable, 1 menu, 2 active, 3 connecting.
 * Numeric settings: volume, music, sensitivity, pitch, FOV. NaN = unavailable.
 * Set/Menu return 0 on rejection. Never invoke from an uninitialized runtime. */
int OG_WebUIState(void);
/* Read-only actual display: 0 width, 1 height, 2 picmip. NaN before renderer. */
double OG_WebDisplay(int field);
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
