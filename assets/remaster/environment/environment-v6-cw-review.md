# First exterior-correct environment scene candidate

`environment-scene-q3dm1-v6-cw.pk3` SHA-256:
`df217c6ddbb90b1d0a566f1df07469ae732b84479cb2e87329c2b2d23f5a4c9c`.
Thirteen instances /31 bound original surfaces. This supersedes all old
CCW scene-v1–v4 appearance judgments, but is not full-level art acceptance.

All four original paid shapes were locally processed and packaged again with
shared exporter `be6a2aa8` (Blender CCW→Q3 CW; decoded preview back to CCW with
smooth MD3 normals). No new shape submission or paid retry. Updated receipts
retain original request/task costs and source GLB hashes. Pre-CW recovery is
hash-verified in both production and main orbs; external durable backup remains
separate.

Corrected actual front is-Y for wall lamp, lion and crest. Wall yaw now
`[90,-90,-90,90,-45,45]`; paired lions90/-90; crest180 with centered
origin `[673.8996875,1205.625,296.37]`, scale.84. Wall companion is atY-4.078125,
X±10,Z15..55; standing lamps keep four exterior companions. All new quad
triangles use Q3 CW and fit within original solid-member bounds after
placement. The bounds include companions. No BSP/AAS is embedded.

Actual WASM `review_lanterns.mjs ... cw`:13 positions × HDR1/HDR0 =26 PASS,
31 binding logs per load, actual300ms lateral movement >10 units, no context
loss. Five scene/companion tests pass, including negative cross·normal for
every new quad and preserved opaque bytes. This run uses default dynamic-light
mode0, not the renderer owner's separate mode2 shadow validation.

Inspected full HDR/LDR contacts and individual views in
`.amp/in/artifacts/environment-v6-cw/`: outward ivory crest/lion faces and
new lamp exteriors are visible; no previous inside-shell/backplate substitution
is seen. East/west LDR near captures explicitly resolve a vertical capsule
below the old diagonal marking, with white core and pale green/cyan halo on
beige body. No exposure, FX intensity or reflectance adjustment was adopted.
Some floor-lamp lower detail is occluded by the original gun/HUD/pickup text;
those original elements are not remade environment content.

Strict private glow-off control:
`assets/remaster/work/environment-private/environment-v6-cw-glow-off.pk3`,
SHA-256 `99072513ed3ab4feedee8fcc84aa81f46e464d7536fcbd29159107e58ee8cd1c`.
Only the two lamp MD3s differ: additive companion blocks removed and MD3
counts/end offsets adjusted. Frame bounds, opaque blocks, instance JSON,
shaders, textures and all other ZIP member contents are byte-identical.
Renderer owner received both exact hashes for independent HDR/LDR occlusion.

Still open: full movement/PVS boundaries and physical collision comparison,
new full Bot match, shadow/foreground tests, generation noise/art polish,
over-bright wall lightmaps, statues, architecture/sky/hazard refinement and
the remaining original geometry. No complete q3dm1 or release claim.
