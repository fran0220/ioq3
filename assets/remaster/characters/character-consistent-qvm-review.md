# Consistent QVM combination rerun

2026-09-11: fetched main through b5b519cd, including the q3lcc header
dependency fix b085af1c. Native build completed 919 steps; Web build completed
567 steps, rebuilding baseq3 and missionpack QVMs. A subsequent observer-enabled
Web build supplies read-only snapshots for the gameplay runner.

Fresh private fixture: `assets/remaster/work/character-consistent-b5b519cd`.
`misc/tests/gameplay/prepare.mjs` repacked current QVMs and GPL `botfiles/inv.h`.
ZIP entries compared byte-for-byte with current build/source inputs:

| Input | SHA256 |
| --- | --- |
| cgame.qvm | bb7f6f60bd073d08d9672582a993a59b17e769f4b42bce72370d6160676cf8ae |
| qagame.qvm | 5bc68620b51aba88c4dcf3696dbd4a3ebd8d68716de879cc879f704f04183254 |
| ui.qvm | beaef2b3f224ded9d45da2aa1a1efce446ea0dd91fb17ff0ab66b5211db1db8b |
| inv.h | dd8677db6015d45dca97c8bd2bfc42a16b9f272a05dc1989c565172cdfd2072d |
| VM PK3 | ac503e3d24a38fef5a8cded5a9a7a1d69f1b1da51c503781eb48d8966a6e1991 |

Browser Web Crypto SHA256 of actual Emscripten FS bytes matched disk for all
nine loaded packages: private Demo, VM, Sarge, machinegun, rocket, shotgun,
grenade, hands, and rocket muzzle effect. Exact values are retained in the
fixture's `results/fs-hashes.json`; Sarge remains e6ee819ac3fa4ca6c96537b31a329f0f05264c8a362651b8e4d0a78fac77055e.

`node misc/tests/gameplay/run.mjs CDP OUTPUT baseline`: four PASS results
(mouse-turn, move-and-pickup, jump-and-land, mouse-fire-consumes-ammo), with
original assertions unchanged. Native `review_native_combat.py` against this
same fixture: three real death IDs 0/2/4 with live respawns and nonfatal bot
damage all PASS. Native screenshots from this rerun have not yet been inspected;
event assertions alone do not establish visual acceptance.

Inspected browser captures `.amp/in/artifacts/character-consistent-mg.png`
and `character-consistent-rocket.png`: intact HUD, connected character body,
visible attached weapons. Hands overlap weapons and framing crops lower body;
machinegun view suggests possible forearm/torso intersection. These captures
do not close precise finger/offhand fit or full-body animation acceptance.
No runtime asset changed and `runtime_accepted` remains false. SG/GL packages
were hash-verified as loaded, not yet accepted as third-person grip poses.

Private Demo data remains private. No generation POST or billing operation was
performed for this rerun. Existing historical failures remain retained.
