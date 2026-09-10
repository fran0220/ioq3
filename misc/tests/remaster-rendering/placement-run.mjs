// Private fixed-camera placement review, not an input/gameplay test.
// The review host starts a real devmap and uses activeAction/setviewpos/noclip.
import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { connect, sleep } from '../gameplay/browser.mjs';

const [cdp, baseURL, outputArg] = process.argv.slice(2);
if (!outputArg) throw Error('Usage: node placement-run.mjs CDP PRIVATE_HOST_URL OUTPUT');
const output = resolve(outputArg);
mkdirSync(output, { recursive: true });
const b = await connect(cdp, join(output, 'placement.jsonl'));
const results = [];
try {
    for (const [name, query, registered, rejected] of [
        ['placed-hdr', '', true, false],
        ['placed-ldr', '?hdr=0', true, false],
        ['original-no-binding', '?noReplacement', false, false],
        ['original-missing-model', '?missingModel', false, true],
        ['original-entities-disabled', '?noEntities', true, false],
        ['placed-far', '?far', true, false],
    ]) {
        await b.send('Page.navigate', { url: baseURL + query });
        await sleep(350);
        await b.waitFor(() => b.evaluate('window.readEngine?.()?.snap?.ps?.origin'),
            p => p && Math.abs(p[0] - 674) < 1, 45000);
        await sleep(1500);
        const state = await b.evaluate(`({snapshot:readEngine(),
            bindings:testLogs.map(s=>s.replace(/\\^[0-9]/g,'')).filter(s=>/Surface replacement|Rejected .*replacement/.test(s)),
            contextLost:!!window.testContextLost,
            glError:document.querySelector('canvas').getContext('webgl2').getError()})`);
        assert.equal(state.contextLost, false);
        assert.equal(state.glError, 0);
        assert.equal(state.bindings.some(s => s.startsWith('Surface replacement q3dm1:2050')), registered);
        assert.equal(state.bindings.some(s => s.startsWith('Rejected ')), rejected);
        assert.ok(Math.abs(state.snapshot.snap.ps.viewangles[1] + 90) < 1);
        await b.screenshot(join(output, name + '.jpg'));
        b.record('placement-state', { name, ...state });
        results.push({ name, bindings: state.bindings, contextLost: false, glError: 0,
            origin: state.snapshot.snap.ps.origin, viewangles: state.snapshot.snap.ps.viewangles });
        console.log('PASS render/registration state:', name, '(visual inspection still required)');
    }
} finally {
    writeFileSync(join(output, 'results.json'), JSON.stringify(results, null, 2));
    await b.close();
}
