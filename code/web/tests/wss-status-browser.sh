#!/usr/bin/env bash
# Requires wss-status-server.py on 4175 with a local disposable TLS certificate.
# Tests the actual production transport and report/UI path, not Quake admission.
set -euo pipefail
base="${1:?Usage: wss-status-browser.sh <private-engine-test-server>}"
init="$(realpath "$(dirname "$0")/wss-status-init.js")"
ab() { agent-browser --session ioq3-wss-status --ignore-https-errors --init-script "$init" --args '--enable-unsafe-swiftshader,--ignore-certificate-errors' "$@"; }
trap 'ab close >/dev/null 2>&1 || true' EXIT
ab open "${base%/}/engine-test.html"
ab set viewport 1280 720 2
ab wait --fn 'document.querySelector("#connection-notice").textContent.includes("Connecting transport")'
ab wait --fn 'document.querySelector("#connection-notice").hidden'
ab wait --fn 'document.querySelector("#connection-notice").textContent.includes("existing session")'
ab eval 'if(document.querySelector("#connection-notice").hidden)throw Error("real reconnect callback not displayed");true'
ab wait --fn 'document.querySelector("#connection-notice").hidden'
ab wait --fn 'document.querySelector("#connection-notice").textContent.includes("Connection failed")'
ab eval 'if(document.querySelector("#connection-notice").hidden||document.body.textContent.includes("local-transport-fixture"))throw Error("failure hidden or credential displayed");true'
if [[ -n "${UI_SCREENSHOT_DIR:-}" ]]; then ab screenshot "$UI_SCREENSHOT_DIR/ui-wss-failed.png"; fi
echo 'PASS: real WSS connecting → ready → 1012 reconnect same session → ready → 1008 failure reaches production menu; not a Quake match/admission test'
