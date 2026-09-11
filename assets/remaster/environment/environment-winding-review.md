# Static exterior winding failure: reproducible browser evidence

All prior static environment art/orientation approvals are provisional until
re-export and repeated inspection. This does not invalidate original BSP/AAS
byte-invariant checks or prove a gameplay change. No paid shape is resubmitted.

Observed sequence, same WASM/QVM/light package/camera/exposure:

1. LDR east/west near lamps failed cyan vertical readability despite earlier
   small contact-sheet approval. Only the old diffuse cyan diagonal was visible.
2. Scenev2(no glow) andv3(glow) showed no distinguishable new vertical capsule.
   The surrounding bright wall existed in both. Captures/journal:
   `.amp/in/artifacts/environment-glow-ab/`.
3. A lower-reflectance bright-neutral texture candidate also failed, and is
   not adopted as a fix. Do not increase FX intensity or exposure.
4. BVH rays from+Y into exported wall-lantern center found opaque surfaces
   atY3.94 and glow atY4.03125, so the quad was outside that shell side.
5. Source reading found Blender loop order retained by `write_md3`, MD3 loader
   and scene submission retain indices, and default GL2 front-sided material
   uses `glCullFace(GL_FRONT)` with no changed front-face convention.
6. `winding_probe.py` reversed only lantern triangle indices. The same near
   view then showed a black backplate with generated labels/holes and a clear
   vertical cyan capsule, rather than the old ivory face. The latter had been
   seen from inside the shell after its near side was culled. Actual exterior
   wall-lantern front is-Y, not the earlier+Y inference. Captures:
   `.amp/in/artifacts/environment-body-winding-ab/east-{without,with}.jpg`.

`models/remaster/environment_fx/lamp_glow` has `cull disable`, so its own winding
does not explain the failure. A separate glow-only reverse control is retained
at `.amp/in/artifacts/environment-glow-winding-ab/`; do not conflate opaque and
two-sided behavior. Renderer owner independently confirmed the loader/cull
source path, but has not yet independently accepted corrected full assets.

The shared exporter owner is responsible for CW output and CCW reconstruction
in Blender preview. Environment will then re-export and recheck every prop,
front/yaw, companion plane, light response and movement visibility. Model hash,
package hash and diagnostic results must change transparently; original paid
sources and pre-fix packages remain available.

Private complete pre-CW recovery archive (four paid assets + manifests):
`assets/remaster/work/environment-pre-cw-recovery.tar.gz`, SHA-256
`784240c237d350529bd46bff421199cc8d62dad27cb68126bfd6a2a4beb6eaf5`.
The main integration thread downloaded and independently matched that hash.
This is verified cross-orb recovery, not durable external backup.
