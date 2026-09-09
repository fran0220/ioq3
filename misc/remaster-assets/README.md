# Remaster asset production tools

This directory owns the image → generated GLB → Blender → **static** MD3/TGA/PK3
sample pipeline. Characters remain IQM-first in the engine workstream. It does
not publish a game, alter Gateway channels/accounts, or implement the web client.

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
