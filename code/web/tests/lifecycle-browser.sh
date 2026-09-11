#!/usr/bin/env bash
# Actual production shell and WASM; no SDK or online connection is simulated.
set -euo pipefail
base="${1:?Usage: lifecycle-browser.sh <private-test-server-url>}"
ab() { agent-browser --session ioq3-lifecycle --args '--use-angle=swiftshader,--enable-unsafe-swiftshader' "$@"; }
trap 'ab close >/dev/null 2>&1 || true' EXIT
ab open "${base%/}/"
ab set viewport 1280 720 2
ab wait --fn 'document.body.dataset.engineState === "ready"'
ab eval 'if(window.OG)throw Error("This test requires standalone without injected SDK"); if(!document.querySelector("iframe").contentWindow.IOQ3_BOOT)throw Error("Missing shell attachment"); true'
ab click '#open-lobby'
ab eval 'if(!document.querySelector("#room-panel").open||!document.querySelector("#lobby-controls").hidden)throw Error("Offline lobby claims admission"); window.oldFrame=document.querySelector("iframe"); window.oldBoot=oldFrame.contentWindow.IOQ3_BOOT; true'
ab click '#local-engine'
ab wait --fn 'document.body.dataset.engineState === "ready" && document.querySelector("iframe") !== window.oldFrame'
ab eval '(async()=>{if(oldFrame.isConnected||document.querySelectorAll("iframe").length!==1)throw Error("Old engine survived");let stale=false;try{await oldBoot.getSession()}catch{stale=true}if(!stale)throw Error("Stale boot accepted");const locks=await navigator.locks.query();if(locks.held.filter(l=>l.name==="ioq3-player-home-v1").length!==1||locks.pending.length)throw Error("Write lease did not transfer");return true})()'
# A graphics failure must recreate the child, not reload the persistent shell.
ab eval 'window.shellMarker={}; window.failedFrame=document.querySelector("iframe");failedFrame.contentDocument.querySelector("canvas").dispatchEvent(new Event("webglcontextlost",{cancelable:true}));true'
ab wait --fn 'document.body.dataset.engineState === "failed" && document.querySelector("#room-panel").open'
ab click '#retry-engine'
ab wait --fn 'document.body.dataset.engineState === "ready" && document.querySelector("iframe") !== window.failedFrame'
ab eval 'if(!window.shellMarker||failedFrame.isConnected)throw Error("Wrong document replaced");true'
ab click '#open-lobby'
ab click '#stop-engine'
ab wait --fn 'document.body.dataset.engineState === "closed" && !document.querySelector("iframe")'
ab eval '(async()=>{const locks=await navigator.locks.query();if(locks.held.some(l=>l.name==="ioq3-player-home-v1"))throw Error("Stopped engine retains storage lock");return true})()'
ab click '#local-engine'
ab wait --fn 'document.body.dataset.engineState === "ready"'
echo 'PASS: actual engine ready → fresh child/one write lease → context failure/retry with persistent shell → stop/release → new local engine'
