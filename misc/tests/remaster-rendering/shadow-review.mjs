// Same real-world cameras for pre/post projected-shadow filtering review.
import assert from 'node:assert/strict';
import { mkdirSync,writeFileSync } from 'node:fs';
import { join,resolve } from 'node:path';
import { connect,sleep } from '../gameplay/browser.mjs';
const [cdp,url,out] = process.argv.slice(2);
const output=resolve(out);mkdirSync(output,{recursive:true});
const b=await connect(cdp,join(output,'shadow.jsonl'));
const results=[];
try {
    await b.send('Page.navigate',{url});await sleep(500);
    await b.waitFor(()=>b.evaluate('window.readEngine?.()?.state'),s=>s===8,60000);
    await b.send('Page.bringToFront');await b.click('#capture');
    for (const hdr of [0,1]) {
        const start=b.messages.length;
        await b.command('devmap q3dm1');
        await b.waitFor(()=>b.messages.slice(start),m=>m.some(s=>s.includes('CL_InitCGame:')),45000);
        for(const command of ['r_forceSun 0','r_sunlightMode 0','cg_shadows 4','r_hdr '+hdr,
            'cg_thirdPerson 1','cg_thirdPersonAngle 180','cg_thirdPersonRange 70']) await b.command(command);
        await b.command('vid_restart');await sleep(2500);
        await b.screenshot(join(output,'spawn-hdr'+hdr+'.jpg'));
        await b.command('noclip');await b.command('setviewpos 1130 450 24 90');await sleep(1000);
        await b.screenshot(join(output,'stress-hdr'+hdr+'.jpg'));
        const state=await b.evaluate(`({snapshot:readEngine(),error:document.querySelector('canvas').getContext('webgl2').getError(),lost:!!window.testContextLost})`);
        assert.equal(state.error,0);assert.equal(state.lost,false);
        results.push({hdr,...state});
    }
} finally {
    writeFileSync(join(output,'results.json'),JSON.stringify(results,null,2));await b.close();
}
