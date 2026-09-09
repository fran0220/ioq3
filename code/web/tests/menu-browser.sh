#!/usr/bin/env bash
# Actual compiled engine with separately supplied authorized data, no fake engine.
set -euo pipefail
base="${1:?Usage: menu-browser.sh <local-test-server-url>}"
session=ioq3-menu-check
ab() { agent-browser --session "$session" "$@"; }
trap 'ab close >/dev/null 2>&1 || true' EXIT
ab open "${base%/}/engine-test.html"
ab set viewport 1280 720 2
ab wait --fn 'document.body.dataset.ready === "true" && !document.querySelector("#menu").hidden'
ab eval 'for(const [id,value] of [[999,1],[-1,1],[0,NaN],[0,Infinity],[0,-0.01],[0,1.01],[3,0]])if(testEngine._OG_WebSetSetting(id,value)!==0)throw Error("invalid setting accepted"); true'
ab click '[data-screen="settings"]'
ab wait --fn '!document.querySelector("[data-page=settings]").hidden'
ab eval 'if(document.pointerLockElement)throw Error("SDL recaptured DOM menu"); true'
ab fill '#setting-0' 0.35
ab press Tab
ab eval 'if(Math.abs(testEngine._OG_WebSetting(0)-0.35)>0.00001)throw Error("C volume unchanged"); true'
ab fill '#setting-2' 7.3
ab press Tab
ab eval 'if(Math.abs(testEngine._OG_WebSetting(2)-7.3)>0.00001)throw Error("C sensitivity unchanged"); true'
ab wait --fn 'document.querySelector("#save-status").textContent === "Settings saved"'
ab reload
ab wait --fn 'document.body.dataset.ready === "true"'
ab click '[data-screen="settings"]'
ab eval 'if(document.querySelector("#setting-0").value!=="0.35"||document.querySelector("#setting-2").value!=="7.3")throw Error("IDBFS reload lost settings"); true'
ab click '[data-screen="help"]'
ab wait --fn '!document.querySelector("[data-page=help]").hidden'
ab eval 'if(document.pointerLockElement)throw Error("SDL recaptured DOM navigation"); true'
ab click '#fullscreen'
ab wait --fn '!!document.fullscreenElement'
ab click '#exit-fullscreen'
ab wait --fn '!document.fullscreenElement'
ab click '#return-engine'
ab wait --fn 'document.querySelector("#menu").hidden'
# Real SDL key events (CDP insertText does not feed SDL_TEXTINPUT here).
ab press '`'
for key in d e v m a p Space q 3 d m 1; do ab press "$key"; done
ab press Enter
ab press '`'
ab wait --fn 'testEngine._OG_WebUIState() === 2'
ab press F10
ab wait --fn '!document.querySelector("#menu").hidden'
ab eval 'if(document.querySelector("#menu").hidden||!document.querySelector("#play").textContent.includes("Resume"))throw Error("in-match menu failed"); true'
ab click '[data-screen="settings"]'
ab fill '#setting-4' 105
ab press Tab
ab eval 'if(testEngine._OG_WebSetting(4)!==105)throw Error("FOV unchanged"); true'
ab click '#return-engine'
ab eval 'if(!document.querySelector("#menu").hidden||testEngine._OG_WebUIState()!==2)throw Error("resume lost match"); true'
ab click '#canvas'
ab wait --fn 'document.pointerLockElement?.id === "canvas"'
# Inject the browser loss event; engine is deliberately still running, exposing
# stale input ownership that would be hidden by testing only an aborted runtime.
ab eval 'canvas.dispatchEvent(new Event("webglcontextlost",{cancelable:true}))'
ab wait --fn 'document.body.dataset.state === "failed" && !document.pointerLockElement'
ab click '#title'
ab eval 'for(const mode of [0,1,2])if(testEngine._OG_WebMenu(mode)!==0)throw Error("terminal failure revived"); true'
ab eval 'new Promise((resolve,reject)=>{let frames=0;function check(){if(document.pointerLockElement)return reject(Error("failed page recaptured"));if(++frames===12)resolve(true);else requestAnimationFrame(check)}requestAnimationFrame(check)})'
ab click '#retry'
ab wait --fn 'document.body.dataset.ready === "true" && !document.querySelector("#menu").hidden'
ab eval 'if(testEngine._OG_WebUIState()!==1)throw Error("reload did not reset terminal state"); true'
echo 'PASS: real C settings/rejection, IDBFS reload, navigation/fullscreen, actual map menu/FOV/resume, terminal failure input block/reload'
