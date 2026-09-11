# Character production and recovery

`contract.md` freezes the runtime axes, segmented bone/tag boundary and original
Sarge frame mapping. `coverage.json` is a verified Demo subset, not the full
base-game roster. No formal runtime character package has passed acceptance.

The first Painter image is reused by revisions v1 and v2. v1 was submitted under
publisher og-atlas and rejected with HTTP403 before a task ID. Keep that receipt
and private journal. Default generation uses xiaomao; publication stays og-atlas.
The coordinating platform thread separately queried production in READ ONLY at
2026-09-10 05:08:10 UTC: exact v1 request journal shows 403, request logs 0 rows,
user27 tasks and billing_operations 0 rows, quota/used_quota both zero. This is
no Gateway task/charge evidence, not a supplier-ledger audit or a known USD cost.

The v2 task is `task_4Yklp9dnD3eQcKosUVthynuw71MEi0rK`. **Resume it, never
submit another shape request merely because this checkout lacks ignored state.**
Source owner: Amp thread T-01a089aa-4a6b-711f-8eae-cde0a44d7d57. Its ignored
`assets/remaster/work/character-sarge-v2/` contains prototype, state, request and
response. Transfer these privately and verify their hashes before recovery.
Do not publish the journal, request data or private original Demo reference.

```sh
M=assets/remaster/characters/character-sarge-v2.json
uv run --with pillow==11.3.0 python assets/remaster/characters/produce.py resume --manifest "$M" --wait 1800
uv run --with pillow==11.3.0 python assets/remaster/characters/produce.py billing --manifest "$M"
uv run --with pillow==11.3.0 python assets/remaster/characters/produce.py receipt --manifest "$M"
```

`produce.py` imports the inspected Painter image and reuses the existing locked,
durably journaled production runner. It deliberately exposes no static MD3
processing. Receipt generation never grants runtime acceptance. Painter cost is
not exposed by the tool; unknown cost must not be converted to zero.

Targeted production-code checks (mock filesystem/renderer registration and
actual CPU tag implementation, **not the loader or a rendered match**):

```sh
cc -ffunction-sections -fdata-sections assets/remaster/characters/registration_test.c code/qcommon/q_shared.c -Wl,--gc-sections -lm -o /tmp/character-registration
/tmp/character-registration
cc -g -O1 -ffunction-sections -fdata-sections $(sdl2-config --cflags) assets/remaster/characters/tag_test.c code/qcommon/q_math.c -Wl,--gc-sections -lm -o /tmp/character-tag
/tmp/character-tag
RUN_BLENDER_TESTS=1 uv run --with pillow==11.3.0 python -m unittest discover -s misc/remaster-assets -p 'test_blender_iqm.py' -v
cmake --build build-orb --parallel 2
```

The tag regression exercises 25% interpolation on asymmetric translations,
negative/one-past-end/large indices in either argument, exact case and static
bind pose. Surface validation cannot protect `R_IQMLerpTag`: cgame queries tags
before scene submission. The implementation now applies the same frame-zero
fallback used by IQM surfaces instead of indexing beyond the pose allocation.

## Downloaded candidate, not combat acceptance

Shape v2 and the Meshy rig succeeded. Receipts retain task/request/input/output
hashes and matched charges. Walking/running came with rigging; source motions
183/184/188 (deaths), 466 (jump), 616 (crouch) succeeded. 605 failed after task
acceptance. 569 returned 402 with no task: read the separate billing-audit JSON,
which records an initial charge and duplicate refunds, not a free request.
Its original journal/receipt uncertainty is retained as historical evidence.
New Meshy submissions are paused at the user's direction; never retry 569.

`rig.py receipt` writes an offline allowlisted public receipt without changing
the original private journal. `status`/`download` resume accepted tasks; all
creates require an inspected GLB hash and refuse ambiguous previous attempts.
The full source motion catalog mapping is in `character-sarge-motion-sources.json`.

```sh
W=assets/remaster/work/character-sarge-v2
blender --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python assets/remaster/characters/prepare_rig.py -- "$W"
blender --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python misc/remaster-assets/blender_iqm.py -- "$W/prepared/source.blend" "$W/prepared/config.json" "$W/prepared/iqm"
python assets/remaster/characters/package_review.py "$W"
python -m unittest discover -s assets/remaster/characters -p test_rig.py
```

