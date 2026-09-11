# Environment material candidate v1 — not a complete level remake

**2026-09-11 winding correction:** the original Blender static exporter
retained CCW indices while Q3's front-sided MD3 path requires CW. Real WASM
lantern probes changing only triangle indices exposed the true black backplate
where earlier captures had shown the distant ivory face through the culled
near shell. Earlier crest/lantern/relief front/yaw and material conclusions are
withdrawn. Scene-v6-cw re-exports all four paid sources with corrected winding
and has 26 actual WASM placement checks; see `environment-v6-cw-review.md` for
scope, hashes and outstanding gates. This is not full-level art acceptance.
See `environment-winding-review.md`. Do not ship the old scene-v1–v4 candidates.

Original Painter 2D artwork is integrated into real q3dm1 WASM rendering, not a
testmodel or Blender preview. The package has 16 × 512² TGA materials and unique
`textures/remaster_environment/*` shaders. It contains no original map, model,
texture, sound, VM or credential. This is diffuse/lightmapped art, **not PBR**.

`environment-coverage.json` enumerates every BSP shader slot in the four available
private Demo references. Material assignment is a candidate, not art acceptance;
all geometry-remade/full-game/runtime-accepted gates remain false. q3dm1 is the
review priority. q3dm7/q3dm17/q3tourney2 assignments are unreviewed expansion,
especially transparency, moving surfaces and authored UVs. Flame effects remain
owned by the effects producer; common clip/caulk/hint materials remain unchanged.

## Integration boundary

Load `environment-materials-v1.pk3` alongside an authorized map whose visual shader
names reference the unique shaders. A PK3 with duplicate original shader names is
insufficient: ioq3 reverses shader-script concatenation and the original explicit
sky shader won in an actual browser test. No renderer change is required.

For private technical verification only, `prepare_map.py` rewrites the 64-byte
name field in each BSP shader record and converts RGB lightmaps, vertex colors,
and lightgrid ambient/directed colors to max-channel neutral gray. Thirteen whole
lumps remain identical. Within the other four lumps, surface/content flags,
vertex positions/UVs/normals/alpha and lightgrid direction bytes remain identical
and receive separate protected-field hashes. BSP header/offsets, geometry,
entities, spawn/trigger timing and PVS are unchanged. The original AAS
is preserved in the reference PK3. The private derived AAS updates only encoded
checksum bytes 8–11, with all navigation payload and lump tables byte-identical.
This adaptation was explicitly approved after BotLib correctly rejected the
first visual BSP's changed whole-file checksum. The tool uses production
`code/qcommon/md4.c` and AAS v4/v5 header encoding; no engine check is disabled.
It records hashes for every BSP lump and AAS payload. Max-channel grayscale is a deliberate art
adjustment after luminance grayscale left red-lit halls excessively dark; it is
not radiometric preservation. The first candidate preserved lightgrid/vertex
colors and produced a severely dark brown wall crest in the renderer owner's
actual placement test. Lighting v2 applies the same neutral transform across
all three representations without brightness multipliers or direction changes.
The old private package is preserved for matched-camera comparison. Neutral
color does not guarantee adequate illumination; runtime art acceptance remains
separate from the byte-invariant checks.

**Do not publish the derived Demo BSP or the fixture directory.** Only original
material assets and generated prop candidates live here. The complete authorized
source data and editable map sources are still missing. Scene-v6-cw binds thirteen
props, but does not claim full geometry rebuilding, statue replacement, new
collision or a compiled release map.

## Reproduction

Use Emscripten 3.1.58 and the observer-enabled fixture instructions in
`misc/tests/gameplay/README.md`; rebuild current QVMs via `prepare.mjs`, including
the Bot inventory ABI adaptation. Then:

```sh
uv run --with pillow==11.3.0 python misc/remaster-assets/environment/package.py \
  PRIVATE/pak0.pk3 assets/remaster/environment/material-atlas-v1.png assets/remaster/environment
uv run --with pillow==11.3.0 python misc/remaster-assets/environment/prepare_map.py \
  PRIVATE/pak0.pk3 PRIVATE/output
uv run --with pillow==11.3.0 python -m unittest discover -s misc/remaster-assets/environment -v
node misc/remaster-assets/environment/review.mjs CDP_WEBSOCKET PRIVATE/review
```

