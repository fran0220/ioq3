# PC UI implementation and acceptance

First slice: functional DOM navigation over the real C/WASM engine. This is not
the completed remaster and does not authorize publishing demo data. Only the
submitted engine frame can signal OG ready. Artwork is actual Painter output;
the background source, transformation and hash live in assets/remaster/ui.

## Screen inventory and ownership

| Screen/state | Current implementation | Remaining interface/acceptance |
| --- | --- | --- |
| WASM / IDBFS / asset verification / world startup | code/web host, real stage messages | Platform and standalone; slow/missing/corrupt assets, no premature ready |
| Startup / runtime failure | DOM recovery, OG.loading.fail, persistent shell/one-shot engine iframe | Production embedded retry/fresh session; actual local replacement and IDBFS lock transfer tested |
| Overview | Painter hangar, DOM navigation | Brand/title final approval |
| Play / map / bot / mode selection | VFS catalogue, supported-mode masks, eight bot slots, skill and transactional limits | Full-content/multimode acceptance; unavailable assets remain disabled |
| Settings: volume/music/sensitivity/pitch/FOV | Numeric C allowlist, live readback, archived engine saves | Actual map input/audio and browser reload; FOV disabled until registered |
| Display | Live filtering/crosshair/FPS plus trusted root resolution/picmip preview, confirmation and rollback | Other-browser/physical-GPU acceptance; no misleading live browser gamma |
| Key bindings | 30 fixed actions, per-key slots/add/clear, explicit conflict replacement, custom-command protection | Non-US keyboard layout testing; original custom console scripts remain outside editor |
| Player profile | Transactional ASCII name, handicap, colors and installed model/skin selection | Full remade-character catalogue; Unicode requires engine text support |
| Field manual | Accessible DOM navigation, PC lifecycle instructions | Update alongside final bindings |
| In-match menu / resume | F10, UI VM open/close, releases held input | Remote game continues; local pause semantics belong to engine |
| Lobby / join / reconnect | Root native reservation UI, 20s heartbeat, persistent shell/engine lifecycle and transport notices | Published release and real multiplayer/expiry/reconnect acceptance; standalone remains unavailable |
| HUD / scoreboard / death / respawn / intermission | Leased production VM snapshot → DOM vitals/inventory/scoreboard/phases; real held respawn/scores, restart/team/leave actions | Full-content modes and multiplayer; original native HUD restores when lease expires |
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

## Display / bindings / profile slice

All additions reuse the existing Painter background and real DOM controls; no
new generated art is required. Display filter is a three-value enum, not a string
command. Crosshair 0 is off, 1..10 select the engine's ten shapes; HUD-related
controls require CA_ACTIVE even when archived cvars exist before a map loads.
Resolution and picmip use the root-owned restart/preview/confirm/rollback
transaction. The child only calls the current boot's `openDisplay()` capability;
without that capability it disables the entry and explains that the full launcher
is required. It does not copy preset state, timers, persistence or cvar commands.

Bindings use immutable action IDs and engine key-code enumeration. Existing
alternate slots are preserved. A conflict makes no mutation until confirmed;
custom executable bindings cannot be displaced even with confirmation. Esc,
console and F10..F12 are reserved. Slot changes clear held engine key states.
The UI never accepts binding command text. Name edits stage numeric character
codes and commit atomically: 1..31 printable ASCII bytes, no info delimiters,
color escapes, edge spaces or runs of four spaces. Invalid staging cannot
partially change userinfo. Existing names are read into DOM text/value only.

`settings-browser.sh` requires a local test build configured with
`-DIOQ3_WEB_TEST_OBSERVER=ON`, the test server, and separately supplied demo data.
It checks pre-init rejection, 31/32-byte name boundaries, invalid profile ranges,
protected custom bindings and conflict cancel/replace; verifies archived literal
`bind k "+forward"`, preserved alternate keys and IDBFS reload. In actual q3dm1,
instrumented real WebGL calls read back MIN_FILTER 9987 then 9984; actual SDL key
events on rebound K move the authoritative player position forward more than
20 units along view yaw. A gravity-only displacement cannot satisfy this check.
The observer is not included in production builds.

