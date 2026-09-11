# PC Web build and host

The DOM menu rollout and full screen/interface inventory are in [UI-PLAN.md](UI-PLAN.md).
The menu uses actual Painter artwork and numeric C settings/profile/binding
bridges. Play uses the real VFS map/mode/bot/model catalogue and validated staged
launch options. The production cgame snapshot drives a leased DOM HUD and match
actions; native HUD remains the fallback. Restart-dependent display quality is
still engine-owned. Native room reservations are distinct from engine entry:
trusted session lifecycle integration and production multiplayer validation are
still required. This is not the completed remaster or a publishable Demo build.

Run `.agents/setup` in an orb, or activate Emscripten **3.1.58** manually:

```sh
emcmake cmake -S . -B build-web -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build-web --parallel 2
```

`build-web/Release/index.html` is the entry point. Serve the directory over HTTP
for local development or HTTPS in production. The target requires WebGL2 and a
secure-context Web Locks API. The orb setup preserves the native Debug build,
installs the SDK outside the repository and exposes it in new login shells.

The default manifest deliberately contains **no game data**. The runtime can
load WASM and restore IndexedDB, but reports missing data without calling ready.
It is not a playable build. The user has authorized remake/publication of the
original content; the source assets still have to be supplied by the asset team.
Never download an unverified commercial PK3 to make this check green.

## Resource contract

Install authorized PK3 packages into `<release>/baseq3/` alongside the matching
generated `<release>/baseq3/vm/{cgame,qagame,ui}.qvm`, then run:

```sh
node code/web/make-manifest.mjs build-web/Release baseq3
```

This hashes existing PK3/QVM files; it never downloads or generates game data.
It refuses a QVM-only package. The manifest is schema version 1, with `basegame`,
content-derived `revision`, and `files: [{path, bytes, sha256}]`. Paths are literal
same-origin relative paths under the selected basegame. Every asset is size/hash
checked before entering MEMFS. A missing or corrupt required asset fails boot;
there are no silently optional packages. For a different basegame provide its
complete standalone data. Missionpack layering is not yet supported by this
single-basegame manifest; do not claim that expansion is playable with it.

Reconfiguration preserves an existing generated manifest. Re-run the manifest
command whenever QVMs or packages change. `EMSCRIPTEN_PRELOAD_FILE=ON` now errors
with migration instructions, rather than bypassing verification/persistence.
Build from a clean output directory for publication; do not ship old demo shells,
tests, configuration secrets, or development artifacts from incremental builds.

## Engine and platform boundaries

`web_bridge.h` is included only by Emscripten engine call sites. Main-thread hooks:

- `OG_WebFrame(1, 0)` after a real, functional menu or active-game frame has been
  submitted. Never signal from renderer initialization or WASM runtime startup.
- `OG_WebFrame(0, 1)` after a successful home config/state file write/close.
  The host serializes and debounces IndexedDB sync. Failed saves stay dirty and
  can be retried with **Save settings**. Failed startup restore stops boot to
  prevent overwriting an existing save with defaults.
- `_OG_WebLoseFocus()` clears held keys and queued sound. Browser blur, hidden
  state and pointer-lock loss invoke it. It does not pause a remote server.
- `_OG_WebResumeAudio()` resumes existing SDL2/OpenAL browser contexts on actual
  pointer/keyboard gestures. Esc releases capture; reacquisition is explicit.

Player files live under `/home/players` (IDBFS); packages remain outside this
mount. An origin-wide Web Lock prevents simultaneous tabs from overwriting the
same player database. Retry reloads the whole engine/iframe instead of trying to
reuse an aborted Emscripten runtime. Browser storage deletion or denied quota is
not a cloud save guarantee. Export/import and migrations remain later work.

The injected `window.OG` is optional, never bundled. Loading begins before
window.load to disable SDK auto-ready. Embedded loading/error screens belong to
the portal; standalone has its own status panel. Only the engine frame hook calls
`OG.ready()`. `OG.loading.fail({code,message,retryable:true})` is capability
detected; older SDKs receive an honest failed stage, never a fake ready. Portal
Retry must destroy/recreate the iframe. Fullscreen uses `OG.fullscreen(true/false)`
when present, native APIs standalone. Explicit enter/exit controls avoid inventing
a synchronized toggle state the current SDK does not expose.

## Optional native multiplayer

Before app.mjs executes, trusted hosting integration may supply:

```js
window.IOQ3_BOOT = { getSession: async () => acquireFreshRoomSession() };
```

The function must return null for offline, or the platform session object:
`{sessionId, token, endpoint, expiresAt, maxDatagramBytes:16384, reconnectGraceMs:15000}`.
The endpoint must be WSS without userinfo, query or fragment; expiresAt is an ISO
timestamp. Acquisition uses the platform's authorized native-room service, not
the AI Gateway. Never put a join capability/token into this file or bundle.
Optional `rtcEndpoint` follows the same WSS URL restrictions and is copied into
the frozen in-memory session; omission preserves compatibility with WSS-only
sessions. No RTC credentials or ICE configuration belong in player settings.

After assets load, the host freezes that session into read-only `Module.ogNetwork`
before `callMain`. An optional `Module.onNativeNetworkStatus({state,code})` reports
connection state. With no session the host sets net_enabled 0. With a session it
sets net_enabled 1 and connects to the fixed engine peer `origingame`; the platform
room allowlist owns the real UDP target. The engine owns og-udp-v1 authentication,
datagrams and reconnect. Credentials never enter console arguments, archived
cvars, URLs, manifests or IDBFS. Exceptions from session acquisition are sanitized.

