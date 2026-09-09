# GLES3 / WebGL2 capability regression

This is a renderer-only test, requiring no Quake game data. It compiles the
production extension initializer (including the GLES version gate), DSA
fallbacks and texture converter, rather than reimplementing capability logic.
Assertions must remain enabled. Run from the repository root:

```sh
cc -g -O1 -ffunction-sections -fdata-sections $(sdl2-config --cflags) \
  code/renderergl2/tests/gles3-capabilities.c code/renderergl2/tr_dsa.c \
  code/renderergl2/tr_image.c code/qcommon/q_shared.c \
  -Wl,--gc-sections $(sdl2-config --libs) -lm -o /tmp/gl2-gles-test
SDL_VIDEODRIVER=offscreen /tmp/gl2-gles-test
SDL_VIDEODRIVER=offscreen MESA_GLES_VERSION_OVERRIDE=2.0 /tmp/gl2-gles-test --gles2
SDL_VIDEODRIVER=offscreen /tmp/gl2-gles-test --desktop
```

On a machine without SDL's offscreen GLES driver, use a desktop session or
Xvfb/Mesa. Do not silently treat failure to create a context as a passing test.

With Emscripten **3.1.58** activated:

```sh
mkdir -p /tmp/gl2-web-test
emcc -O1 -g -ffunction-sections -fdata-sections -sUSE_SDL=2 \
  -sMIN_WEBGL_VERSION=2 -sMAX_WEBGL_VERSION=2 -sASSERTIONS=1 -sEXIT_RUNTIME=1 \
  code/renderergl2/tests/gles3-capabilities.c code/renderergl2/tr_dsa.c \
  code/renderergl2/tr_image.c code/qcommon/q_shared.c \
  -o /tmp/gl2-web-test/index.html
```

Serve that directory over HTTP and open `index.html` in a real WebGL2 browser.
In an Amp orb use a supervised `amp orb service start` HTTP service. The output
must end with `PASS: GLES3 capabilities, bindings, float conversion,
DSA/blit/readback and failure fallbacks`, without assertion/runtime errors.
An exit status from emcc alone is not a browser test.

## Coverage and observed results (2026-09-09)

- `cmake --build build-orb --parallel 2`: full native Debug build passed.
- Native test: Mesa OpenGL ES 3.2, SDL offscreen, passed.
- Regression initialization in an actual Mesa GLES 2.0 context (version override)
  and desktop GL 4.5 compatibility context passed. These are initialization
  checks, not full GLES2/desktop gameplay or physical GPU checks.
- Browser test: the same C program compiled using Emscripten 3.1.58, Chromium
  WebGL2 with ANGLE SwiftShader, passed. This is software rendering, not a
  performance or vendor GPU compatibility claim.
- Tests check nonzero, distinct read/draw framebuffer and texture/VAO bindings
  survive initialization, actual DSA renderbuffer allocation, FBO completion,
  color blit and asymmetric pixel readback, RGBA8-to-float conversion including
  its output boundary, and floating texture allocation/readback when supported.
- Failure injection covers missing FBO/VAO functions, incomplete FBO, real GL
  allocation errors, separate RGBA16F and R32F allocation failures (RGBA8 must
  remain usable), hidden float-renderability extension and disabled cvars.
  The ES2 guard is also tested after ES3 initialization to catch stale flags.

## Capability contract and remaining validation

GLES3 now loads the core FBO and VAO entry points before the GLES extension
branch exits. It checks real RGBA8 + DEPTH_COMPONENT24 framebuffer completion,
GL errors and limits before enabling FBO/blit. Float texture support alone is
insufficient: EXT_color_buffer_float plus successful RGBA16F and R32F color
attachment probes are required. Failing those probes keeps RGBA8 and disables
the SSAO/shadow-blur effects that require R32F. The probe restores raw bindings
before the renderer establishes its DSA state cache. Native desktop capability
selection is unchanged; ES2 does not enter the new core ES3 path.

GLES image allocation now handles DEPTH_COMPONENT24, RGBA16F and R32F transfer
types; initialized RGBA16F levels textures convert RGBA8 to float with the
correct temporary buffer size. R32F uses nearest sampling without assuming
OES_texture_float_linear. This is not a general float-source asset importer.

GLES3 framebuffer MSAA deliberately remains disabled: GL_MAX_SAMPLES does not
prove the selected floating color/depth format supports that sample count.
Desktop MSAA is unchanged. A later stage needs per-format supported sample
counts, an actual multisampled color/depth allocation + resolve probe and
fallback to a lower sample count or single-sample targets.

