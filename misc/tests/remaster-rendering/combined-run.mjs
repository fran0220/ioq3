// Private renderer integration: real console/input, never writes to engine memory.
import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { connect, sleep } from '../gameplay/browser.mjs';

const [cdp, url, outputArg] = process.argv.slice(2);
if (!outputArg) throw Error('Usage: combined-run.mjs CDP PRIVATE_HOST_URL OUTPUT');
const output = resolve(outputArg); mkdirSync(output, { recursive: true });
const b = await connect(cdp, join(output, 'combined.jsonl'));
const results = [];
const ready = () => b.waitFor(() => b.evaluate('window.readEngine?.()'), s => s?.state === 8 && s.snap.valid, 60000);
const restartMap = async () => {
    const start=b.messages.length;
    await b.command('devmap q3dm1');
    await b.waitFor(()=>b.messages.slice(start),lines=>lines.some(s=>s.includes('CL_InitCGame:')),45000);
    await ready();
    await b.waitFor(()=>b.evaluate('readEngine().snap.ps.pm_type'),type=>type===0);
};
const capture = async name => {
    await sleep(300);
    const state = await b.evaluate(`({snapshot:readEngine(),contextLost:!!window.testContextLost,
        error:document.querySelector('canvas').getContext('webgl2').getError()})`);
    assert.equal(state.error, 0); assert.equal(state.contextLost, false);
    await b.screenshot(join(output, name + '.jpg'));
    b.record('capture-state', {name,...state});
    results.push({name,error:state.error,contextLost:state.contextLost,origin:state.snapshot.snap.ps.origin});
};
try {
    await b.send('Page.navigate', {url}); await sleep(500); await ready();
    await b.send('Page.bringToFront'); await b.click('#capture');
    await restartMap();
    await b.command('r_showcluster 1');
    await b.command('noclip'); await b.command('setviewpos 674 1350 286 270');
    await capture('crest-start');
    const before = await b.evaluate('readEngine().snap.ps.origin');
    await b.key('w',true); await sleep(1700); await b.key('w',false); await sleep(150);
    const after = await b.evaluate('readEngine().snap.ps.origin');
    assert.ok(Math.hypot(...after.map((x,i)=>x-before[i])) > 250);
    await capture('crest-moved-away');
    await b.key('s',true); await sleep(1700); await b.key('s',false);
    await capture('crest-return');
    const clusters = b.messages.filter(s => /cluster:/.test(s));
    assert.ok(clusters.length >= 2, 'movement must exercise multiple cluster transitions');
    results.push({name:'real-movement-clusters',before,after,clusters});

    for (const hdr of [0,1]) {
        await b.command('r_hdr ' + hdr);
        await b.command('r_normalMapping 1'); await b.command('r_specularMapping 1');
        await b.command('r_pbr 0'); await b.command('r_glossType 1');
        await b.command('vid_restart'); await sleep(1800); await ready();
        if (await b.evaluate('readEngine().snap.ps.pm_type') !== 1) await b.command('noclip');
        await b.command('setviewpos 674 1350 286 270');
        await capture('crest-hdr' + hdr);
        await restartMap(); // noclip returns before PM_Weapon; never use it for firing tests
        await b.command('cg_thirdPerson 1');
        await b.command('cg_thirdPersonAngle 180'); await b.command('cg_thirdPersonRange 70');
        await capture('character-materials-hdr' + hdr);
        await b.command('r_normalMapping 0'); await b.command('r_specularMapping 0');
        await b.command('vid_restart'); await sleep(1800); await ready();
        await capture('character-flat-hdr' + hdr);
        await b.command('r_normalMapping 1'); await b.command('r_specularMapping 1');
        await b.command('r_forceSun 1'); await b.command('r_sunlightMode 2');
        await b.command('r_dlightMode 2'); await b.command('cg_shadows 4');
        await b.command('vid_restart'); await sleep(1800); await ready();
        await capture('character-shadows-hdr' + hdr);
        await b.command('cg_thirdPerson 0');
        await b.command('god'); await b.command('give all'); await b.command('weapon 5');
        await b.waitFor(()=>b.evaluate('readEngine().snap.ps.weapon'),weapon=>weapon===5);
        await capture('rocket-near-hdr' + hdr);
        const ammoBefore=await b.evaluate('readEngine().snap.ps.ammo[5]');
        await b.send('Input.dispatchMouseEvent',{type:'mousePressed',x:400,y:300,button:'left',clickCount:1});
        for (let frame=0; frame<8; frame++) {
            await b.screenshot(join(output,`rocket-action-hdr${hdr}-${frame}.jpg`));
            await sleep(60);
        }
        await b.send('Input.dispatchMouseEvent',{type:'mouseReleased',x:400,y:300,button:'left',clickCount:1});
        await sleep(700); await capture('rocket-impact-hdr' + hdr);
        assert.ok(await b.evaluate('readEngine().snap.ps.ammo[5]') < ammoBefore,'rocket must actually fire');
        const timing = await b.evaluate(`new Promise(resolve=>{
            const samples=[];let prev;function frame(t){if(prev!==undefined)samples.push(t-prev);prev=t;
            if(samples.length<120)requestAnimationFrame(frame);else {samples.sort((a,b)=>a-b);
            resolve({p50:samples[59],p95:samples[113],p99:samples[118],heap:engine.HEAPU8.length});}}
            requestAnimationFrame(frame);})`);
        await b.command('imagelist'); results.push({name:'software-frame-deltas-hdr'+hdr,...timing});
    }
    const errors = await b.evaluate('testLogs.filter(s=>/GL_INVALID|GLSL.*failed|FBO.*incomplete/i.test(s))');
    assert.deepEqual(errors, []);
} finally {
    await b.send('Input.dispatchMouseEvent',{type:'mouseReleased',x:400,y:300,button:'left',clickCount:1}).catch(()=>{});
    for (const key of ['w','s']) await b.key(key,false).catch(()=>{});
    writeFileSync(join(output,'results.json'),JSON.stringify(results,null,2));
    await b.close();
}
