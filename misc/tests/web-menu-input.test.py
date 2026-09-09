"""Run production IN_Frame against an input-state matrix, native and Web."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


class MenuInputTest(unittest.TestCase):
    def test_capture_priority_and_close_restoration(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "code/sdl/sdl_input.c").read_text()
        function = re.search(r"^void IN_Frame\( void \)\n\{.*?^\}", source, re.M | re.S)
        self.assertIsNotNone(function)
        prelude = r'''
#include <assert.h>
#include <string.h>
typedef int qboolean;
#define qfalse 0
#define CA_DISCONNECTED 0
#define CA_ACTIVE 1
#define KEYCATCH_CONSOLE 1
#define SDL_WINDOW_INPUT_FOCUS 1
static struct { int state; } clc;
static struct { struct { int isFullscreen; } glconfig; } cls;
static int fullscreen, catcher, focus, menu, activated, deactivated, cursorArg;
static int events, joy, in_eventTime, vidRestartTime, restarts;
static void *SDL_window;
static void IN_JoyMove(void) { joy++; }
static int Cvar_VariableIntegerValue(const char *name) { (void)name; return fullscreen; }
static int Key_GetCatcher(void) { return catcher; }
static int SDL_GetWindowFlags(void *window) { (void)window; return focus; }
#ifdef __EMSCRIPTEN__
static int OG_WebMenuOpen(void) { return menu; }
#endif
static void IN_DeactivateMouse(int fs) { deactivated++; cursorArg = fs; }
static void IN_ActivateMouse(int fs) { activated++; cursorArg = fs; }
static void IN_ProcessEvents(void) { events++; }
static int Sys_Milliseconds(void) { return 2000; }
static void Cbuf_AddText(const char *text) { assert(!strcmp(text, "vid_restart\n")); restarts++; }
'''
        checks = r'''
int main(void) {
    for (fullscreen = 0; fullscreen <= 1; fullscreen++)
    for (catcher = 0; catcher <= 1; catcher++)
    for (focus = 0; focus <= 1; focus++)
    for (clc.state = 0; clc.state <= 2; clc.state++)
    for (menu = 0; menu <= 1; menu++) {
        activated = deactivated = events = joy = 0;
        int expected = focus && (fullscreen || (!catcher && clc.state != 2));
#ifdef __EMSCRIPTEN__
        if (menu) expected = 0;
#endif
        IN_Frame(); IN_Frame();
        assert(activated == expected * 2 && deactivated == (1 - expected) * 2);
        assert(events == 2 && joy == 2 && in_eventTime == 2000);
#ifdef __EMSCRIPTEN__
        assert(cursorArg == (menu ? 0 : fullscreen));
#else
        assert(cursorArg == fullscreen);
#endif
    }
    menu = 0; fullscreen = 0; catcher = 0; focus = 1; clc.state = CA_ACTIVE;
    activated = 0; vidRestartTime = 1999;
    IN_Frame();
    assert(activated == 1 && restarts == 1 && vidRestartTime == 0);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            program = Path(tmp) / "frame.c"
            program.write_text(prelude + function.group() + checks)
            for web in (False, True):
                with self.subTest(web=web):
                    binary = Path(tmp) / ("web" if web else "native")
                    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                                    *(["-D__EMSCRIPTEN__=1"] if web else []),
                                    str(program), "-o", str(binary)], check=True)
                    subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    unittest.main()