### Production match UI (2026-09-10)

`cg_ui_snapshot.c` owns the v1 read-only snapshot. Supporting CG_INIT returns a
capability magic; CG_UI_SNAPSHOT returns a VM-local static offset, never a host
pointer. The client validates bounds/version/size and copies into its own cache.
DOM calls OG_WebHUDRefresh once per animation frame, reads that cache and only
then renews OG_WebHUDEnabled. The ROM, non-archived cg_webHUD defaults to zero;
the one-second heartbeat lease restores native rendering if JS stops. No
observer exports are required. Health/armor/ammo use player state; team scores
use current configstrings rather than an older requested scoreboard response.
The displayed clock freezes at the first observed intermission snapshot, then
resets with the next match. It does not simulate server time.

Original crosshair, pickups, rewards, powerups, votes, lagometer and CTF flag
status remain engine-owned. DOM weapon slots use the real inventory bitmask;
CG_DrawWeaponSelect suppresses only duplicate pixels under the same lease.
Scoreboard visibility/fade and deferred player loading retain original rules.
Respawn is a held +attack/-attack with a dedicated input identity, not a direct
health write or zero-duration pulse. Keyboard/pointer release, blur and failure
clear that held action. Restart is local-server-only; action acceptance is not
a claim of server completion.

Play/character records come from the q3_ui VFS catalogue and are scoped to an
explicit generation. Mode support and availability are not guessed by JS.
Eight bot slots and integer limits stage before a validated launch; SP retains
the original arena roster/limits. A rejected transaction requires Refresh
content, avoiding hidden staged limits leaking into an SP retry. Accepted launch
releases C menu ownership before DOM hides, even if the client is connecting.
Existing Painter hangar artwork/provenance is reused; no duplicate paid artwork
was generated and no controls/numbers are baked into images.

Executed on Chromium/SwiftShader at 1280×720 DPR2 with Emscripten 3.1.58,
observer OFF, privately transferred official Demo data and freshly matched QVMs
plus the existing inv.h compatibility override (not a publishable asset set):

- `node --test code/web/hud.test.mjs code/web/play.test.mjs`: snapshot field/row
  mapping, one refresh, clock boundaries, literal names, catalogue generation,
  unavailable content and stale/missing rejection semantics pass.
- `cc -std=c99 code/web/tests/ui-snapshot.c code/cgame/cg_ui_snapshot.c -o /tmp/ui-snapshot && /tmp/ui-snapshot`:
  production snapshot version/size, asymmetric values, invalid clients,
  current-vs-old team scores, intermission and disconnected clearing pass.
- `bash code/web/tests/match-browser.sh <private-test-server>`: real DOM
  catalogue/model/limits → q3dm1 → Gauntlet/infinite ammo/inventory → actual
  death → keyboard-held respawn → Bot standings/timed intermission → local
  restart → spectator → disconnect passes. First fraglimit-2 match also ended
  with Grunt score 2; restart read score 0 and elapsed 822ms.
- `menu-browser.sh` rerun passes actual settings/IDBFS/fullscreen/FOV/resume and
  terminal input-failure/reload regression. Model/headmodel `visor/default`
  were independently read back from the engine-written q3config.cfg.
- Original-roster SP launch and q3tourney2 Tournament launch read matching
  production map/mode/limits. Two-bot Tournament is rejected without launching.
- The requested FFA-no-bots q3dm1 → Tournament q3tourney2, bot 0, skill 2,
  fraglimit 3 / timelimit 7 regression also passes after the disconnect-before-map
  lifecycle fix: after 15 seconds the production HUD reports q3tourney2 / 1 / 3 / 7.
- `tests/lobby-fixture.mjs` is explicitly a DOM/SDK contract fixture, not real
  platform admission: full-room disable, visibility, code validation, owner
  close, leave and sanitized failures pass without acquiring a session.

Inspected real Play available/rejected/SP, character profile, active HUD,
death/standings, in-match menu, spectator and intermission captures. Final-frame
artwork integration, ultrawide/physical GPU/other browsers, complete CTF assets,
and production embedded multiplayer remain release gates. The private Demo has
no complete CTF artwork/maps; a controlled CTF-mode HUD check showed missing
flag shader placeholders, not a validated CTF match.

