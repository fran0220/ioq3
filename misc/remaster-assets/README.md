# Remaster asset production tools

This directory owns the image → generated GLB → Blender → **static** MD3/TGA/PK3
sample pipeline. Characters remain IQM-first in the engine workstream. It does
not publish a game, alter Gateway channels/accounts, or implement the web client.

## Animated IQM2 export and actual-engine pose tests

`blender_iqm.py` exports **prepared** Blender meshes, all rig/attachment joints,
and explicit action ranges to `model.iqm`, inspectable `source.json` and
`animation-contract.json`. `iqm_export.py` writes the same format from that JSON;
`iqm_validate.py` independently decodes bytes and checks layout, hierarchy,
weights, clip ranges and skinned bounds. No new character generation is involved.

```sh
F=assets/remaster/work/iqm-fixture
blender --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python misc/remaster-assets/blender_iqm_fixture.py -- "$F"
blender --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python misc/remaster-assets/blender_iqm.py -- "$F/fixture.blend" "$F/config.json" "$F/out"
python misc/remaster-assets/iqm_validate.py "$F/out/model.iqm" --output "$F/validation.json"
RUN_BLENDER_TESTS=1 uv run --with pillow==11.3.0 python -m unittest discover -s misc/remaster-assets -v
```

The fixture is conspicuous **TEST ONLY** asymmetric tetrahedral geometry, two
materials, three joints including `tag_weapon`, two actions/five frames and mixed
20/80 weights. It is not a paid/generated character or replacement game asset.
Tests compare exported skinning/socket transforms with Blender's evaluated
armature modifier and independently calculated numeric values, including reversed
interpolation traps, quaternion signs, exact 999/1000 vertices, 5997/6000 indices,
128/129 joints and deliberately corrupted IQM bytes. The Blender integration test
also compiles **production** `ComputePoseMats` and `R_IQMLerpTag` via
`iqm_pose_probe.c` and compares their output with Blender, including a 25% socket
interpolation. It requires `cc`, SDL2 development headers/`sdl2-config`, and libm.
This probe does not call the full loader or draw OpenGL; engine rendering and
cgame gameplay acceptance remain separate gates. Never run the probe on unvalidated
or untrusted binaries; it is a trusted-fixture test, not an asset loader.

