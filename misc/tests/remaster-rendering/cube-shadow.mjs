// Production radial-distance writer/reader: all cube faces, before/behind occluder.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { connect } from '../gameplay/browser.mjs';
const root = new URL('../../../code/renderergl2/glsl/',import.meta.url);
const writer = readFileSync(new URL('shadowfill_fp.glsl',root),'utf8');
const reader = readFileSync(new URL('lightall_fp.glsl',root),'utf8')
    .match(/vec3 packedDepth[\s\S]*?attenuation \*= step\(receiver - bias, blocker\);/)[0];
// Check the actual six view axes against GL cube addressing, using asymmetric
// off-axis receivers so a face swap or flipped texture coordinate cannot pass.
const main = readFileSync(new URL('../tr_main.c',root),'utf8');
const views = main.slice(main.indexOf('void R_RenderDlightCubemaps('), main.indexOf('// Projected shadows run'));
const axes = [...views.matchAll(/VectorSet\( shadowParms\.or\.axis\[\d\],\s*(-?\d),\s*(-?\d),\s*(-?\d)\);/g)]
    .map(m=>m.slice(1).map(Number));
assert.equal(axes.length,18);
const rays = [[1,.2,.3],[-1,.1,.4],[.3,1,-.2],[.1,-1,.4],[.2,-.4,1],[-.3,.2,-1]];
const cubeST = [[-.3,-.2],[.4,-.1],[.3,-.2],[.1,-.4],[.2,.4],[.3,-.2]];
for(let face=0;face<6;face++) {
    const p=rays[face].map(x=>-x), dot=a=>a.reduce((s,x,i)=>s+x*p[i],0);
    const depth=dot(axes[face*3]);
    const actual=[-dot(axes[face*3+1])/depth,dot(axes[face*3+2])/depth];
    actual.forEach((x,i)=>assert.ok(Math.abs(x-cubeST[face][i])<1e-8));
}
const b = await connect(process.argv[2]);
try {
    const result = await b.evaluate(`(() => {
        const gl=document.createElement('canvas').getContext('webgl2');
        const compile=(kind,source)=>{const s=gl.createShader(kind);gl.shaderSource(s,source);gl.compileShader(s);
            if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;};
        const program=(vs,fs)=>{const p=gl.createProgram();gl.attachShader(p,compile(gl.VERTEX_SHADER,vs));
            gl.attachShader(p,compile(gl.FRAGMENT_SHADER,fs));gl.linkProgram(p);
            if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));return p;};
        const vertex='#version 300 es\\nuniform vec3 point;out vec3 var_Position;void main(){var_Position=point;gl_Position=vec4(float((gl_VertexID<<1)&2)*2.-1.,float(gl_VertexID&2)*2.-1.,0,1);}';
        const head='#version 300 es\\nprecision highp float;\\n#define varying in\\n#define gl_FragColor color\\n#define textureCube texture\\n#define PSHADOW_MAP_SIZE 512.0\\nout vec4 color;\\n';
        const write=program(vertex,head+'#define USE_DEPTH\\n'+${JSON.stringify(writer)});
        const read=program(vertex,head+'uniform samplerCube u_ShadowMap;uniform vec3 query;uniform float normalizedReceiver;void main(){vec3 L=normalize(query);vec3 N=L;float sqrLightDist=pow(normalizedReceiver*128.0,2.0);vec4 var_LightDir=vec4(0,0,0,16384);float attenuation=1.0;'+${JSON.stringify(reader)}+'color=vec4(vec3(attenuation),1);}');
        const cube=gl.createTexture();gl.bindTexture(gl.TEXTURE_CUBE_MAP,cube);
        for(let face=0;face<6;face++)gl.texImage2D(gl.TEXTURE_CUBE_MAP_POSITIVE_X+face,0,gl.RGBA8,4,4,0,gl.RGBA,gl.UNSIGNED_BYTE,null);
        for(const p of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER])gl.texParameteri(gl.TEXTURE_CUBE_MAP,p,gl.NEAREST);
        for(const p of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T,gl.TEXTURE_WRAP_R])gl.texParameteri(gl.TEXTURE_CUBE_MAP,p,gl.CLAMP_TO_EDGE);
        const fbo=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,fbo);gl.viewport(0,0,3,4);gl.useProgram(write);
        gl.uniform4f(gl.getUniformLocation(write,'u_LightOrigin'),0,0,0,1);gl.uniform1f(gl.getUniformLocation(write,'u_LightRadius'),128);
        const bytes=[];
        for(let face=0;face<6;face++){
            gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_CUBE_MAP_POSITIVE_X+face,cube,0);
            if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw Error('incomplete cube face');
            gl.clearColor(1,1,1,1);gl.clear(gl.COLOR_BUFFER_BIT);
            gl.uniform3f(gl.getUniformLocation(write,'point'),128*(.13+face*.117),0,0);gl.drawArrays(gl.TRIANGLES,0,3);
            const pixel=new Uint8Array(4);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);bytes.push(Array.from(pixel));
        }
        gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.viewport(0,0,1,1);gl.useProgram(read);
        const directions=[[1,.2,.3],[-1,.1,.4],[.3,1,-.2],[.1,-1,.4],[.2,-.4,1],[-.3,.2,-1]],visibility=[];
        for(let face=0;face<6;face++)for(const delta of [-.01,.01]){
            gl.uniform3fv(gl.getUniformLocation(read,'query'),directions[face]);
            gl.uniform1f(gl.getUniformLocation(read,'normalizedReceiver'),.13+face*.117+delta);gl.drawArrays(gl.TRIANGLES,0,3);
            const pixel=new Uint8Array(4);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);visibility.push(pixel[0]);
        }
        gl.uniform3f(gl.getUniformLocation(read,'query'),1,.2,-.9);
        gl.uniform1f(gl.getUniformLocation(read,'normalizedReceiver'),.95);gl.drawArrays(gl.TRIANGLES,0,3);
        const empty=new Uint8Array(4);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,empty);visibility.push(empty[0]);
        const error=gl.getError();gl.getExtension('WEBGL_lose_context')?.loseContext();return {bytes,visibility,error};
    })()`);
    assert.equal(result.error,0);
    result.bytes.forEach((p,i)=>{
        const decoded=(p[0]*65536+p[1]*256+p[2])/16777215;
        assert.ok(Math.abs(decoded-(.13+i*.117))<4/16777215,`face ${i} depth ${decoded}`);
    });
    assert.deepEqual(result.visibility,[255,0,255,0,255,0,255,0,255,0,255,0,255]);
    console.log('PASS production RGBA8 radial depth and six-face receiver occlusion:',result);
} finally { await b.close(); }
