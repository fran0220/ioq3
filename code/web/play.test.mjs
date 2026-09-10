// SPDX-License-Identifier: GPL-2.0-or-later
import test from 'node:test';
import assert from 'node:assert/strict';
import { readCatalog, playError } from './play.mjs';

test('unavailable engine never supplies a demonstration catalogue', () => {
    assert.equal(readCatalog({}), null);
    assert.equal(readCatalog({ _OG_WebCatalogRefresh: () => 0 }), null);
});
test('catalogue keeps engine IDs, missing assets, mode masks and generation', () => {
    let calls = 0;
    const data = [
        [{ id: 7, mask: 9, available: 1, name: 'q3dm1', title: '^3Arena' }, { id: 23, mask: 16, available: 0, name: 'q3ctf1', title: 'Missing' }],
        [{ id: 12, mask: 0, available: 1, name: 'sarge', title: 'Sarge' }],
        [{ id: 4, mask: 0, available: 1, name: 'sarge/default', title: 'Sarge / default' }],
    ];
    const result = readCatalog({
        _OG_WebCatalogRefresh: () => { calls++; return 19; },
        _OG_WebCatalogCount: kind => data[kind].length,
        _OG_WebCatalogValue: (kind, index, field) => {
            const row = data[kind][index]; return [row.id, row.mask, row.available][field];
        },
        _OG_WebCatalogText: (kind, index, field, byte) => data[kind][index][field ? 'title' : 'name'].charCodeAt(byte) || 0,
    });
    assert.equal(calls, 1);
    assert.equal(result.generation, 19);
    assert.deepEqual(result.maps, [
        { id: 7, modes: 9, available: true, name: 'q3dm1', title: 'Arena' },
        { id: 23, modes: 16, available: false, name: 'q3ctf1', title: 'Missing' },
    ]);
    assert.equal(result.models[0].id, 4);
    assert.equal(result.bots[0].id, 12);
});
test('stale and missing assets failures are not described as successful launches', () => {
    assert.match(playError(-1), /changed/);
    assert.match(playError(-3), /missing/);
    assert.match(playError(0), /not ready/);
});
