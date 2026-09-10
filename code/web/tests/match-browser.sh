#!/usr/bin/env bash
# Production HUD + catalogue/actions on real WASM; private q3dm1 data required.
# The console is used only to trigger a deterministic real death, never to
# supply HUD values or launch matches. No test-observer build is needed.
set -euo pipefail
base="${1:?Usage: match-browser.sh <private-test-server-url>}"
session=ioq3-match-check
ab() { agent-browser --session "$session" --args '--enable-unsafe-swiftshader' "$@"; }
trap 'ab close >/dev/null 2>&1 || true' EXIT
capture() {
    if [[ -n "${UI_SCREENSHOT_DIR:-}" ]]; then
        mkdir -p "$UI_SCREENSHOT_DIR"
        ab screenshot "$UI_SCREENSHOT_DIR/$1.png"
    fi
}
pick() {
    local value
    value="$(ab eval "Array.from(document.querySelector('$1').options).find(o=>o.textContent==='$2').value" | jq -r)"
    ab select "$1" "$value"
}
ab open "${base%/}/engine-test.html"
ab set viewport 1280 720 2
ab wait --fn 'document.body.dataset.ready === "true" && !document.querySelector("#menu").hidden'
ab click '#play'
pick '#arena-map' 'Arena Gate'
ab select '#arena-mode' 2
ab eval 'if(!document.querySelector("#arena-limit").disabled||!document.querySelector("#arena-bots").hidden)throw Error("SP accepts manual overrides"); true'
ab select '#arena-mode' 0
pick '#arena-bot-0' 'Grunt'
pick '#arena-bot-1' 'Sarge'
ab select '#arena-skill' 4
ab fill '#arena-limit' 0
ab fill '#arena-time' 1
pick '#arena-model' 'sarge/default'
ab click '[data-apply-model="play"]'
ab eval 'if(!document.querySelector("#play-status").textContent.includes("Character applied"))throw Error("character rejected"); true'
capture ui-play-final
ab click '#launch-match'
ab wait --fn 'testEngine._OG_WebHUDRefresh()===1 && document.querySelector("[data-hud=map]").textContent==="maps/q3dm1.bsp" && document.querySelector("#menu").hidden'
ab eval '(()=>{testEngine._OG_WebHUDRefresh();if(testEngine._OG_WebHUD(13,0)!==0||testEngine._OG_WebHUD(16,0)!==0||testEngine._OG_WebHUD(17,0)!==1||canvas.inert)throw Error("launch options not applied");return true})()'
ab press 1
ab wait --fn 'document.querySelector("[data-hud=weapon]").textContent==="Gauntlet" && document.querySelector("[data-hud=ammo]").textContent==="∞"'
ab eval 'if(document.querySelector("[data-hud=inventory] [data-selected=true]").textContent!=="Gauntlet")throw Error("weapon slot stale"); true'
capture ui-hud-final
ab press '`'
for key in / k i l l; do ab press "$key" >/dev/null; done
ab press Enter
ab press '`'
ab wait --fn 'document.querySelector("#hud").dataset.phase==="dead"'
capture ui-death-final
ab press F10
ab click '[data-screen="match"]'
ab eval 'if(document.pointerLockElement||!canvas.inert||document.querySelector("#match-respawn").disabled)throw Error("death menu isolation");document.querySelector("#match-respawn").focus(); true'
ab keydown Enter
sleep 0.5
ab keyup Enter
ab wait --fn 'document.querySelector("#hud").dataset.phase==="active" && document.querySelector("#menu").hidden'
ab eval 'if(canvas.inert)throw Error("respawn retained inert canvas"); true'
# Real server timelimit, not a test-generated intermission snapshot.
ab wait --fn 'document.querySelector("#hud").dataset.phase==="intermission"' --timeout 100000
ab eval '(()=>{testEngine._OG_WebHUDRefresh();if(testEngine._OG_WebHUD(10,0)!==1||testEngine._OG_WebHUD(18,0)<3)throw Error("missing authoritative standings");window.finalClock=document.querySelector("[data-hud=clock]").textContent;return [...document.querySelectorAll("[data-hud=rows] tr")].map(r=>r.textContent)})()'
sleep 2
ab eval 'if(document.querySelector("[data-hud=clock]").textContent!==window.finalClock)throw Error("intermission counted as match time"); true'
capture ui-intermission-final
ab press F10
ab click '[data-screen="match"]'
ab click '#match-restart'
ab wait --fn 'document.querySelector("#hud").dataset.phase==="active" && document.querySelector("#menu").hidden'
ab eval '(()=>{testEngine._OG_WebHUDRefresh();if(testEngine._OG_WebHUD(6,0)!==0||testEngine._OG_WebHUD(8,0)>5000)throw Error("restart did not reset match");return true})()'
ab press F10
ab click '[data-screen="match"]'
ab select '#match-team' 3
ab click '#match-join-team'
ab wait --fn 'document.querySelector("#hud").dataset.phase==="spectator"'
ab press F10
ab click '[data-screen="match"]'
ab click '#match-disconnect'
ab wait --fn 'testEngine._OG_WebUIState()===1 && document.querySelector("#hud").hidden'
echo 'PASS: real DOM catalogue/model/limits launch → weapon → death → keyboard respawn → Bot standings → timed intermission → restart → spectator → leave; no observer'
