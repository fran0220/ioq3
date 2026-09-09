#!/usr/bin/env bash
# Host regression suite; fixture tests explicitly do not certify gameplay.
set -euo pipefail
base="${1:?Usage: code/web/tests/browser.sh <test-server-url>}"
base="${base%/}"
session=ioq3-m1-check
ab() { agent-browser --session "$session" "$@"; }
trap 'ab close >/dev/null 2>&1 || true' EXIT

ab open "$base/tests/canvas.html"
ab set viewport 1280 720 2
ab wait --fn '!!window.canvasProbe && !!window.resizeCanvasProbe'
ab eval 'if(JSON.stringify(canvasProbe)!==JSON.stringify({sdl:[800,600],buffer:[800,600],corner:[0,255,0,255]}))throw Error(JSON.stringify(canvasProbe)); true'
ab eval 'resizeCanvasProbe()'
ab wait --fn 'canvasProbe.sdl[0] === 1024'
ab eval 'if(JSON.stringify(canvasProbe)!==JSON.stringify({sdl:[1024,768],buffer:[1024,768],corner:[0,255,0,255]}))throw Error(JSON.stringify(canvasProbe)); true'

ab open "$base/tests/runtime.html"
ab set viewport 1280 720 2
ab wait --fn 'document.querySelector("#result").dataset.complete === "true"'
ab click '#write'
ab wait --fn 'document.querySelector("#result").dataset.save === "saved"'
ab reload
ab wait --fn 'document.querySelector("#result").dataset.complete === "true"'
ab eval 'if(!JSON.parse(document.querySelector("#result").textContent).matches)throw Error("IDBFS bytes changed across reload"); true'
ab click '#remove'
ab wait --fn 'document.querySelector("#result").textContent === "Fixture removed."'

ab open "$base/tests/controls.html"
ab wait --fn 'document.body.dataset.state === "ready"'
ab click '#fullscreen'
ab eval 'if(!document.fullscreenElement)throw Error("fullscreen enter failed"); true'
ab click '#exit-fullscreen'
ab eval 'if(document.fullscreenElement)throw Error("fullscreen exit failed"); true'
ab click '#capture'
ab wait --fn 'document.pointerLockElement?.id === "canvas" && fixture.audioState() === "running"'
ab eval 'document.exitPointerLock()'
ab wait --fn '!document.pointerLockElement'
ab eval 'window.dispatchEvent(new Event("blur")); if(fixture.blur<1)throw Error("blur bridge not called"); true'
ab eval 'document.documentElement.dataset.embedded="true"; fixture.fail(); if(getComputedStyle(document.querySelector("#status-panel")).display!=="block")throw Error("post-ready recovery hidden"); true'

ab open "$base/"
ab wait --fn 'document.body.dataset.state === "failed"'
ab eval 'if(document.body.dataset.runtimeLoaded!=="true" || !document.querySelector("#detail").textContent.includes("Game data is not installed"))throw Error("expected real WASM with missing-data failure"); true'
ab click '#retry'
ab wait --fn 'document.body.dataset.state === "failed" && document.body.dataset.runtimeLoaded === "true"'
ab tab new "$base/"
ab wait --fn 'document.body.dataset.state === "failed"'
ab eval 'if(!document.querySelector("#detail").textContent.includes("another tab"))throw Error("concurrent save writer allowed"); true'
echo 'PASS: real SDL2/WebGL2 canvas sizing/pixels/resize, WASM/IDBFS reload, host controls fixture, missing data/retry, exclusive settings lease'
