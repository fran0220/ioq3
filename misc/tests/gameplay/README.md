# Real-WASM gameplay regression (technical demo only)

This harness runs the actual ioq3 WASM engine, QVM game rules, SDL input,
renderer and local server. Chromium CDP dispatches native input; the runner
does not synthesize DOM events, inject game commands into memory, teleport,
grant items, change health or change scores. Setup commands are typed into the
real console. The read-only observer reads authoritative client snapshots,
not a fake DOM or a prediction computed by the test.

This is **not the final game, production host, multiplayer service test or
release artifact**. The original demo assets must never be published from this
directory. Missing newer sounds remain a known demo/current-QVM mismatch.

## Prepare locally

Requirements: Emscripten **3.1.58**, Node 22+ with global WebSocket, Python 3,
agent-browser/Chromium, and a locally extracted official Linux Quake 3 demo
with `demoq3/pak0.pk3` and `Help/Q3A_EULA.txt` retained. The preparation script
does not download data. Official technical fixture source:

https://ftp.gwdg.de/pub/misc/ftp.idsoftware.com/idstuff/quake3/linux/linuxq3ademo-1.11-6.x86.gz.sh

For that exact installer, `tail -n +165 installer.sh | tar xzf -` extracts it.
Keep the extracted EULA/help and installer provenance. Do not put them in Git.

```sh
# With the pinned SDK activated; this observer MUST NOT enter release builds.
emcmake cmake -S . -B build-gameplay-engine -DCMAKE_BUILD_TYPE=Release \
  -DIOQ3_WEB_TEST_OBSERVER=ON
cmake --build build-gameplay-engine --parallel 4
node misc/tests/gameplay/prepare.mjs build-gameplay-engine/Release \
  /path/to/extracted-demo build-gameplay-fixture
```

Preparation requires a new output directory, preserves the demo EULA/help,
copies the real WASM/JS, packages current QVMs, and writes input SHA-256 hashes
to `technical-fixture.json`. It does not edit production `code/web` or engine
gameplay. The fixture has no saved settings, credentials or external network.

**Bot ABI compatibility:** demo 1.11 `botfiles/inv.h` uses bullets index 16 and
health index 24. Current `code/game/inv.h` uses 19 and 29 even for baseq3.
Without a matching header, the old weapon-weight scripts falsely see no ammo,
select the gauntlet and produce misleading bot failures. The separate QVM PK3
therefore overrides only `botfiles/inv.h` with the current GPL engine header;
original `pak0.pk3` is unchanged. Provenance records the override and its hash.
This is a test-data ABI adaptation, not an assertion that all demo scripts,
navigation data or sounds match the current game.

## Run through an actual browser

In an Amp orb use a supervised local service, never publish the fixture:

```sh
amp orb service start q3-gameplay --port 8767 \
  --command 'python3 -m http.server 8767 --bind 0.0.0.0 --directory build-gameplay-fixture'
FLAGS='--use-angle=swiftshader,--enable-unsafe-swiftshader,--enable-logging,--log-file=/tmp/q3-gameplay-chrome.log'
ab() { agent-browser --session q3-gameplay --args "$FLAGS" "$@"; }
ab open http://127.0.0.1:8767/
ab set viewport 1280 720 2
CDP=$(ab get cdp-url)
node misc/tests/gameplay/run.mjs "$CDP" /tmp/q3-baseline baseline
node misc/tests/gameplay/run.mjs "$CDP" /tmp/q3-reliability reliability
node misc/tests/gameplay/run.mjs "$CDP" /tmp/q3-bot bot
ab close
```

These loopback URLs are for orb tools, not user-facing portal links. Use a
fresh output directory for each run. The browser must have only the intended
test page open; the driver attaches to the first HTTP page in its CDP session.
Do not run multiple runners against the same page concurrently.

Each mode writes timestamped JSONL input/console/snapshot evidence, JSON
assertion results, and actual engine screenshots. A failing assertion sets a
nonzero exit status and saves the failing snapshot. Inspect screenshots before
claiming visual success. Hashes identify the binaries and data under test;
the read-only observer is not present in default/production builds.

## What the checks mean

- `baseline`: starts at the original q3dm1 spawn; records the post-capture
  angles, then uses real mouse input to establish −45° yaw / zero pitch before
  measuring the turn toward −90° (the >30° assertion remains unchanged).
  Pointer capture/recentring can itself rotate the view in some browser runs;
  that setup movement is not the measured turn. W moves south to real armor shards; armor must increase and
  position must move over 100 units. Space must produce positive vertical
  velocity, a higher position and `ENTITYNUM_NONE` ground state, followed by
  landing. Mouse attack must reduce actual machinegun ammunition.
- `reliability`: HDR=0 and HDR=1 each execute `vid_restart`, wait for a new
  cgame initialization, then require real keyboard turn input to change
  snapshot angles. Switch q3tourney2 → q3dm17 → q3dm1 and verify actual map
  configstrings and a live WebGL context. Force `WEBGL_lose_context`, then
  perform a full page reload and require fresh active snapshots/context.
  This does **not** test in-place restoration of stale renderer GL objects.
- `bot`: uses q3dm17 for actual falling death and attack-click respawn, then
  starts a fresh scored q3dm1 round with Sarge at skill 3 and fraglimit 3.
  Bot tracking uses only visible snapshot entities, turns through existing
  keyboard-look bindings, and fires actual mouse input. It requires increased
  `PERS_HITS`, intermission at score ≥3, actual `PM_INTERMISSION`, then a console
  `map_restart 0` returning to a living player with reset score/intermission.
  Either player may win. The runner is an automated test player, not a claim
  that a human completed the match. No bot AI or damage rules are changed.

Captured mouse rotation is tested separately from keyboard tracking because
CDP absolute mouse positions outside the viewport stop producing reliable
relative motion. Console input uses `/command`, not unprefixed text (which
Quake treats as chat during play). It waits for the real key catcher and
console echo rather than assuming a fixed sleep means the command executed.

## Release limits

Passing these tests establishes only this finite local gameplay baseline on
the tested browser/GPU. It does not establish all maps/modes/characters,
balanced gameplay, production UI, platform iframe, multiplayer networking,
complete audio, physical-GPU compatibility, sustained performance or shipping
readiness. Do not reuse demo content or observer-enabled binaries for release.
