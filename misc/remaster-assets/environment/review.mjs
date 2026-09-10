// Real input walkthrough; no teleport, testmodel, or snapshot writes.
import { mkdirSync, writeFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { connect, sleep } from '../../tests/gameplay/browser.mjs';
const [cdp, out] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const b = await connect(cdp, `${out}/walk.jsonl`);
const read = () => b.evaluate('window.readEngine?.()');
const hold = async (key, ms) => {
    await b.key(key, true);
    try { await sleep(ms); } finally { await b.key(key, false); }
};
const capture = async name => {
    const snapshot = await read();
    b.record('snapshot', { name, value: snapshot });
    await b.screenshot(`${out}/${name}.jpg`);
    return snapshot.snap.ps;
};
const aim = async yaw => {
    for (let i = 0; i < 15; i++) {
        const ps = (await read()).snap.ps;
        const delta = ((yaw - ps.viewangles[1] + 540) % 360) - 180;
        if (Math.abs(delta) < 3) return;
        await hold(delta > 0 ? 'ArrowLeft' : 'ArrowRight', Math.min(300, Math.abs(delta) / 140 * 1000));
        await sleep(120);
    }
    throw new Error('Keyboard yaw failed');
};
try {
    await b.send('Page.reload', { ignoreCache: true });
    await b.waitFor(read, s => s?.state === 8 && s.snap.valid, 45000);
    await b.evaluate('document.querySelector("canvas").focus()');
    const start = await capture('01-courtyard-spawn');
    await aim(-90);
    await b.key('w', true);
    let picked;
    try { picked = await b.waitFor(read, s => s.snap.ps.stats.armor > start.stats.armor, 4000); }
    finally { await b.key('w', false); }
    assert.ok(picked.snap.ps.origin[1] < start.origin[1] - 100);
    await sleep(250);
    await capture('02-courtyard-shards');
    await b.key('Space', true);
    try { await b.waitFor(read, s => s.snap.ps.velocity[2] > 30 && s.snap.ps.groundEntityNum === 1023); }
    finally { await b.key('Space', false); }
    await b.waitFor(read, s => s.snap.ps.groundEntityNum !== 1023);
    await aim(-135);
    await hold('w', 950);
    await capture('03-central-approach');
    await aim(0);
    await capture('04-reverse-sightline');
    await aim(-90);
    await hold('w', 1300);
    await capture('05-arch-passage');
    const logs = await b.evaluate('testLogs');
    assert.ok(logs.some(x => x.includes('zzzz-environment-private-maps.pk3')));
    assert.ok(!logs.some(x => /WARNING.*remaster_environment/.test(x)));
    writeFileSync(`${out}/result.json`, JSON.stringify({ passed: true,
        checks: ['live WASM', 'keyboard turn', 'movement >100 units', 'armor pickup',
            'jump airborne', 'land', 'five motion-linked viewpoints', 'runtime packages loaded'],
        limits: ['not full navigation coverage', 'not final geometry', 'software GPU'] }, null, 2));
    console.log('PASS environment walk: movement, armor pickup, jump/land, five viewpoints');
} finally { await b.close(); }
