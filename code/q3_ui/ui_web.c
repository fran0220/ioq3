/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "ui_local.h"

static int webBots[8];
static int webFrag = -1, webTime = -1, webModelCount;

static qboolean WebPath(const char *name) {
	const char *p;
	if (!name || !*name || strlen(name) >= MAX_QPATH || name[0] == '/' || strstr(name, "..")) return qfalse;
	for (p = name; *p; p++)
		if (!((*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z') ||
			(*p >= '0' && *p <= '9') || *p == '_' || *p == '-' || *p == '/')) return qfalse;
	return qtrue;
}

static qboolean WebFile(const char *path) {
	fileHandle_t file;
	int size = trap_FS_FOpenFile(path, &file, FS_READ);
	if (file) trap_FS_FCloseFile(file);
	return size > 0;
}

static int WebModes(const char *info) {
	char types[MAX_INFO_STRING], *p, *token;
	int bits = 0;
	Q_strncpyz(types, Info_ValueForKey(info, "type"), sizeof(types));
	p = types;
	while ((token = COM_ParseExt(&p, qfalse))[0]) {
		if (!Q_stricmp(token, "ffa")) bits |= 1 << GT_FFA;
		else if (!Q_stricmp(token, "single")) bits |= (1 << GT_SINGLE_PLAYER) | (1 << GT_FFA);
		else if (!Q_stricmp(token, "tourney")) bits |= 1 << GT_TOURNAMENT;
		else if (!Q_stricmp(token, "team")) bits |= 1 << GT_TEAM;
		else if (!Q_stricmp(token, "ctf")) bits |= 1 << GT_CTF;
	}
	return bits;
}

static qboolean WebModel(int id, char *name, int size) {
	const char *icon = UI_WebPlayerModelName(id), *skin;
	char model[MAX_QPATH];
	int i, length;
	const char *parts[] = { "lower", "upper", "head" };
	if (!icon || Q_strncmp(icon, "models/players/", 15)) return qfalse;
	skin = strstr(icon + 15, "/icon_");
	if (!skin) return qfalse;
	length = skin - (icon + 15);
	if (length <= 0 || length >= sizeof(model)) return qfalse;
	memcpy(model, icon + 15, length); model[length] = 0;
	Com_sprintf(name, size, "%s/%s", model, skin + 6);
	if (!WebPath(name)) return qfalse;
	for (i = 0; i < 3; i++) {
		if (!WebFile(va("models/players/%s/%s.iqm", model, parts[i])) &&
			!WebFile(va("models/players/%s/%s.md3", model, parts[i]))) return qfalse;
		if (!WebFile(va("models/players/%s/%s_%s.skin", model, parts[i], skin + 6))) return qfalse;
	}
	return WebFile(va("models/players/%s/animation.cfg", model));
}

const ui_web_record_t *UI_WebCatalog(int kind, int id, int version, int size) {
	static ui_web_record_t record;
	const char *info;
	if (version != UI_WEB_VERSION || size != sizeof(record) || kind < 0 || kind > UI_WEB_MODEL) return NULL;
	memset(&record, 0, sizeof(record));
	record.version = version; record.size = size; record.kind = kind; record.id = id;
	record.count = kind == UI_WEB_MAP ? UI_GetNumArenas() : kind == UI_WEB_BOT ? UI_GetNumBots() : webModelCount;
	if (id == -1) return &record;
	if (id < 0 || id >= record.count) return NULL;
	if (kind == UI_WEB_MODEL) {
		record.available = WebModel(id, record.name, sizeof(record.name));
		Q_strncpyz(record.displayName, record.name, sizeof(record.displayName));
		return &record;
	}
	info = kind == UI_WEB_MAP ? UI_GetArenaInfoByNumber(id) : UI_GetBotInfoByNumber(id);
	if (!info) return NULL;
	Q_strncpyz(record.name, Info_ValueForKey(info, kind == UI_WEB_MAP ? "map" : "name"), sizeof(record.name));
	Q_strncpyz(record.displayName, Info_ValueForKey(info, kind == UI_WEB_MAP ? "longname" : "name"), sizeof(record.displayName));
	if (!record.displayName[0]) Q_strncpyz(record.displayName, record.name, sizeof(record.displayName));
	record.available = WebPath(record.name);
	if (kind == UI_WEB_MAP) {
		record.modes = WebModes(info);
		record.available = record.available && WebFile(va("maps/%s.bsp", record.name));
	}
	return &record;
}

int UI_WebEdit(int op, int a, int b) {
	int i;
	char name[UI_WEB_TEXT];
	const ui_web_record_t *record;
	switch (op) {
	case UI_WEB_RESET:
		for (i = 0; i < ARRAY_LEN(webBots); i++) webBots[i] = -1;
		webFrag = webTime = -1;
		webModelCount = UI_WebPlayerModels();
		return 1;
	case UI_WEB_BOT_SLOT:
		if (a < 0 || a >= ARRAY_LEN(webBots) || b < -1 || b >= UI_GetNumBots()) return -2;
		if (b != -1) {
			record = UI_WebCatalog(UI_WEB_BOT, b, UI_WEB_VERSION, sizeof(ui_web_record_t));
			if (!record || !record->available) return -3;
		}
		webBots[a] = b;
		return 1;
	case UI_WEB_LIMITS:
		if (a < 0 || a > 999 || b < 0 || b > 999) return -2;
		webFrag = a; webTime = b;
		return 1;
	case UI_WEB_SELECT_MODEL:
		if (!WebModel(a, name, sizeof(name))) return -3;
		trap_Cvar_Set("model", name); trap_Cvar_Set("headmodel", name);
		trap_Cvar_Set("team_model", name); trap_Cvar_Set("team_headmodel", name);
		return 1;
	default: return -2;
	}
}

int UI_WebLaunch(int mapId, int mode, int skill) {
	const ui_web_record_t *record;
	const char *limitCvar, *timeCvar;
	char map[MAX_QPATH], bots[8][MAX_QPATH];
	int i, count = 0, limit, time;
	if (mode < GT_FFA || mode > GT_CTF || skill < 1 || skill > 5) return -2;
	record = UI_WebCatalog(UI_WEB_MAP, mapId, UI_WEB_VERSION, sizeof(ui_web_record_t));
	if (!record || !record->available) return -3;
	if (!(record->modes & (1 << mode))) return -2;
	Q_strncpyz(map, record->name, sizeof(map));
	for (i = 0; i < ARRAY_LEN(webBots); i++) {
		if (webBots[i] == -1) continue;
		record = UI_WebCatalog(UI_WEB_BOT, webBots[i], UI_WEB_VERSION, sizeof(ui_web_record_t));
		if (!record || !record->available) return -3;
		Q_strncpyz(bots[count++], record->name, sizeof(bots[0]));
	}
	if ((count || mode == GT_SINGLE_PLAYER) && !WebFile(va("maps/%s.aas", map))) return -3;
	if (mode == GT_SINGLE_PLAYER) {
		if (count || webFrag != -1 || webTime != -1) return -2;
		trap_Cvar_SetValue("g_spSkill", skill);
		trap_Cvar_SetValue("dedicated", 0);
		UI_SPArena_Start(UI_GetArenaInfoByNumber(mapId));
		UI_ForceMenuOff();
		return 1;
	}
	if (mode == GT_TOURNAMENT && count > 1) return -2;
	limitCvar = mode == GT_CTF ? "ui_ctf_capturelimit" : mode == GT_TEAM ? "ui_team_fraglimit" :
		mode == GT_TOURNAMENT ? "ui_tourney_fraglimit" : "ui_ffa_fraglimit";
	timeCvar = mode == GT_CTF ? "ui_ctf_timelimit" : mode == GT_TEAM ? "ui_team_timelimit" :
		mode == GT_TOURNAMENT ? "ui_tourney_timelimit" : "ui_ffa_timelimit";
	limit = webFrag >= 0 ? webFrag : (int)trap_Cvar_VariableValue(limitCvar);
	time = webTime >= 0 ? webTime : (int)trap_Cvar_VariableValue(timeCvar);
	if (limit < 0 || limit > (mode == GT_CTF ? 100 : 999) || time < 0 || time > 999) return -2;
	/* No mutation until every id/token/mode/limit is validated. Existing server
 	 * map/addbot/team commands retain the authoritative game rules. */
	trap_Cvar_SetValue(limitCvar, limit); trap_Cvar_SetValue(timeCvar, time);
	trap_Cvar_SetValue("g_gametype", mode); trap_Cvar_SetValue("dedicated", 0);
	trap_Cvar_SetValue("sv_maxclients", mode == GT_TOURNAMENT ? 2 : 12);
	trap_Cvar_SetValue("timelimit", time);
	trap_Cvar_SetValue(mode == GT_CTF ? "capturelimit" : "fraglimit", limit);
	if (mode >= GT_TEAM) {
		trap_Cvar_SetValue("g_friendlyfire", trap_Cvar_VariableValue(mode == GT_CTF ? "ui_ctf_friendly" : "ui_team_friendly"));
		trap_Cvar_Set("g_localTeamPref", "Red");
	}
	trap_Cmd_ExecuteText(EXEC_APPEND, va("wait; wait; map %s\nwait 3\n", map));
	for (i = 0; i < count; i++)
		trap_Cmd_ExecuteText(EXEC_APPEND, va("addbot %s %d %s\n", bots[i], skill, mode >= GT_TEAM ? (i % 2 ? "Red" : "Blue") : ""));
	if (mode >= GT_TEAM) trap_Cmd_ExecuteText(EXEC_APPEND, "wait 5; team Red\n");
	UI_ForceMenuOff();
	return 1;
}
