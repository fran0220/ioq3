# Private combined runtime review — 2026-09-11

This is a local Demo-based test, not a release candidate or publication.
Engine source: [5e7aed0a](https://github.com/fran0220/ioq3/commit/5e7aed0ae3d3baea882433a43edf8d96fbb21a8e),
Emscripten 3.1.58, Release, `IOQ3_WEB_TEST_OBSERVER=OFF`.
Rebuilt WASM SHA256 `3046d2487ac5cd3f80b197e8882a4e14c7fee6d1e60242bcf9b3afedc8ff81da`;
JS `db53f0ec69f5229c9676f0d3148f481caa3edf499dfe78b952e9399ab0860b23`;
fresh three-QVM + current `inv.h` PK3 `b0f5f54b8ca41ac2614820520d0ebe31f2fb098acefcb41fc0f1ed5d741f9c79`.

## v6 CW scene + welded Sarge + four weapons

Private manifest revision `3d7a1038218cfc573ecab9db7f8b451482f36b3c56ae9c27e0224e002b902aa5`.
Fourteen PK3 sizes and SHA256 values independently match actual WASM FS bytes.
Scene `df217c6ddbb90b1d0a566f1df07469ae732b84479cb2e87329c2b2d23f5a4c9c`;
Sarge `8af2817673ca88b2c99530bc48d1c1cd384400a943e37959d3f022f338ce1b19`.
Includes MG/RL/SG/GL, current hands, SG audio, muzzle, new UI icons and the private
neutral-lighting map. The obsolete standalone crest binding pack is absent.

`code/web/tests/match-browser.sh` passed real DOM catalogue/model/limits launch,
Gauntlet infinite-ammo HUD, death, keyboard respawn, actual Bot timelimit standings,
frozen intermission clock, restart, spectator and disconnect. No observer.
Independent q3dm1 launch logged all 31 surface bindings and no context loss.
The first logging probe incorrectly read stdout only (zero total lines); corrected
test-only capture includes stderr, where `Sys_Print` writes. No renderer workaround.
Private raw results: `assets/remaster/work/combined-v6-cw-{fs,bindings}.json`.

Inspected `.amp/in/artifacts/combined-v6-cw-gameplay.jpg`: scene, HUD and MG render
without a black frame/default-texture blocks; weapon/material detail remains soft.
This is not full environment art/PVS acceptance, per-weapon combat validation,
SG audio/visual synchronization, platform multiplayer, or hardware performance.
