#!/usr/bin/env bash
# Real WASM + locally supplied demo data; test observer required for movement.
set -euo pipefail
base="${1:?Usage: settings-browser.sh <test-server-url>}"
session=ioq3-settings-check
ab() { agent-browser --session "$session" "$@"; }
trap 'ab close >/dev/null 2>&1 || true' EXIT
ab open "${base%/}/engine-test.html"
ab set viewport 1280 720 2
ab wait --fn 'document.body.dataset.ready === "true" && !menu.hidden'
ab eval 'window.readPlayerName=()=>{let s="";for(let i=0;i<31;i++){let n=testEngine._OG_WebName(3,i);if(!n)break;s+=String.fromCharCode(n)}return s}; true'
ab eval 'const original=readPlayerName(); for(const name of ["", " leading", "trailing ", "a;b", "a\\b", "a\"b", "^1name", "line\nbreak", "x".repeat(32), "é"]){testEngine._OG_WebName(0,0);for(const c of name)testEngine._OG_WebName(1,c.codePointAt(0));if(testEngine._OG_WebName(2,0)!==0||readPlayerName()!==original)throw Error("invalid name mutated userinfo")} testEngine._OG_WebName(0,0);for(let i=0;i<31;i++)testEngine._OG_WebName(1,65);if(testEngine._OG_WebName(2,0)!==1||readPlayerName().length!==31)throw Error("31-byte boundary");true'
ab eval 'for(const [id,v] of [[8,0],[8,101],[8,1.5],[9,0],[10,8]])if(testEngine._OG_WebSetSetting(id,v)!==0)throw Error("profile bounds accepted");if(testEngine._OG_WebTextureFilter(3)!==-2||testEngine._OG_WebBind(0,-1,27,1)!==0||testEngine._OG_WebBind(0,-1,96,1)!==0)throw Error("reserved action accepted"); if(testEngine._OG_WebBinding(45)!==-2||testEngine._OG_WebBind(0,-1,45,1)!==3)throw Error("custom sizedown overwritten");true'
ab click '[data-screen="profile"]'
ab fill '#player-name' 'Arena Pilot 17'
ab click '#profile-form button'
ab fill '#setting-8' 75
ab press Tab
ab fill '#setting-9' 3
ab press Tab
ab fill '#setting-10' 6
ab press Tab
ab eval 'if(readPlayerName()!=="Arena Pilot 17"||testEngine._OG_WebSetting(8)!==75||testEngine._OG_WebSetting(9)!==3||testEngine._OG_WebSetting(10)!==6)throw Error("DOM profile did not apply");true'
ab click '[data-screen="display"]'
ab select '#texture-filter' 0
ab eval 'if(testEngine._OG_WebTextureFilter(-1)!==0)throw Error("filter readback");true'
ab eval 'if(testEngine._OG_WebBind(0,-1,105,1)!==1||testEngine._OG_WebBind(1,-1,107,1)!==1)throw Error("test slots unavailable");true'
ab click '[data-screen="bindings"]'
ab select '#binding-0-0' 107
ab wait --fn '!document.querySelector("#binding-conflict").hidden'
ab eval 'if(testEngine._OG_WebBinding(105)!==0||testEngine._OG_WebBinding(107)!==1)throw Error("conflict mutated bindings");true'
ab click '#binding-cancel'
ab select '#binding-0-0' 107
ab click '#binding-replace'
ab eval 'if(testEngine._OG_WebBinding(105)!==-1||testEngine._OG_WebBinding(107)!==0||testEngine._OG_WebBinding(119)!==0)throw Error("replace erased alternate/kept old slot");true'
ab eval 'if(testEngine._OG_WebBind(0,105,106,1)!==0||testEngine._OG_WebBind(0,107,45,1)!==3||testEngine._OG_WebBinding(107)!==0)throw Error("rejection partially unbound source");true'
ab select '#binding-0-2' -1
ab eval 'if(testEngine._OG_WebBinding(132)!==-1||testEngine._OG_WebBinding(119)!==0||testEngine._OG_WebBinding(107)!==0)throw Error("clear affected other slots");true'
ab wait --fn 'document.querySelector("#save-status").textContent === "Settings saved"'
ab eval 'if(!testEngine.FS.readFile("/home/players/demoq3/q3config.cfg",{encoding:"utf8"}).includes("bind k \"+forward\""))throw Error("wrong command archived");true'
ab reload
ab wait --fn 'document.body.dataset.ready === "true"'
ab eval 'const name=Array.from({length:31},(_,i)=>testEngine._OG_WebName(3,i)).filter(Boolean).map(c=>String.fromCharCode(c)).join("");if(testEngine._OG_WebTextureFilter(-1)!==0||testEngine._OG_WebBinding(107)!==0||testEngine._OG_WebBinding(105)!==-1||testEngine._OG_WebSetting(8)!==75||testEngine._OG_WebSetting(9)!==3||testEngine._OG_WebSetting(10)!==6||name!=="Arena Pilot 17")throw Error("IDBFS reload lost settings");true'
ab click '#play'
ab press '`'
for key in d e v m a p Space q 3 d m 1; do ab press "$key"; done
ab press Enter
ab press '`'
ab wait --fn 'testEngine._OG_WebUIState() === 2'
ab press F10
ab click '[data-screen="display"]'
# Menu-only textures need not be mipmapped; observe real world textures after map load.
ab eval 'if(testEngine._OG_WebSetSetting(5,10)!==1||testEngine._OG_WebSetSetting(5,11)!==0||testEngine._OG_WebSetSetting(5,2.5)!==0)throw Error("crosshair boundary");true'
ab eval 'window.minFilters=[];const gl=canvas.getContext("webgl2");for(const method of ["texParameteri","texParameterf"]){const native=gl[method].bind(gl);gl[method]=(target,p,value)=>{const result=native(target,p,value);if(p===gl.TEXTURE_MIN_FILTER)minFilters.push(gl.getTexParameter(target,p));return result}}true'
ab select '#texture-filter' 2
ab wait --fn 'minFilters.includes(9987)'
ab select '#texture-filter' 0
ab wait --fn 'minFilters.includes(9984)'
ab fill '#setting-5' 7
ab press Tab
ab fill '#setting-6' 32
ab press Tab
ab fill '#setting-7' 1
ab press Tab
ab eval 'if(testEngine._OG_WebSetting(5)!==7||testEngine._OG_WebSetting(6)!==32||testEngine._OG_WebSetting(7)!==1)throw Error("map display settings rejected");true'
ab click '#return-engine'
# Actual key down/up through SDL, and server snapshot observation (test-only C).
ab eval 'window.snap=()=>{const p=testEngine._OG_WebTestSnapshot();let e=p;while(testEngine.HEAPU8[e])e++;return JSON.parse(new TextDecoder().decode(testEngine.HEAPU8.subarray(p,e)))};window.beforeMove=snap().snap.ps.origin;window.moveYaw=snap().snap.ps.viewangles[1]*Math.PI/180;canvas.dispatchEvent(new KeyboardEvent("keydown",{key:"k",code:"KeyK",keyCode:75,which:75,bubbles:true}));true'
ab wait --fn '(snap().snap.ps.origin[0]-beforeMove[0])*Math.cos(moveYaw)+(snap().snap.ps.origin[1]-beforeMove[1])*Math.sin(moveYaw)>20'
ab eval 'canvas.dispatchEvent(new KeyboardEvent("keyup",{key:"k",code:"KeyK",keyCode:75,which:75,bubbles:true}));true'
echo 'PASS: actual renderer filtering, profile/name bounds, protected/conflicting bindings, IDBFS reload, map display cvars and rebound-key movement'
