"""Compile the production close/open functions against controlled I/O failures."""
import pathlib
import re
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]


class PersistenceTest(unittest.TestCase):
    def test_only_successful_home_writes_notify(self):
        source = (ROOT / "code/qcommon/files.c").read_text()
        names = ["FS_FCloseFile", "FS_FOpenFileWrite_HomeConfig",
                 "FS_FOpenFileWrite_HomeState", "FS_FOpenFileWrite_HomeData"]
        functions = []
        for name in names:
            match = re.search(r"^(?:void|fileHandle_t) " + name + r"\([^\n]*\) \{\n.*?^\}",
                              source, re.M | re.S)
            self.assertIsNotNone(match, name)
            functions.append(match.group())
        prelude = r'''
#include <assert.h>
#include <string.h>
#define __EMSCRIPTEN__ 1
#define qtrue 1
#define qfalse 0
#define ERR_FATAL 0
typedef int qboolean;
typedef int fileHandle_t;
typedef struct { int error; int closeError; } FakeFile;
typedef struct {
    struct { union { FakeFile *o; int z; } file; int unique; } handleFiles;
    int zipFile;
    int webSyncOnClose;
} Handle;
static Handle fsh[3];
static FakeFile file;
static int fs_searchpaths = 1, notifications, openFails, closed;
static const char *fs_gamedir = "baseq3";
typedef struct { const char *string; } Path;
static Path path = {"/home"};
static Path *fs_homeconfigpath = &path, *fs_homestatepath = &path, *fs_homedatapath = &path;
static void Com_Error(int code, const char *message) { (void)code; (void)message; assert(0); }
static void OG_WebFrame(int playable, int changed) { assert(!playable && changed); notifications++; }
static int fakeError(FakeFile *f) { return f->error; }
static int fakeClose(FakeFile *f) { closed++; return f->closeError; }
static void unzCloseCurrentFile(int f) { (void)f; }
static void unzClose(int f) { (void)f; }
#define ferror fakeError
#define fclose fakeClose
#define Com_Memset memset
static const char *FS_BuildOSPath(const char *home, const char *game, const char *name) {
    (void)home; (void)game; return name;
}
static fileHandle_t FS_OSPath_FOpenFileWrite(const char *path, const char *name) {
    (void)path; (void)name;
    if (openFails) return 0;
    fsh[1].handleFiles.file.o = &file;
    return 1;
}
'''
        checks = r'''
int main(void) {
    fileHandle_t f = FS_FOpenFileWrite_HomeConfig("q3config.cfg");
    assert(f == 1 && notifications == 0);
    FS_FCloseFile(f);
    assert(notifications == 1 && closed == 1 && fsh[1].webSyncOnClose == 0);

    file.error = 1;
    FS_FCloseFile(FS_FOpenFileWrite_HomeConfig("q3config.cfg"));
    assert(notifications == 1 && closed == 2);
    file.error = 0;
    file.closeError = -1;
    FS_FCloseFile(FS_FOpenFileWrite_HomeState("progress.dat"));
    assert(notifications == 1 && closed == 3);
    file.closeError = 0;

    FS_FCloseFile(FS_FOpenFileWrite_HomeState("progress.dat"));
    assert(notifications == 2);
    FS_FCloseFile(FS_FOpenFileWrite_HomeData("large-demo.dm_68"));
    assert(notifications == 2 && fsh[1].webSyncOnClose == 0);

    openFails = 1;
    assert(FS_FOpenFileWrite_HomeConfig("q3config.cfg") == 0);
    assert(fsh[0].webSyncOnClose == 0 && notifications == 2);
    fsh[2].zipFile = 1;
    fsh[2].webSyncOnClose = 1;
    FS_FCloseFile(2);
    assert(notifications == 2 && fsh[2].webSyncOnClose == 0);
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix="ioq3-persistence-") as directory:
            directory = pathlib.Path(directory)
            program = directory / "check.c"
            program.write_text(prelude + "\n".join(functions) + checks)
            executable = directory / "check"
            subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                            str(program), "-o", str(executable)], check=True)
            subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    unittest.main()
