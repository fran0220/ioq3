# E2/E3 glow companion, 2026-09-11

`environment-scene-q3dm1-v3.pk3` SHA-256
`2e7d5f8b23ebd4da47642be9880be2ffad6a1182e952f291a1a0449116a69881`.
Eleven model instances bind the same27 original surfaces as v2. Each lamp
retains its original opaque surface bytes; a new surface adds four floor
quads or one wall quad. Headers/frame bounds change to enclose them, and
placement is recomputed inside the original solid-source envelope.

FX source: `effect-environment-lamp-v1-candidate.pk3`, SHA-256
`5b6e8030ca2a09936760b44d7b0ea51d312253e82521f9b9683d1d2c33b5f42b`.
Quarter intensity is baked by the FX owner, unchanged here. No new dynamic
light, exposure compensation, sound or gameplay event. Exact quad positions,
UVs and normals are in the environment-*-lantern-glow-v1 derivative receipts.

Rebuilt current WASM with additive companion support and repackaged current
Release QVM via `misc/tests/gameplay/prepare.mjs`, including current inv.h.
`review_lanterns.mjs`: ten positions × HDR1/HDR0 =20 PASS; 27binding logs,
real300ms lateral input moved each camera >10 units, no context loss.
Inspected `.amp/in/artifacts/environment-e3-v3-glow/{hdr-contact,ldr-contact}.jpg`:
all ten lamps show restrained narrow cyan centers, no visible black rectangle,
wrong facing or bleed through the body. Large bright wall patches predate
these emissive surfaces and remain a separate environment-art refinement.

Five scene/companion tests pass, including byte-preserved opaque surfaces,
independent expected appended bounds, signed rotations and degenerate fit
rejection. Shared asset suite:45 tests, OK with2 Blender opt-in tests skipped.
This does not certify complete map art, moving-PVS boundaries, foreground
occlusion, shadows, collision/AAS, Bot competition or hardware performance.
Renderer owner is independently checking grouping and companion behavior.
