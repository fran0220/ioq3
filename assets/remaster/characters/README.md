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
It is still **not accepted**: review placeholders remain for backward jump/turn,
final material maps and complete combat/timing tests. See
`character-runtime-checks.json`; do not promote render checks to rules coverage.

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
The separate baseline is **not passing**: mouse capture shifts initial yaw to
-72.828°, so its turn to -90° correctly travels only 17.16°, below the test's
hardcoded >30° assertion. Reproduced in a fresh browser and reported to the
integration owner; neither the assertion nor the game was changed to hide it.
