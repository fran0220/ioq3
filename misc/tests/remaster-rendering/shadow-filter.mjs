// Execute the production projected-shadow filter on WebGL2, with asymmetric coverage.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { connect } from '../gameplay/browser.mjs';
const b = await connect(process.argv[2]);
const shader = readFileSync(new URL('../../../code/renderergl2/glsl/pshadow_fp.glsl',import.meta.url),'utf8');
const filter = shader.slice(shader.indexOf('float SampleProjectedShadow'),shader.indexOf('\nvoid main()'));
try {
    const actual = await b.evaluate(`(() => {
        const gl=document.createElement('canvas').getContext('webgl2');
        const compile=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
            if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;};
        const p=gl.createProgram();
        gl.attachShader(p,compile(gl.VERTEX_SHADER,'#version 300 es\\nvoid main(){gl_Position=vec4(float((gl_VertexID<<1)&2)*2.-1.,float(gl_VertexID&2)*2.-1.,0,1);}'));
        gl.attachShader(p,compile(gl.FRAGMENT_SHADER,'#version 300 es\\nprecision highp float;\\n#define USE_PCF\\n#define PSHADOW_MAP_SIZE 4.0\\n#define texture2D texture\\nuniform sampler2D u_ShadowMap;\\nuniform vec2 uv;\\nout vec4 color;\\n'+${JSON.stringify(filter)}+'\\nvoid main(){color=vec4(vec3(SampleProjectedShadow(uv)),1);}'));
        gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));gl.useProgram(p);
        gl.bindTexture(gl.TEXTURE_2D,gl.createTexture());
        const pixels=new Uint8Array(64).fill(255);pixels[20]=0;
        gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA8,4,4,0,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
        for(const name of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER])gl.texParameteri(gl.TEXTURE_2D,name,gl.NEAREST);
        for(const name of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T])gl.texParameteri(gl.TEXTURE_2D,name,gl.CLAMP_TO_EDGE);
        gl.viewport(0,0,1,1);
        const out=[];
        for(const uv of [[.375,.375],[.4375,.375],[.5625,.375],[.4375,.5625],[.125,.125],[.625,.375]]){
            gl.uniform2fv(gl.getUniformLocation(p,'uv'),uv);gl.drawArrays(gl.TRIANGLES,0,3);
            const pixel=new Uint8Array(4);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);out.push(pixel[0]);}
        const error=gl.getError();gl.getExtension('WEBGL_lose_context')?.loseContext();return {out,error};
    })()`);
    assert.equal(actual.error,0);
    const expected=[255,191,64,48,0,0];
    actual.out.forEach((n,i)=>assert.ok(Math.abs(n-expected[i])<=1,`sample ${i}: ${n} != ${expected[i]}`));
    console.log('PASS production WebGL2 bilinear coverage:',actual);
} finally { await b.close(); }
