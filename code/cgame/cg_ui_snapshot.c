/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "cg_local.h"
#include "cg_ui_public.h"

/* A production display snapshot, owned entirely by this VM. The engine copies
 * the returned VM offset after checking capability, version and memory bounds.
 * Never expose cg/cgs pointers or mutate prediction/game rules from this API. */
const cg_ui_snapshot_t *CG_UISnapshot( int version, int size ) {
	static cg_ui_snapshot_t result;
	const playerState_t *ps;
	int i, client;

	if ( version != CG_UI_VERSION || size != sizeof( result ) ) {
		return NULL;
	}
	memset( &result, 0, sizeof( result ) );
	result.version = CG_UI_VERSION;
	result.size = sizeof( result );
	if ( !cg.snap || cg.loading || cg.levelShot || !cg_draw2D.integer ) {
		return &result;
	}
	ps = &cg.snap->ps;
	result.valid = 1;
	result.health = ps->stats[STAT_HEALTH];
	result.armor = ps->stats[STAT_ARMOR];
	result.weapon = cg.predictedPlayerState.weapon;
	if ( result.weapon >= 0 && result.weapon < MAX_WEAPONS ) {
		result.ammo = ps->ammo[result.weapon];
	}
	result.weapons = ps->stats[STAT_WEAPONS];
	result.team = ps->persistant[PERS_TEAM];
	result.score = ps->persistant[PERS_SCORE];
	result.time = cg.time;
	result.elapsed = cg.time - cgs.levelStartTime;
	result.pmType = ps->pm_type;
	result.intermission = ps->pm_type == PM_INTERMISSION;
	result.scoresShowing = cg.showScores || cg.scoreBoardShowing;
	result.localClient = cg.clientNum;
	result.gametype = cgs.gametype;
	result.teamScores[0] = cg.teamScores[0];
	result.teamScores[1] = cg.teamScores[1];
	result.fraglimit = cgs.gametype >= GT_CTF ? cgs.capturelimit : cgs.fraglimit;
	result.timelimit = cgs.timelimit;
	Q_strncpyz( result.mapName, cgs.mapname, sizeof( result.mapName ) );
	for ( i = 0; i < cg.numScores && result.scoreCount < CG_UI_MAX_SCORES; i++ ) {
		cg_ui_score_t *row;
		client = cg.scores[i].client;
		if ( client < 0 || client >= MAX_CLIENTS ) {
			continue;
		}
		row = &result.scores[result.scoreCount++];
		row->client = client;
		row->team = cgs.clientinfo[client].team;
		row->score = cg.scores[i].score;
		row->ping = cg.scores[i].ping;
		row->time = cg.scores[i].time;
		Q_strncpyz( row->name, cgs.clientinfo[client].name, sizeof( row->name ) );
	}
	return &result;
}
