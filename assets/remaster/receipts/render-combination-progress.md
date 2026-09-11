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
evidence. The runner now asserts actual weapon=5 and ammo decrease. Main is
investigating QVM header dependency/ABI mismatch; a completely rebuilt QVM must
be used before attributing these HUD/weapon failures to rendering. Missing
demo BFG explosion image warnings also remain unrelated fixture limitations.

Material-map on/off images are not proof of specular removal: disabling
`r_specularMapping` removes the texture, not necessarily the default specular
term. Source defaults in legacy mode are F0 .04, smoothness .3; at glossType1
this is roughness .7. Material-local zero `specularScale` is the appropriate
negative control. No global brightening/darkening or default-image workaround
was applied. Final clean-QVM materials, weapon/particle/occlusion, new lamp glow,
complete matches and hardware/browser performance are still open gates.
