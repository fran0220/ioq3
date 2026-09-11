// Controlled native-input firing workload. RAF is software frame latency, not GPU time.
import assert from 'node:assert/strict';
import { mkdirSync,writeFileSync } from 'node:fs';
import { resolve,join } from 'node:path';
import { connect,sleep } from '../gameplay/browser.mjs';
const [cdp,url,directory]=process.argv.slice(2), output=resolve(directory);
mkdirSync(output,{recursive:true});
const b=await connect(cdp,join(output,'modes.jsonl')),results=[];
const mouse=type=>b.send('Input.dispatchMouseEvent',{type,x:400,y:300,button:'left',clickCount:1});
try {
    await b.send('Page.navigate',{url});
    await b.waitFor(()=>b.evaluate('window.readEngine?.()?.state'),s=>s===8,60000);
    await b.send('Page.bringToFront'); await b.click('#capture'); await mouse('mouseReleased');
    for(const hdr of [0,1]) for(const mode of [0,1,2]) {
        const start=b.messages.length;
        await b.command('devmap q3dm1');
        await b.waitFor(()=>b.messages.slice(start),lines=>lines.some(s=>s.includes('CL_InitCGame:')),45000);
        for(const command of ['r_hdr '+hdr,'r_dlightMode '+mode,'r_forceSun 0','r_sunlightMode 0',
            'cg_shadows 1','r_normalMapping 1','r_specularMapping 1','r_pbr 0','r_glossType 1']) await b.command(command);
        await b.command('vid_restart'); await sleep(2000);
        for(const command of ['god','give all','weapon 5']) await b.command(command);
        await b.waitFor(()=>b.evaluate('readEngine().snap.ps.weapon'),w=>w===5);
        assert.equal(await b.evaluate('readEngine().snap.ps.pm_type'),0);
        const before=await b.evaluate('readEngine().snap.ps.ammo[5]');
        await mouse('mousePressed'); await sleep(500);
        const timing=await b.evaluate(`new Promise(resolve=>{
            const samples=[];let prev;function frame(t){if(prev!==undefined)samples.push(t-prev);prev=t;
            if(samples.length<120)requestAnimationFrame(frame);else{samples.sort((a,b)=>a-b);
                const gl=document.querySelector('canvas').getContext('webgl2'),ext=gl.getExtension('WEBGL_debug_renderer_info');
                resolve({p50:samples[59],p95:samples[113],p99:samples[118],heap:engine.HEAPU8.length,
                    renderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),
                    timerQuery:!!gl.getExtension('EXT_disjoint_timer_query_webgl2'),error:gl.getError(),
                    lost:!!window.testContextLost,snapshot:readEngine()});}}
            requestAnimationFrame(frame);})`);
        await b.screenshot(join(output,`firing-hdr${hdr}-mode${mode}.jpg`));
        await mouse('mouseReleased');
        assert.equal(timing.error,0);assert.equal(timing.lost,false);
        assert.equal(timing.snapshot.snap.ps.weapon,5);
        assert.ok(timing.snapshot.snap.ps.ammo[5]<before);
        results.push({hdr,mode,ammoBefore:before,...timing});
        await b.command('imagelist');
        console.log('PASS',hdr,mode,JSON.stringify({p50:timing.p50,p95:timing.p95,p99:timing.p99,
            ammo:timing.snapshot.snap.ps.ammo[5],renderer:timing.renderer}));
    }
} finally {
    await mouse('mouseReleased').catch(()=>{});
    writeFileSync(join(output,'results.json'),JSON.stringify(results,null,2));
    await b.close();
}