## Verification

Use Node 22+ (not the SDK's private Node 16) or Bun:

```sh
node --test code/web/host.test.mjs
# or: bun test code/web/host.test.mjs
```

Build the real SDL2/WebGL2 canvas regression probe with the same pinned SDK,
then run the test server as a supervised service:

```sh
emcc code/web/tests/canvas-probe.c -O2 -sUSE_SDL=2 \
  -sMIN_WEBGL_VERSION=2 -sMAX_WEBGL_VERSION=2 -sEXPORT_ES6 \
  -o build-web/canvas-probe.js
amp orb service start ioq3-web-tests --port 4174 \
  --command 'python3 code/web/tests/serve.py build-web/Release'
```

`/tests/canvas.html` uses the generated production template with real SDL2/WASM,
not a fake renderer. SDL2 in this SDK hardcodes `#canvas`; passing Module.canvas
alone does not satisfy its resize/event selectors. The suite requires matching
SDL and WebGL backing sizes at 800×600 and 1024×768, plus an upper-right green
pixel outside the default 300×150 canvas. Neither this probe nor its outputs
belong in the release directory. It does not certify game content or gameplay.

Open `/tests/runtime.html` through the local browser tool. Write the asymmetric
settings fixture, reload and require `wasm:true,idbfs:true,matches:true`; then
remove it. This is real WASM/IDBFS, not gameplay verification. The test route is
served only by the test server and is never copied into the Web release.

`bash code/web/tests/browser.sh "$TEST_SERVER_URL"` runs these checks using the
installed agent-browser and closes its session afterward. It also tests native
browser fullscreen, Pointer Lock and AudioContext resume with `/tests/controls.html`:
that route uses an explicitly fake engine to exercise the real production host
DOM/event handlers. It does not certify the C audio backend or gameplay. Append
`?hold` to that fixture URL to inspect the standalone loading layout.

Also exercise the root page with the empty manifest, missing/corrupt assets,
module/network failures and multiple tabs. Capture and inspect loading/error
states. A usable menu, actual audio output, gameplay mouse capture and first-frame
ready integration require a complete authorized data package and the shared
engine call sites; unit fixtures must never be reported as playable-game proof.

With separately supplied authorized local data including q3dm1, run
`bash code/web/tests/menu-browser.sh "$TEST_SERVER_URL"`. It drives actual compiled
C exports through /engine-test.html: rejects pre-init/invalid setting access,
changes values through DOM, reloads IDBFS, navigates screens and fullscreen,
then enters a real map through SDL key events and checks in-match menu/FOV/resume.
No test route or test data is deployed. Its values live only in that disposable
browser session. Do not run this on a published build or download data in tests.

`bash code/web/tests/settings-browser.sh "$TEST_SERVER_URL"` adds actual GPU
filtering, profile validation, key conflict/protected-script checks and IDBFS
reload. Configure this local test build with `-DIOQ3_WEB_TEST_OBSERVER=ON` so its
final rebound-key check can observe authoritative movement in q3dm1. Reconfigure
with that flag OFF for production; never deploy this test server or demo data.

`wss-status-browser.sh` exercises the actual production WASM transport against
`tests/wss-status-server.py`, a local TLS WebSocket responder, not a Quake server
or platform admission API. Install Python `websockets==15.0.1`, create a disposable
localhost certificate/key outside tracked files, and start the responder with
`--cert <cert.pem> --key <key.pem> --port 4175` as an orb service. Run the browser
script against the private engine test server. It uses the explicit test-only
boot session in `wss-status-init.js`, never replaces WebSocket, and checks real
auth/ready, transient 1012 close/same-session reconnect, recovery and terminal
1008 close reaching the production banner. Stop that service and delete the
disposable certificate/key afterward. These tests do not certify multiplayer
gameplay, production room admission or RTC; no test assets go into a release.

## Display preview is a disposable engine transaction

The persistent root's Display quality section offers fixed 720p/picmip 1,
1080p/picmip 0, and desktop-resolution/picmip 0 presets. `boot.openDisplay()` only
opens, scrolls and focuses that section; it does not start a preview or set cvars.
Preview replaces the engine (ending a local match or reconnecting a reserved
room). Read-only `OG_WebDisplay(0..2)` reports actual width, height and picmip;
renderer fallback cannot be confirmed as a successful preset.

The root starts the 15-second confirmation deadline after a functional frame
and verified display settings, with a separate two-minute startup limit. A
timeout, cancellation or failed preview destroys the child and reloads saved
settings. All IDBFS flush paths are held during preview, including automatic,
manual, focus and disposal saves. Only confirmation enables persistence and
saves the allowlisted preset; other changes made during an unconfirmed preview
are discarded too. Root reload also discards an unconfirmed preview.

`node --test code/web/{host,lifecycle,display,hud,play}.test.mjs` checks timer,
stale completion, mount/cancel, storage failure and renderer-fallback boundaries.
`bash code/web/tests/display-browser.sh "$TEST_SERVER_URL"` runs actual WASM
720p confirmation/reload, 1080p timed rollback and context-failure rollback,
including the 1024×600 toolbar clearance check. This verifies local display
transactions, not platform room admission or a preserved multiplayer match.
