# Original UI texture pack

Four original Painter atlases supply engine pickup, weapon, ammunition,
powerup, flag-state, network and award artwork. `provenance.json` records every
source URL/hash and the unavailable cost/task-ID information. No source game
texture, model, text or logo was used as input. The first atlas's similar flag
silhouettes are intentionally excluded in favor of the dedicated status atlas.

`ui-icons-v1.pk3` contains only 73 textures. It covers all 51 `bg_itemlist` icon
paths, native status flags and six medal textures. Shader names and gameplay
remain unchanged. Character portraits belong to the character workstream;
world pickups and first-person 3D models are not this UI package's scope.

`ui/remaster/loading.jpg` reuses the existing Painter hangar, with the earlier
provenance in `../provenance.json`. It is neutral loading artwork, not a map
screenshot. `CG_DrawInformation` selects it only when installed; actual loading
text, server rules and map name remain engine-rendered, and stock installs keep
their original levelshot fallback.

## Reproduce

`python package.py` uses Pillow and the committed transparent `tiles/` to build
a deterministic archive and per-file SHA256 receipt. For source reprocessing,
use `python package.py --prepare` with rembg 2.0.84 / ONNX Runtime 1.30.0 /
Pillow 12.3.0. This uses rembg's u2net segmentation; it never invents alpha via
color thresholds. Existing tiles are retained, so routine package builds do not
repeat inference or paid generation. Health/armor colors are derived from the
original generated silhouettes, retaining their alpha.

`python test_package.py` checks source/archive hashes, reproducibility, actual
engine item-icon path coverage, transparency and distinct ammo/weapon and
team/flag-state images. Package after the source game data as a later VFS pak;
do not copy the private Demo used in local engine tests into a release.

## Acceptance status

Web engine/QVM build passes; processed icon contact sheet inspected at 64px.
Actual WASM mounts the 73-file pack. Native HUD visual acceptance is **pending**:
current local engine shows default black/white placeholder textures in both the
new-pack case and the stock-Demo negative control, including original numeric
digits. This is not recorded as a successful icon rendering test. The renderer
owner has the paired captures. Final flag/medal/loading state captures and the
combined remaster release remain required after resolving that control failure.
