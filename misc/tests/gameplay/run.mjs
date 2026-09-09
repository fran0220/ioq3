// SPDX-License-Identifier: GPL-2.0-or-later
import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { connect, sleep } from './browser.mjs';

const [cdp, directory, mode = 'baseline'] = process.argv.slice(2);
if (!directory) throw new Error('Usage: node run.mjs CDP_WEBSOCKET OUTPUT_DIR [baseline|reliability|bot]');
const output = resolve(directory);
mkdirSync(output, { recursive: true });
const b = await connect(cdp, join(output, `${mode}.jsonl`));
const results = [];
const read = () => b.evaluate('window.readEngine?.() ?? null');
const ready = () => b.waitFor(read, s => s?.state === 8 && s.snap.valid, 45000);
const evidence = async name => {
    const value = await read();
    b.record('snapshot', { name, value });
    return value;
};
const pass = (name, data) => { results.push({ name, status: 'PASS', ...data }); console.log('PASS', name); };
let mouseX = 400, mouseY = 300;
const mouse = async (dx, dy) => {
    mouseX += dx; mouseY += dy;
    b.record('input', { mouseDelta: [dx, dy], x: mouseX, y: mouseY });
    await b.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: mouseX, y: mouseY });
};
const capture = async () => {
    await b.click('#capture');
    assert.equal(await b.evaluate('document.pointerLockElement?.id'), 'canvas');
    mouseX = 400; mouseY = 300;
    await b.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: mouseX, y: mouseY });
    await sleep(150);
};
const wrap = degrees => ((degrees + 540) % 360) - 180;
const aim = async (yaw, pitch = 0) => {
    for (let attempt = 0; attempt < 5; attempt++) {
        const ps = (await read()).snap.ps;
        if (ps.pm_type !== 0) return false;
        const angles = ps.viewangles;
        const dyaw = wrap(yaw - angles[1]), dpitch = pitch - angles[0];
        if (Math.abs(dyaw) < 1 && Math.abs(dpitch) < 1) return true;
        // Default sensitivity=5, m_yaw=m_pitch=.022; verify final snapshot.
        await mouse(-dyaw / .11, dpitch / .11);
        await sleep(120);
    }
    const angles = (await read()).snap.ps.viewangles;
    assert.ok(Math.abs(wrap(yaw - angles[1])) < 2 && Math.abs(pitch - angles[0]) < 2,
        `Mouse aim did not reach target: ${angles} versus ${yaw},${pitch}`);
    return true;
};
const hold = async (key, ms) => {
    await b.key(key, true);
    try { await sleep(ms); } finally { await b.key(key, false); }
};
const aimKeys = async (yaw, pitch = 0) => {
    // CDP absolute mouse positions stop delivering deltas outside the viewport.
    // Use Quake's existing keyboard look bindings for unrestricted tracking;
    // the baseline separately asserts real captured-mouse rotation.
    for (let i = 0; i < 12; i++) {
        const ps = (await read()).snap.ps;
        if (ps.pm_type !== 0) return false;
        const dyaw = wrap(yaw - ps.viewangles[1]);
        const dpitch = pitch - ps.viewangles[0];
        if (Math.abs(dyaw) < 3 && Math.abs(dpitch) < 3) return true;
        if (Math.abs(dyaw) >= 3) await hold(dyaw > 0 ? 'ArrowLeft' : 'ArrowRight', Math.min(350, Math.abs(dyaw) / 140 * 1000));
        if (Math.abs(dpitch) >= 3) await hold(dpitch > 0 ? 'Delete' : 'PageDown', Math.min(350, Math.abs(dpitch) / 140 * 1000));
        await sleep(80);
    }
    const ps = (await read()).snap.ps;
    return ps.pm_type === 0 && Math.abs(wrap(yaw - ps.viewangles[1])) < 3 && Math.abs(pitch - ps.viewangles[0]) < 3;
};
const fire = async down => {
    b.record('input', { mouseButton: 'left', down });
    await b.send('Input.dispatchMouseEvent', {
        type: down ? 'mousePressed' : 'mouseReleased', x: mouseX, y: mouseY,
        button: 'left', clickCount: 1,
    });
};
try {
    await ready();
    if (mode === 'baseline') {
        await b.send('Page.reload', { ignoreCache: true });
        await sleep(300);
        await ready();
        await capture();
        const start = await evidence('spawn');
        assert.ok(Math.hypot(start.snap.ps.origin[0] - 212, start.snap.ps.origin[1] - 2360) < 10,
            'Fixture requires the unmodified q3dm1 initial spawn');
        await aim(-90);
        const turned = await evidence('mouse-turned-south');
        assert.ok(Math.abs(wrap(turned.snap.ps.viewangles[1] - start.snap.ps.viewangles[1])) > 30);
        pass('mouse-turn', { before: start.snap.ps.viewangles, after: turned.snap.ps.viewangles });
        await b.key('w', true);
        let picked;
        try { picked = await b.waitFor(read, s => s.snap.ps.stats.armor > start.snap.ps.stats.armor, 4000); }
        finally { await b.key('w', false); }
        b.record('snapshot', { name: 'armor-pickup', value: picked });
        assert.ok(picked.snap.ps.origin[1] < start.snap.ps.origin[1] - 100);
        pass('move-and-pickup', { before: start.snap.ps, after: picked.snap.ps });
        await sleep(250);
        const grounded = await evidence('before-jump');
        await b.key('Space', true);
        let airborne;
        try { airborne = await b.waitFor(read, s => s.snap.ps.velocity[2] > 30 &&
            s.snap.ps.origin[2] > grounded.snap.ps.origin[2] + 10 && s.snap.ps.groundEntityNum === 1023, 3000); }
        finally { await b.key('Space', false); }
        b.record('snapshot', { name: 'airborne', value: airborne });
        await b.waitFor(read, s => s.snap.ps.groundEntityNum !== 1023, 3000);
        pass('jump-and-land', { before: grounded.snap.ps, airborne: airborne.snap.ps });
        const beforeFire = await evidence('before-fire');
        await fire(true);
        try { await sleep(350); } finally { await fire(false); }
        const afterFire = await evidence('after-fire');
        assert.ok(afterFire.snap.ps.ammo[2] < beforeFire.snap.ps.ammo[2]);
        pass('mouse-fire-consumes-ammo', { before: beforeFire.snap.ps.ammo[2], after: afterFire.snap.ps.ammo[2] });
        await b.screenshot(join(output, 'baseline.jpg'));
    } else if (mode === 'reliability') {
        for (const hdr of [0, 1]) {
            await b.command(`set r_hdr ${hdr}`);
            const count = b.messages.filter(s => s.includes('CL_InitCGame:')).length;
            await b.command('vid_restart');
            await b.waitFor(async () => b.messages.filter(s => s.includes('CL_InitCGame:')).length, n => n > count, 30000);
            await ready();
            const before = await evidence(`hdr${hdr}-restarted`);
            if (before.keyCatcher & 1) await b.press('Backquote');
            await capture();
            const angle = (await read()).snap.ps.viewangles[1];
            await hold('ArrowRight', 300);
            await b.waitFor(read, s => Math.abs(wrap(s.snap.ps.viewangles[1] - angle)) > 10, 5000);
            const after = await evidence(`hdr${hdr}-input-after-restart`);
            assert.ok(after.snap.messageNum > before.snap.messageNum);
            assert.equal(await b.evaluate('document.querySelector("canvas").getContext("webgl2").isContextLost()'), false);
            pass(`HDR${hdr}-vid_restart`, { before: before.snap.messageNum, after: after.snap.messageNum });
            await b.screenshot(join(output, `hdr${hdr}-restart.jpg`));
        }
        for (const map of ['q3tourney2', 'q3dm17', 'q3dm1']) {
            await b.command(`map ${map}`);
            await b.waitFor(read, s => s?.state === 8 && s.snap.valid &&
                s.configstrings.serverInfo.includes(`\\mapname\\${map}\\`), 30000);
            await sleep(1000);
            await evidence(`map-${map}`);
            assert.equal(await b.evaluate('document.querySelector("canvas").getContext("webgl2").isContextLost()'), false);
            pass(`map-switch-${map}`);
            await b.screenshot(join(output, `${map}.jpg`));
        }
        await b.evaluate('document.querySelector("canvas").getContext("webgl2").getExtension("WEBGL_lose_context").loseContext()');
        await b.waitFor(() => b.evaluate('window.testContextLost'), Boolean);
        assert.equal(await b.evaluate('document.querySelector("canvas").getContext("webgl2").isContextLost()'), true);
        await b.send('Page.reload', { ignoreCache: true });
        await sleep(500);
        await ready();
        assert.equal(await b.evaluate('document.querySelector("canvas").getContext("webgl2").isContextLost()'), false);
        pass('forced-context-loss-full-reload');
    } else if (mode === 'bot') {
        // Reload the fixture so prior test/debug bots cannot survive map changes.
        await b.send('Page.reload', { ignoreCache: true });
        await sleep(500);
        await ready();
        await b.command('map q3dm17');
        await b.waitFor(read, s => s?.state === 8 && s.snap.valid &&
            s.configstrings.serverInfo.includes('\\mapname\\q3dm17\\'), 30000);
        await b.command('addbot sarge 3');
        await b.waitFor(read, s => s.players.some(p => p.clientNum !== s.snap.ps.clientNum), 15000);
        await capture();
        // Walk off the platform, rather than using kill/setviewpos/give cheats.
        // This independently exercises actual falling death and respawn input.
        const platform = await evidence('before-falling-death');
        assert.ok(await aimKeys(Math.atan2(platform.snap.ps.origin[1], platform.snap.ps.origin[0]) * 180 / Math.PI));
        await b.key('w', true);
        await b.key('Space', true);
        let fallingDeath;
        try { fallingDeath = await b.waitFor(read, s => s.snap.ps.pm_type === 3 && s.snap.ps.stats.health <= 0, 12000); }
        finally { await b.key('w', false); await b.key('Space', false); }
        b.record('snapshot', { name: 'falling-death', value: fallingDeath });
        await b.screenshot(join(output, 'death.jpg'));
        await sleep(1800);
        await fire(true); await sleep(100); await fire(false);
        const firstRespawn = await b.waitFor(read, s => s.snap.ps.pm_type === 0 && s.snap.ps.stats.health > 0, 5000);
        b.record('snapshot', { name: 'first-respawn', value: firstRespawn });
        pass('death-and-click-respawn');
        // Use the enclosed arena for the scored round, not the void-death
        // fixture. Ordinary map switching retains the bot and resets scores.
        await b.command('map q3dm1');
        await b.waitFor(read, s => s.state === 8 && s.snap.valid && s.snap.ps.pm_type === 0 &&
            s.snap.ps.persistant.score === 0 && s.configstrings.serverInfo.includes('\\mapname\\q3dm1\\'), 20000);
        await capture();
        const initial = await evidence('bot-match-start');
        let hit = false, wasDead = false;
        let deadSince = 0, intermission;
        const end = Date.now() + 180000;
        while (Date.now() < end) {
            const state = await read();
            const ps = state.snap.ps;
            if (state.configstrings.intermission === '1' || ps.pm_type === 5) {
                intermission = state;
                break;
            }
            if (!hit && ps.persistant.hits > initial.snap.ps.persistant.hits) {
                hit = true;
                await fire(false);
                b.record('snapshot', { name: 'confirmed-hit', value: state });
                pass('shooting-damages-bot', { hits: ps.persistant.hits });
                await b.screenshot(join(output, 'bot-hit.jpg'));
            }
            if (ps.pm_type === 3 && ps.stats.health <= 0) {
                if (!wasDead) {
                    wasDead = true;
                    deadSince = Date.now();
                    await fire(false);
                    b.record('snapshot', { name: 'dead', value: state });
                    await b.screenshot(join(output, 'death.jpg'));
                }
                if (Date.now() - deadSince > 1800) {
                    // Actual attack click asks the unchanged game rules to respawn.
                    await fire(true); await sleep(100); await fire(false);
                }
            } else {
                if (wasDead) {
                    assert.ok(ps.stats.health > 0 && ps.pm_type === 0);
                    wasDead = false;
                    b.record('snapshot', { name: 'respawned', value: state });
                }
                const target = state.players.find(p => p.clientNum !== ps.clientNum && !(p.eFlags & 1));
                if (target) {
                    await fire(false);
                    const dx = target.origin[0] - ps.origin[0], dy = target.origin[1] - ps.origin[1];
                    const dz = target.origin[2] + 10 - (ps.origin[2] + 26);
                    const aimed = await aimKeys(Math.atan2(dy, dx) * 180 / Math.PI,
                        -Math.atan2(dz, Math.hypot(dx, dy)) * 180 / Math.PI);
                    if (aimed) { await fire(true); await sleep(100); await fire(false); }
                    if (ps.ammo[2] <= 0 && Math.hypot(dx, dy) > 80) await hold('w', 200);
                }
            }
            await sleep(100);
        }
        await fire(false);
        assert.ok(hit, 'No independently observed damage to a bot');
        assert.ok(intermission, 'Bot match did not reach fraglimit within 180 seconds');
        assert.ok(Math.max(Number(intermission.configstrings.scores1), Number(intermission.configstrings.scores2)) >= 3,
            'Intermission was not a fraglimit=3 finish');
        b.record('snapshot', { name: 'fraglimit-reached', value: intermission });
        // CS_INTERMISSION precedes the actual score-screen player state.
        const settled = await b.waitFor(read, s => s.snap.ps.pm_type === 5, 10000);
        b.record('snapshot', { name: 'score-screen', value: settled });
        pass('bot-fraglimit-score-screen', { scores: settled.configstrings });
        await b.screenshot(join(output, 'score-screen.jpg'));
        await b.command('map_restart 0');
        const restarted = await b.waitFor(read, s => s.snap.valid && s.snap.ps.pm_type === 0 &&
            s.configstrings.intermission !== '1' && s.snap.ps.persistant.score === 0, 20000);
        b.record('snapshot', { name: 'match-restarted', value: restarted });
        pass('match-restart');
        await b.screenshot(join(output, 'match-restarted.jpg'));
    } else throw new Error(`Unknown mode: ${mode}`);
} catch (error) {
    results.push({ name: mode, status: 'FAIL', error: String(error), snapshot: await read().catch(() => null) });
    console.error(error);
    process.exitCode = 1;
    await b.screenshot(join(output, `${mode}-failure.jpg`)).catch(() => {});
} finally {
    await b.key('w', false).catch(() => {});
    await b.key('Space', false).catch(() => {});
    await fire(false).catch(() => {});
    writeFileSync(join(output, `${mode}-result.json`), JSON.stringify(results, null, 2));
    await b.close();
}