This reproducible **inspection-only** package uses the genuine generated rig,
seven source motions, 137 frames, 24 bones, 9964 triangles and the existing IQM
exporter. Decimation and four-weight pruning are explicit authoring steps;
the exporter still rejects invalid weights/tangents. Horizontal visual root
travel is removed, never applied to physics. It has no character override,
weapon socket, team skins or final normal/specular material.

Native GL2 and real browser WASM/WebGL testmodel inspections found the original
exporter passed Blender CCW faces to Q3's clockwise front-sided renderer.
The independent `cull back` negative control exposed that error. Export now
reverses winding, with a cross-product regression and inverse conversion only
in the Blender wire-format review tool. Default single-sided shader now shows
the correct face/chest; browser frame98 also displays the walking pose. This is
real loader/renderer evidence, **not** lower/upper/weapon/player acceptance.
Screenshots are in the source thread's `.amp/in/artifacts/character-browser-*`.

Remaining work is explicit in coverage.json. In particular the whole-rig
inspection clips are NOT the final rebased lower/upper cfg layout; do not copy
their frame numbers into a released player. Private Demo data is not in the
review PK3 and must never be copied into an asset publication.

## Segmented combat-test candidate

`segment_rig.py` uses Blender math and the same IQM writer to cut the real
generated armor at waist/neck, fix boundary weights, express upper/head relative
to their parent sockets, and retain the original cfg frame indices. It authors
explicit two-bone IK holding/recoil/jab/gesture/drop/raise actions on the paid rig;
these are not Meshy outputs and are recorded as hand-authored provenance.
`package_segmented.py` writes only generated assets and authored cfg/skins,
never Demo files. Its `zz-` prefix is necessary when testing beside `pak0.pk3`:
otherwise old skins override the new IQM surface names.

```sh
blender --background --factory-startup --threads 2 --python-exit-code 1 --python assets/remaster/characters/segment_rig.py -- "$W"
blender --background --factory-startup --threads 2 --python-exit-code 1 --python assets/remaster/characters/bake_material.py -- "$W"
uv run --with pillow==11.3.0 python assets/remaster/characters/package_segmented.py "$W"
blender --background --factory-startup --threads 2 --python-exit-code 1 --python assets/remaster/characters/test_segment_rig.py
```

This candidate has been rendered as an actual CG_Player in native GL2 and
browser WebGL, including head/waist assembly, original gun attachment, and team
red. A subsequent candidate adds authored armor ID plates (chevron versus two
bars); front and side were inspected. Rear projection was corrected against
the actual armor and its readable chevron inspected in native GL2.
It is still **not accepted**: final motion/material review and complete
combat/timing tests remain. See
`character-runtime-checks.json`; do not promote render checks to rules coverage.

The subsequent parented-socket candidate replaces the backward-jump/turn
placeholders with an authored leg counterbalance over the paid neutral jump
and a planted alternating knee/ankle shuffle. Idle deliberately remains a
static planted stance. This is authoring, not completed motion acceptance.
`tag_torso`, `tag_head`, `tag_weapon` are children of Hips, Head, RightHand:
flattening tags to roots had passed endpoint tests but produced a 0.776-unit
waist gap during asymmetric SLERP. The new independent interpolation check
measures <=.001031 units at 254 waist pairs and <=.000011 at 326 neck pairs.
Authored lower clips preserve limb lengths within .000023 units and turn
introduces no root transform. Generated portraits now replace reference icons.
Current palm fitting is weapon-specific, not a single shared offhand point;
see `contract.md`. Final hand contact and every combat pose still need review.

Team dyes use a conservative UV triangle mask derived from the actual rig's
head/arm weights; exposed skin and gloves keep their source color, and head
skins explicitly use the default material. The original 65% whole-image tint
made blue look olive in q3dm1 and tinted the face. The new 90% armor-only dye
was inspected in browser front/back: blue/red armor are distinguishable while
skin remains natural; two bars/chevron provide a second identification channel.
Front chest marks can still be occluded by the gun. Test skin changes with
`cg_deferPlayers 0` or a genuine reload: deferred models intentionally retain
the previous appearance, so setting a cvar alone does not prove skin loading.