The actual contract is `code/renderercommon/iqm.h` and
`code/renderergl2/tr_model_iqm.c`: IQM version2, ≤16MiB, ≤128 parent-before-child
joints, each mesh ≤999 vertices/1999 triangles, float position3/normal3/UV2/**tangent4**,
UBYTE index4/weight4. Weight bytes total255, positive influences precede zeros,
and even zero-weight slots have valid indices. The writer normalizes and quantizes
1–4 influences; more than4 is rejected, not silently pruned. UV V and tangent
handedness are flipped for Q3. Position/bone translation units are explicit;
model basis is X-forward/Y-left/Z-up, with no guessed axis conversion.

Preprocess source: apply object transforms, retopologize/triangulate/UV and prepare
Q3 shader textures before export. Only one active unmasked linear armature modifier
per mesh is accepted. No shape keys, object animation, B-bones, dual-quaternion
skinning, envelopes, shear, or non-unit bone scale. Constraints are sampled into
parent-local TRS; NLA is disabled and unkeyed channels reset between explicit
actions. Animated root/object motion must be consciously baked into root joints;
root motion must not accidentally replace authoritative player physics. The
exporter retains every bone, including non-deforming sockets, and stops at the
128-joint ceiling. It does not infer rigs, retarget motion or convert PBR textures.
Material mappings preserve explicit runtime shader paths and source material names;
retain the source `.blend`/textures and the JSON sidecar in source archival.

Config fields: `classification`, `coordinate_system`, `units_per_meter`,
`armature`, `meshes`, `materials` (Blender material→Q3 shader), `attachments`
(exact joint names), `clips` with `name`, `action`, inclusive integer `start/end`,
`fps`, `loop`, optional `semantic/events`. Events are preserved in the sidecar;
they are not IQM engine callbacks. See generated fixture config as runnable input.
Bounds deliberately use a conservative rigid-joint sphere, covering rotations
between frames rather than endpoint AABBs alone; production bounds/performance
need per-character review before tightening.

**Required cgame handoff:** IQM clip names/FPS/loop metadata are stored in the file
but the current renderer does not consume them. Cgame must map gameplay semantics
to `refEntity.frame`, `oldframe`, `backlerp` using sidecar ranges. Stock cgame still
loads lower/upper/head plus `animation.cfg`, rebases leg frame offsets and maps
torso attack/drop frames to weapon-hand frames. Either implement the whole-body
client interface or supply verified segmented IQMs; `.iqm` is not an automatic
override of an existing valid `.md3`. `R_IQMLerpTag` matches exact case-sensitive
joint names and returns animated model-space joint transforms. Cgame must provide
valid attachment frames (the tag path does not clamp), and handle `tag_torso`,
`tag_head`, `tag_weapon`, `tag_barrel`/`tag_flash` conventions as appropriate. The
fixture preserves `tag_weapon`; it does not claim to implement these player/weapon
semantics. Keep `runtime_accepted=false` until actual engine/cgame/visual gates.

## Authorized source inventory and production work packages (offline)

`inventory.py`, `batches.py` and `archive.py` use Python's standard library only.
They do not download commercial assets, extract ZIP paths, call generation APIs
or submit paid work. Keep local source manifests and generated detailed reports
under ignored `assets/remaster/work/`; they can include original entity data.
Do not commit or publish Demo assets, EULA, or extracted map/entity reports.

Create `sources.json` beside your explicitly supplied local PK3s:

```json
{
  "scope": "demo",
  "authorization": "User supplied/authorized local inspection only; record actual scope",
  "archives": [
    {"path": "pak0.pk3", "sha256": "<actual 64-character lowercase SHA256>",
     "provenance": "<supplier/version/source URL and applicable rights record>"}
  ]
}
```

List archives in **low-to-high VFS priority**. Every input hash is verified; all
overridden versions remain in the report. Duplicate/case-conflicting paths inside
one archive, traversal, oversized members and mismatched hashes stop scanning.
The scopes are `demo`, `partial`, `full-user-declared`; the last is an attestation,
not proof. No scan ever sets `full_game_complete=true` or calls Demo full coverage.
PK3 priority, loose files, active game directory and runtime registration traces
must match the actual engine before making release claims.

```sh
D=assets/remaster/work/demo-input
python misc/remaster-assets/inventory.py scan --sources "$D/sources.json" --output "$D/inventory.json"
python misc/remaster-assets/inventory.py dependencies --inventory "$D/inventory.json" --root maps/q3dm1.bsp --output "$D/map-dependencies.json"
python misc/remaster-assets/batches.py plan --inventory "$D/inventory.json" --manifest assets/remaster/manifests/production-batches.json --map maps/q3dm1.bsp --output "$D/first-map-plan.json"
python misc/remaster-assets/inventory.py coverage --inventory "$D/inventory.json" --replacements "$D/replacements.json" --output "$D/coverage.json"
python misc/remaster-assets/batches.py gate --plan "$D/first-map-plan.json" --evidence "$D/evidence.json" --output "$D/gates.json"
```

The map must exist and have parsed BSP46 model bounds. The plan carries actual
entity origins, bounds and logic-lump hashes, not dimensions guessed from a
prototype. Bounds are **not connector drawings**: brush/clearance measurements
remain required. Inventory reads BSP/AAS header, shaders/image/sky/animation
references, MD3 frames/tags (including zero-surface attachment models), IQM2
materials/animation metadata, skin files, animation.cfg rows and WAV metadata.
Unknown formats are still hashed; this is not a full validator for every format.
The dependency command walks transitive model→shader→texture/script references.
Dynamic QVM/code registrations, skin/LOD selection and sound aliases need runtime
capture. Missing references can be editor-only or already baked into BSP; do not
equate every global shader reference to an in-game failure. Ambiguous definitions
and image alternatives stay visible instead of pretending engine order is known.

Coverage mappings contain `inventory_sha256` (the scan's `canonical_sha256`) and
`replacements`: each has `source_path`, `source_sha256`, `asset_id`, and `gates`.
Each gate is `{ "passed": true, "evidence": "review/log reference" }`. Counts are
per inventoried source path, never per entire game or automatically accepted art.
The batch manifest defines full environment/character/weapon/pickup/effect/audio
families, prerequisites, output contracts, unimplemented format work and gates.
Expansion is reference assignment, **not one paid job per file**. UI/icons/menu
cinematics go to M1; configuration/VM/replay exclusions are listed, not counted as
remade. Unclassified files remain blockers. Overlapping material families must
share a single measured asset specification before commissioning.

`batches.py gate` returns exit 2 until all requirements have evidence. Its input
pins `plan_sha256` = SHA256 of `json.dumps(plan, sort_keys=True).encode()` and has
`batches: {batch_id: {gate_name: {passed, evidence, reviewer}}}`. Demo/partial fails
even with every checkbox filled. Unresolved dependency dispositions are keyed by
SHA256 of `json.dumps(edge, sort_keys=True).encode()` under
`dependency_dispositions`; allowed classifications are `compile-only`,
`baked-into-bsp`, `runtime-resolved`, each with reviewer and concrete evidence.
There is no silent ignore list. Review evidence must include artifact hashes;
these attestations require human audit, not trust in automated visual QA.
Budget is already approved; source/art/runtime gates are not budget approvals.

## Private source/recovery archival (offline)

```sh
S=assets/remaster/work/source-archive
python misc/remaster-assets/archive.py snapshot --store "$S" --work assets/remaster/work/energy-pillar-v2 --receipt assets/remaster/receipts/energy-pillar-v2.json
# Use the exact snapshots/<hash>.json path printed above:
python misc/remaster-assets/archive.py verify --store "$S" --snapshot "$S/snapshots/<hash>.json"
python misc/remaster-assets/archive.py restore --store "$S" --snapshot "$S/snapshots/<hash>.json" --work assets/remaster/work/restored-energy-pillar-v2
```

Snapshots validate receipt hashes, preserve task/request/operation IDs and copy
source/master/runtime files **and private state/request/response data** to deduped
SHA256 blobs. Store permissions are private. Do not publish or commit the store:
requests/responses can include signed URLs and source payloads. A snapshot is
written only after blobs; interruption leaves reusable blobs, not a valid partial
snapshot. Restore preflights all hashes/conflicts and is idempotent; it never
overwrites different work or invokes generation. Use the matching committed
production manifest when resuming. Existing pipeline receipt/task guards remain
in force. Local verify/restore does **not** prove off-orb backup; retain a separate
durable copy and verify its hashes before marking archival complete.

## Environment and identity

Python 3.11, Pillow 11.3.0 (`uv run --with pillow==11.3.0 python …`), and Blender
3.4.1 are the tested baseline. For this Debian orb, Blender uses
`/usr/local/lib/python3.11`, not Debian's Python module directory. Its bundled
glTF importer still uses `np.bool`, so install **NumPy 1.23.5** in the Python
environment Blender actually imports. NumPy 1.24+ fails with this importer.

```sh
sudo apt-get install -y blender
blender --background --factory-startup --python-expr 'import sys; print(sys.path)'
# For the observed /usr/local Python in this orb:
uv pip install --python /usr/local/bin/python3 numpy==1.23.5
```

No setup files outside this directory were changed. Ask the setup owner to
persist the verified dependency configuration. A different Blender version must
run the integration test before production. CPU Cycles explicitly disables
denoising because Debian's Blender does not include OpenImageDenoiser.

Generation defaults to `OG_API_KEY`; `--credential publisher` explicitly selects
the root identity's `OG_CREATOR_KEY_<HANDLE>`. These are separate from publication:
the root publisher remains **og-atlas**, and this tool never edits that identity.
Before a paid stage the runner queries `/v1/origin/studio-account` and
`/api/usage/token/`, records generating account ID/username, and keeps the key
scope private. It does not print key values or email. `account` reports quota in
Gateway units and whether the default/publisher keys are the same, not the keys.

## Execute one asset, with a visual gate between image and 3D

From repository root (v2 is the GPT Image 2 revision after unavailable Grok):

```sh
M=assets/remaster/manifests/energy-pillar-v2.json
uv run --with pillow==11.3.0 python misc/remaster-assets/pipeline.py account --manifest "$M"
uv run --with pillow==11.3.0 python misc/remaster-assets/pipeline.py image --manifest "$M"
# Inspect assets/remaster/work/energy-pillar-v2/prototype.png, then:
python misc/remaster-assets/pipeline.py approve --manifest "$M" --reviewer '<reviewer>' --note '<actual findings>'
uv run --with pillow==11.3.0 python misc/remaster-assets/pipeline.py shape --manifest "$M"
python misc/remaster-assets/pipeline.py resume --manifest "$M" --wait 1800
python misc/remaster-assets/pipeline.py billing --manifest "$M"
python misc/remaster-assets/pipeline.py process --manifest "$M"
# Inspect processed/review-front.png and review-back.png; not an engine test.
python misc/remaster-assets/pipeline.py package --manifest "$M"
python misc/remaster-assets/pipeline.py receipt --manifest "$M"
```

The style brief uses an original energy pillar, not an exact remake of absent
original game data. The one-click `hunyuan3d-2` supplies geometry and material;
Blender then cleans, triangulates, reduces, ground-centers/scales, creates a new
UV atlas, bakes base color to TGA, exports MD3, decodes the exported bytes and
renders **that MD3** for front/back review. Base color baking uses emission to
avoid turning fully metallic materials black. The result has traditional
diffuse lighting; PBR/emission fidelity is not claimed. The raw GLB is preserved.

`hunyuan3d-2-shape` is also accepted for geometry generation, but `process`
deliberately stops when there is no UV/material. The separate texture-only API
handoff is documented upstream but is **not implemented in this version**.
Never substitute new shape generation just because painting is unavailable.

## Recovery and avoiding duplicate charges

- Every paid stage has a UUID, canonical request hash, private credential scope,
  request body, response and request ID, plus actual account attribution.
  State and response files are atomically replaced and fsynced. A filesystem
  lock excludes concurrent runners on one work directory.
- Re-run `image` after completion: validates artifact hash and returns it. After
  a saved response but interrupted decode: decodes saved bytes, no new POST.
  After an ambiguous image POST with no response: stops; no automatic retry.
- Hunyuan transport timeout before ID: repeat `shape` under the **same key and
  immutable manifest/work directory**. Exact JSON/key replay is supported by
  the current Hunyuan contract. Once ID exists use `resume`, never a new create.
- HTTP errors are retained privately and block further POST. Inspect the exact
  error and billing before an explicit new revision. A new work directory is a
  **new operation**, not a recovery technique. Do not use one for unknown tasks.
- Read-only polling/download errors retain task IDs. Repeat `resume`. It polls
  every 10 seconds for the bounded `--wait`; status 202 is not success. A failed
  task stops and retains its report; refunds need billing reconciliation.
- A changed manifest, input or token cannot replay an old operation. Keep old
  revisions and receipts. Do not delete work directories to get past protection.
- Unlimited budget is authorized: there is no manual budget gate. The prototype
  approval is an **art inspection** gate, not another request for funding/rights.
- No arbitrary URL download carries the Gateway Bearer. HTTP redirects are
  rejected. Images request `b64_json`; unexpected URL-only results stay private
  for unauthed download recovery, without regenerating. GLB external resources
  are rejected before Blender import. Local data hashes are checked on resume.

Billing matches `/api/log/token` by exact request ID **and model**, separating
consumption (type 2) and refund (type 6). Recorded USD uses the source contract's
500000 quota units/USD. Missing/ambiguous/aged-out records remain `unreconciled`,
not zero. Task JSON has no trustworthy cost field. Recent unrelated requests
never substitute for a match. Token-wide usage is not this sample's bill.

## Deliverables, storage and handoff

`assets/remaster/work/` is ignored. It contains private responses (possibly
base64 or transient URLs), raw GLB, prototype, `.blend`, processing reports and
candidate PK3. Never `git add -f` the work directory. `receipt` is an allowlisted
public projection; review it before committing under `assets/remaster/receipts/`.

Small inspected runtime PK3s and review JPEGs can be copied into tracked
`assets/remaster/runtime/` and `assets/remaster/reviews/`. Source GLB/prototypes/
Blender masters require durable asset storage or thread-file transfer; an orb's
ignored files are **not backed up by Git**. Do not claim archival complete until
the destination and hashes are recorded. Do not expose private request JSON.
When a tracked `<asset-id>.json` receipt exists but local state is absent, the
runner refuses to create another job. Restore the private state and artifacts
from the production orb/storage first; a fresh checkout is not a new commission.

The PK3 contains only `models/remaster/<name>.md3`, its `.tga`, and the unique
`scripts/remaster_<asset-id>.shader`. Packaging verifies processed hashes and
model shader names. ZIP timestamps/order are fixed for reproducibility. It does
not contain a map, collision, scripts that load the model, or commercial data.
The receiving engine workstream must load it from the virtual filesystem, add
it to a controlled test scene, check orientation/lighting/scaling and browser
memory, and provide engine review. `runtime_accepted` stays false here.

MD3 export: one frame, no tags/rig; UV seam/normal splits, **≤999 vertices and
≤5999 indices per surface** (whole triangles therefore ≤1999 / 5997 indices),
≤32 surfaces, strict signed-short × 1/64 position range, no quantization-collapsed
triangles. `R_LoadMD3` in `code/renderergl2/tr_model.c` rejects counts ≥1000
vertices or ≥6000 indices (`SHADER_MAX_*` in `qfiles.h`), stricter than the MD3
format's 4096/8192 limits. Both writer and read-back/package validation enforce
the runtime limits. It is not a generic character exporter.

## Tests (no network or paid generation)

```sh
python -m unittest discover -s misc/remaster-assets -v
RUN_BLENDER_TESTS=1 uv run --with pillow==11.3.0 python -m unittest discover -s misc/remaster-assets -v
```

The Blender fixture is explicitly **TEST ONLY**, not generated production art.
It exercises asymmetric shape, two materials including fully metallic cyan,
scale/pivot, UV rebake, MD3 export and CPU front/back rendering. Its output is
temporary and never packaged into the game. Pure tests cover no-duplicate image
POST, exact Hunyuan replay, credential/input drift, concurrent lock, billing
attribution, private receipt fields and independent MD3 byte-layout/boundary
expectations. This verifies local processing, not supplier quality or WASM.

Contract snapshot inspected: Origin Game
[`7eb275d9`](https://github.com/fran0220/origingame/commit/7eb275d91abdae9331c7e8c457257644f432f388),
`docs/origin-gateway.md`, `docs/hunyuan3d-workflow.md`, deploy skill/script,
generate skill and account/token/router implementations. Re-read them before
changing provider behavior. No platform configuration changes were made here.
