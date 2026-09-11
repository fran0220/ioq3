# E2/E3 atomic placement candidate, 2026-09-11

`environment-scene-q3dm1-v2.pk3` SHA-256
`0fbc6d2fdd5da67191864a7a840dbc6cfbbbb4e386fb25761ea1df7a98027726`
contains eleven model instances: one crest, four standing lanterns and six
wall lanterns. Twenty-seven original surfaces are bound, including ten
original flame surfaces suppressed atomically with their solid fixture.
All shapes fit original solid-member bounds; flame extents do not enlarge
them. No source BSP/AAS is packaged. No new lighting or glow is included yet.

The observer-enabled Emscripten3.1.58 WASM was rebuilt with renderer atomic
groups present. `review_lanterns.mjs` ran ten camera locations in HDR1/HDR0,
with real 300ms lateral keyboard input at each. All twenty states loaded
27 bindings, moved more than10 units and retained the WebGL2 context.
Snapshots and forty captures are in this production orb's private review
directory `.amp/in/artifacts/environment-e3-v2-motion/`.

Inspected HDR/LDR contact sheets: all six wall lanterns show their ivory
fronts, including both diagonal walls; no old fire or obvious floating/
detached fixture is visible. Four standing fixtures remain too dark and
their detail is weak against the bright walls. This is not final art.
The generated cyan glow companion will be integrated as a deliberate lamp
surface, not exposure compensation or an invented dynamic light source.
Moving captures still need individual inspection before visibility approval.
Noclip inspection is not collision, AAS, Bot or full-map acceptance.

Two camera assertions failed before the completed run and remain in sibling
`environment-e3-v2` and `environment-e3-v2-settled` journals. Input
`[825,1510,40],yaw90` settled at Y1525.50134 in one run and Y1529.29529 in
another. Source `g_misc.c` adds velocity400 and Z+1; `PM_NoclipMove` applies
friction9 with variable frame time. The final check therefore verifies
forward displacement between0 and400/9, near-zero sideways displacement,
and Z+1 rather than assuming a fixed position. No original failure was
rewritten as PASS.

Four scene-fit tests cover asymmetric pivots/limiting axes, signed90° yaw,
45° extrema from all eight corners, strict margins and degenerate bounds.
Geometry master source hashes and unique paid tasks remain in asset receipts.
