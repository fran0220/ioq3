// Real WASM camera inspection and keyboard lateral motion, not Bot acceptance.
import { mkdirSync, writeFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { connect, sleep } from '../../tests/gameplay/browser.mjs';

const [cdp, out, batch = 'lamps'] = process.argv.slice(2);
assert.ok(['lamps', 'reliefs', 'cw', 'statues'].includes(batch));
mkdirSync(out, { recursive: true });
const b = await connect(cdp, `${out}/journal.jsonl`);
const cameras = batch === 'statues' ? [
    ['statue-w', 650, 2088, 145, 180], ['statue-e', 700, 2088, 145, 0],
    ['statue-w-oblique', 520, 1880, 145, 130], ['statue-e-oblique', 830, 1880, 145, 50],
] : batch === 'reliefs' ? [
    ['relief-w', 620, 221, 80, 180], ['relief-e', 724, 221, 80, 0],
] : [
    ['floor-ne', 825, 1510, 40, 90], ['floor-nw', 521, 1510, 40, 90],
    ['floor-se', 1201, 630, 0, 270], ['floor-sw', 145, 630, 0, 270],
    ['wall-nw', 420, 1538, 90, 180], ['wall-ne', 924, 1536, 90, 0],
    ['wall-e', 1050, 1020, 76, 0], ['wall-w', 294, 1020, 76, 180],
    ['wall-diag-e', 740, 790, 35, 45], ['wall-diag-w', 604, 790, 35, 135],
];
if (batch === 'cw') cameras.push(['crest', 674, 1350, 286, 270],
    ['relief-w', 620, 221, 80, 180], ['relief-e', 724, 221, 80, 0]);
const results = [];
try {
    const base = await b.evaluate('location.origin');
    for (const hdr of [1, 0]) {
        await b.send('Page.navigate', { url: `${base}/?scene=1&hdr=${hdr}` });
        await sleep(500);
        await b.waitFor(() => b.evaluate('window.readEngine?.()'), s => s?.state === 8 && s.snap.valid, 60000);
        const bindings = await b.evaluate('testLogs.filter(x=>x.startsWith("Surface replacement q3dm1:"))');
        assert.equal(bindings.length, batch === 'statues' ? 42 : batch === 'lamps' ? 27 : 31);
        await b.evaluate('document.querySelector("canvas").focus()');
        for (const [name, x, y, z, yaw] of cameras) {
            await b.command(`setviewpos ${x} ${y} ${z} ${yaw}`);
            await sleep(500);
            const before = await b.evaluate('readEngine().snap.ps');
            b.record('settled-camera', { input: [x, y, z, yaw], observed: before });
            // g_misc.c adds forward velocity400 and Z+1. Noclip friction9
            // is frame-time dependent, so displacement is bounded, not fixed.
            // Preserve both earlier failed fixed-position journals.
            const angle = yaw * Math.PI / 180;
            const dx = before.origin[0] - x, dy = before.origin[1] - y;
            const forward = dx * Math.cos(angle) + dy * Math.sin(angle);
            assert.ok(forward >= 0 && forward <= 400 / 9);
            assert.ok(Math.abs(-dx * Math.sin(angle) + dy * Math.cos(angle)) < .1);
            assert.ok(Math.abs(before.origin[2] - z - 1) < .1);
            await b.screenshot(`${out}/${name}-hdr${hdr}.jpg`);
            await b.key('d', true);
            await sleep(300);
            await b.key('d', false);
            await sleep(300);
            const after = await b.evaluate('readEngine().snap.ps');
            assert.ok(Math.hypot(...before.origin.map((n, i) => n - after.origin[i])) > 10);
            assert.equal(await b.evaluate('document.querySelector("canvas").getContext("webgl2").isContextLost()'), false);
            await b.screenshot(`${out}/${name}-hdr${hdr}-moved.jpg`);
            results.push({ name, hdr, before, after, contextLost: false });
            console.log('PASS', name, 'hdr', hdr);
        }
    }
} finally {
    writeFileSync(`${out}/results.json`, JSON.stringify({ results, artAccepted: false,
        note: 'Noclip camera plus actual lateral keyboard input, not collision/AAS/Bot regression' }, null, 2));
    await b.close();
}
