import test from 'node:test';
import assert from 'node:assert/strict';
import { createDisplayPreview, displayArguments } from './display.mjs';

function fixture({ replace, confirm = async () => {} } = {}) {
    const calls = [], timers = new Map(), reports = [];
    let id = 0;
    const controller = createDisplayPreview({
        replace: async p => { calls.push(p); await replace?.(p); }, confirm,
        report: r => reports.push(r), schedule: (fn, ms) => { timers.set(++id, { fn, ms }); return id; },
        cancel: id => timers.delete(id),
    });
    return { controller, calls, timers, reports };
}

test('fixed display presets have distinct resolution and picmip; commands are rejected', () => {
    assert.deepEqual(displayArguments('balanced'), ['+set', 'r_picmip', '1', '+set', 'r_mode', '-1',
        '+set', 'r_customwidth', '1280', '+set', 'r_customheight', '720']);
    assert.deepEqual(displayArguments('high'), ['+set', 'r_picmip', '0', '+set', 'r_mode', '-1',
        '+set', 'r_customwidth', '1920', '+set', 'r_customheight', '1080']);
    assert.deepEqual(displayArguments(null), []);
    for (const value of ['constructor', '+quit', 'high;quit', {}, undefined]) assert.throws(() => displayArguments(value));
});

test('15-second confirmation starts only on actual ready; timeout restores saved settings', async () => {
    const f = fixture();
    await f.controller.preview('high');
    assert.equal(f.timers.values().next().value.ms, 120000);
    assert.equal(await f.controller.accept(), false);
    f.controller.ready();
    assert.equal(f.timers.size, 1);
    assert.equal(f.timers.values().next().value.ms, 15000);
    f.timers.values().next().value.fn();
    await f.controller.rollback();
    await new Promise(r => setImmediate(r));
    assert.deepEqual(f.calls, ['high', null]);
    assert.equal(f.controller.state, 'idle');
});

test('cancel during mount waits for destruction boundary; stale ready cannot confirm', async () => {
    let finish;
    const f = fixture({ replace: p => p && new Promise(r => { finish = r; }) });
    const starting = f.controller.preview('balanced');
    const reverting = f.controller.rollback();
    f.controller.ready();
    assert.equal(await f.controller.accept(), false);
    assert.deepEqual(f.calls, ['balanced']);
    finish(); await starting; await reverting;
    assert.deepEqual(f.calls, ['balanced', null]);
});

test('confirmation persists once; save failure rolls back; abandonment ignores late completion', async () => {
    for (const failure of [false, true]) {
        let saves = 0;
        const f = fixture({ confirm: async () => { saves++; if (failure) throw Error('quota'); } });
        await f.controller.preview('high'); f.controller.ready();
        assert.equal(await f.controller.accept(), !failure);
        assert.equal(await f.controller.accept(), false);
        assert.equal(saves, 1); assert.equal(f.timers.size, 0);
        assert.deepEqual(f.calls, failure ? ['high', null] : ['high']);
    }
    let finish;
    const f = fixture({ confirm: () => new Promise(r => { finish = r; }) });
    await f.controller.preview('native'); f.controller.ready();
    const pending = f.controller.accept();
    f.controller.abandon(); const count = f.reports.length;
    finish(); assert.equal(await pending, false);
    assert.equal(f.reports.length, count);
});