**Admission still does not mean connected play.** OG.native presence is SDK
support, not proof of a provisioned release. The new root shell owns room
reservation and engine replacement. Inner `engine.html` only receives the
current boot's memory-only facade; tokens never enter URLs, storage or cvars.
The platform loading Retry is not a room-switch API. The shell closes old
transports and destroys the old iframe before requesting a fresh session.
Standalone rooms remain unavailable. Reconnect/409/expiry and actual multi-client
matches still need production release validation, not the DOM admission fixture.

### PC layout/accessibility follow-through (2026-09-11)

`ui-quality-browser.sh` passes on the production WASM fixture at 1024×600,
1280×720, 1920×1080 and 2560×1080, DPR2. The menu/status scroll viewport reserves
the actual wrapping toolbar height. Forward/reverse Tab cycles through visible,
enabled menu and toolbar controls without reaching the covered canvas. Focused
Launch remains unobscured at every size; there is no horizontal page overflow.
Ultrawide HUD vitals stay within a central 1600px span without altering the
engine viewport. Match phase changes have a polite atomic status region; rapidly
changing health/ammo/clock are not live announcements. Short-height score rows
and high-contrast preferences retain labels and non-color team markers.

Inspected 2560×1080 Play/live HUD and corrected 1024×600 scrolled Play screenshots.
Physical GPU, screen-reader output, non-US keyboards and other browser engines
still require separate acceptance. This supersedes the earlier ultrawide gate
only for the tested Chromium configuration, not every display/browser.

The root/child lifecycle browser test also passes real engine replacement,
single IDBFS write-lock transfer, context-failure retry, stop and restart. At
1024×600, child fullscreen controls enter/exit parent-document fullscreen while
the menu keeps canvas inert and pointer lock released. Closing the root rooms
dialog returns focus to the engine iframe. Its short-height capture is inspected.
Axe 4.12.1 reports zero violations for the root dialog and inner Play; named
scroll groups now have explicit group roles. Background-image contrast remains
an incomplete automatic check, not a claimed screen-reader/contrast certification.

`networkNotice` accepts only the documented transport event enum. Reconnecting
explicitly retains the existing session; failed/closed directs users to the
trusted shell. Connected removes the trouble banner but never announces a ready
Quake match. Unknown values are ignored; terminal engine failure overrides late
network events. The Node and DOM presentation fixtures pass and the banner
capture is inspected; these are not real reconnect acceptance evidence.

Subsequent `wss-status-browser.sh` passes with the actual compiled production
transport and a real local TLS WebSocket responder: auth/ready → 1012 transient
close → same-session reconnect/auth/ready → terminal 1008 close. The production
host report drives banner appearance, recovery hiding and failure text; raw
session text is not displayed. The inner `ready` event and outer `connected`
normalization both clear only the trouble notice. Failure screenshot inspected.
This is real WSS/DOM integration with a controlled responder, not platform
admission, RTC or a Quake gameplay handshake. Test service/certificate removed.

### Display entry keyboard acceptance (2026-09-11)

`display-entry-browser.sh` passes at 1024×600, 1280×720 and 2560×1080: Tab reaches
the child Display quality entry; Enter opens the root section and focuses its
heading without starting a transaction. Preset and Preview are keyboard reachable.
Actual balanced preview reads 1280×720/picmip1. Revert receives default focus;
Shift+Tab reaches Keep. Keyboard confirmation and explicit rollback return focus
to the engine iframe. The panel remains centered and above the engine toolbar.
Standalone `engine-test.html` correctly disables the unavailable root capability.

This test exposed a real ready-order focus race: the child's queued menu opening
stole focus from Revert. The root now focuses after that work with current-frame,
current-boot, preview-state and dialog guards; the previously failing assertion
passes without being removed. Separate `display-browser.sh` also passed actual
confirmation/reload, 15-second timeout rollback and context-failure rollback.
Final short-height entry and ultrawide focused-Revert captures are inspected;
the combined Web Node tests pass 29/29. This is display/input acceptance, not a
publication or whole-game release declaration.
