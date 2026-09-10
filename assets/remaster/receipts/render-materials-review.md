# Renderer material/data and shadow review — 2026-09-10

Status: independently verified renderer fixes and partial combined scene; **not
whole-game visual approval or PBR fidelity**. No paid generation by this thread.

## Changes and executed checks

- Production specular lobe formerly returned 0/0 at smoothness=1 / NH=1.
  Roughness floor 0.045 and a cancellation-resistant denominator produce finite
  results. PBR scalar metallic remains continuous rather than thresholding 0.5.
- Explicit specular stages formerly received color gamma/intensity scaling,
  unlike automatic `_s` maps. A production parser test reproduced the missing
  NOLIGHTSCALE assertion before the fix. Both paths now use the shared appended
  `IMGTYPE_SPECULAR`; CPU picmip/mips average linear RGBA, not sRGB values.
- IQM projected-shadow setup previously dereferenced optional missing bounds
  before frame validation. It now skips that shadow safely when bounds are
  absent; static/wrapped/invalid frames, off-center bounds, both blended poses,
  and entity scale are handled. This does not fabricate bounds or animations.

Executed the README commands in `misc/tests/remaster-rendering`:

- `material-math.py`: 3 tests OK (production code extracted into float C).
- `material-parser`: PASS map/clampmap/animMap data flags and type, unchanged
  diffuse/normal controls. Parser is compiled from production, not duplicated.
- `specular-mips`: PASS actual picmip and asymmetric 2D/1D/1x1 data averages.
- `iqm-shadow`: PASS optional bounds, origin-centered pose union and frames.
- Complete native Debug and Emscripten 3.1.58 Release observer builds: exit 0.
- Actual Chromium WebGL2: production CalcSpecular GLSL compiled and executed for
  roughness 0/.001/.045/.2/1; all five finite-result pixels matched, GL error 0.

## Combined real-WASM run

Used original private Demo pak + current QVM/inventory overlay, tracked
energy-pillar-v2, environment-materials-v1, weapon-rocket-v1-candidate, and the
environment thread's private renamed-shader/neutral-lightmap BSP+AAS pack.
No private assets are committed or published. Binary/input hashes are retained
in the thread's `.amp/in/artifacts/render-review/technical-fixture.json`.

`misc/tests/remaster-rendering/run.mjs`: exit 0. Inspected HDR/LDR, exposure -1/1,
far view, firing, and forced-sun/projected-shadow captures. Original map geometry
remains; the new environment is a 2D material refresh. The floating original
generated pillar is a testmodel, not a placed/environment-integrated asset.
Environment graphite/ivory colors render; retained original lightgrid makes
the pillar/weapons reddish. No renderer-wide desaturation was applied.
The muzzle flash is visible. A distinct pillar projected shadow and impact
decal were **not** established by the captures; enabling options is not proof.

Repeated existing gameplay `reliability` and `bot` runners on this combined
fixture: all six restart/map/context-loss-reload checks and all four
death/respawn, bot-hit, fraglimit-score-screen and restart checks PASS.
The original baseline runner failed its >30-degree mouse-turn precondition:
capture had already changed yaw to -72.828 degrees; actual aim reached -89.989.
This failure was retained, not relabeled as a passed mouse baseline.

Chromium / ANGLE Vulkan SwiftShader (software only), viewport 1280×720 DPR2,
fixed 800×600 engine canvas. The black margin is private test-host layout.
Final shadow stress (cg_shadows4, forceSun1, sunlightMode2, dlightMode2, HDR0):
120 RAF intervals P50=50ms, P95=50.1ms, P99=66.6ms. These are browser/software
rendering intervals, **not GPU timings or hardware performance acceptance**.
WASM heap capacity 268,435,456 bytes; imagelist estimates 78,275,436 bytes over
288 images (allocation proxy, not measured physical VRAM). No matched engine
GL/shader/FBO errors or spontaneous game context loss; Chromium log has no
GL_INVALID or GPU-process-exit entry. Forced loss was tested only with reload.

## Remaining gates

The source pillar GLB has one base-color texture and roughnessFactor .903602;
it contains no normal/metallic-roughness/emission textures. Environment and
rocket candidate also remain diffuse-only. Their appearance cannot prove
normal/specular/emission conversion fidelity. Production multi-channel assets,
transparent particle/decal occlusion, visible character/model shadows and IQM
poses, finished first-person hands/weapons, combined final HUD/match, physical
GPU/cross-browser/long-session performance remain required. Full replacement
geometry and coherent map lightmaps/lightgrid are content/integration work.