## Full-engine context-loss regression (2026-09-09)

The capability probe alone passed while the full renderer crashed. With
Emscripten 3.1.58 Release, Chromium 152 / ANGLE SwiftShader on Linux, the
production ES3 `precision mediump float` header caused the GPU process to
exit with code 11 on map startup. GDB caught SIGSEGV in `libvk_swiftshader.so`
(stripped: the exact internal function is not established). Context loss
followed the GPU crash; subsequent unsupported FBO / shader-source `None`
messages were not evidence of the initial cause. Disabling HDR or replacing
the presentation blit did not reliably cure it.

Changing only the modern GLES shader float precision to highp eliminated
the reproduced crash; reverting to mediump reproduced it again with the same
HDR=1 / q3dm1 launch. ES3 guarantees fragment highp, and world-space lighting
and HDR also benefit from its range. ES2 retains its separate mediump header;
desktop headers are unchanged. This is a driver-path workaround supported by
an A/B experiment, not a claim that every mediump shader crashes every GPU.

The registration-time `RB_ShowImages` preview produced four sampler mismatch
errors by sampling comparison-enabled sunlight depth textures with sampler2D.
Disabling comparison only around those preview draws, then restoring it,
removed all four errors without changing the sunlight rendering pass.

The HDR=0 map regression exposed a separate per-frame error:
`CopyTexSubImage2D: Invalid format`. The direct-to-default-framebuffer path
tried to copy depth into a texture for screen effects, which WebGL does not
permit with that operation. ES3 now also uses the existing RGBA8 color/depth
texture render FBO in LDR, avoiding that copy. This does not enable HDR or
require float renderability; desktop direct rendering is unchanged.

Production header regression (both vertex and fragment stages):

```sh
cc -O1 -ffunction-sections -fdata-sections $(sdl2-config --cflags) \
  code/renderergl2/tests/shader-header.c code/qcommon/q_shared.c \
  -Wl,--gc-sections -lm -o /tmp/gl2-header-test
/tmp/gl2-header-test
```

Expected: `PASS: ES3 vertex/fragment highp, ES2 mediump, desktop unchanged`.
This checks the real header builder, not shader execution or driver safety.

Full-engine technical fixture, **not release content**: official Linux Quake 3
demo `linuxq3ademo-1.11-6.x86.gz.sh` from id Software's GWDG mirror, locally
extracted with its documentation/EULA retained. Its `demoq3/pak0.pk3` plus
current ioq3 QVMs in a separate PK3 were loaded through the Web manifest.
No demo assets are committed or authorized for redistribution by this test.
Temporary test-output host fixes exposed console logs and corrected the canvas
selector; no renderer patch changes the host, SDL or gameplay.

Observed with `--use-angle=swiftshader --enable-unsafe-swiftshader`:

- Full Web Release and native Debug builds passed, as did the native
  GLES3/GLES2/desktop capability tests and the header regression above.
- HDR=1 q3dm1 loaded 1942 faces, 113 meshes, 42 trisurfs and entered the game.
  Inspected screenshots show textured world geometry, weapon and HUD. The
  context stayed alive over several minutes; the final browser log contained
  no GL_INVALID errors or GPU-process exits.
- HDR=0 q3dm1 also entered the game with the LDR FBO fix, with an inspected
  textured-world/weapon/HUD screenshot and no GL_INVALID or GPU-exit messages
  in a fresh browser log. This is not a no-FBO or forced probe-failure test.
- Escape opened the complete in-game menu; a separate normal startup followed
  by Escape dismissed the CD-key prompt and rendered the full main menu.
  Screenshots of both menus were inspected, not inferred from readiness.
- The old demo lacks some assets referenced by current QVMs, producing missing
  sound/music warnings. Audio completeness was not established.

**Not yet verified:** every production GLSL/material permutation, full-resolution
FBO allocation under memory pressure, HDR exposure/tonemapping/bloom visual
correctness against a reference, real GLES2 hardware, Firefox/Edge/Safari and
physical GPUs, forced context-loss recovery / vid_restart, actual platform
iframe, sustained input/gameplay and performance. Demo startup is not the
all-maps/modes/bots/multiplayer release matrix. Capability-test PASS and this
software-renderer scene test do not establish that the game is ready to ship.
