// Private fixture inspection: camera commands are not gameplay regression input.
import { mkdirSync, writeFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { connect, sleep } from '../../tests/gameplay/browser.mjs';

const [cdp, out] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const b = await connect(cdp, `${out}/comparison.jsonl`);
const results = [];
try {
    const base = await b.evaluate('location.origin');
    for (const hdr of [0, 1]) {
        for (const lighting of ['v1', 'v2']) {
            await b.send('Page.navigate', { url: `${base}/?lighting=${lighting}&hdr=${hdr}` });
            await sleep(500);
            await b.waitFor(() => b.evaluate('window.readEngine?.()'),
                s => s?.state === 8 && s.snap.valid && Math.abs(s.snap.ps.origin[0] - 674) < 1, 45000);
            await sleep(1800);
            const snapshot = await b.evaluate('readEngine()');
            const ps = snapshot.snap.ps;
            assert.ok(Math.abs(ps.origin[1] - 1334.5) < 1);
            assert.ok(Math.abs(ps.origin[2] - 287) < 1);
            assert.ok(Math.abs(ps.viewangles[1] + 90) < .1);
            const logs = await b.evaluate('testLogs');
            assert.ok(logs.some(s => s.includes('Surface replacement q3dm1:2050 -> models/remaster/environment_wall_crest.md3')));
            assert.equal(await b.evaluate('document.querySelector("canvas").getContext("webgl2").isContextLost()'), false);
            const name = `${lighting}-hdr${hdr}`;
            b.record('snapshot', { name, value: snapshot });
            await b.screenshot(`${out}/${name}.jpg`);
            results.push({ name, origin: ps.origin, angles: ps.viewangles, binding: true, contextLost: false });
            console.log('PASS', name, JSON.stringify(ps.origin));
        }
    }
    writeFileSync(`${out}/results.json`, JSON.stringify({
        results, artAccepted: false, note: 'Inspect captures separately; startup noclip/setviewpos is a visual fixture, not a gameplay test',
    }, null, 2));
} finally { await b.close(); }
