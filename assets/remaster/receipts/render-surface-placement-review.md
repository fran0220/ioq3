# Renderer-owned static surface substitution review

Technical integration only; not final environment/art acceptance or release.

The renderer loads a map-side JSON binding, validates exact map/index/shader/
AABB and opaque static model bounds, allocates normal backend-owned entities,
and preserves original surface visibility ownership. No public ABI or BSP,
collision or PVS bytes change. The manifest contract is documented in
`misc/tests/remaster-rendering/README.md`.

Native build and five renderer C test programs pass. New loader tests include
wrong map/index/shader/bounds, missing model, oversized transforms, invalid
numbers, missing bounds and nonopaque materials. Scene tests cover capacity
failure and scene/frame reset. Emscripten 3.1.58 Web build passed.

Real WASM review used private Demo/QVM, environment material v1, private
environment BSP v1, and wall-crest model/config SHA-256
`d7eeef0944a46b36685980c9508a47cc1b82f0edc6063baf2d82b24ffa5da1c2`.
No private data is committed or exposed through a portal. Browser was
Chromium/SwiftShader; no physical GPU performance claim.

`placement-run.mjs` passed six registration/GL/context cases: placed HDR,
placed LDR, absent binding, missing model, entities disabled, and farther
placement. Each reported GL error 0 and no spontaneous context loss. Captures
are under `.amp/in/artifacts/render-placement/v1/` in the renderer thread.
The mounted generated crest is dark brown; the no-binding/missing-model/
entities-disabled controls restore the original gray bull head. No duplicate
source bull head appears in replacement captures. Far placement remains
mounted. HDR/LDR do not show a clear brightness difference in these captures.
The dark brown appearance is not accepted as finished lighting/material art.

Camera startup: `activeAction "noclip; setviewpos 674 1350 286 270"` then
`devmap q3dm1`; settled origin approximately `[674,1334.499,287]`, angles
`[0,-90,0]`. Far variant uses Y=1500. HDR 0/1, framebuffer object 1,
otherwise default exposure/tonemap settings. This fixed-camera test does not
prove keyboard input, moving visibility, shadow silhouette or final combined
environment/character/weapon/HUD acceptance. CDP keyboard stopped reaching SDL
also on the preceding unmodified fixture; that unresolved automation issue is
not classified as a renderer regression or claimed passing.

## Matched private lightgrid/vertex-neutralization comparison

Repeated all six cases with private environment lighting v2 SHA-256
`bb08ca72689dcb5319ea55e1100ccf1419c6f4e34a537141a8829c7d74f6239f`:
all passed registration/fallback, GL error 0 and no context loss. Only the
private map PK3 changed; the same WASM, model, camera and exposure settings
were retained. Captures are in `render-placement/v2`; inspected comparison
is `.amp/in/artifacts/render-placement/lighting-comparison.jpg` (v1 top,
v2 bottom; HDR left, LDR right). The neutralized crest becomes gray instead
of brown, with unchanged silhouette and placement. It remains underlit
relative to the arch and its engraving lacks contrast, especially in LDR.
This supports a lightgrid color contribution, not finished art acceptance.
Defaults used are cameraExposure=1, autoExposure=1, toneMap=1,
forceAutoExposure=0, forceToneMap=0. Rebased combined native and Web builds
also succeeded; three material-math tests passed.
