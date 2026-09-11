/* Compile the real shared prediction/server weapon state machine. No substitute
 * simulation: only engine logging is stubbed, and expected rates are independent.
 */
#include "../../../code/game/bg_pmove.c"
#include <assert.h>
#include <stdio.h>

void QDECL Com_Printf(const char *format, ...) {}
void QDECL Com_Error(int level, const char *format, ...) { abort(); }

int main(void) {
    const int weapons[] = {WP_GAUNTLET, WP_MACHINEGUN, WP_SHOTGUN,
        WP_GRENADE_LAUNCHER, WP_ROCKET_LAUNCHER, WP_LIGHTNING,
        WP_RAILGUN, WP_PLASMAGUN, WP_BFG};
    const int normal[] = {400,100,1000,800,800,50,1500,100,200};
    const int haste[] = {307,76,769,615,615,38,1153,76,153};
    int w, fast, ms;
    for (fast=0; fast<2; ++fast) for (w=0; w<9; ++w) {
        playerState_t state = {0};
        pmove_t move = {0};
        int weapon = weapons[w], interval = fast ? haste[w] : normal[w];
        move.ps = &state;
        move.cmd.weapon = state.weapon = weapon;
        move.cmd.buttons = BUTTON_ATTACK;
        move.gauntletHit = qtrue;
        state.stats[STAT_HEALTH] = 100;
        state.stats[STAT_WEAPONS] = 1 << weapon;
        state.ammo[weapon] = 7;
        state.weaponstate = WEAPON_READY;
        state.powerups[PW_HASTE] = fast;
        pm = &move;
        memset(&pml, 0, sizeof(pml));
        PM_Weapon();
        assert(state.ammo[weapon] == 6 && state.eventSequence == 1);
        assert(state.weaponTime == interval);
        assert(state.events[0] == EV_FIRE_WEAPON);
        pml.msec = 1;
        for (ms=1; ms<interval; ++ms) {
            PM_Weapon();
            assert(state.ammo[weapon] == 6 && state.eventSequence == 1);
        }
        PM_Weapon();
        assert(state.ammo[weapon] == 5 && state.eventSequence == 2);
        assert(state.weaponTime == interval);
        move.cmd.buttons = 0;
        for (ms=0; ms<interval+20; ++ms) PM_Weapon();
        assert(state.ammo[weapon] == 5 && state.eventSequence == 2);
        assert(state.weaponTime == 0 && state.weaponstate == WEAPON_READY);
        state.ammo[weapon] = 0;
        move.cmd.buttons = BUTTON_ATTACK;
        PM_Weapon();
        assert(state.ammo[weapon] == 0 && state.weaponTime == 500);
        assert(state.events[2 & (MAX_PS_EVENTS-1)] == EV_NOAMMO);
    }
    {
        playerState_t state = {0};
        pmove_t move = {0};
        move.ps = &state;
        pm = &move;
        pml.msec = 0;
        state.stats[STAT_HEALTH] = 100;
        state.stats[STAT_WEAPONS] = (1<<WP_GAUNTLET)|(1<<WP_SHOTGUN);
        state.weapon = move.cmd.weapon = WP_GAUNTLET;
        state.ammo[WP_GAUNTLET] = -1;
        state.ammo[WP_SHOTGUN] = 3;
        move.cmd.buttons = BUTTON_ATTACK;
        PM_Weapon();
        assert(state.eventSequence == 0); /* no gauntlet contact */
        move.gauntletHit = qtrue;
        PM_Weapon();
        assert(state.ammo[WP_GAUNTLET] == -1 && state.eventSequence == 1);
        state.weaponTime = 0;
        state.weaponstate = WEAPON_READY;
        move.cmd.weapon = WP_SHOTGUN;
        PM_Weapon();
        assert(state.weapon == WP_GAUNTLET && state.weaponTime == 200);
        assert(state.weaponstate == WEAPON_DROPPING);
        pml.msec = 199;
        PM_Weapon();
        assert(state.weapon == WP_GAUNTLET && state.weaponTime == 1);
        pml.msec = 1;
        PM_Weapon();
        assert(state.weapon == WP_SHOTGUN && state.weaponTime == 250);
        assert(state.weaponstate == WEAPON_RAISING);
        pml.msec = 249;
        PM_Weapon();
        assert(state.weaponstate == WEAPON_RAISING && state.ammo[WP_SHOTGUN] == 3);
        pml.msec = 1;
        PM_Weapon();
        assert(state.weaponstate == WEAPON_READY && state.ammo[WP_SHOTGUN] == 3);
        PM_Weapon();
        assert(state.ammo[WP_SHOTGUN] == 2 && state.weaponTime == 1000);
    }
    puts("PASS: actual PM_Weapon nine rates/haste/boundaries/release/no-ammo, melee contact, 200+250ms switch");
    return 0;
}
