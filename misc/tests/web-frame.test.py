"""Exercise production screen submission and readiness with a stub renderer/VM."""
import pathlib
import re
import subprocess
import tempfile
import unittest


class FrameTest(unittest.TestCase):
    def test_ready_only_after_functional_submission(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        source = (root / "code/client/cl_scrn.c").read_text()
        functions = []
        for name in ["SCR_DrawScreenField", "SCR_UpdateScreen"]:
            match = re.search(r"^void " + name + r"\([^\n]*\) \{\n.*?^\}", source, re.M | re.S)
            self.assertIsNotNone(match)
            functions.append(match.group())
        prelude = r'''
#include <assert.h>
#include <stddef.h>
#define __EMSCRIPTEN__ 1
#define qtrue 1
#define qfalse 0
#define ERR_FATAL 0
#define KEYCATCH_UI 1
typedef int qboolean;
typedef int stereoFrame_t;
enum { STEREO_CENTER, STEREO_LEFT, STEREO_RIGHT };
enum { CA_DISCONNECTED, CA_CINEMATIC, CA_CONNECTING, CA_CHALLENGING,
       CA_CONNECTED, CA_LOADING, CA_PRIMED, CA_ACTIVE };
enum { UI_IS_FULLSCREEN, UI_SET_ACTIVE_MENU, UI_REFRESH, UI_DRAW_CONNECT_SCREEN, UIMENU_MAIN };
static struct { int state; } clc;
static struct { struct { int vidWidth, vidHeight, stereoEnabled; } glconfig;
                int whiteShader, realtime; } cls = {{640, 480, 0}, 0, 0};
static struct { int integer; } zero, speed;
#define com_dedicated (&zero)
#define com_speeds (&speed)
#define cl_debuggraph (&zero)
#define cl_timegraph (&zero)
#define cl_debugMove (&zero)
static int time_frontend, time_backend;
static int uivm = 1, scr_initialized = 1, scr_webPlayable;
static int catcher, fullscreen, submitted, notifications, playable;
static float g_color_table[1][4];
static void begin(int eye) { (void)eye; submitted = 0; }
static void end(int *front, int *back) { (void)front; (void)back; submitted = 1; }
static void color(const void *value) { (void)value; }
static void draw(int x,int y,int w,int h,int s,int t,int u,int v,int shader) {
    (void)x;(void)y;(void)w;(void)h;(void)s;(void)t;(void)u;(void)v;(void)shader;
}
static struct { void (*BeginFrame)(int); void (*EndFrame)(int *,int *);
                void (*SetColor)(const void *);
                void (*DrawStretchPic)(int,int,int,int,int,int,int,int,int); } re = {begin,end,color,draw};
static int VM_Call(int vm, int operation, ...) { (void)vm; return operation == UI_IS_FULLSCREEN && fullscreen; }
static int Key_GetCatcher(void) { return catcher; }
static int Cvar_VariableIntegerValue(const char *name) { (void)name; return 0; }
static void Com_Error(int code,const char *text) { (void)code; (void)text; assert(0); }
static void CL_CGameRendering(int eye) { (void)eye; }
static void SCR_DrawCinematic(void) {}
static void S_StopAllSounds(void) {}
static void SCR_DrawDemoRecording(void) {}
static void Con_DrawConsole(void) {}
static void SCR_DrawDebugGraph(void) {}
static void OG_WebFrame(int p,int dirty) { assert(submitted && !dirty); notifications++; playable = p; }
'''
        checks = r'''
int main(void) {
    for (int state = CA_DISCONNECTED; state <= CA_ACTIVE; state++) {
        for (catcher = 0; catcher <= KEYCATCH_UI; catcher++) {
            for (fullscreen = 0; fullscreen <= 1; fullscreen++) {
                for (speed.integer = 0; speed.integer <= 1; speed.integer++) {
                    clc.state = state;
                    int before = notifications;
                    SCR_UpdateScreen();
                    assert(notifications == before + 1);
                    int expected = (state == CA_ACTIVE && !fullscreen)
                        || (catcher && (state == CA_DISCONNECTED || state == CA_ACTIVE));
                    assert(playable == expected);
                }
            }
        }
    }
    int before = notifications;
    scr_initialized = 0;
    SCR_UpdateScreen();
    assert(notifications == before);
    scr_initialized = 1;
    uivm = 0;
    SCR_UpdateScreen();
    assert(notifications == before);
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix="ioq3-frame-") as directory:
            directory = pathlib.Path(directory)
            program = directory / "check.c"
            program.write_text(prelude + "\n".join(functions) + checks)
            executable = directory / "check"
            subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                            str(program), "-o", str(executable)], check=True)
            subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    unittest.main()
