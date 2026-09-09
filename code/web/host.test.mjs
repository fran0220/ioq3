// SPDX-License-Identifier: GPL-2.0-or-later
import test from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { validateManifest, validateSession, engineArguments, fetchChecked, persistence, startHost } from './host.mjs';
globalThis.crypto ??= webcrypto;

const file = { path: 'baseq3/test.pk3', bytes: 3,
    sha256: 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad' }; // SHA256("abc")
const manifest = { schemaVersion: 1, basegame: 'baseq3', revision: 'test', files: [file] };
const session = { endpoint: 'wss://native.example/v1/native/socket', token: 'TEST-ONLY-SECRET',
    sessionId: 'test', expiresAt: '2999-01-01T00:00:00Z', maxDatagramBytes: 16384, reconnectGraceMs: 15000 };

test('manifest confines unique hashed assets to the basegame, never player storage', () => {
    assert.equal(validateManifest(manifest), manifest);
    for (const path of ['baseq3/../home/players/config', '/baseq3/test.pk3', 'https://other/file', 'baseq3/%2e/file', 'baseq3//x']) {
        assert.throws(() => validateManifest({ ...manifest, files: [{ ...file, path }] }));
    }
    assert.throws(() => validateManifest({ ...manifest, files: [file, file] }));
    assert.throws(() => validateManifest({ ...manifest, basegame: 'home' }));
    assert.throws(() => validateManifest({ ...manifest, files: [{ ...file, sha256: '' }] }));
});

test('asset bytes must match independent size and SHA256, including same-size corruption', async () => {
    const fetcher = text => async () => new Response(text);
    assert.deepEqual(await fetchChecked('https://test/asset', file, fetcher('abc')), new Uint8Array([97, 98, 99]));
    await assert.rejects(fetchChecked('https://test/asset', file, fetcher('abd')), /checksum/);
    await assert.rejects(fetchChecked('https://test/asset', file, fetcher('ab')), /size/);
    await assert.rejects(fetchChecked('https://test/asset', file, async () => new Response('', { status: 404 })), /Missing asset/);
});

test('sessions remain memory-only; offline never connects; session transport fields are constrained', () => {
    assert.equal(validateSession(null), null);
    assert(Object.isFrozen(validateSession(session)));
    assert.throws(() => validateSession({ ...session, endpoint: 'ws://native.example/socket' }));
    assert.throws(() => validateSession({ ...session, endpoint: `${session.endpoint}?token=secret` }));
    assert.throws(() => validateSession({ ...session, expiresAt: '2020-01-01' }));
    assert(!engineArguments('baseq3', null).includes('+connect'));
    const args = engineArguments('baseq3', session);
    assert.deepEqual(args.slice(-2), ['+connect', 'origingame']);
    assert(!args.join(' ').includes(session.token));
    assert(!args.join(' ').includes(session.endpoint));
});

test('IDBFS serializes dirty writes arriving during save; failed writes retry', async () => {
    const callbacks = [], statuses = [];
    const store = persistence({ syncfs: (populate, cb) => callbacks.push({ populate, cb }) }, s => statuses.push(s));
    store.changed();
    const pending = store.flush();
    store.changed();
    assert.equal(store.flush(), pending);
    assert.equal(callbacks.length, 1);
    callbacks.shift().cb();
    await Promise.resolve();
    assert.equal(callbacks.length, 1);
    callbacks.shift().cb(new Error('quota'));
    await assert.rejects(pending, /quota/);
    const retry = store.flush();
    assert.equal(callbacks[0].populate, false);
    callbacks.shift().cb();
    await retry;
    assert.equal(statuses.at(-1), 'saved');
    // Later writes must still schedule a save after an explicit flush cleared a timer.
    store.changed();
    await new Promise(r => setTimeout(r, 550));
    assert.equal(callbacks.length, 1);
    callbacks.shift().cb();
    await store.flush();
});

async function fixture({ files = [file], restoreError = false, getSession, abort = false } = {}) {
    const events = [], reports = [], writes = [], calls = [];
    let options;
    const module = {
        FS: { mkdirTree() {}, mount() {}, writeFile: (...a) => writes.push(a),
            syncfs: (populate, cb) => cb(restoreError && populate ? new Error('restore denied') : null) },
        IDBFS: {}, callMain: args => { calls.push(args); if (abort) options.onExit(3); },
        _OG_WebLoseFocus: () => events.push('blur'), _OG_WebResumeAudio: () => events.push('audio'),
    };
    const host = await startHost({
        factory: async o => { options = o; return module; }, manifestURL: new URL('https://test/game-manifest.json'),
        og: { loading: { begin: () => events.push('begin'), progress() {}, fail: e => events.push(e) },
            ready: () => events.push('ready') },
        getSession, report: r => reports.push(r),
        fetcher: async url => String(url).endsWith('.json') ? Response.json({ ...manifest, files }) : new Response('abc'),
    });
    return { host, module, options, events, reports, calls, writes };
}

test('runtime and assets do not ready; only functional engine frame does, once', async () => {
    const f = await fixture({ getSession: async () => session });
    assert.equal(f.calls.length, 1);
    assert(!f.events.includes('ready'));
    f.options.onEngineFrame({ playable: false, configChanged: false });
    assert(!f.events.includes('ready'));
    f.options.onEngineFrame({ playable: true, configChanged: true });
    f.options.onEngineFrame({ playable: true, configChanged: false });
    await f.host.flush();
    assert.equal(f.events.filter(e => e === 'ready').length, 1);
    assert.equal(f.module.ogNetwork.token, session.token);
    assert.throws(() => { f.module.ogNetwork = null; });
    assert(!JSON.stringify(f.writes).includes(session.token));
    f.host.loseFocus(); f.host.resumeAudio();
    assert(f.events.includes('blur') && f.events.includes('audio'));
});

test('missing assets, failed restore and aborted engine cannot send ready or continue main', async () => {
    for (const options of [{ files: [] }, { restoreError: true }, { abort: true }]) {
        const f = await fixture(options);
        f.options.onEngineFrame({ playable: true });
        assert(!f.events.includes('ready'));
        assert.equal(f.reports.at(-1).state, 'failed');
        assert.equal(f.calls.length, options.abort ? 1 : 0);
        assert.equal(f.events.filter(e => e?.retryable === true).length, 1);
    }
});

test('session acquisition error text cannot leak token to UI or OG telemetry', async () => {
    const f = await fixture({ getSession: async () => { throw new Error(session.token); } });
    assert.equal(f.calls.length, 0);
    assert(!JSON.stringify([f.reports, f.events]).includes(session.token));
});
