// SPDX-License-Identifier: GPL-2.0-or-later
// Presentation only: time, inventory, phase and scores always come from cgame.
export const weaponNames = ['Unarmed', 'Gauntlet', 'Machinegun', 'Shotgun', 'Grenade launcher',
    'Rocket launcher', 'Lightning gun', 'Railgun', 'Plasma gun', 'BFG', 'Grappling hook',
    'Nailgun', 'Proximity launcher', 'Chaingun'];
export const teamNames = ['FFA', '▲ RED', '■ BLUE', 'SPECTATOR'];
export const modeNames = ['Free for all', 'Tournament', 'Single player', 'Team deathmatch', 'Capture the flag'];

// IDs mirror cg_ui_public.h v1. Refresh performs exactly one bounded VM copy;
// subsequent reads use the CL-owned cache, never cgame globals or an observer.
export function readHUD(module) {
    if (module?._OG_WebHUDRefresh?.() !== 1) return null;
    const read = (field, row = 0) => module._OG_WebHUD(field, row);
    const text = (kind, row = 0) => {
        let value = '';
        for (let i = 0; i < 64; i++) {
            const byte = module._OG_WebHUDText(kind, row, i);
            if (byte <= 0) break;
            value += String.fromCharCode(byte);
        }
        return value;
    };
    return {
        health: read(0), armor: read(1), ammo: read(2), weapon: read(3), weapons: read(4),
        team: read(5), score: read(6), time: read(7), elapsed: read(8), pmType: read(9),
        intermission: read(10), scoresShowing: read(11), localClient: read(12), gametype: read(13),
        redScore: read(14), blueScore: read(15), fraglimit: read(16), timelimit: read(17), map: text(0),
        rows: Array.from({ length: Math.max(0, Math.min(64, read(18))) }, (_, row) => ({
            client: read(19, row), team: read(20, row), score: read(21, row), ping: read(22, row),
            time: read(23, row), name: text(1, row),
        })),
    };
}

export function matchClock(milliseconds) {
    const seconds = Math.max(0, Math.floor(milliseconds / 1000));
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}

// Quake color escapes are styling, never HTML. Keep player supplied content text-only.
export function playerText(value) {
    return value.replace(/\^[^^]/g, '').replace(/[\x00-\x1f\x7f]/g, '');
}

export function createHUD(root) {
    const nodes = Object.fromEntries([...root.querySelectorAll('[data-hud]')].map(node => [node.dataset.hud, node]));
    let lastRows = '';
    const set = (key, value) => {
        const text = String(value);
        if (nodes[key].textContent !== text) nodes[key].textContent = text;
    };
    return {
        hide() { root.hidden = true; },
        render(s, menuOpen) {
            root.hidden = menuOpen || !s;
            if (!s) return;
            root.dataset.phase = s.intermission ? 'intermission' : s.team === 3 ? 'spectator' : s.health <= 0 ? 'dead' : 'active';
            root.dataset.team = s.team;
            root.dataset.lowHealth = String(s.health > 0 && s.health <= 25);
            set('health', Math.max(0, s.health));
            set('armor', s.armor);
            set('ammo', s.ammo < 0 ? '∞' : s.ammo);
            set('weapon', weaponNames[s.weapon] ?? 'Unknown weapon');
            set('team', teamNames[s.team] ?? '');
            set('score', s.score);
            set('clock', matchClock(s.elapsed));
            set('mode', modeNames[s.gametype] ?? 'Arena');
            set('map', playerText(s.map));
            set('red', s.redScore);
            set('blue', s.blueScore);
            nodes.teams.hidden = s.gametype < 3;
            set('phase', s.intermission ? 'MATCH COMPLETE' : s.team === 3 ? 'SPECTATING' : s.health <= 0 ? 'FRAGGED' : '');
            set('phaseNote', s.intermission ? 'The server controls the next round. F10 opens match actions.'
                : s.team === 3 ? 'Follow players with Fire. F10 opens team selection.'
                    : s.health <= 0 ? 'Press Fire to respawn when the server allows it. F10 opens match actions.' : '');
            nodes.phasePanel.hidden = !s.intermission && s.team !== 3 && s.health > 0;
            nodes.vitals.hidden = !!s.intermission || s.team === 3 || s.health <= 0;
            nodes.scoreboard.hidden = !s.scoresShowing && !s.intermission && s.health > 0;
            set('boardTitle', s.intermission ? 'FINAL STANDINGS' : 'SCOREBOARD');
            // Do not recreate rows every frame: text updates must not churn the accessibility tree.
            const rows = JSON.stringify([s.localClient, s.rows]);
            if (rows !== lastRows) {
                lastRows = rows;
                nodes.rows.replaceChildren();
                for (const score of s.rows) {
                    const row = document.createElement('tr');
                    row.dataset.local = String(score.client === s.localClient);
                    row.dataset.team = score.team;
                    for (const value of [playerText(score.name) + (score.client === s.localClient ? ' · YOU' : ''),
                        teamNames[score.team] ?? '', score.score, score.ping < 0 ? 'Connecting' : score.ping, score.time]) {
                        const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
                    }
                    nodes.rows.append(row);
                }
            }
            nodes.empty.hidden = s.rows.length > 0;
        },
    };
}