`bake_material.py` bakes the original paid rig's high-resolution geometry to
the reduced UV mesh in bind pose (1024² tangent +Y, explicit cage/ray distances).
The material uses an authored coated-dielectric response F0=.04/roughness=.72,
not guessed ORM channels or a bare-metal claim. It has no emissive component.
Both native GL2 and browser rendered the normal/F0 version without visible
normal inversion; final close-up/light/skin reviews remain open. Preserve
`prepared/material-bake.json` alongside the source and generated normal map.

Current-main real-WASM `run.mjs ... bot` with the segmented package passed all
four checks: falling death/click respawn, damage to bot, 3-frag score screen,
and match restart (`character-gameplay-bot/bot-result.json` in private work).
The earlier separate baseline was **not passing**: mouse capture shifted initial yaw to
-72.828°, so its turn to -90° correctly travels only 17.16°, below the test's
hardcoded >30° assertion. Reproduced in a fresh browser and reported to the
integration owner; neither the assertion nor the game was changed to hide it.

The subsequent runner `8cf23370` restores the documented start through real
mouse input (-45 yaw / zero pitch), retaining the >30-degree assertion. A fresh
run with the grounded `e6ee819a…` character package passed all four baseline
checks: yaw -45 → -89.989, movement/armor 0 → 5, jump/land, ammo 100 → 98.
Exact runner/WASM/QVM hashes and evidence paths are in
`character-runtime-checks.json`. Earlier failure records/logs remain intact.
The integration owner also confirmed the original, parented and grounded
source archives in the main orb, including byte-identical candidate PK3;
this is cross-orb recovery, not completed external durable backup.

## Actual death and damage checks

`review_native_combat.py ENGINE PRIVATE_BASEPATH` runs native GL2 against the
private q3dm1 fixture. It waits for real self-rocket death logs and animation
IDs 0/2/4, stops firing before automatic respawn, verifies live torso animation
after respawn, then observes nonfatal bot damage. It uses `com_blood 0`, the
engine's real no-gib setting, not the internal C variable name `g_blood`.
Fixed wait-only scripts were rejected: pickup commands need a server snapshot
before selecting the rocket, and a guessed delay can photograph a live player
or already-respawned body. This driver is a visual inspection aid with cheats
for setup and slow motion for damage capture, not a rules/timing benchmark.

Actual death captures exposed floor penetration in the paid retargeted clips.
Authoring now raises only the source skin pose as needed, preserving entity
origin, collision and the original animation clocks. Grounding includes IQM
byte weights and pinned cut-ring vertices. The independent decoded-mesh check
fails the earlier candidate at Z=-28.075206 and passes all 90 corrected lower
death frames at minimum Z=-24.000476 (authored floor -24, tolerance .02).
Native/Web death/respawn logs pass; several corpse captures still have poor
framing/near-camera occlusion, so this does not close full visual acceptance.

The generated-only candidate is tracked at
`assets/remaster/runtime/character-sarge-v2-candidate.pk3`; installation name,
hashes, provenance references, recovery chain and open QA are in
`character-sarge-v2-runtime.json`. Rename it to the documented `zz-` basename
when installing beside the private Demo. No Demo, VM or sound files are in it.

## Closed-topology correction, 2026-09-11

The source audit found a real preprocessing defect: decimating GLB's disconnected
UV/normal islands before welding opened the surface. Original generated rig
vertices weld from25003 to19927 with zero boundary edges; welding the already
decimated old master still leaves6834 boundary edges. `prepare_rig.py` now welds
geometry at1e-5m before decimation, preserves per-loop UVs and bone weights, and
rejects an opened result from a previously closed surface. A focused Blender
test preserves distinct UV islands and asymmetric .375 weights while restoring
the shared edge. The new master remains closed after decimation.

The independent rebuilt source is in private `character-sarge-v2-welded` rather
than overwriting paid inputs or historical masters. Normals and portrait were
rebaked, all seven source motions retained, and segmented clocks/timing remain
unchanged. Current PK3 hash starts `8af28176`; full hashes/recovery paths are in
the runtime manifest. No new generation request or cost was incurred.

Native four checks and WASM three death/respawn cases plus four baseline checks
pass with the new package. Runtime near views show continuous shoulders/forearms;
settled full-body corpses were inspected in both clients. Finger/grip deformation
and full-speed motion quality remain open. `review_browser_combat.mjs` and the
native driver capture four corpse angles rather than accepting cropped views.
`review_grips.py` reads actual IQM poses/normals and includes the MG barrel, but
its Blender render is an inspection aid, never runtime acceptance.
