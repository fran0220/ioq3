/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real SDL2/WebGL2 regression fixture; no game data or game-ready assertion. */
#include <SDL.h>
#include <GLES3/gl3.h>
#include <emscripten.h>

static SDL_Window *window;

static void draw(void)
{
    int width, height;
    unsigned char corner[4];
    SDL_Event event;
    while (SDL_PollEvent(&event)) {}
    SDL_GL_GetDrawableSize(window, &width, &height);
    glViewport(0, 0, width, height);
    glDisable(GL_SCISSOR_TEST);
    glClearColor(0.08f, 0.12f, 0.18f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
    glEnable(GL_SCISSOR_TEST);
    glScissor(width - 80, height - 80, 80, 80);
    glClearColor(0, 1, 0, 1);
    glClear(GL_COLOR_BUFFER_BIT);
    glScissor(0, 0, 40, 40);
    glClearColor(1, 0.25f, 0, 1);
    glClear(GL_COLOR_BUFFER_BIT);
    glDisable(GL_SCISSOR_TEST);
    glReadPixels(width - 1, height - 1, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, corner);
    EM_ASM({
        var gl = Module['canvas'].getContext('webgl2');
        window.canvasProbe = ({ sdl: [$0, $1],
            buffer: [gl.drawingBufferWidth, gl.drawingBufferHeight],
            corner: [$2, $3, $4, $5] });
    }, width, height, corner[0], corner[1], corner[2], corner[3]);
    SDL_GL_SwapWindow(window);
}

EMSCRIPTEN_KEEPALIVE void resize_probe(void) { SDL_SetWindowSize(window, 1024, 768); }

int main(void)
{
    if (SDL_Init(SDL_INIT_VIDEO)) return 1;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);
    window = SDL_CreateWindow("SDL canvas probe", 0, 0, 800, 600, SDL_WINDOW_OPENGL);
    if (!window || !SDL_GL_CreateContext(window)) return 2;
    emscripten_set_main_loop(draw, 0, 1);
    return 0;
}
