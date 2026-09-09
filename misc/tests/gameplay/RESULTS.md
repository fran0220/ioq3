# Observed gameplay baseline — 2026-09-09

Environment: Emscripten 3.1.58 Release, Chromium 152 headless on Linux,
ANGLE SwiftShader, 1280×720 browser viewport at DPR 2, 800×600 engine canvas.
The black margin outside that fixed canvas is intentional test-fixture layout,
not the production UI. Native Debug full build also passed.

The observer-enabled binary included the read-only clock/snapshot bridge from
[cf45cd75](https://github.com/fran0220/ioq3/commit/cf45cd75). Its incremental
build's embedded version still said d6a45460; the evidence fixture manifest
records binary/data SHA-256 hashes rather than relying on that version text.

## Final executed results

Commands run against an actual agent-browser CDP session:

```sh
node misc/tests/gameplay/run.mjs "$CDP" /tmp/gameplay-final baseline
# PASS mouse-turn
# PASS move-and-pickup
# PASS jump-and-land
# PASS mouse-fire-consumes-ammo

node misc/tests/gameplay/run.mjs "$CDP" /tmp/gameplay-final reliability
# PASS HDR0-vid_restart
# PASS HDR1-vid_restart
# PASS map-switch-q3tourney2
# PASS map-switch-q3dm17
# PASS map-switch-q3dm1
# PASS forced-context-loss-full-reload

node misc/tests/gameplay/run.mjs "$CDP" /tmp/gameplay-enclosed2 bot
node misc/tests/gameplay/run.mjs "$CDP" /tmp/gameplay-repeat bot
# Both runs:
# PASS death-and-click-respawn
# PASS shooting-damages-bot
# PASS bot-fraglimit-score-screen
# PASS match-restart
```

All four invocations exited 0. The final browser native log contained zero
`GL_INVALID` or `GPU process exited` entries. Screenshots of baseline gameplay,
HDR/LDR restarts, each map, bot hit, death, score screen and restart were
inspected. Renderer appearance alone was not used to assert gameplay actions.

Independent snapshot evidence from the first final run:

| Check | Before | Observed result |
|---|---|---|
| Movement / pickup | origin (212,2360,56.125), armor 0 | origin (212.011,2151.053,25.916), armor 5 |
| Jump | z=24.125 on world ground | z=35.699, positive upward velocity, groundEntityNum=1023; then landed |
| Mouse fire | machinegun ammo 100 | ammo 97 |
| Falling death | alive on q3dm17 | health −999, pm_type=3, killed=1, score=−1 |
| Click respawn | dead | health 125, pm_type=0; killed=1 retained |
| Bot round hit | hits=0 | hits=1 at serverTime 24100; later hits=3 |
| Bot kills | player killed=0 | killed=3, actual Sarge kill-feed messages |
| Fraglimit | scores below 3 | scores1=3, scores2=0, intermission="1" |
| Score screen | pm_type=3 after final death | pm_type=5 at serverTime 52450; visible Sarge 3 / BrowserTest 0 |
| Restart | intermission active | pm_type=0, health 125, score/killed/hits=0 at serverTime 53500 |

The second complete Bot run repeated the same assertions with a fresh fixture
reload. It is evidence of repeatability here, not a guarantee for every seed,
map, browser or hardware combination.

## Failures investigated rather than hidden

- Early runs with the untouched 1.11 demo bot inventory header repeatedly
  timed out before fraglimit. Inventory indices differ from the current QVM:
  old scripts thought armed bots had no ammunition and selected gauntlets.
  The documented test-only GPL inventory overlay restored actual machinegun,
  shotgun and rocket selection. Original demo data remains unmodified.
- Waiting for a bot to attack an elevated q3dm17 spawn and continuously firing
  while turning produced ammunition waste and void suicides; those runs failed.
  Final inputs use q3dm17 for falling death, then the enclosed q3dm1 for the
  scored match, and turn before firing. The fraglimit remains 3, skill remains
  3, and no game damage, movement, AI or scoring rules were changed.
- Fixed sleeps around console toggling and a missing final aiming re-check
  caused test-driver false failures. Final driver waits for actual key catcher
  transitions/console echo and checks actual final snapshot angles. A diagnostic
  `in_restart` was tried during investigation but is absent from final tests.
  The initial interpretation of eFlags=4100 as connection loss was wrong:
  it is TALK|TELEPORT. Clock/usercmd observations showed real commands reaching
  snapshots; no SDL fix was justified by those samples.

## Not established

This does not validate the final remaster assets, UI, complete sound set,
all maps/modes/bots, multiplayer, physical GPUs, cross-browser behavior,
long-session performance or in-place context restoration. Full reload after
loss passed; stale-object restoration was not claimed. The production host's
loss message and reload were separately observed during diagnosis, but this
runner's finite gameplay contract uses its own real-WASM test host.

Review artifacts and JSONL snapshots are retained in the source Amp thread's
`.amp/in/artifacts/gameplay-evidence/`, not in the release or Git. Demo content,
observer-enabled binaries and diagnostic logs are not release deliverables.
