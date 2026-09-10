# Rocket/right-arm/muzzle candidate — 2026-09-10

**Not release accepted and not complete base-Q3 weapon production.**
The three runtime candidates are `weapon-rocket-v1-candidate.pk3`,
`weapon-hands-v1-candidate.pk3`, and `effect-rocket-muzzle-v1-candidate.pk3`
under `assets/remaster/runtime/`. Install all three for the first-person check.
No commercial reference meshes, textures, sounds or maps are in those packages.

Production: Amp Painter → Hunyuan3D2 → Blender3.4.1 cleanup/UV/base-color bake →
shared skeletal IQM exporter. Rocket has 3600 triangles and root/flash/barrel
joints, one rigid frame. The generated right arm has 3600 triangles, root and
tag_weapon, 15 mapped frames. Root motion is presentation only, not player
movement. It is not a two-handed or articulated-finger final animation set.
The additive muzzle is separately authored 2D Painter content, 256² TGA with
black padding, no depth write, no generated 3D claim.

Actual Hunyuan charges matched by request ID: rocket $0.50, machinegun $0.50,
right arm $0.50. Each was submitted once. Painter cost/task/model IDs are not
exposed by the Amp tool; receipts retain unknown cost and exact attachment/hash.
Machinegun reached generated GLB and cleaned Blender only: spinning barrel
separation, rig and runtime acceptance are pending.

## Verified, with boundaries

- Native cgame and Emscripten3.1.58 base-Q3 QVM builds pass.
- Five offline tests pass, including actual-C mapper boundary/priority tests,
  actual-C HUD gate draw/state checks, immutable Painter input replay, and
  independently decoded 15-frame hand socket coordinates/orientations.
- Chromium/SwiftShader actual q3dm1 devmap with private official Demo and current
  QVM: first-person generated rocket/right arm draws; third-person body/weapon
  pickup draws. Screenshot inspection found no giant third-person model or
  through-torso attachment, and no final first-person geometry spikes.
- Normal-time HDR and LDR runs independently read `r_hdr=1` / `r_hdr=0`, actual
  page URL, and SHA256 of all three runtime packages **inside Emscripten VFS**
  plus the loaded QVM package. Single key shot consumed 999→998, stayed998 after
  release; switch rocket→machinegun→rocket stayed998; held fire consumed three
  more, to995, and stayed995 after release, weaponTime0.
- Separate timescale0.1 visual sequences show the compact new orange muzzle
  flash, disappearance in following frames, no black quad and no aim-obscuring
  bloom in HDR and LDR. Slow time is for visibility only, not fire-rate evidence.
  Following missile/trail/explosion effects are still original reference art.
- A prior LDR-labelled command run was found to target an old HDR browser tab;
  it is discarded. Final `browser-verified-{hdr,ldr}` runs pin URL/actual cvar
  and loaded package hashes. Do not cite the earlier `browser-final-*` runs.
- Agent-browser recording yielded an unusable 0.3s capture, so it was removed;
  inspected sequential actual-browser JPEGs, not that clip, support VFX review.

Reproduce with `misc/remaster-assets/weapons/verify_rocket.mjs CDP OUTPUT_DIR`
from repo root, using `build-weapon-review` as the private prepared fixture.
Close extra game tabs: shared gameplay CDP helper selects the first HTTP page.
Detailed read-only observations and input journals are private under
`assets/remaster/work/weapon-rocket-v1/browser-verified-{hdr,ldr}/`.

## Still required

Material has diffuse only; normal/F0/roughness/emission baking is not finished.
Close-up review finds muddy texture detail, thin bright seams and grip contact
obscured by the weapon. Left support arm, finger articulation, two-handed grip
and side-view grip approval remain. These are production tasks, not solved by
claiming a static pose is a full animation library.

Hit/damage/knockback/rocket-jump regressions, all-weapon first/third-person and
near/far matrices, physical GPUs and non-Chromium browsers are not covered by
this batch. Full base-Q3 reference data is still absent; Demo contains missing
sounds and BFG effect images and must not become the publication package.
All remaining weapons/ammo/health/armor/powerups and effects are explicitly
tracked in `coverage.json`; no original fallback counts as remade.

DOM HUD gate is independently committed: `cg_webHUD` is ROM/default0 and leased
by the actual host only after it draws a valid snapshot. The weapon strip skips
pixels after retaining health/fade/pickup state behavior. Full DOM lease/menu
browser acceptance is owned by the UI/integration threads, not claimed here.
