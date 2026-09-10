/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef UI_WEB_PUBLIC_H
#define UI_WEB_PUBLIC_H
#define UI_WEB_CAPABILITY 0x4f475032
#define UI_WEB_VERSION 1
#define UI_WEB_TEXT 128
typedef struct {
	int version, size, kind, id, count, modes, available;
	char name[UI_WEB_TEXT], displayName[UI_WEB_TEXT];
} ui_web_record_t;
enum { UI_WEB_MAP, UI_WEB_BOT, UI_WEB_MODEL };
enum { UI_WEB_RESET, UI_WEB_BOT_SLOT, UI_WEB_LIMITS, UI_WEB_SELECT_MODEL };
#endif
