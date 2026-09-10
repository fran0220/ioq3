/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef CG_UI_PUBLIC_H
#define CG_UI_PUBLIC_H

/* Optional paired engine/cgame extension; no pointers, floats or native longs
 * cross the QVM boundary. CG_INIT returns this magic only in supporting VMs. */
#define CG_UI_CAPABILITY 0x4f475531
#define CG_UI_VERSION 1
#define CG_UI_MAX_SCORES 64
#define CG_UI_NAME_BYTES 64
#define CG_UI_MAP_BYTES 64

typedef struct {
	int client, team, score, ping, time;
	char name[CG_UI_NAME_BYTES];
} cg_ui_score_t;

typedef struct {
	int version, size, valid;
	int health, armor, ammo, weapon, weapons, team, score;
	int time, elapsed, pmType, intermission, scoresShowing, localClient;
	int gametype, teamScores[2], fraglimit, timelimit;
	int scoreCount;
	char mapName[CG_UI_MAP_BYTES];
	cg_ui_score_t scores[CG_UI_MAX_SCORES];
} cg_ui_snapshot_t;

/* Browser field IDs. Time/elapsed are milliseconds; scoreboard time and
 * timelimit are the game's original minutes. Ammo -1 retains infinite ammo.
 * Snapshot values come from cgame display state, never the test observer. */
enum {
	CG_UI_HEALTH, CG_UI_ARMOR, CG_UI_AMMO, CG_UI_WEAPON, CG_UI_WEAPONS,
	CG_UI_TEAM, CG_UI_SCORE, CG_UI_TIME, CG_UI_ELAPSED, CG_UI_PM_TYPE,
	CG_UI_INTERMISSION, CG_UI_SCORES_SHOWING, CG_UI_LOCAL_CLIENT,
	CG_UI_GAMETYPE, CG_UI_TEAM_SCORE1, CG_UI_TEAM_SCORE2, CG_UI_FRAGLIMIT,
	CG_UI_TIMELIMIT, CG_UI_SCORE_COUNT,
	CG_UI_ROW_CLIENT, CG_UI_ROW_TEAM, CG_UI_ROW_SCORE, CG_UI_ROW_PING, CG_UI_ROW_TIME
};
enum { CG_UI_TEXT_MAP, CG_UI_TEXT_PLAYER };

#endif
