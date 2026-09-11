# Character review and completion plan — 2026-09-11

This workstream implements the user's request to review the game, plan the
remaining work in full, and finish it. It does not replace the integration
owner's game-wide plan in `docs/remaster-plan.md` or declare a candidate released.

## Audit findings

1. Sarge is the only produced character. His segmented IQM works in actual
   native and Web clients, with independent clocks and MG/RL attachment offsets.
   Latest consistent-QVM baseline and native death/respawn events pass. Final
   finger/forearm fit, full-speed combined animation and team combat remain open.
2. Current review cameras crop corpses/lower body or hide the support hand.
   Such screenshots cannot close full-body or two-hand acceptance. Offline grip
   inspection also needs stored skinned vertex normals rather than flat shading.
3. Default/red/blue skins and one portrait exist; krusade and the other verified
   characters/alternate skins remain production work. No Sarge recolor may count
   as Grunt, Major or Visor.
4. Four reference models and fifteen model/skin combinations are verified from
   the private Demo. This is not a complete base-game inventory. Full original
   archive/version/priority remains an input dependency, not an authorization gap.
5. The whole-rig editable Blender master and later segmented JSON/IQM source
   differ. Recovery copies are hash-verified across two orbs, but external durable
   backup and a reproducible final authoring handoff remain open.
6. Shared game status, based on tracked coverage rather than new independent
   acceptance: weapons still lack several final models, pickups and effects;
   environment relief materials remain too dark; production platform full match,
   real hardware performance and clean redistributable game package are unclosed.

## Execution order and acceptance

| Batch | Work and output | Required evidence |
| --- | --- | --- |
| C1: trustworthy inspection | Correct grip review normals, show both palms/forearms from opposing views; frame complete live/dead body in actual clients | Inspect captures; distinguish preview artifacts from runtime defects; no runtime acceptance from Blender alone |
| C2: Sarge geometry and rig | Repair demonstrated arm weight/twist or contact defects; preserve UVs, materials and silhouette; author finger controls where topology supports them, repair topology otherwise | Before/after decoded mesh checks and near native/Web captures on both hands, not wrist sockets alone |
| C3: all weapon grips | Consume weapon owner's measured grip/support frames for all nine weapons, share derived hand source without shared-file edits; explicit upper frame blocks as needed | Rest/fire/drop/raise, both frame endpoints and weapon switch transitions; original mapper, shot times and physics unchanged |
| C4: complete action/skin set | Review walk/run/back/crouch/swim/jump/land/backjump/turn/gesture/attack/pain/death/dead/respawn, default/red/blue/krusade, all relative aim directions | Full-speed native and browser combat; full-body front/back/both sides; three deaths and death-to-respawn transitions; natural exposed skin and distinguishable team symbols |
| C5: verified roster | Grunt, Major, Visor individually: private reference review → Painter prototype → one tracked Hunyuan task → Blender topology/material/rig/action production → segmented IQM; produce stripe/daemia variants and matching portraits | Each original identity and skin has its own model/portrait review, bounds/tags/clips validation and actual combat evidence; no recolor stand-ins |
| C6: remaining base roster | Inventory authorized full archive when available, extend the same production and acceptance sequence to every remaining base character/skin | Hash/version/VFS-order inventory reconciles exactly with production manifest; missing items remain explicit |
| C7: integration and release | Rebuild current QVMs after shared headers, repack inv.h, verify loaded FS hashes, combine final map/weapons/UI; preserve final source and license/provenance package | Rules regression plus native/Web matches, platform two-player match, device/browser performance, durable source backup, clean release scan and post-publish verification owned by integration |

## Fixed contracts and responsibilities

- Character owner: `cg_players.c`, actual IQM loader defects, character assets,
  IQM tools and `models/players/*/icon_*.tga`. No gameplay or root-motion changes.
- Weapon owner: weapon geometry, measured sockets, first-person dual hands and
  original 15-frame mapper. Character owner consumes approved support transforms;
  no guessed universal offhand point for different guns.
- Environment may derive static statues in its own directory from the generated
  Sarge source. Static decimation needs separate topology/winding validation;
  character runtime checks do not certify that conversion.
- Integration owns shared ABI, full game manifests, clean builds, multiplayer,
  release and global plan; renderer owns other renderer files. Request exact
  interface changes before touching their files.

## Production controls and completion rule

Meshy submissions remain paused; do not resubmit failed operation 569. Its
refund deduplication fix is deployed according to coordinator process/version
evidence, not a production concurrency-injection test. Hunyuan availability
does not imply an existing character task: inspect receipts, private task state
and generation identity before each new revision. Retain request IDs, hashes,
known costs and unknown accounting separately; never overwrite failed evidence.
Manual rig/animation authoring remains available and does not depend on Meshy.

Only promote `runtime_accepted` after the corresponding acceptance matrix passes.
Do not block available production on the missing full archive, but do not publish
private Demo content or call the four-model subset complete. Real PC tests and
external backup require their actual device/storage access, not simulated PASS.
Commit verified batches separately to main; retain negative controls and failed
captures. Re-review changed combinations after every shared ABI or asset revision.
