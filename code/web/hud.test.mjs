// SPDX-License-Identifier: GPL-2.0-or-later
import test from 'node:test';
import assert from 'node:assert/strict';
import { readHUD, matchClock, playerText } from './hud.mjs';

test('clock uses engine milliseconds; minute boundaries do not round up', () => {
    assert.equal(matchClock(59999), '0:59');
    assert.equal(matchClock(60001), '1:00');
    assert.equal(matchClock(3723000), '62:03');
    assert.equal(matchClock(-1), '0:00');
});
test('text preserves markup literally and strips game styling/control characters', () => {
    assert.equal(playerText('^1<player>\u0007 ^2wins'), '<player> wins');
});
test('no valid production snapshot means no stale or demonstration values', () => {
    assert.equal(readHUD({}), null);
    assert.equal(readHUD({ _OG_WebHUDRefresh: () => 0, _OG_WebHUD: () => assert.fail('must not read stale cache') }), null);
});
test('snapshot refresh is atomic once, field IDs and row order match cgame v1', () => {
    let refreshes = 0;
    const values = [37, 91, -1, 1, 6, 2, -3, 123456, 114456, 0, 0, 1, 7, 4, 8, 9, 10, 12, 2];
    const rows = [[7, 2, -3, 47, 2], [4, 1, 9, 65, 3]];
    const result = readHUD({
        _OG_WebHUDRefresh: () => ++refreshes,
        _OG_WebHUD: (id, row) => id < 19 ? values[id] : rows[row][id - 19],
        _OG_WebHUDText: (kind, row, index) => (kind === 0 ? 'maps/q3dm1.bsp' : ['^4Player', 'Opponent'][row]).charCodeAt(index) || 0,
    });
    assert.equal(refreshes, 1);
    assert.equal(result.health, 37); assert.equal(result.armor, 91); assert.equal(result.ammo, -1);
    assert.equal(result.elapsed, 114456); assert.equal(result.gametype, 4); assert.equal(result.blueScore, 9);
    assert.deepEqual(result.rows, [
        { client: 7, team: 2, score: -3, ping: 47, time: 2, name: '^4Player' },
        { client: 4, team: 1, score: 9, ping: 65, time: 3, name: 'Opponent' },
    ]);
});
