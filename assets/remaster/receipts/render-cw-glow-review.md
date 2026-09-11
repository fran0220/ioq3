# Strict v6 CW lamp glow and foreground-depth review

This is renderer-orb evidence for the v6 additive companion, not v7/full-game
art acceptance, collision/gameplay acceptance, or a point-light shadow test.
Private Demo BSP input stayed on loopback; no portal or publication was used.

## Exact input and control

- Scene: `environment-scene-q3dm1-v6-cw.pk3`, SHA256
  `df217c6ddbb90b1d0a566f1df07469ae732b84479cb2e87329c2b2d23f5a4c9c`.
- Control: `environment-v6-cw-glow-off.pk3`, SHA256
  `99072513ed3ab4feedee8fcc84aa81f46e464d7536fcbd29159107e58ee8cd1c`.
- Independent ZIP/MD3 comparison: only floor/wall lamp MD3 differ. Their last
  companion surface is removed (7→6 and 5→4 surfaces); frame data, opaque surface
  bytes, placement JSON and all other ZIP members are identical.
- Private neutral-map input SHA256
  `bb08ca72689dcb5319ea55e1100ccf1419c6f4e34a537141a8829c7d74f6239f`.
- Prepared/tested WASM SHA256
  `f41145a014bd52029ac459b49682765adca9e0965ce342f0548228059b8aaec8`;
  current QVM pack `fd7bc4d637ab901f0c6de4faadb8699dc176f9869b96cd1dd96374741f93ddb3`.
  All five PK3 hashes in the final on host were verified inside WASM FS.

## Tests distinguish depth rejection from model culling

`glow-control.mjs CDP ON_HOST OFF_HOST OUTPUT` captures lossless 2× canvas PNGs
in HDR0/1 with glow on, glow off and a deliberately broken GL-only depth-bypass
control. The wrong variant disables depth only around additive six-index draws
and restores state; the hook is removed at completion. No production shader,
model, exposure, light, collision or engine memory is changed by this control.

`glow-pixels.py OUTPUT` checks a 200×200 center region:

| HDR | visible on/off changed pixels / peak channel delta | blocked on/off | deliberately broken depth |
| --- | --- | --- | --- |
| 0 | 4501 / 74 | 0 / 0 | 493 / 93 |
| 1 | 4372 / 61 | 0 / 0 | 530 / 116 |

All twelve states: GL0, no context loss, matched snapshot camera origin/angles.
Inspected `.amp/in/artifacts/render-cw-glow-final/contact.jpg`: the visible lamp
adds restrained cyan/green glow without a black quad border. Foreground geometry
fully blocks normal glow, while the intentionally broken control leaks cyan.
This negative control demonstrates real depth rejection, not only PVS absence.
HUD/canvas-edge crops are not part of the lamp region or a HUD acceptance claim.

The east lamp center is approximately `[1170.312471,1020.067485,102.390996]`.
Settled camera player origins are `[1086.08887,1020.0202,76.3909988]` (visible,
yaw .0329589844) and `[975.532715,825.504395,76.3909988]` (blocked,
yaw 44.967041). Script inputs are recorded in its source. `pmove_fixed 1` and
`pmove_msec 8` make teleport velocity decay repeatable; this is not a movement
timing/physics acceptance test. No brightness adjustment was made.

## Failed preliminary controls found an inactive diagnostic switch

The initial frame-time-dependent camera comparison failed and was not used for
pixel evidence. Matching fixed-step captures with ordinary PVS showed zero
blocked difference, but disabling depth alone did not reveal the lamp: that
could not prove depth correctness. Locking the visible lamp PVS then omitted
the foreground wall, so that alternative was also rejected.

Source inspection and a failing native test established that GL2 registered
`r_novis` but never consumed it. The repair uses it when selecting cluster PVS
and invalidates cached clusters on both toggle edges. Default remains 0; area
masks and frustum culling remain active. The final depth control explicitly uses
`r_novis 1` to submit both lamp and foreground; it is not a shipping profile.
Native `replacement-visibility.c` now tests hidden-leaf visibility before/on/off
with an unchanged camera, red before the fix and green after. All six renderer
C test programs and native/Web builds pass.

Remaining: other lamps and v7 combined scenes, dynamic particle/decal overlap,
controlled point-light blocker/receiver accuracy, and hardware performance.
The environment owner's 26-state review and parent's full matches are separate
evidence, not duplicated renderer-orb acceptance here.
