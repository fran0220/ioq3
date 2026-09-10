# GL2 remaster material contract v1

This is a runtime conversion contract, not a claim of glTF/PBR fidelity or
whole-game visual acceptance. Keep generated GLB/Blender and original channels.
The first integrated scene uses `r_pbr 0`, `r_glossType 1`,
`r_normalMapping 1`, `r_specularMapping 1`. HDR and LDR use the same materials.
Do not change global PBR per asset: it reinterprets every existing specular map.

## Authoring and GLB conversion

- Base RGB: ordinary color texture, with original coverage alpha. GL2's legacy
  path does not provide a standard linear-light sRGB pipeline. Do not pre-square
  normal, specular or alpha data. Document color encoding in the asset receipt.
- Normal: tangent-space OpenGL +Y, RGB encoded from [-1,1] to [0,1]; flat is
  (128,128,255). GL2 reconstructs positive Z from XY. Export tangent handedness
  correctly, including mirrored UVs. Invert G only for an actual DirectX -Y
  source, not as an arbitrary appearance adjustment. Use `normalScale 1 1`.
- Legacy specular: RGB = linear normal-incidence reflectance F0, A = smoothness
  = 1 - perceptual roughness. Pack as lossless RGBA TGA/PNG, not JPEG. For glTF
  inputs first multiply texture channels by their scalar factors; roughness is
  G and metallic is B in the glTF metallic-roughness texture. AO R is separate,
  **not** roughness and **not** a runtime slot here.
- An explicit approximate metallic conversion is F0 = mix(0.04, linear base
  color, metallic), and diffuse color = base color attenuated by (1-metallic).
  Decode sRGB before the F0 mix, and re-encode color after any linear diffuse
  operation. GL2 further multiplies diffuse by (1-F0), so this is a conservative
  legacy approximation, not an exact metallic-roughness conversion. Preserve
  originals for a later fully linear workflow. Pure metals without reflection
  probes will be dark; do not compensate by inventing bright diffuse or glow.
- Emission: separate black-background RGB map, multiplied by a documented
  modest scalar. A late additive stage adds it without ambient/dynamic lighting.
  It is **not** a light source and does not create a bloom pass. Real dynamic
  lights come from game presentation events; emissive areas need authored
  lightmaps or intentional scene lights. Do not bake bright emission into
  diffuse as well, which doubles its contribution.

Example for a model (declare `stage` **before** `map`, so normal/specular loading
uses the right image type). Explicit and automatic specular maps now share the
linear-data image type: no gamma/intensity correction, linear CPU picmip and mip
averaging. Color and normal processing are unchanged. Do not reuse one filename
for both color and data: image caching is by name. Paths below are schematic:

```text
models/remaster/example
{
    {
        stage diffuseMap
        map models/remaster/example_d.tga
        rgbGen lightingDiffuse
    }
    {
        stage normalMap
        map models/remaster/example_n.tga
        normalScale 1 1
    }
    {
        stage specularMap
        map models/remaster/example_s.tga
        specularScale 1 1 1 1
    }
    {
        map models/remaster/example_e.tga
        blendFunc add
        rgbGen const ( 0.25 0.25 0.25 )
        depthFunc equal
    }
}
```

For BSP use the original lightmap stage and UV channel, not model
`lightingDiffuse`; preserve lightmap blending/order when adding normal/specular
stages. Explicit stages beat automatic `_n`/`_s` discovery. Register `.shader`
files normally; a standalone `.mtr` is not independently enumerated.

Transparency: particles use straight-alpha `blendFunc blend`, `rgbGen vertex`,
`alphaGen vertex`, and no `depthWrite`. Additive fire uses `blendFunc add` with
black RGB outside its shape. Cutouts use `alphaFunc GE128` and opaque depth
writes; they are not semitransparent glass. Coplanar decals use `polygonOffset`
and appropriate blend state. Never set `depthFunc equal` on a free-floating
particle; that is only for an overlay of already-rendered identical geometry.
Surface ordering remains Quake shader-sort/batch ordering, not per-triangle
order-independent transparency. Avoid interpenetrating transparent meshes.

## Independent checks and integrated acceptance

```sh
python3 misc/tests/remaster-rendering/material-math.py
for test in material-parser specular-mips iqm-shadow; do
  cc -O1 -ffunction-sections -fdata-sections $(sdl2-config --cflags) \
    misc/tests/remaster-rendering/$test.c code/qcommon/q_shared.c \
    code/qcommon/q_math.c code/renderergl2/tr_extramath.c \
    -Wl,--gc-sections -lm -o /tmp/$test && /tmp/$test || exit 1
done
cmake --build build-orb --parallel 4
# With Emscripten 3.1.58 active:
cmake --build build-web --parallel 4
```

The math test extracts the actual scalar GLSL function and PBR parameter
conversion, compiles them to float C, and checks an independent analytic lobe
center plus asymmetric metallic values on both sides of the old 0.5 threshold.
It does not replace GLSL compilation/execution. Minimum specular roughness 0.045
regularizes the zero-width lobe, retaining continuous highlights without 0/0;
stable denominator arithmetic avoids cancellation at normal incidence.

Parser tests execute the real parser and capture image flags/types for map,
clampmap and animMap, including unchanged diffuse/normal controls. Mip tests
exercise real picmip scaling with asymmetric RGBA values, explicitly rejecting
the sRGB average, and check 1D mip tails. IQM tests exercise the real shadow
radius: missing optional bounds, static models, invalid/wrapped frames and
off-center bounds enclosing both interpolated poses. IQM without bounds skips
projected shadow generation; production exports must provide per-frame bounds.

Use the existing private gameplay fixture preparation and CDP driver in
`../gameplay/README.md`; no demo data or observer build may be published.
The renderer wrapper accepts additional local PK3s and hashes every input:

```sh
node misc/tests/remaster-rendering/prepare.mjs build-web/Release /path/to/demo \
  /tmp/new-render-fixture assets/remaster/runtime/energy-pillar-v2.pk3
# Additional environment/weapon/private BSP packs can follow the pillar pack.
# Serve privately with the supervised service workflow in ../gameplay/README.md.
node misc/tests/remaster-rendering/run.mjs "$CDP" /tmp/new-render-evidence
```

The current browser driver checks actual production specular GLSL finite output
on five roughness boundaries in a separate WebGL2 context, then captures the
real WASM pillar, HDR/LDR/exposure/near-far, firing, and forced sun/projected
shadow settings. It records 120 RAF deltas plus imagelist in its JSONL journal.
These captures require inspection; the driver does not assert that a visible
decal, shadow or production normal/specular/emission material passed review.

Integrated acceptance requires both HDR=0 and HDR=1, matched exposure/camera,
bright/dark views, close/far and motion, normals/specular on/off comparisons,
additive emission with no opaque rectangle, alpha particles/decals crossing
opaque geometry, weapon dynamic light, model shadows, and actual IQM poses.
Inspect screenshots, collect context-loss and GL errors, record browser/GPU,
WASM heap, image-list allocation estimates and frame-time percentiles. Software
SwiftShader frame timings are diagnostic CPU/software-rasterizer values, never
physical GPU performance. Full q3dm1 environment/character/weapon/HUD match
acceptance must be repeated with the content groups' final packs.
