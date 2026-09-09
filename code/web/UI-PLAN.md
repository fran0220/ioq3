# PC UI implementation and acceptance

First slice: functional DOM navigation over the real C/WASM engine. This is not
the completed remaster and does not authorize publishing demo data. Only the
submitted engine frame can signal OG ready. Artwork is actual Painter output;
the background source, transformation and hash live in assets/remaster/ui.

## Screen inventory and ownership

| Screen/state | Current implementation | Remaining interface/acceptance |
| --- | --- | --- |
| WASM / IDBFS / asset verification / world startup | code/web host, real stage messages | Platform and standalone; slow/missing/corrupt assets, no premature ready |
| Startup / runtime failure | DOM recovery, OG.loading.fail capability detection | iframe replacement, fresh session, IDBFS preserved |
| Overview | Painter hangar, DOM navigation | Brand/title final approval |
| Play / map / bot / mode selection | Explicit return to original engine menu | Coordinated q3_ui arena catalogue + validated launch interface, not arbitrary command text |
| Settings: volume/music/sensitivity/pitch/FOV | Numeric C allowlist, live readback, archived engine saves | Actual map input/audio and browser reload; FOV disabled until registered |
| Display / bindings / player profile | Original engine menu | Structured renderer modes, restart transaction/rollback, key conflict handling and profile validation |
| Field manual | Accessible DOM navigation, PC lifecycle instructions | Update alongside final bindings |
| In-match menu / resume | F10, UI VM open/close, releases held input | Remote game continues; local pause semantics belong to engine |
| Lobby / join / reconnect | Host session injection and network status | Platform room catalogue + fresh capability flow + failure/rejoin UX |
| HUD / scoreboard / death / respawn / intermission | Original cgame | Main-thread coordinated snapshot contract and engine-native gameplay HUD; no duplicate game rules |
| Credits / licenses / provenance | This asset record and engine source licenses | Complete product-level asset ledger and public source offer before release |

## Delivery dependencies

1. **This host slice** owns code/web and assets/remaster/ui. Main owns CMake
   deployment copying menu.mjs and ui/hangar.webp, shared engine wiring and tests.
   UI text/buttons remain DOM, not image pixels. The palette is graphite, ivory,
   cyan and restrained orange; no CSS-generated artwork substitutes for Painter.
2. **Play/profile/display migration** needs q3_ui coordination before replacing
   the original menu. Enumerate valid content from engine VFS; validate launches
   and latched changes in C; preserve working menu on failure. Test absent maps,
   bot roster, invalid modes, resolution restart failure and settings persistence.
3. **Online flow** depends on platform rooms and actual native/WSS/RTC playtests.
   Credentials remain in Module.ogNetwork only. Explicit reconnect and fresh
   session after full reload; no secret-bearing URL, config or manifest fields.
4. **HUD and end-of-match work** depends on cgame-owned observations, not browser
   simulation. Verify health/ammo/score/team/timer, death/respawn and scoreboards
   against actual server state. Generate additional Painter assets per approved
   screen need and retain every source attachment/hash/cost availability record.
5. **Polish/release gate**: 1280×720 through ultrawide PC, keyboard-only focus,
   readable contrast, pointer-lock/fullscreen/audio reacquisition, tab/blur,
   offline bot match and remote multi-client match, disconnect/reconnect, IDBFS
   errors and loading recovery. Capture actual affected states, not only mocks.
   No mobile UI and no unverified demo publication.

## Safety and tests

OG_WebUIState requires live client + UI VM; only disconnected/active states allow
settings/menu changes. The host additionally requires the real ready event.
OG_WebSetting returns NaN when absent; OG_WebSetSetting rejects unknown IDs,
non-finite/out-of-range values and zero pitch. No arbitrary cvar or command API.
DOM keyboard events are isolated from SDL while the overlay is visible.
SDL IN_Frame respects the menu ownership predicate, including fullscreen; it
must not reacquire Pointer Lock over DOM controls. Failure mode 3 clears menu
ownership but sets a terminal input block: no menu/settings mutations or mouse
recapture until full reload. The underlying canvas is inert while covered.
Engine archive writes and successful-close → IDBFS synchronization remain the
source of truth; successful C readback is not reported as a completed disk save.

The local test server's /engine-test.html exposes the **actual compiled module**
for boundary and persistence assertions. It is never copied to a release.
Authorized local data must be supplied separately; do not download it in tests.

## First-slice verification (2026-09-09)

- Real Emscripten 3.1.58 engine with locally transferred official demo data,
  original source GWDG idsoftware mirror linuxq3ademo-1.11-6; data/EULA stayed in
  ignored build output and were not published or committed.
- menu-browser.sh passes pre-init rejection, invalid numeric boundaries, volume
  0.35/sensitivity 7.3 C readback and IDBFS reload, continuous DOM navigation,
  fullscreen enter/exit without capture, actual q3dm1 entry, FOV 105 and resume.
- Fault-injected post-ready context-loss event while C still runs: terminal menu
  calls reject, no recapture for 12 frames and a click, reload resets the block.
- Separate live DOM check reads music 0.15 and negative pitch -0.028 from C.
- Host browser suite passes real SDL canvas size/resize/pixel checks, IDBFS,
  missing-data/retry and exclusive-tab lease. Control fixture tests are explicitly
  not gameplay. Node host/network tests and production persistence/frame/input
  fault/matrix checks pass.
- Inspected 1280×720 DPR2 overview, settings, manual, in-match and failure screens.
  Settings help bottom is at 639px, above toolbar at 662px; unavailable FOV has
  readable disabled state. No claim of ultrawide/other-browser release acceptance.
