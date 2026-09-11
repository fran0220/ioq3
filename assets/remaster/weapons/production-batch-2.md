# Continued complete base-Q3 production, not a two-weapon scope

Execution order: finish MG/RL materials and two-hand fitting while producing
shotgun/grenade; then gauntlet/lightning/rail/plasma/BFG individually with
view/world/pickup meshes, hands, attachment sockets, sound and associated FX.
Follow with all eight ammunition classes, health/armor, holdables, six powerups,
two CTF flags and shared blood/water/teleport/respawn effects. Every item retains
its independent visual, audio and actual-gameplay acceptance gate. No weapon
is complete merely because its image or GLB exists.

Shared registration stays with the integration owner: cg_main graphics/sounds,
cg_ents pickup presentation and cg_event mappings only where required by actual
new content. Weapon IQM body/hands/barrel/flash interfaces currently suffice;
no new shared header/ABI, game event, reload, damage or physics change is planned.
Per-weapon measured left-hand points go to the character owner after mesh review.

2026-09-11 paid batch, original Painter concepts:

- Shotgun: `task_Cjyt1XZ1JdAYFhwEI7JEa25oMMTK4ZJE`, generated GLB downloaded,
  Blender cleanup and initial rigid IQM complete. Full side view inspected:
  distinct twin barrel and fixed grips; generated length about 1m exceeds the
  intended .7m and needs authored size/fitting. Material still dark/noisy and
  is not final. Matched Hunyuan charge $0.50.
- Grenade launcher: `task_a53zMOoUfFmv3F4Le5bxwSotgfV5JVZP`, GLB downloaded and
  Blender cleanup complete; attachment fitting pending. Matched charge $0.50.
- `effect-shotgun-fire-v1`: one ElevenLabs sound submission, matched $0.0007.
  Inspected audio has one immediate blast, decay under a second, no speech,
  music, reload or extra shot. ffprobe: mono PCM16, 22050Hz, 1.48 seconds.
  Source hash and request/cost in receipt. Not yet installed or in-engine synced.
- Painter costs are not exposed and remain unknown, not zero.

`sound.py` saves submission-unknown before network and never automatically
retries a sound POST, even after transport failure. The recovery unit test
simulates an ambiguous failure, repeats the invocation and changes input,
proving only one request occurs and the immutable state survives. Seven weapon
tool tests pass. Decoding a saved successful response is local/repeatable.

`bake_normal.py` runs the actual paid high-resolution mesh against the immutable
cleaned runtime UV mesh, records hashes, and writes a separate material stage.
Rocket bake executed and atlas inspected: coherent main islands, localized
saturated small islands need engine inspection. No new normal map is installed
in the validated runtime package yet. Bake output alone is not material approval.

All new source data remains private in `assets/remaster/work/{asset-id}`;
cross-orb recovery and final source archival are required before closing this
batch. Original Demo is reference only, never part of these generated outputs.

Runtime follow-through: shotgun fit uniformly scales mesh/socket translations
by .8, giving .80m length and unit attachment axes. Actual IQM bytes independently
test tag_flash (25.664,0,4.48) Q3 units. Grenade retains measured .48m length.
Both have candidate PK3s; right-arm package explicitly supplies those two view
slots in addition to MG/RL, still no final left arm/finger articulation.
`verify_batch2.mjs` ran in actual Chromium SwiftShader HDR and LDR with original
private Demo reference character/environment: each gun single shot costs one,
held input costs three, release stops, switch preserves ammo. VFS body/hand/QVM
hashes and actual r_hdr are checked, not inferred from the URL alone. Current
full Web build and eight weapon-tool tests pass. First/third-person screenshots
were inspected: forward continuous attachment, no visible inverted faces/spikes;
washed-out receivers and obscured grips block final art acceptance. This is not
exact cadence, damage, knockback or final segmented-character fit acceptance.
New source archives before fitting were copied/hash-verified by the integration
orb; later rigged derivatives still need recovery transfer. Sound remains
reviewed but uninstalled and no new firearm FX is claimed complete.

Lightning `task_d9K2uCcnMZosQFgIdarBRLf78yFWDNmP` is downloaded and processed
in Blender, charged once at matched $0.50; no runtime integration yet. Its
Painter prototype has two forward conductors, not a beam baked into geometry.
Sarge's existing generated source archive was copied into the weapon-private
directory and matched SHA256 d38908d61475806cb720a45a8a6f20c56ac2842ec98307a6c870f1e5b10b62ed.
It may supply consistent forearm geometry without another generation fee;
24 source bones have no separate finger rig, and topology still needs inspection.

Nine weapon-tool tests now pass. `fire_rules.c` includes actual `bg_pmove.c`
and links production shared event/item functions, not a reimplemented weapon
simulation. Independent normal/haste interval tables test each base weapon at
one millisecond before/at refire, release, missing ammo, infinite-ammo melee
contact, and 200ms drop/250ms raise boundaries. This is native shared-rule
verification, not browser cadence/damage/knockback/rocketjump acceptance.

After the QVM header dependency fix, fetched through b5b519cd and executed
`cmake --build build-web --clean-first --parallel 2` (602 steps), then rebuilt
the private QVM/`inv.h` package using gameplay `prepare.mjs`. Package SHA256:
ac503e3d24a38fef5a8cded5a9a7a1d69f1b1da51c503781eb48d8966a6e1991.
SG/GL/MG/RL all reran successfully in HDR and LDR with actual VFS hashes,
`ps.weapon`/ready checks and ammo assertions. Evidence is private
`weapon-shotgun-v1/browser-clean-{hdr,ldr}` (also GL), and corresponding
MG/RL work directories. Clean-build inspected images still show overbright
ivory; do not attribute this to mixed QVMs or fix it by global exposure changes.

Ten tool tests now pass including actual `G_Damage`/`CheckArmor` and production
team predicate for nonfatal FFA cases. Asymmetric direction (3,0,4), 100 damage,
g_knockback=1000 gives (300,0,400) impulse; self-health damage halves only after
impulse. Armor uses .66 (50 self damage saves33, takes17), not exact two-thirds.
Battlesuit radius protection retains impulse; explicit no-knockback does not.
This tests server damage math, not full projectile collision, radial falloff,
target deaths, browser hit registration or performed rocket jumps.

`extract_arms.py` executed against copied Sarge source; left/right forearm/hand
cuts have 699/859 vertices. Inspected left render shows coarse joined finger
geometry and an open proximal cut: not a finished hand rig or releasable arms.
No character source was changed and no additional generation fee was incurred.

Environment lamp companion was handed off to the environment owner. Independent
inspection of its reported HDR/LDR contact sheets found no black quad/obvious
ghosting; original LDR wall-east/west close frames remain too white to discern
the vertical cyan capsule. Requested same-camera A/B from environment; do not
claim all ten lamps accepted or infer the white wall light came from this glow.
