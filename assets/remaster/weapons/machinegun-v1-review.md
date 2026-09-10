# Machinegun candidate — not final weapon completion

2026-09-10: reused the existing paid Painter/Hunyuan GLB; no paid resubmission.
Blender full-object side/front inspection established the receiver bearing at
X=.025m, spin axis +X at Y=0/Z=.19m. Grip origin is (-.26,0,.075)m.
`rig_machinegun.py` splits generated surfaces at that bearing and exports body
and barrel separately through the shared clockwise IQM exporter. The open cut
stays inside the bearing; no synthetic visible gun replaces generated geometry.

Runtime uses the original `CG_MachinegunSpinAngle`, including EF_FIRING/coast;
the same generated 15-frame right-arm controller is fitted to the grip. This is
not a complete two-hand/finger animation set. Cgame partial-pack fallback now
keeps original body/barrel/flash together in first person when new hands are
absent. Native/reference-only packs retain their original behavior.

Executed checks:

- Six offline tests pass, including actual compiled C partial-pack registration
  and body/barrel/flash selection across all 16 availability combinations in
  first/third person, original torso mapper boundaries, and HUD state gate.
- Native cgame, Web cgame QVM and full Emscripten 3.1.58 Web build pass.
- `verify_machinegun.mjs` real Chromium/SwiftShader HDR and LDR: held input
  consumes six bullets in each run; release stops consumption; switch to rocket
  and back preserves ammo. Actual URL/r_hdr and all five WASM-FS PK3 hashes are
  recorded in private `work/weapon-machinegun-v1/browser-{hdr,ldr}/results.json`.
  This is not a precise fire-cadence or hit-damage test.
- Slow-time captured poses are visual-only. Inspected HDR contact sheet shows
  barrel-slot rotation and continuous attachment. LDR poses remain attached,
  but blur/cropping prevent precise rotation acceptance. Third-person angle
  shows forward attachment to the reference character, but obscures the grip.
- Rocket/arms were re-exported using the shared CW fix; both HDR/LDR reran the
  actual single-shot/switch/held-fire test against current package hashes and
  passed. Inspected current exterior has no inverted faces/spikes. Previous
  records apply only to their older hashes, not these new packages.

Release blockers: blurred/washed-out diffuse-only material, support arm/finger
articulation, exact third-person grip approval, near/far, target hit damage,
knockback/rocket jump, exact cadence and all remaining base-Q3 content. Original
Demo environment/character/audio/most FX remain private technical reference.
No release or claim of all-weapons completion is made.

All three paid GLBs and the Painter muzzle source have hash-matched copies in
the integration orb; this is cross-orb recovery, not external durable backup.
New split Blender/exports still need transfer after this stage.
