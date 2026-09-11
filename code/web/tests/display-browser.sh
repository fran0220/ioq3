#!/usr/bin/env bash
# Real production shell/WASM/IDBFS. Only disposable local browser storage is used.
set -euo pipefail
base="${1:?Usage: display-browser.sh <private-test-server-url>}"
ab() { agent-browser --session ioq3-display --args '--use-angle=swiftshader,--enable-unsafe-swiftshader' "$@"; }
trap 'ab close >/dev/null 2>&1 || true' EXIT
ab open "${base%/}/"
ab set viewport 1024 600 2
ab wait --fn 'document.body.dataset.engineState === "ready"'
ab eval 'document.querySelector("iframe").contentWindow.IOQ3_BOOT.openDisplay(); if(document.activeElement.id!=="display-title" || document.body.dataset.displayState!=="idle")throw Error("Display capability must only open and focus settings"); true'
ab select '#display-preset' balanced
ab click '#display-start'
ab wait --fn 'document.body.dataset.displayState === "preview"'
ab eval 'new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))'
ab eval 'if(document.activeElement.id!=="display-revert")throw Error("Child ready menu stole preview focus");true'
ab eval 'if(!document.querySelector("#display-current").textContent.includes("1280 × 720, texture reduction 1"))throw Error("Renderer differs from preset"); const banner=document.querySelector("#display-preview").getBoundingClientRect();const controls=document.querySelector("iframe").contentDocument.querySelector("#controls").getBoundingClientRect();if(banner.bottom>controls.top||banner.top<0)throw Error("Preview covers toolbar or escapes viewport");true'
if [[ -n "${SCREENSHOT_DIR:-}" ]]; then ab screenshot "$SCREENSHOT_DIR/display-preview-short.jpg"; fi
ab press Shift+Tab
ab eval 'if(document.activeElement.id!=="display-keep")throw Error("Keep display not keyboard reachable");true'
ab press Enter
ab wait --fn 'document.body.dataset.displayState === "idle"'
ab reload
ab wait --fn 'document.body.dataset.engineState === "ready"'
ab eval 'if(!document.querySelector("#display-current").textContent.includes("1280 × 720, texture reduction 1. Current settings."))throw Error("Confirmation did not persist");true'
ab click '#open-lobby'
ab select '#display-preset' high
ab click '#display-start'
ab wait --fn 'document.body.dataset.displayState === "preview"'
ab eval 'if(!document.querySelector("#display-current").textContent.includes("1920 × 1080, texture reduction 0"))throw Error("High preset not applied");window.oldPreview=document.querySelector("iframe");true'
sleep 16
ab wait --fn 'document.body.dataset.engineState === "ready" && document.querySelector("iframe") !== window.oldPreview'
ab eval 'if(!document.querySelector("#display-current").textContent.includes("1280 × 720, texture reduction 1"))throw Error("Timeout leaked preview to IDBFS");true'
ab click '#open-lobby'
ab select '#display-preset' high
ab click '#display-start'
ab wait --fn 'document.body.dataset.displayState === "preview"'
ab eval 'window.oldPreview=document.querySelector("iframe");oldPreview.contentDocument.querySelector("canvas").dispatchEvent(new Event("webglcontextlost",{cancelable:true}));true'
ab wait --fn 'document.body.dataset.engineState === "ready" && document.querySelector("iframe") !== window.oldPreview'
ab eval 'if(!document.querySelector("#display-current").textContent.includes("1280 × 720, texture reduction 1"))throw Error("Failed preview did not restore settings");true'
# Hold only the parent's focus RAF; the production child keeps its normal ready
# microtask. Exercise both cancelled state and replacement identity boundaries.
ab click '#hide-lobby'
ab click '#open-lobby'
ab eval 'window.originalRAF=window.requestAnimationFrame;window.focusCallbacks=[];window.requestAnimationFrame=fn=>{focusCallbacks.push(fn);return 0};true'
ab click '#display-start'
ab wait --fn 'document.body.dataset.displayState === "preview"'
ab eval 'if(focusCallbacks.length!==1)throw Error("Expected one deferred focus");window.oldPreview=document.querySelector("iframe");document.querySelector("#open-lobby").focus();document.querySelector("#display-revert").click();focusCallbacks[0]();if(document.activeElement.id!=="open-lobby")throw Error("Cancelled callback stole focus");window.requestAnimationFrame=originalRAF;true'
ab wait --fn 'document.body.dataset.engineState === "ready" && document.querySelector("iframe") !== window.oldPreview'
ab click '#open-lobby'
ab click '#display-start'
ab wait --fn 'document.body.dataset.displayState === "preview"'
ab eval 'new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))'
ab eval 'document.querySelector("#display-keep").focus();focusCallbacks[0]();if(document.activeElement.id!=="display-keep")throw Error("Previous frame callback stole new preview focus");window.oldPreview=document.querySelector("iframe");document.querySelector("#display-revert").click();true'
ab wait --fn 'document.body.dataset.engineState === "ready" && document.querySelector("iframe") !== window.oldPreview'
echo 'PASS: actual display confirm/reload, 15s/context rollback, short-height toolbar, keyboard focus and cancelled/replaced focus callbacks'
