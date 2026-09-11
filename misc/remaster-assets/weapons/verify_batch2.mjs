// Actual browser input, hashes and ammo checks for generated SG/GL candidates.
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
const capture = async name => {
    await sleep(500);
    const image = await browser.send('Page.captureScreenshot', { format: 'jpeg', quality: 90 });
    writeFileSync(join(output, name + '.jpg'), Buffer.from(image.data, 'base64'));
};
try {
    const hashes = {};
    for (const name of ['zzz-shotgun.pk3', 'zzz-grenade.pk3', 'zzz-hands.pk3', 'zz-ioq3-vm.pk3']) {
        hashes[name] = await browser.evaluate(`(async () => {
            const bytes = engine.FS.readFile(${JSON.stringify('/demoq3/' + name)});
            return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
                b => b.toString(16).padStart(2, '0')).join('');
        })()`);
        assert.equal(hashes[name], createHash('sha256').update(readFileSync('build-weapon-batch2/demoq3/' + name)).digest('hex'));
    }
    await browser.command('r_hdr');
    results.push({ url: await browser.evaluate('location.href'), hashes,
        hdr: await browser.evaluate('testLogs.filter(s => s.includes("r_hdr")).slice(-3)') });
    await browser.command('give all');
    await browser.command('god');
    await browser.command('bind f +attack');
    for (const [weapon, name] of [[3, 'shotgun'], [4, 'grenade']]) {
        await browser.command('weapon ' + weapon);
        const before = await browser.waitFor(read, s => s.snap.ps.weapon === weapon && s.snap.ps.weaponTime === 0);
        await capture(name + '-idle');
        await browser.key('f', true);
        await sleep(60);
        await browser.key('f', false);
        await sleep(1300);
        const single = await read();
        assert.equal(single.snap.ps.ammo[weapon], before.snap.ps.ammo[weapon] - 1);
        assert.equal(single.snap.ps.weaponTime, 0);
        await browser.key('f', true);
        await browser.waitFor(read, s => s.snap.ps.ammo[weapon] === single.snap.ps.ammo[weapon] - 3);
        await browser.key('f', false);
        await sleep(1300);
        const held = await read();
        assert.equal(held.snap.ps.ammo[weapon], single.snap.ps.ammo[weapon] - 3);
        assert.equal(held.snap.ps.weaponTime, 0);
        await browser.command('weapon 2');
        await browser.waitFor(read, s => s.snap.ps.weapon === 2 && s.snap.ps.weaponTime === 0);
        await browser.command('weapon ' + weapon);
        const switched = await browser.waitFor(read, s => s.snap.ps.weapon === weapon && s.snap.ps.weaponTime === 0);
        assert.equal(switched.snap.ps.ammo[weapon], held.snap.ps.ammo[weapon]);
        await browser.command('cg_thirdPerson 1');
        await browser.command('cg_thirdPersonAngle 75');
        await browser.command('cg_thirdPersonRange 90');
        await capture(name + '-third');
        await browser.command('cg_thirdPerson 0');
        results.push({ name, before, single, held, switched });
    }
    writeFileSync(join(output, 'results.json'), JSON.stringify({ passed: true, results }, null, 2));
    console.log('PASS: actual SG/GL hashes, single 1 / held 3 shots, release stops, switch preserves ammo');
} finally {
    await browser.key('f', false);
    await browser.close();
}
