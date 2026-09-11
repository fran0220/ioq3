# Renderer combination progress, not release acceptance

## Replacement groups and controlled glow

Atomic `surfaces` arrays use exact index/shader/bounds validation, union AABB
model bounds and any-member per-view visibility. Failed member/model/scene
allocation keeps every source member. Native tests execute real traversal and
submission: both members independently visible, PVS exit/reentry, frustum
turn, separate views, mask reset and actual two-original-surface draw output
on entity capacity failure. No global shader hiding or shared ABI changes.
Opaque models can carry bounded ONE/ONE additive companions with normal depth
test, no depth write/equal; all-glow, alpha blend, missing material and forbidden
depth state cases reject the whole group. Every MD3 LOD requires opaque body.

Six C test programs pass; native and Emscripten 3.1.58 builds pass. Real WASM
single-crest movement crossed clusters 511/766 and returned to a single crest;
native tests, rather than that noclip route alone, verify PVS submission. The
route also crossed solid cluster -1, so it is not a normal-player collision
test. New environment multi-owner content and glow assembly need their own
combined review. The environment owner reported its 20-state opaque group
review separately; it is not independent renderer-orb evidence yet.

## Projected shadow filtering

Real Sarge captures isolated the stepped shadow to `cg_shadows 4` with forced
sun disabled; `cg_shadows 0` removed it. Four equal-weight nearest samples
quantized coverage into 25% levels and produced offset gray fringes. The new
filter samples texel centers and bilinearly interpolates coverage with the
same four texture fetches. Texture size comes from `PSHADOW_MAP_SIZE`, not a
duplicated GLSL literal. No resolution, light energy or shadow opacity increase.

`node misc/tests/remaster-rendering/shadow-filter.mjs "$CDP"` executes the
production function on WebGL2. A single asymmetric covered texel gives
`[255,191,64,48,0,0]`, GL error 0, including two different axis weights and
clear/full endpoints. Equal-weight PCF cannot satisfy these expected values.
`shadow-review.mjs` captured real WASM before/after in HDR0/1. Inspected
`.amp/in/artifacts/render-shadow/spawn-comparison.jpg` retains body/shadow with
slightly smoother feet/floor edges; stress comparison removes separate gray
bands but still has visible resolution-limited jaggies. Stress cameras differ
by a few units due to teleport velocity, so this is not a pixel-exact A/B.
This fixes coverage discontinuity, not all projected-shadow quality issues.

## Combination evidence and invalidated weapon captures

The first `combined-run.mjs` run used explicit current packs and recorded real
movement of about 490 units, all captured GL errors 0 and no context loss.
SwiftShader 120 RAF deltas (not GPU timings): HDR0 P50/P95/P99 50/50.1/66.7 ms,
HDR1 50/66.7/66.8 ms; WASM heap 256 MiB. Imagelist proxies were 87,438,324 bytes
/334 images and 91,278,336 bytes/335 images respectively. These are short-run
software/allocator observations, not physical GPU VRAM or release performance.

Its labels `rocket-*` did NOT prove rocket firing: inspection showed no effect,
and subsequent snapshot audit found `ps.weapon=2`, weaponTime=0 and no rocket
ammo consumption despite console echoes. Those captures are invalid weapon/FX
evidence. A full clean 602-target rebuild reproduced the failure, and inspection
of `PMoveSingle` established its cause: `PM_NOCLIP` returns before `PM_Weapon`,
so this movement mode cannot switch/fire weapons. This is a test setup error,
not a QVM/renderer weapon defect. The runner now restarts into `PM_NORMAL` for
character/weapon checks, asserts actual weapon=5 and ammo decrease, and uses
native mouse press/release with an eight-frame capture burst. Main's separately
confirmed QVM header-dependency/HUD correction remains independent evidence.
Missing demo BFG explosion image warnings are unrelated fixture limitations.

Material-map on/off images are not proof of specular removal: disabling
`r_specularMapping` removes the texture, not necessarily the default specular
term. Source defaults in legacy mode are F0 .04, smoothness .3; at glossType1
this is roughness .7. Material-local zero `specularScale` is the appropriate
negative control. No global brightening/darkening or default-image workaround
was applied. Final clean-QVM materials, weapon/particle/occlusion, new lamp glow,
complete matches and hardware/browser performance are still open gates.

## Point-light cube path: actual HDR copy failure repaired

With current clean QVMs and PM_NORMAL, real rocket fire in `r_dlightMode 2`
produced GL1282: HDR `glCopyTexSubImage2D` into an RGBA8 cube is invalid.
The experimental path also lacked a radial-color draw after its depth prepass
and compiled the sun sampler2D path rather than a point samplerCube comparison.
It now renders directly into RGBA8 cube faces with a shared depth buffer,
packs radial distance into UNORM8 bytes and selects a separate point-light
variant. Empty faces clear to distance 1. The existing inward face convention
uses receiver-to-light direction; source-axis checks cover asymmetric offsets
on all six faces. No-FBO builds retain mode-1 lighting. Default mode unchanged.

`cube-shadow.mjs` executes the production GLSL writer/reader on WebGL2:
six different blocker distances, before/behind receiver pairs and an empty
region yield `[255,0,255,0,255,0,255,0,255,0,255,0,255]`, GL0.
Native build, Emscripten 3.1.58 build and six C test programs passed.
`combined-run.mjs` independently ran actual rocket5 fire with ammo consumption
in HDR0/1, restarted contexts and crossed map clusters. All captured GL errors
were 0 with no context loss. The inspected eight-moment contact sheet at
`.amp/in/artifacts/render-pointshadow2-current/action-contact.jpg` shows weapon
and explosion effects without black squares or missing geometry. This is not
yet a controlled in-map blocker/receiver comparison or final shadow quality.

All ten installed PK3 hashes were checked inside WASM FS, including current
QVM `a68331a6c3ebc4396fe0deacf60f446e9d42f0c0c299947b82aaf8a4e72205f1`.
The development host's initial manifest predates its shader rebuild: the
actually served/tested WASM is
`08d0962dfbe92a33550d5a2fe158745a601119655abf390d2c379cc4f844b9d6`,
JS `8fc14b2205ce94c2968b7a4d0389a58eb79d57eba069e081def992e2d1b03c76`;
both match build-web/Release. The earlier manifest binary hashes are not used
as evidence for this run.

SwiftShader RAF deltas over 120 samples: HDR0 P50/P95/P99 66.6/66.8/83.4 ms;
HDR1 66.7/83.4/83.4 ms. Heap 256 MiB, imagelist proxy 89,797,620 bytes/336 images
and 93,637,632 bytes/337 images. These are software timing and renderer accounting,
not GPU measurements. Imagelist undercounts cube faces: mode2 reserves 32 × 6 ×
512 × 512 × 4 = 192 MiB of cube color storage by format/dimension calculation,
plus shared depth storage. That cost and six views per active point light mean
mode2 is not automatically a production performance recommendation.

## Environment winding invalidates previous front-face art interpretation

The environment owner subsequently reported an index-only CW/CCW comparison
showing that the old static exporter exposed the far shell from inside.
Independent renderer inspection confirms MD3 indices retain file order and
default front-sided materials cull GL_FRONT. The previous yaw0 ivory crest
interpretation is therefore not a valid final front-face acceptance criterion.
Placement/atomic fallback tests remain valid; content front direction, yaw,
glow placement and screenshots require rerun after the exporter correction.
Lamp glow itself uses cull disable, so its visibility must not be attributed
to its own triangle winding alone. No material brightening was applied.
