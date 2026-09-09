/* SPDX-License-Identifier: GPL-2.0-or-later
 * Read-only server-snapshot observer. Never compiled into release builds.
 * This observes authoritative snapshots, not cgame prediction or commands. */
#include "client.h"

#ifdef IOQ3_WEB_TEST_OBSERVER
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#else
#define EMSCRIPTEN_KEEPALIVE
#endif

/* Worst-case escaped configstrings, numeric state and visible snapshot entities. */
static char webTestJSON[4 * MAX_GAMESTATE_CHARS * 6 + 4096 + MAX_SNAPSHOT_ENTITIES * 512];

static char *WebTestString(char *out, const char *in)
{
	static const char hex[] = "0123456789abcdef";
	*out++ = '"';
	while (*in) {
		unsigned char c = (unsigned char)*in++;
		if (c == '"' || c == '\\') {
			*out++ = '\\';
			*out++ = c;
		} else if (c < 32 || c >= 127) {
			/* Preserve Quake's byte-oriented strings as JSON code points. */
			*out++ = '\\'; *out++ = 'u'; *out++ = '0'; *out++ = '0';
			*out++ = hex[c >> 4]; *out++ = hex[c & 15];
		} else {
			*out++ = c;
		}
	}
	*out++ = '"';
	*out = 0;
	return out;
}

/* Main thread only. Static result remains valid until the next invocation.
 * Test hosts can decode Module.HEAPU8 from the returned pointer to the NUL. */
EMSCRIPTEN_KEEPALIVE const char *OG_WebTestSnapshot(void)
{
	const playerState_t *ps = &cl.snap.ps;
	char *out = webTestJSON;
	int i;
	const int ids[] = { CS_SERVERINFO, CS_INTERMISSION, CS_SCORES1, CS_SCORES2 };
	const char *names[] = { "serverInfo", "intermission", "scores1", "scores2" };

	out += sprintf(out, "{\"schemaVersion\":1,\"state\":%d,\"keyCatcher\":%d,\"snap\":{"
		"\"valid\":%s,\"messageNum\":%d,\"serverTime\":%d,\"ps\":{"
		"\"clientNum\":%d,\"origin\":[%.9g,%.9g,%.9g],"
		"\"velocity\":[%.9g,%.9g,%.9g],\"viewangles\":[%.9g,%.9g,%.9g],"
		"\"pm_type\":%d,\"groundEntityNum\":%d,\"weapon\":%d,\"weaponTime\":%d,"
		"\"stats\":{\"health\":%d,\"armor\":%d,\"weapons\":%d},\"ammo\":[",
		clc.state, Key_GetCatcher(), cl.snap.valid ? "true" : "false", cl.snap.messageNum, cl.snap.serverTime,
		ps->clientNum, ps->origin[0], ps->origin[1], ps->origin[2],
		ps->velocity[0], ps->velocity[1], ps->velocity[2],
		ps->viewangles[0], ps->viewangles[1], ps->viewangles[2],
		ps->pm_type, ps->groundEntityNum, ps->weapon, ps->weaponTime,
		ps->stats[STAT_HEALTH], ps->stats[STAT_ARMOR], ps->stats[STAT_WEAPONS]);
	for (i = 0; i < MAX_WEAPONS; i++)
		out += sprintf(out, "%s%d", i ? "," : "", ps->ammo[i]);
	out += sprintf(out, "],\"persistant\":{\"score\":%d,\"killed\":%d,\"hits\":%d},"
		"\"eFlags\":%d}},\"configstrings\":{",
		ps->persistant[PERS_SCORE], ps->persistant[PERS_KILLED],
		ps->persistant[PERS_HITS], ps->eFlags);
	for (i = 0; i < ARRAY_LEN(ids); i++) {
		out += sprintf(out, "%s\"%s\":", i ? "," : "", names[i]);
		out = WebTestString(out, cl.gameState.stringData + cl.gameState.stringOffsets[ids[i]]);
	}
	out += sprintf(out, "},\"players\":[");
	if (cl.snap.valid && cl.parseEntitiesNum - cl.snap.parseEntitiesNum < MAX_PARSE_ENTITIES) {
		int count = 0;
		for (i = 0; i < cl.snap.numEntities; i++) {
			const entityState_t *ent = &cl.parseEntities[(cl.snap.parseEntitiesNum + i) & (MAX_PARSE_ENTITIES - 1)];
			if (ent->eType != ET_PLAYER) continue;
			out += sprintf(out, "%s{\"number\":%d,\"eType\":%d,\"eFlags\":%d,"
				"\"origin\":[%.9g,%.9g,%.9g],\"angles\":[%.9g,%.9g,%.9g],"
				"\"weapon\":%d,\"clientNum\":%d}", count++ ? "," : "",
				ent->number, ent->eType, ent->eFlags,
				ent->pos.trBase[0], ent->pos.trBase[1], ent->pos.trBase[2],
				ent->apos.trBase[0], ent->apos.trBase[1], ent->apos.trBase[2], ent->weapon, ent->clientNum);
		}
	}
	sprintf(out, "]}");
	return webTestJSON;
}
#endif
