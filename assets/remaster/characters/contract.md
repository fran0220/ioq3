# Segmented skeletal character contract v1

Status: production contract, **runtime acceptance pending**. No full-body layered
skeleton ABI is introduced. Three IQM2 meshes retain the original independent
lower/upper clocks, relative aiming and pain twitch. Author the visible seams
under overlapping waist/neck armor; do not split exposed skin across a joint.

## Coordinates and sockets

- X forward, Y left, Z up, 40 Q3 units per meter, unit bone scale.
- Lower origin is the authoritative player origin: standing feet at Z=-24.
  Visual size never changes collision, viewheight, speed or root motion rules.
- Lower owns `tag_torso`; upper origin is that socket, and owns `tag_head`,
  `tag_weapon`, optionally `tag_flag`; head origin is `tag_head`.
- Socket names are case-sensitive. Socket X points forward, Y left, Z up.
  Weapon geometry's grip reference is its local origin. Weapon owns
  `tag_flash` at muzzle and `tag_barrel` on the spin axis, forward +X.
- Export attachment bones as non-deforming joints, with every parent retained.
  Socket transforms use the same frame/oldframe/backlerp as their mesh,
  including cross-clip transitions. Never reset a socket's clip separately.

## Clips and authoritative events

Use `animation.cfg` in existing `animNumber_t` order and existing timing.
IQM names/FPS/events are production metadata, not renderer callbacks.
The cgame subtracts `LEGS_WALKCR.firstFrame - TORSO_GESTURE.firstFrame`
from all leg-only frame indices. Export lower frames in that rebased layout;
upper uses unre-based cfg frame indices. BOTH death/dead indices agree in both.
Head uses frame zero; aiming is composed by `CG_PlayerAngles`.

Sarge Demo reference verified privately (not redistributed):

| Semantics | cfg first/count/loop/FPS | Runtime lower first |
|---|---|---|
| DEATH1 / DEAD1 | 0/30/0/20; 29/1/0/20 | 0;29 |
| DEATH2 / DEAD2 | 30/30/0/20; 59/1/0/20 | 30;59 |
| DEATH3 / DEAD3 | 60/30/0/20; 89/1/0/20 | 60;89 |
| GESTURE | 90/40/0/18 | — |
| ATTACK / ATTACK2 | 130/6/0/15; 136/6/0/15 | — |
| DROP / RAISE | 142/5/0/20; 147/4/0/20 | — |
| STAND / STAND2 | 151/1/0/15; 152/1/0/15 | — |
| WALKCR / WALK | 153/8/8/20; 161/12/12/20 | 90;98 |
| RUN / BACK | 173/11/11/21; 184/10/10/20 | 110;121 |
| SWIM | 194/10/10/15 | 131 |
| JUMP / LAND | 204/10/0/18; 214/6/0/20 | 141;151 |
| JUMPB / LANDB | 220/8/0/15; 228/1/0/15 | 157;165 |
| IDLE / IDLECR | 229/10/10/15; 239/8/8/15 | 166;176 |
| TURN | 247/7/7/15 | 184 |

`CG_MapTorsoToWeaponFrame` maps ATTACK/ATTACK2's first six frames to
hands 1..6; DROP's **nine-frame window** to hands 6..14. Thus DROP's five
frames map 6..10 and immediately adjacent RAISE's four frames map 11..14.
Everything else maps zero. It is not a 0..8 fire clip. Preserve this adjacency.
Backward crouch/walk are reversed clips. Additional torso gestures must have
explicit production clips, not be claimed complete by the legacy fallback.

Pain uses the original timed torso twitch, not a new animation lock. Fire,
muzzleFlashTime, footsteps, hit, death, respawn, haste and movement remain
game/cgame events. Clips never delay shots, add reloads or drive player origin.

## Materials and acceptance

Initial material contract: r_pbr=0, r_glossType=1; lightingDiffuse base stage,
tangent +Y normalMap, specularMap RGB linear F0 / alpha 1-roughness. Never
feed ORM directly. Separate restrained additive emission with depthFunc equal.
Red/blue skins require different shape symbols as well as colors, consistently
visible from front/back/sides. Preserve mesh names in all .skin mappings.

Required native and PC browser evidence: real loader/skin/shader registration,
lower/upper simultaneous non-default poses, walk/run/crouch/jump/attack/pain,
three deaths/dead poses, respawn, aimed gun/muzzle/barrel, both teams, and
front/back/side inspected captures. Export/math tests are not that evidence.
No synthetic fixture is a release character. Full base-Q3 coverage remains open
until full reference archives/version/priority are supplied and inventoried.
