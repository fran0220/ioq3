// SPDX-License-Identifier: GPL-2.0-or-later
// Run against the private gameplay fixture with energy-pillar-v2.pk3 loaded.
import assert from 'node:assert/strict';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { connect, sleep } from '../gameplay/browser.mjs';

const [cdp, outputArg] = process.argv.slice(2);
if (!outputArg) throw new Error('Usage: node run.mjs CDP OUTPUT_DIRECTORY');
const output = resolve(outputArg);
mkdirSync(output, { recursive: true });
const b = await connect(cdp, join(output, 'render.jsonl'));
const results = [];
const ready = () => b.waitFor(() => b.evaluate('window.readEngine?.()'), s => s?.state === 8 && s.snap.valid, 45000);
const capture = async name => {
    await sleep(350);
    assert.equal(await b.evaluate('!!window.testContextLost'), false);
    await b.screenshot(join(output, name + '.jpg'));
    b.record('snapshot', { name, value: await b.evaluate('readEngine()') });
};
try {
    await ready();
    // Execute the actual production GLSL on WebGL2, including r=0/NH=1.
    const shader = readFileSync(new URL('../../../code/renderergl2/glsl/lightall_fp.glsl', import.meta.url), 'utf8');
    const specular = shader.match(/vec3 CalcSpecular\([^}]+\}/)[0];
    const gpu = await b.evaluate(String.raw`(() => {
        const gl = document.createElement('canvas').getContext('webgl2');
        if (!gl) throw Error('No WebGL2');
        const compile = (type, source) => {
            const s = gl.createShader(type); gl.shaderSource(s, source); gl.compileShader(s);
            if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(s));
            return s;
        };
        const p = gl.createProgram();
        gl.attachShader(p, compile(gl.VERTEX_SHADER, '#version 300 es\nvoid main(){gl_Position=vec4(float((gl_VertexID<<1)&2)*2.0-1.0,float(gl_VertexID&2)*2.0-1.0,0,1);}'));
        gl.attachShader(p, compile(gl.FRAGMENT_SHADER, '#version 300 es\nprecision highp float;\n#define EPSILON 0.00000001\n' + ${JSON.stringify(specular)} + '\nout vec4 color;\nuniform float roughness;\nvoid main(){vec3 s=CalcSpecular(vec3(.04),1.0,1.0,roughness);color=vec4(any(isnan(s))||any(isinf(s))?vec3(1,0,0):vec3(0,1,0),1);}'));
        gl.linkProgram(p);
        if (!gl.getProgramParameter(p,gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(p));
        gl.useProgram(p); gl.viewport(0,0,1,1);
        const samples = [];
        for (const r of [0,.001,.045,.2,1]) {
            gl.uniform1f(gl.getUniformLocation(p,'roughness'),r); gl.drawArrays(gl.TRIANGLES,0,3);
            const pixel = new Uint8Array(4); gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);
            samples.push({roughness:r,pixel:Array.from(pixel)});
        }
        const debug=gl.getExtension('WEBGL_debug_renderer_info');
        const result={samples,error:gl.getError(),renderer:debug?gl.getParameter(debug.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER)};
        gl.getExtension('WEBGL_lose_context')?.loseContext();
        return result;
    })()`);
    assert.equal(gpu.error, 0);
    for (const s of gpu.samples) assert.deepEqual(s.pixel, [0, 255, 0, 255]);
    results.push({ name: 'production-specular-WebGL2-finite', ...gpu });
    await b.command('devmap q3dm1');
    await ready();
    await b.command('r_hdr 1');
    await b.command('r_dlightMode 1');
    await b.command('vid_restart');
    await sleep(1500);
    await ready();
    await b.command('testmodel models/remaster/energy_pillar.md3');
    await capture('pillar-hdr');
    for (const exposure of [-1, 1]) {
        await b.command('r_cameraExposure ' + exposure);
        await capture('pillar-exposure-' + exposure);
    }
    await b.command('r_cameraExposure 1');
    await b.key('s', true); await sleep(350); await b.key('s', false);
    await capture('pillar-far');
    await b.command('r_hdr 0');
    await b.command('vid_restart');
    await sleep(1500); await ready();
    await b.command('testmodel models/remaster/energy_pillar.md3');
    await capture('pillar-ldr');
    await b.command('testmodel');
    await b.command('+attack'); await sleep(500);
    await capture('dynamic-light-firing');
    await b.command('-attack');
    await capture('decal-after-firing');
    await b.command('cg_shadows 4');
    await b.command('r_forceSun 1');
    await b.command('r_sunlightMode 2');
    await b.command('r_dlightMode 2');
    await b.command('vid_restart');
    await sleep(1500); await ready();
    await b.command('testmodel models/remaster/energy_pillar.md3');
    await capture('sun-projected-shadows');
    // RAF deltas measure browser scheduling + software rendering, not GPU time.
    const timings = await b.evaluate(`new Promise(resolve => {
        const samples=[]; let previous;
        function frame(now) {
            if(previous!==undefined) samples.push(now-previous); previous=now;
            if(samples.length<120) requestAnimationFrame(frame);
            else {samples.sort((a,b)=>a-b);resolve({count:samples.length,p50:samples[59],p95:samples[113],p99:samples[118],heap:engine.HEAPU8.length});}
        } requestAnimationFrame(frame);
    })`);
    await b.command('imagelist');
    results.push({ name: 'LDR-software-frame-deltas', ...timings });
    const errors = await b.evaluate('testLogs.filter(s=>/GL_INVALID|GLSL.*failed|shader.*error|FBO.*incomplete/i.test(s))');
    assert.deepEqual(errors, []);
    assert.equal(await b.evaluate('!!window.testContextLost'), false);
    results.push({ name: 'context-and-engine-GL-errors', errors, contextLost: false });
    console.log(JSON.stringify(results, null, 2));
} finally {
    await b.command('-attack').catch(() => {});
    await b.key('s', false).catch(() => {});
    writeFileSync(join(output, 'results.json'), JSON.stringify(results, null, 2));
    await b.close();
}
