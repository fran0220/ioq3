#!/usr/bin/env bash
# Real production DOM and WASM. Caller supplies a private authorized data build.
set -euo pipefail
base="${1:?Usage: ui-quality-browser.sh <private-test-server>}"
ab() { agent-browser --session ioq3-ui-quality --args '--enable-unsafe-swiftshader' "$@"; }
trap 'ab close >/dev/null 2>&1 || true' EXIT
ab open "${base%/}/engine-test.html"
ab wait --fn 'document.body.dataset.ready === "true"'
ab click '#play'
for size in '1024 600' '1280 720' '1920 1080' '2560 1080'; do
    read -r width height <<< "$size"
    ab set viewport "$width" "$height" 2
    ab eval 'new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))'
    ab eval '(()=>{const m=document.querySelector("#menu").getBoundingClientRect(),c=document.querySelector("#controls").getBoundingClientRect();if(m.bottom>c.top+1||document.documentElement.scrollWidth>innerWidth)throw Error("toolbar overlap/overflow");document.querySelector("#launch-match").focus();return true})()'
    ab eval '(()=>{const b=document.querySelector("#launch-match").getBoundingClientRect(),m=document.querySelector("#menu").getBoundingClientRect();if(b.top<m.top||b.bottom>m.bottom)throw Error("focused launch obscured");return true})()'
done
ab eval '(()=>{const f=[...document.querySelectorAll("#menu button,#menu input,#menu select,#menu [tabindex=\"0\"],#controls button")].filter(e=>!e.disabled&&e.getClientRects().length);window.focusFirst=f[0];window.focusLast=f.at(-1);focusLast.focus();return true})()'
ab press Tab
ab eval 'if(document.activeElement!==focusFirst)throw Error("forward focus escaped");true'
ab press Shift+Tab
ab eval 'if(document.activeElement!==focusLast)throw Error("reverse focus escaped");true'
ab select '#arena-mode' 0
ab click '#launch-match'
ab wait --fn 'testEngine._OG_WebHUDRefresh()===1 && document.querySelector("#menu").hidden'
ab eval '(()=>{const b=document.querySelector(".vitals").getBoundingClientRect();if(b.left<479||b.right>2081||canvas.inert)throw Error("ultrawide HUD safe area/input");if(document.querySelector("[data-hud=phasePanel]").getAttribute("aria-live")!=="polite")throw Error("missing phase semantics");return true})()'
echo 'PASS: 1024/1280/1920/2560 PC layout, focused controls clear toolbar, bidirectional keyboard cycle, live ultrawide HUD and phase semantics'
