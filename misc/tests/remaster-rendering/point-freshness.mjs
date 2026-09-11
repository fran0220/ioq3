// Observe real GL submission without changing engine/game memory or draw output.
import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { connect, sleep } from '../gameplay/browser.mjs';
const [cdp,url,directory]=process.argv.slice(2);
const output=resolve(directory); mkdirSync(output,{recursive:true});
const b=await connect(cdp,join(output,'trace.jsonl'));
try {
    await b.send('Page.navigate',{url});
    await b.waitFor(()=>b.evaluate('window.readEngine?.()?.state'),state=>state===8,60000);
    await b.send('Page.bringToFront'); await b.click('#capture');
    await b.send('Input.dispatchMouseEvent',{type:'mouseReleased',x:400,y:300,button:'left',clickCount:1});
    await b.command('devmap q3dm1'); await sleep(1000);
    await b.command('r_dlightMode 2'); await b.command('vid_restart'); await sleep(2000);
    for(const command of ['god','give all','weapon 5']) await b.command(command);
    await b.waitFor(()=>b.evaluate('readEngine().snap.ps.weapon'),weapon=>weapon===5);
    assert.equal(await b.evaluate('readEngine().snap.ps.pm_type'),0);
    const before=await b.evaluate('readEngine().snap.ps.ammo[5]');
    await b.evaluate(`(()=>{
        const gl=document.querySelector('canvas').getContext('webgl2');
        const programs=new WeakMap(),faces=new WeakMap();
        window.pointTrace=[]; let frame=0,active=true;
        function tick(){if(active){frame++;requestAnimationFrame(tick)}} requestAnimationFrame(tick);
        const attach=gl.framebufferTexture2D, draw=gl.drawElements;
        gl.framebufferTexture2D=function(...args){
            if(args[2]>=34069 && args[2]<=34074 && args[3]){
                let entry=faces.get(args[3]);
                if(!entry || entry.frame!==frame) faces.set(args[3],entry={frame,bits:0});
                entry.bits|=1<<(args[2]-34069);
            }
            return attach.apply(this,args);
        };
        gl.drawElements=function(...args){
            const program=gl.getParameter(gl.CURRENT_PROGRAM);
            if(program && !programs.has(program)) {
                const point=gl.getAttachedShaders(program).some(shader=>gl.getShaderSource(shader).includes('#define USE_CUBESHADOW'));
                programs.set(program,point ? gl.getUniformLocation(program,'u_ShadowMap') : null);
            }
            const uniform=program && programs.get(program);
            if(uniform) {
                const unit=gl.getUniform(program,uniform),previous=gl.getParameter(gl.ACTIVE_TEXTURE);
                gl.activeTexture(gl.TEXTURE0+unit);
                const texture=gl.getParameter(gl.TEXTURE_BINDING_CUBE_MAP);
                gl.activeTexture(previous);
                const completed=faces.get(texture);
                pointTrace.push({frame,cubeFrame:completed?.frame ?? -1,bits:completed?.bits ?? 0});
            }
            return draw.apply(this,args);
        };
        window.stopPointTrace=()=>{active=false;gl.framebufferTexture2D=attach;gl.drawElements=draw;};
    })()`);
    await b.send('Input.dispatchMouseEvent',{type:'mousePressed',x:400,y:300,button:'left',clickCount:1});
    await sleep(1800);
    await b.send('Input.dispatchMouseEvent',{type:'mouseReleased',x:400,y:300,button:'left',clickCount:1});
    await sleep(300);
    const result=await b.evaluate(`({trace:pointTrace,ammo:readEngine().snap.ps.ammo[5],
        error:document.querySelector('canvas').getContext('webgl2').getError(),lost:!!window.testContextLost})`);
    writeFileSync(join(output,'result.json'),JSON.stringify(result,null,2));
    assert.ok(result.ammo<before,'must fire in PM_NORMAL');
    assert.equal(result.error,0); assert.equal(result.lost,false);
    assert.ok(result.trace.length>0,'must observe actual point-shadow draws');
    assert.deepEqual(result.trace.filter(draw=>draw.bits!==63 || draw.cubeFrame!==draw.frame),[],
        'each sampled cube must have all six faces submitted in the current frame');
    console.log('PASS current-frame six-face freshness:',result.trace.length,'actual point draws; ammo',before,'->',result.ammo);
} finally {
    await b.send('Input.dispatchMouseEvent',{type:'mouseReleased',x:400,y:300,button:'left',clickCount:1}).catch(()=>{});
    await b.evaluate('window.stopPointTrace?.()').catch(()=>{});
    await b.close();
}
