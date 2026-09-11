/* Actual G_Damage/CheckArmor, nonfatal FFA cases. Unused scoring/death code is
 * linker-discarded. CTF callbacks are forbidden, not silently simulated. */
#include "../../../code/game/g_combat.c"
#include <assert.h>
#include <stdio.h>

level_locals_t level;
gentity_t g_entities[MAX_GENTITIES];
vmCvar_t g_knockback, g_friendlyFire, g_debugDamage, g_gametype;

void QDECL G_Printf(const char *format, ...) {}
void Team_CheckHurtCarrier(gentity_t *targ, gentity_t *attacker) { abort(); }
void G_AddEvent(gentity_t *ent, int event, int parm) {
    assert(event == EV_POWERUP_BATTLESUIT);
}

int main(void) {
    int mode;
    g_knockback.value = 1000;
    g_gametype.integer = GT_FFA;
    for (mode=0; mode<5; ++mode) {
        gclient_t client = {0}, other = {0};
        gentity_t target = {0}, attacker = {0};
        vec3_t dir = {3,0,4};
        target.client = &client;
        target.takedamage = qtrue;
        target.health = 200;
        target.s.eType = ET_PLAYER;
        attacker.client = &other;
        other.ps.stats[STAT_MAX_HEALTH] = 100;
        if (mode == 2) client.ps.stats[STAT_ARMOR] = 50;
        if (mode == 4) client.ps.powerups[PW_BATTLESUIT] = 1;
        G_Damage(&target, &target, mode==0 ? &attacker : &target,
                 dir, NULL, 100, mode==3 ? DAMAGE_NO_KNOCKBACK : DAMAGE_RADIUS, MOD_ROCKET_SPLASH);
        /* Q3 armor is .66, not exact 2/3: 50 self damage saves 33, takes 17. */
        assert(target.health == (mode==0 ? 100 : mode==2 ? 183 : mode==4 ? 200 : 150));
        assert(client.ps.stats[STAT_ARMOR] == (mode==2 ? 17 : 0));
        assert(fabsf(client.ps.velocity[0] - (mode==3 ? 0 : 300)) < .001f);
        assert(client.ps.velocity[1] == 0);
        assert(fabsf(client.ps.velocity[2] - (mode==3 ? 0 : 400)) < .001f);
        assert(client.ps.pm_time == (mode==3 ? 0 : 200));
        if (mode==0) assert(other.ps.persistant[PERS_HITS] == 1);
    }
    puts("PASS: actual G_Damage self-half after full knockback, asymmetric impulse, armor, battlesuit, no-knockback");
    return 0;
}
