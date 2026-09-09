# PC Web build and host

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

For a real-WASM IndexedDB round trip, run the test server as a supervised service:

```sh
amp orb service start ioq3-web-tests --port 4174 \
  --command 'python3 code/web/tests/serve.py build-web/Release'
```

Open `/tests/runtime.html` through the local browser tool. Write the asymmetric
settings fixture, reload and require `wasm:true,idbfs:true,matches:true`; then
remove it. This is real WASM/IDBFS, not gameplay verification. The test route is
served only by the test server and is never copied into the Web release.

Also exercise the root page with the empty manifest, missing/corrupt assets,
module/network failures and multiple tabs. Capture and inspect loading/error
states. A usable menu, actual audio output, gameplay mouse capture and first-frame
ready integration require a complete authorized data package and the shared
engine call sites; unit fixtures must never be reported as playable-game proof.
