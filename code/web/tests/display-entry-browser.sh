#!/usr/bin/env bash
# Production child menu → trusted root transaction, using real keyboard events.
set -euo pipefail
base="${1:?Usage: display-entry-browser.sh <private-test-server>}"
ab() { agent-browser --session ioq3-display-entry --args '--enable-unsafe-swiftshader' "$@"; }
trap 'ab close >/dev/null 2>&1 || true' EXIT
ab open "${base%/}/"
ab wait --fn 'document.body.dataset.engineState === "ready"'
for size in '1024 600' '1280 720' '2560 1080'; do
    read -r width height <<< "$size"
    ab set viewport "$width" "$height" 2
    ab eval 'document.querySelector("iframe").contentDocument.querySelector("[data-screen=display]").focus()'
    ab press Enter
    ab eval '(()=>{const d=document.querySelector("iframe").contentDocument;if(d.querySelector("#display-quality").disabled)throw Error("missing trusted capability");d.querySelector("#return-engine").focus();return true})()'
    ab press Tab
    ab eval 'if(document.querySelector("iframe").contentDocument.activeElement.id!=="display-quality")throw Error("Display entry not keyboard reachable");true'
    if [[ -n "${UI_SCREENSHOT_DIR:-}" && "$width" == 1024 ]]; then ab screenshot "$UI_SCREENSHOT_DIR/ui-display-entry-short.png"; fi
    ab press Enter
    ab eval 'if(!document.querySelector("#room-panel").open||document.activeElement.id!=="display-title"||document.body.dataset.displayState!=="idle")throw Error("entry changed settings or failed focus transfer");true'
    ab press Tab
    ab eval 'if(document.activeElement.id!=="display-preset")throw Error("preset not next after section heading");true'
    ab select '#display-preset' balanced
    ab press Tab
    ab eval 'if(document.activeElement.id!=="display-start")throw Error("preview button not next");true'
    ab press Enter
    ab wait --fn 'document.body.dataset.displayState === "preview"'
    ab eval '(()=>{const b=document.querySelector("#display-preview").getBoundingClientRect(),c=document.querySelector("iframe").contentDocument.querySelector("#controls").getBoundingClientRect();if(b.top<0||b.bottom>c.top||Math.abs((b.left+b.right-innerWidth)/2)>1)throw Error("preview obscured or not centered");if(document.activeElement.id!=="display-revert")throw Error("safe revert focus absent: "+document.activeElement.tagName+"#"+document.activeElement.id);if(!document.querySelector("#display-current").textContent.includes("1280 × 720, texture reduction 1"))throw Error("actual renderer not preset");return true})()'
    if [[ -n "${UI_SCREENSHOT_DIR:-}" && "$width" == 2560 ]]; then ab screenshot "$UI_SCREENSHOT_DIR/ui-display-preview-wide.png"; fi
    if [[ "$width" == 1024 ]]; then
        ab press Shift+Tab
        ab eval 'if(document.activeElement.id!=="display-keep")throw Error("keep not keyboard reachable");true'
    fi
    # Confirm at short size, explicitly revert at other sizes; timeout/fault
    # behavior is covered by the separate production display-browser suite.
    ab press Enter
    ab wait --fn 'document.body.dataset.displayState === "idle" && document.body.dataset.engineState === "ready"'
    ab eval 'if(document.activeElement!==document.querySelector("iframe"))throw Error("transaction failed to return frame focus");true'
done
ab open "${base%/}/engine-test.html"
ab wait --fn 'document.body.dataset.ready === "true"'
ab click '[data-screen="display"]'
ab eval 'if(!document.querySelector("#display-quality").disabled||!document.querySelector("#display-quality-note").textContent.includes("full game launcher"))throw Error("standalone implies unavailable preview capability");true'
echo 'PASS: child keyboard entry/root heading/preset/preview/keep/revert/focus at short, standard and ultrawide sizes; standalone capability unavailable'
