// Focused actual-engine checks. Devmap/give set up inventory; CDP key events fire.
import assert from 'node:assert/strict';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { connect, sleep } from '../../tests/gameplay/browser.mjs';

const [url, output] = process.argv.slice(2);
mkdirSync(output, { recursive: true });
const browser = await connect(url, join(output, 'rocket-input.jsonl'));
const read = () => browser.evaluate('readEngine()');
const results = [];
try {
    const actualURL = await browser.evaluate('location.href');
    const hashes = {};
    for (const [vfs, disk] of [
        ['zzz-weapon.pk3', 'assets/remaster/runtime/weapon-rocket-v1-candidate.pk3'],
        ['zzz-hands.pk3', 'assets/remaster/runtime/weapon-hands-v1-candidate.pk3'],
        ['zzz-muzzle.pk3', 'assets/remaster/runtime/effect-rocket-muzzle-v1-candidate.pk3'],
        ['zz-ioq3-vm.pk3', 'build-weapon-review/demoq3/zz-ioq3-vm.pk3'],
    ]) {
        const actual = await browser.evaluate(`(async () => {
            const bytes = engine.FS.readFile(${JSON.stringify('/demoq3/' + vfs)});
            return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
                b => b.toString(16).padStart(2, '0')).join('');
        })()`);
        assert.equal(actual, createHash('sha256').update(readFileSync(disk)).digest('hex'), 'stale or wrong browser target: ' + vfs);
        hashes[vfs] = actual;
    }
    await browser.command('r_hdr');
    const hdrReport = await browser.evaluate('testLogs.filter(line => line.includes("r_hdr")).slice(-3)');
    results.push({ test: 'actual-browser-target-and-packages', actualURL, hashes, hdrReport });
    await browser.command('give all');
    await browser.command('weapon 5');
    await browser.command('bind f +attack');
    await browser.waitFor(read, state => state.snap.ps.weapon === 5 && state.snap.ps.weaponTime === 0);
    const before = await read();
    await browser.key('f', true);
    await sleep(70);
    await browser.key('f', false);
    const after = await browser.waitFor(read, state => state.snap.ps.ammo[5] < before.snap.ps.ammo[5]);
    assert.equal(after.snap.ps.ammo[5], before.snap.ps.ammo[5] - 1);
    await sleep(1100);
    const settled = await read();
    assert.equal(settled.snap.ps.ammo[5], after.snap.ps.ammo[5]);
    assert.equal(settled.snap.ps.weaponTime, 0);
    results.push({ test: 'single-real-key-fire-consumes-exactly-one-and-stops', before, after, settled });
    await browser.command('weapon 2');
    await browser.waitFor(read, state => state.snap.ps.weapon === 2 && state.snap.ps.weaponTime === 0);
    await browser.command('weapon 5');
    const switched = await browser.waitFor(read, state => state.snap.ps.weapon === 5 && state.snap.ps.weaponTime === 0);
    assert.equal(switched.snap.ps.ammo[5], settled.snap.ps.ammo[5]);
    results.push({ test: 'switch-away-and-back-preserves-ammo', switched });
    await browser.key('f', true);
    const held = await browser.waitFor(read, state => state.snap.ps.ammo[5] === switched.snap.ps.ammo[5] - 3);
    await browser.key('f', false);
    await sleep(1100);
    const released = await read();
    assert.equal(released.snap.ps.ammo[5], held.snap.ps.ammo[5]);
    assert.equal(released.snap.ps.weaponTime, 0);
    results.push({ test: 'held-fire-repeats-three-shots-and-release-stops', held, released });
    writeFileSync(join(output, 'rocket-results.json'), JSON.stringify({ passed: true, results }, null, 2));
    console.log('PASS: single-shot ammo, switch preservation, held-fire repetition/release (actual WASM)');
} finally {
    await browser.key('f', false);
    await browser.close();
}
