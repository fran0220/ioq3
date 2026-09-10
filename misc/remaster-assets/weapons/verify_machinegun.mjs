// Actual WASM regression and slow-time barrel inspection are separate phases.
import assert from 'node:assert/strict';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { connect, sleep } from '../../tests/gameplay/browser.mjs';

const [url, output] = process.argv.slice(2);
mkdirSync(output, { recursive: true });
const browser = await connect(url, join(output, 'inputs.jsonl'));
const read = () => browser.evaluate('readEngine()');
const results = [];
try {
    const hashes = {};
    for (const name of ['zzz-machinegun.pk3', 'zzz-hands.pk3', 'zzz-weapon.pk3', 'zzz-muzzle.pk3', 'zz-ioq3-vm.pk3']) {
        hashes[name] = await browser.evaluate(`(async () => {
            const bytes = engine.FS.readFile(${JSON.stringify('/demoq3/' + name)});
            return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
                b => b.toString(16).padStart(2, '0')).join('');
        })()`);
        assert.equal(hashes[name], createHash('sha256').update(readFileSync('build-machinegun-review/demoq3/' + name)).digest('hex'));
    }
    await browser.command('r_hdr');
    results.push({ url: await browser.evaluate('location.href'), hashes,
        hdr: await browser.evaluate('testLogs.filter(s => s.includes("r_hdr")).slice(-3)') });
    await browser.command('give all');
    await browser.command('weapon 2');
    await browser.command('bind f +attack');
    const before = await browser.waitFor(read, s => s.snap.ps.weapon === 2 && s.snap.ps.weaponTime === 0);
    await browser.key('f', true);
    await sleep(520);
    await browser.key('f', false);
    await sleep(200);
    const released = await read();
    const spent = before.snap.ps.ammo[2] - released.snap.ps.ammo[2];
    assert.ok(spent >= 3, 'held key must fire repeatedly at normal timescale');
    await sleep(1100);
    const settled = await read();
    assert.equal(settled.snap.ps.ammo[2], released.snap.ps.ammo[2]);
    assert.equal(settled.snap.ps.weaponTime, 0);
    await browser.command('weapon 5');
    await browser.waitFor(read, s => s.snap.ps.weapon === 5 && s.snap.ps.weaponTime === 0);
    await browser.command('weapon 2');
    const switched = await browser.waitFor(read, s => s.snap.ps.weapon === 2 && s.snap.ps.weaponTime === 0);
    assert.equal(switched.snap.ps.ammo[2], settled.snap.ps.ammo[2]);
    results.push({ test: 'normal-time-held-fire-release-and-switch', before, released, settled, switched, spent });
    // Slow time makes individual presentation poses inspectable, not a cadence test.
    await browser.command('timescale 0.1');
    await browser.key('f', true);
    for (let frame = 0; frame < 8; frame++) {
        await sleep(100);
        const shot = await browser.send('Page.captureScreenshot', { format: 'jpeg', quality: 90 });
        writeFileSync(join(output, `spin-${frame}.jpg`), Buffer.from(shot.data, 'base64'));
    }
    writeFileSync(join(output, 'results.json'), JSON.stringify({ passed: true, results }, null, 2));
    console.log(`PASS: WASM package hashes, held fire (${spent} bullets), release stops, switch preserves ammo`);
} finally {
    await browser.key('f', false);
    await browser.command('timescale 1');
    await browser.close();
}