Copy the original material package and private map package into the fixture's
`demoq3` directory and add both names to its preload array after the VM package.
Use a supervised private HTTP service **without a portal**. Neither observer
build nor Demo input is release material.

## Evidence and unfinished content

2026-09-10: current engine/QVM build completed (599 Ninja steps). Four asymmetric
unit tests pass: flag preservation, visual-only mutation, independent max-channel
expected bytes, skipped flame/clip slots, corrupt BSP rejection and independently
expected AAS v4/v5 encoded checksum bytes. Real Chromium
SwiftShader/WebGL2 HDR walkthrough passed actual keyboard yaw, >100-unit motion,
armor pickup, airborne jump and landing, and captured five linked viewpoints.
Sky atlas-border seam was seen in v2, removed by cropping and edge mirroring, and
rechecked in v3. Package-loading logs contain no remaster texture warnings.
The shared reliability runner passed HDR0/HDR1 `vid_restart`, q3tourney2/q3dm17/
q3dm1 switching, and full reload after forced context loss. After AAS adaptation,
the unchanged shared Bot runner passed falling death/click respawn, actual hit
damage, fraglimit-3 score screen and match restart. This finite match does not
prove every route or all-map navigation. Initial AAS failure remains in the log.

The existing shared `baseline` run **failed** its mouse-turn assertion: capture
already changed yaw from the original −45° to −72.828°, leaving only 17.161° to
the requested −90°. Its failure is retained, not relabeled PASS. The independent
environment keyboard walk does not claim to fix or validate that mouse harness.

Art inspection remains partial: original statues/heads and geometry are obvious;
near-black arch interiors and bright window panels need lighting work. Five views
do not cover every room or Bot route. Full geometry, formally generated 3D
architecture, LOD/PBR, authored placement/visibility, full navigation, native/LDR,
physical-GPU performance and all-map acceptance remain outstanding. LDR loading
was tested, but its bright window panels need art refinement. The existing pillar
was not purchased again.

## Historical wall crest candidate — superseded by scene-v6-cw

The following records the old CCW experiment, not a currently valid front-facing
art judgment. Correct CW export uses yaw180 and the placement in
`environment-wall-crest-placement-cw.json`; see `environment-v6-cw-review.md`.

`environment-wall-crest-q3dm1-v1.pk3` combines the existing approved Painter
prototype → one Hunyuan3D task → Blender 3.4.1 cleanup/bake → decoded MD3 pipeline
with `maps/q3dm1.remaster.json`. The 1800-triangle, five-surface opaque model uses
1024px diffuse only. Generation cost matched the exact request ID at **$0.50**;
Painter cost remains unknown. The source receipt is
`assets/remaster/receipts/environment-wall-crest-v1.json`.

Placement now uses runtime-verified yaw0, uniform scale0.84 and origin
[673.9128125,1205.625,296.37]. The earlier preview-derived yaw180 was wrong:
it displayed the generated back, not a severely underlit ivory front. A same-camera
yaw0 control exposed the front without model, texture or exposure changes.
Exported vertices fit wholly inside original
surface2050's AABB. This is not an inferred center-pivot placement: the exporter
uses XY-centered, Z-bottom coordinates. The five environment tests include an
asymmetric transform and rejection on both sides of the allowed envelope.

The renderer's original-surface/leaf registration is integrated and locally tested;
this package does not use testmodel or hide every instance of a material. Four
matched-camera WASM states (v1/v2 lighting × HDR/LDR) passed binding and context
checks. Inspected v2 front views show ivory and cyan; v1 front views retain warm
gold/brown cast. The initial dark-back captures do not establish front-lighting
quality. Source texture fringe, faceting and thin cyan remain art issues; broader
moving/oblique visibility and complete-level acceptance are still outstanding.

`package_crest.py SOURCE_PK3 RECEIPT PLACEMENT OUTPUT_PK3` reproduces the combined
package and verifies the receipt hash and every transformed vertex. Source GLB,
Blender master, paid-state recovery and prototype are in the ignored archive
recorded by `environment-wall-crest.json`; 14 files verified locally. Off-orb
durable backup is not claimed.
