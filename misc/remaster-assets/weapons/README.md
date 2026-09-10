# Weapon production and cgame binding

This is an in-progress content branch, not all-base-Q3 completion. The authoritative
coverage is `assets/remaster/weapons/coverage.json`. No old weapon or generated
test geometry is labelled a remake. Current visible geometry starts in Amp
Painter, then Hunyuan, then Blender, then the shared IQM exporter.

`import_painter.py MANIFEST DOWNLOADED_IMAGE --note INSPECTED_FINDINGS` imports
one actual Painter output into the existing task ledger, preserving unknown
Painter cost rather than inventing billing IDs. Run through
`uv run --with pillow==11.3.0 python`. Existing `pipeline.py shape`, `resume`,
`billing`, `process` perform the paid and Blender stages. Never use `image` to
regenerate an imported Painter concept. Receipts prevent duplicate commissions
in a new checkout; restore ignored private work before resuming.

`rig_weapon.py` runs in Blender on the generated cleaned mesh. It creates only
the armature/sockets, never replacement visible geometry, and reuses
`blender_iqm.py`. `package_weapon.py MANIFEST` validates generated inputs and
the rigid IQM and emits a reproducible **candidate** PK3 with public receipts.
The current material is diffuse only, not finished normal/specular/emission.

Runtime names are `models/remaster/weapons/NAME/{weapon,hands,barrel,flash}.iqm`
for the nine names in coverage. A body has frame zero plus exact `tag_flash` and
`tag_barrel`, axes X-forward/Y-left/Z-up, 40 Q3 units/m, unit scale. Body origin
is the grip socket. Hands contain `tag_weapon`; their mesh is explicitly drawn
with first-person depth hack, unlike the old attachment-only hand MD3.

Hands must have 15 mapped frames: rest0; attack1–6; drop6–10; raise11–14.
Frame6 is intentionally shared by attack-end/drop-start. Cgame preserves the
original mapper and oldframe/frame/backlerp; clips never schedule fire events.
The actual Demo Sarge torso layout is attack130/6, attack2 136/6, drop142/5,
raise147/4; character export keeps those independent torso semantics.

The old hand socket is **not grip-origin compatible**: the Demo rocket idle
`tag_weapon` is (-10.359375,-4.71875,-9.3125) Q3 units. A new grip-origin body
mounted directly on it clips behind the camera. Until a weapon has its matching
new hands, first person retains the reference model; world/pickup can load the
new body. This is a technical fallback and a release blocker, not arm completion.
Stock fire, ammo, projectile, damage and switch state are untouched.

Run offline checks:

```sh
uv run --with pillow==11.3.0 python -m unittest discover -s misc/remaster-assets/weapons -v
cmake --build build-web --target cgameqvm_baseq3 --parallel 2
cmake --build build-orb --target cgame.so --parallel 2
```

Browser inspection uses `misc/tests/gameplay/prepare.mjs` with private Demo input
and current QVM. `console.mjs CDP_WEBSOCKET COMMAND...` uses real Chromium char
events through the existing gameplay harness (agent-browser keyboard insertion
does not produce SDL text input reliably). It never writes player state.

Source GLBs, prototype images, rigged `.blend`, private task state and responses
stay in ignored `assets/remaster/work/weapon-*`. Committed candidate PK3s do not
include them, commercial Demo data, sounds, or original textures. Private source
transfer/backup and final visual/runtime acceptance remain separate gates.

For the generated machinegun, run `rig_machinegun.py` in Blender with the cleaned
source, `assets/remaster/weapons/machinegun-v1-attachments.json`, and the work
directory's `split` output. Package with `package_weapon.py MANIFEST
--rotating-barrel`. Hand package `--hand-slots rocket machinegun` explicitly
assigns the same generated grip controller to those two candidate slots. These
are export choices recorded in receipts, not edits to an immutable paid manifest.
`verify_machinegun.mjs CDP OUTPUT` validates the actual five loaded PK3 hashes,
normal-time held fire/release/switch, then captures slow-time presentation poses.
See `assets/remaster/weapons/machinegun-v1-review.md` for measured coverage and
remaining art/gameplay gates. Never interpret a passed hash or build as approval.
