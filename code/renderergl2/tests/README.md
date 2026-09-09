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

**Not yet verified:** full engine Web build and game/map startup, production
GLSL material permutations, full-resolution FBO allocation under memory
pressure, HDR exposure/tonemapping/bloom screenshots, real GLES2 hardware,
Firefox/Edge/Safari and physical GPUs, context loss/restart, actual platform
iframe, performance. The focused test does not execute `R_CreateBuiltinImages`
or the entire `FBO_Init` graph. Subsequent HDR/material work must first run
those paths with real game data and inspect representative rendered scenes;
capability-test PASS is not evidence that the game is ready to ship.
