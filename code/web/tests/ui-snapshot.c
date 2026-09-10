/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Link the actual production snapshot source, not an observer implementation. */
#include "../../cgame/cg_local.h"
#include "../../cgame/cg_ui_public.h"
#include <assert.h>

cg_t cg;
cgs_t cgs;
vmCvar_t cg_draw2D;
const cg_ui_snapshot_t *CG_UISnapshot( int version, int size );

/* Only the engine's bounded string utility is stubbed in this isolated test. */
void Q_strncpyz( char *dest, const char *src, int size ) {
	strncpy( dest, src, size - 1 );
	dest[size - 1] = 0;
}

int main( void ) {
	snapshot_t snap;
	const cg_ui_snapshot_t *s;
	memset( &snap, 0, sizeof( snap ) );
	assert( !CG_UISnapshot( 2, sizeof( *s ) ) );
	assert( !CG_UISnapshot( 1, sizeof( *s ) - 1 ) );
	assert( !CG_UISnapshot( 1, sizeof( *s ) )->valid );
	cg.snap = &snap;
	cg_draw2D.integer = 1;
	cg.clientNum = 7;
	cg.time = 123456;
	cgs.levelStartTime = 9000;
	cgs.gametype = GT_CTF;
	cgs.fraglimit = 23;
	cgs.capturelimit = 8;
	cgs.scores1 = 4;
	cgs.scores2 = 7;
	cg.teamScores[0] = 1; /* Older scoreboard response must not stale the HUD. */
	cg.teamScores[1] = 2;
	snap.ps.stats[STAT_HEALTH] = 37;
	snap.ps.stats[STAT_ARMOR] = 91;
	snap.ps.stats[STAT_WEAPONS] = 6;
	snap.ps.persistant[PERS_TEAM] = TEAM_BLUE;
	snap.ps.persistant[PERS_SCORE] = -3;
	cg.predictedPlayerState.weapon = WP_GAUNTLET;
	snap.ps.ammo[WP_GAUNTLET] = -1;
	cg.numScores = 3;
	cg.scores[0].client = -1;
	cg.scores[1].client = 7;
	cg.scores[1].score = -3;
	cg.scores[1].ping = 47;
	cg.scores[1].time = 2;
	cg.scores[2].client = MAX_CLIENTS;
	cgs.clientinfo[7].team = TEAM_BLUE;
	strcpy( cgs.clientinfo[7].name, "^4Player <7>" );
	s = CG_UISnapshot( 1, sizeof( *s ) );
	assert( s->valid && s->version == 1 && s->size == sizeof( *s ) );
	assert( s->health == 37 && s->armor == 91 && s->ammo == -1 );
	assert( s->team == TEAM_BLUE && s->score == -3 && s->elapsed == 114456 );
	assert( s->fraglimit == 8 && s->scoreCount == 1 && s->scores[0].client == 7 );
	assert( s->teamScores[0] == 4 && s->teamScores[1] == 7 );
	assert( s->scores[0].ping == 47 && s->scores[0].time == 2 );
	assert( !strcmp( s->scores[0].name, "^4Player <7>" ) );
	cg.numScores = 0;
	snap.ps.pm_type = PM_INTERMISSION;
	s = CG_UISnapshot( 1, sizeof( *s ) );
	assert( s->intermission && !s->scoreCount && !s->scores[0].name[0] );
	cg.snap = NULL;
	s = CG_UISnapshot( 1, sizeof( *s ) );
	assert( !s->valid && !s->health && !s->intermission );
	puts( "production snapshot: boundaries, live values, score rows and stale reset PASS" );
	return 0;
}
