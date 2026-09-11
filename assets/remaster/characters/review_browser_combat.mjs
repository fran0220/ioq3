// Actual WASM console/input review; no engine state writes or fake snapshots.
// Usage: node review_browser_combat.mjs CDP_URL OUTPUT_DIRECTORY
import assert from 'node:assert/strict';
import { mkdirSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { connect, sleep } from '../../../misc/tests/gameplay/browser.mjs';

const [cdp, directory] = process.argv.slice(2);
if (!directory) throw new Error('Usage: CDP_URL OUTPUT_DIRECTORY');
const output = resolve(directory);
mkdirSync(output, { recursive: true });
const b = await connect(cdp, join(output, 'character-combat.jsonl'));
try {
    const read = () => b.evaluate('readEngine()');
    await b.command('devmap q3dm1');
    await b.waitFor(read, s => s.state === 8 && s.snap.valid);
    await b.command('fraglimit 0; com_blood 0; bot_minplayers 0; cg_debugAnim 1; cg_deferPlayers 0; model sarge; headmodel sarge; cg_draw2D 0; cg_thirdPerson 1');
    for (const [number, animation] of [0, 2, 4].entries()) {
        await b.command('give weapons; give ammo; give health');
        await sleep(600);
        await b.command('weapon 5; setviewpos 600 1250 24 0; +lookdown');
        await b.waitFor(read, s => s.snap.ps.weapon === 5);
        await sleep(1200);
        const first = await b.evaluate('testLogs.length');
        await b.command('-lookdown; +attack');
        await b.waitFor(read, s => s.snap.ps.pm_type === 3, 20000);
        await b.command('-attack');
        const logs = await b.evaluate(`testLogs.slice(${first})`);
        assert.ok(logs.some(line => line.includes('blew himself up.')));
        assert.ok(logs.some(line => line.includes('Anim: ' + animation)), `Missing actual death ${animation}`);
        await sleep(1700);
        for (const angle of [0, 90, 180, 270]) {
            await b.command(`cg_thirdPersonRange 140; cg_thirdPersonAngle ${angle}`);
            await sleep(200);
            assert.equal((await read()).snap.ps.pm_type, 3, 'Corpse review must remain dead');
            await b.screenshot(join(output, `death-${number + 1}-orbit-${angle}.png`));
        }
        await b.command('+attack');
        await b.waitFor(read, s => s.snap.ps.pm_type === 0);
        await b.command('-attack');
        await b.screenshot(join(output, `respawn-${number + 1}.png`));
        console.log(`PASS real WASM death ${animation}, four corpse views, live respawn`);
    }
} finally {
    b.close();
}
