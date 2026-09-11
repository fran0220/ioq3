import test from 'node:test';
import assert from 'node:assert/strict';
import { createLifecycle } from './lifecycle.mjs';

function fixture(native = { getSession: async id => ({ token: `private-${id}` }) }) {
    const frames = [], events = [];
    const lifecycle = createLifecycle({ native, sleep: async () => {}, report: e => events.push(e),
        mount: async boot => {
            const frame = { boot, removed: false, async remove() { this.removed = true; } };
            frames.push(frame); return frame;
        } });
    return { lifecycle, frames, events };
}

test('fresh engines destroy predecessors; offline never admits; stale status ignored', async () => {
    let calls = 0;
    const f = fixture({ getSession: async () => { calls++; return { token: 'private' }; } });
    await f.lifecycle.replace();
    assert.equal(await f.frames[0].boot.getSession(), null);
    assert.equal(calls, 0);
    await f.lifecycle.replace('A');
    assert.equal(f.frames[0].removed, true);
    const count = f.events.length;
    f.frames[0].boot.report({ state: 'ready', network: 'ready' });
    assert.equal(f.events.length, count);
    const session = await f.frames[1].boot.getSession();
    assert.equal(session.token, 'private');
    assert(!f.events.some(e => e.network === 'connected'));
    f.frames[1].boot.report({ network: 'ready', token: 'private' });
    assert.deepEqual(f.events.at(-1), { network: 'connected' });
    await assert.rejects(f.frames[1].boot.getSession(), /already/);
    await f.lifecycle.stop();
    assert.equal(f.frames[1].removed, true);
    assert(!JSON.stringify(f.events).includes('private'));
});

test('late admission discarded and serialized before replacement request', async () => {
    let resolve, calls = 0;
    const f = fixture({ getSession: () => { calls++; return new Promise(r => { resolve = r; }); } });
    await f.lifecycle.replace('A');
    const old = f.frames[0].boot.getSession();
    const rejected = assert.rejects(old, /replaced/);
    await Promise.resolve();
    await f.lifecycle.replace('B');
    const next = f.frames[1].boot.getSession();
    assert.equal(calls, 1);
    resolve({ token: 'old' });
    await rejected;
    await Promise.resolve();
    assert.equal(calls, 2);
    resolve({ token: 'new' });
    assert.deepEqual(await next, { token: 'new' });
});

test('only explicit attached-transport rejection retries, never ambiguous failures', async () => {
    for (const message of ['timeout secret', 'native release changed; reload game', 'close active transport before replacing session']) {
        let calls = 0;
        const f = fixture({ getSession: async () => { calls++; throw Error(message); } });
        await f.lifecycle.replace('A');
        await assert.rejects(f.frames[0].boot.getSession(), /Session unavailable/);
        assert.equal(calls, message.startsWith('close active') ? 4 : 1);
    }
});

test('new child cannot mount before old document destruction completes', async () => {
    let finish;
    const f = fixture();
    await f.lifecycle.replace('A');
    f.frames[0].remove = () => new Promise(r => { finish = r; });
    const next = f.lifecycle.replace('B');
    await Promise.resolve();
    assert.equal(f.frames.length, 1);
    await assert.rejects(f.lifecycle.replace('C'), /transition/);
    finish();
    await next;
    assert.equal(f.frames.length, 2);
});
