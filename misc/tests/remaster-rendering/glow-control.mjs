// CW lamp control: identical opaque model/placement, additive companion on/off.
import assert from 'node:assert/strict';
import {mkdirSync,writeFileSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {connect,sleep} from '../gameplay/browser.mjs';
const [cdp,on,off,directory]=process.argv.slice(2),output=resolve(directory);
mkdirSync(output,{recursive:true});
const b=await connect(cdp,join(output,'glow.jsonl')),results=[];
const cameras=[['visible',1050,1020,75.39099564,.03213825],
    ['blocked',950,800,75.39099564,44.96812609]];
try {
    for(const hdr of [0,1]) for(const [variant,url] of [['on',on],['off',off],['leak',on]]) {
        await b.send('Page.navigate',{url:url+'?hdr='+hdr});
        await b.waitFor(()=>b.evaluate('window.readEngine?.()?.state'),s=>s===8,60000);
        await b.send('Page.bringToFront');await b.click('#capture');
        await b.send('Input.dispatchMouseEvent',{type:'mouseReleased',x:400,y:300,button:'left',clickCount:1});
        const start=b.messages.length;await b.command('devmap q3dm1');
        await b.waitFor(()=>b.messages.slice(start),m=>m.some(s=>s.includes('CL_InitCGame:')),45000);
        // Fixed movement steps make the teleport's built-in velocity decay
        // reproducible. This is a visual control, not gameplay timing evidence.
        // Disable PVS for this depth-only control: both the lamp and foreground
        // must be submitted. Locking the lamp PVS can omit the foreground wall.
        for(const c of ['pmove_fixed 1','pmove_msec 8','noclip','cg_drawGun 0','r_showcluster 1','r_novis 1'])await b.command(c);
        if(variant==='leak') await b.evaluate(`(()=>{
            // Deliberately wrong GL-only negative control, discarded on navigation.
            // If the model were merely culled/PVS-hidden, this could not reveal it.
            const gl=document.querySelector('canvas').getContext('webgl2'),draw=gl.drawElements;
            gl.drawElements=function(...args){
                const bypass=args[1]===6 && gl.isEnabled(gl.DEPTH_TEST) && gl.isEnabled(gl.BLEND)
                    && gl.getParameter(gl.BLEND_SRC_RGB)===gl.ONE && gl.getParameter(gl.BLEND_DST_RGB)===gl.ONE;
                if(bypass)gl.disable(gl.DEPTH_TEST);
                try{return draw.apply(this,args);}finally{if(bypass)gl.enable(gl.DEPTH_TEST);}
            };
            window.restoreGlowDepth=()=>{gl.drawElements=draw;};
        })()`);
        for(const [name,x,y,z,yaw] of cameras) {
            await b.command(`setviewpos ${x} ${y} ${z} ${yaw}`);await sleep(2200);
            const state=await b.evaluate(`({ps:readEngine().snap.ps,
                gl:document.querySelector('canvas').getContext('webgl2').getError(),lost:!!window.testContextLost})`);
            assert.equal(state.ps.pm_type,1);assert.equal(state.gl,0);assert.equal(state.lost,false);
            const clip=await b.evaluate(`(()=>{const r=document.querySelector('canvas').getBoundingClientRect();
                return {x:r.x,y:r.y,width:r.width,height:r.height,scale:2}})()`);
            const image=await b.send('Page.captureScreenshot',{format:'png',clip});
            writeFileSync(join(output,`${name}-${variant}-hdr${hdr}.png`),Buffer.from(image.data,'base64'));
            results.push({hdr,variant,name,...state});
        }
    }
    for(const hdr of [0,1]) for(const [name] of cameras) {
        const group=results.filter(r=>r.hdr===hdr&&r.name===name);
        for(const other of group.slice(1)) assert.ok(Math.hypot(...group[0].ps.origin.map((v,i)=>v-other.ps.origin[i]))<.01,
            'all control cameras must match before pixel comparison');
    }
    console.log('PASS twelve CW glow control captures, matched cameras, GL0/no loss');
} finally {
    await b.evaluate('window.restoreGlowDepth?.()').catch(()=>{});
    writeFileSync(join(output,'results.json'),JSON.stringify(results,null,2));await b.close();
}
