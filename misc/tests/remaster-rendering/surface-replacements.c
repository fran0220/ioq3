/* Production map-side manifest parsing and replacement validation. */
#include <assert.h>
#include "../../../code/renderergl2/tr_bsp.c"

refimport_t ri;
static char manifest[4096];
static model_t model;
static iqmData_t iqm;
static srfIQModel_t modelSurface;
static shader_t material = { .sort = SS_OPAQUE, .numUnfoggedPasses = 1 };
static float modelBounds[6] = { -1, -2, -3, 1, 2, 3 };
static world_t world;
static msurface_t surfaces[3];
static shader_t original;

void QDECL Com_Error(int level, const char *format, ...) { abort(); }
void QDECL Com_Printf(const char *format, ...) { abort(); }
static void QDECL quiet(int level, const char *format, ...) {}
static void *allocate(int size, ha_pref preference, char *label, char *file, int line) { return calloc(1, size); }
static int failScratch;
static void *scratch(int size) { return failScratch ? NULL : malloc(size); }
static void clearWorld(void)
{
    for (int i = 0; i < world.numSurfaceReplacements; i++)
        free(world.surfaceReplacements[i].surfaceIndices);
    free(world.surfaceReplacements);
    memset(&world, 0, sizeof(world));
}
static long readManifest(const char *name, void **out)
{
    assert(!strcmp(name, "maps/test.remaster.json"));
    *out = malloc(strlen(manifest) + 1);
    strcpy(*out, manifest);
    return strlen(manifest);
}
qhandle_t RE_RegisterModel(const char *name) { return strcmp(name, "missing.iqm") ? 1 : 0; }
model_t *R_GetModelByHandle(qhandle_t handle) { return &model; }
shader_t *R_GetShaderByHandle(qhandle_t handle) { return &material; }
void R_ModelBounds(qhandle_t handle, vec3_t mins, vec3_t maxs)
{
    VectorCopy(modelBounds, mins);
    VectorCopy(modelBounds + 3, maxs);
}

static void check(const char *map, const char *surface, const char *shader,
                  const char *modelName, const char *scale, const char *angles, int accepted)
{
    clearWorld();
    memset(surfaces, 0, sizeof(surfaces));
    strcpy(world.baseName, "test");
    world.numWorldSurfaces = world.numsurfaces = 2;
    world.surfaces = surfaces;
    strcpy(original.name, "same-shader");
    surfaces[0].shader = surfaces[1].shader = &original;
    surfaces[0].cullinfo.type = surfaces[1].cullinfo.type = CULLINFO_BOX;
    VectorSet(surfaces[1].cullinfo.bounds[0], 8, 16, 22);
    VectorSet(surfaces[1].cullinfo.bounds[1], 12, 24, 38);
    snprintf(manifest, sizeof(manifest),
        "{\"schemaVersion\":1,\"map\":\"%s\",\"replacements\":[{"
        "\"surface\":%s,\"shader\":\"%s\",\"bounds\":[[8,16,22],[12,24,38]],"
        "\"model\":\"%s\",\"origin\":[10,20,30],\"angles\":%s,\"scale\":%s}]}",
        map, surface, shader, modelName, angles, scale);
    R_LoadSurfaceReplacements(&world);
    assert(world.numSurfaceReplacements == accepted);
    assert(surfaces[0].replacementIndex == 0); // never all instances of same shader
    assert(surfaces[1].replacementIndex == accepted);
    if (accepted) {
        assert(world.surfaceReplacements[0].numSurfaces == 1);
        assert(world.surfaceReplacements[0].surfaceIndices[0] == 1);
        assert(world.surfaceReplacements[0].entityNum == -1); // no allocation yet
        assert(world.surfaceReplacements[0].entity.hModel == 1);
    }
}

static void groupCheck(const char *members, const char *modelName, const char *origin, int accepted)
{
    clearWorld();
    memset(surfaces, 0, sizeof(surfaces));
    strcpy(world.baseName, "test");
    world.numWorldSurfaces = world.numsurfaces = 3; world.surfaces = surfaces;
    for (int i = 0; i < 3; i++) {
        surfaces[i].shader = &original;
        surfaces[i].cullinfo.type = CULLINFO_BOX;
    }
    VectorSet(surfaces[0].cullinfo.bounds[0], -2, -2, -3);
    VectorSet(surfaces[0].cullinfo.bounds[1], 0, 2, 3);
    VectorSet(surfaces[1].cullinfo.bounds[0], 0, -2, -3);
    VectorSet(surfaces[1].cullinfo.bounds[1], 1, 2, 3);
    char entry[1536];
    snprintf(entry, sizeof(entry), "{\"surfaces\":%s,\"model\":\"%s\",\"origin\":%s,\"angles\":[0,0,0],\"scale\":1}", members, modelName, origin);
    // A second overlapping group must never steal an already accepted owner.
    snprintf(manifest, sizeof(manifest), "{\"schemaVersion\":1,\"map\":\"test\",\"replacements\":[%s,%s]}", entry, entry);
    R_LoadSurfaceReplacements(&world);
    assert(world.numSurfaceReplacements == accepted);
    assert(surfaces[0].replacementIndex == accepted && surfaces[1].replacementIndex == accepted);
    assert(surfaces[2].replacementIndex == 0); // unrelated same-shader surface
    if (accepted) assert(world.surfaceReplacements[0].numSurfaces == 2);
}

int main(void)
{
    ri.Printf = quiet; ri.Hunk_AllocDebug = allocate;
    ri.Malloc = scratch; ri.Free = free;
    ri.FS_ReadFile = readManifest; ri.FS_FreeFile = free;
    model.type = MOD_IQM; model.modelData = &iqm;
    iqm.num_surfaces = 1; iqm.surfaces = &modelSurface; iqm.bounds = modelBounds;
    modelSurface.shader = &material;
    check("test", "1", "same-shader", "valid.iqm", "1", "[0,0,0]", 1);
    check("test", "1", "same-shader", "valid.iqm", "1", "[0,90,0]", 1);
    check("wrong", "1", "same-shader", "valid.iqm", "1", "[0,0,0]", 0);
    check("test", "0", "same-shader", "valid.iqm", "1", "[0,0,0]", 0); // wrong bounds
    check("test", "2", "same-shader", "valid.iqm", "1", "[0,0,0]", 0);
    check("test", "1.5", "same-shader", "valid.iqm", "1", "[0,0,0]", 0);
    check("test", "1", "wrong-shader", "valid.iqm", "1", "[0,0,0]", 0);
    check("test", "1", "same-shader", "missing.iqm", "1", "[0,0,0]", 0);
    check("test", "1", "same-shader", "valid.iqm", "3", "[0,0,0]", 0); // outside original leaves
    check("test", "1", "same-shader", "valid.iqm", "0", "[0,0,0]", 0);
    check("test", "1", "same-shader", "valid.iqm", "1e99", "[0,0,0]", 0);
    check("test", "1", "same-shader", "valid.iqm", "true", "[0,0,0]", 0);
    check("test", "1", "same-shader", "valid.iqm", "1", "[0,0]", 0);
    material.defaultShader = qtrue;
    check("test", "1", "same-shader", "valid.iqm", "1", "[0,0,0]", 0);
    material.defaultShader = qfalse; material.sort = SS_BLEND1;
    check("test", "1", "same-shader", "valid.iqm", "1", "[0,0,0]", 0);
    material.sort = SS_OPAQUE; iqm.bounds = NULL;
    check("test", "1", "same-shader", "valid.iqm", "1", "[0,0,0]", 0);
    iqm.bounds = modelBounds;
    const char *left = "{\"surface\":0,\"shader\":\"same-shader\",\"bounds\":[[-2,-2,-3],[0,2,3]]}";
    const char *right = "{\"surface\":1,\"shader\":\"same-shader\",\"bounds\":[[0,-2,-3],[1,2,3]]}";
    char members[1024];
    snprintf(members, sizeof(members), "[%s,%s]", left, right);
    groupCheck(members, "valid.iqm", "[0,0,0]", 1); // spans both; neither owner alone contains model
    groupCheck(members, "missing.iqm", "[0,0,0]", 0);
    groupCheck(members, "valid.iqm", "[0.02,0,0]", 0); // positive envelope boundary
    groupCheck(members, "valid.iqm", "[-1.02,0,0]", 0); // negative envelope boundary
    failScratch = 1; groupCheck(members, "valid.iqm", "[0,0,0]", 0); failScratch = 0;
    snprintf(members, sizeof(members), "[%s,%s]", right, left);
    groupCheck(members, "valid.iqm", "[0,0,0]", 1); // order independent
    snprintf(members, sizeof(members), "[%s,%s]", left, left);
    groupCheck(members, "valid.iqm", "[0,0,0]", 0); // duplicate
    snprintf(members, sizeof(members), "[%s,{\"surface\":1,\"shader\":\"wrong\",\"bounds\":[[0,-2,-3],[1,2,3]]}]", left);
    groupCheck(members, "valid.iqm", "[0,0,0]", 0); // valid first member must not hide
    groupCheck("[]", "valid.iqm", "[0,0,0]", 0);
    groupCheck("{}", "valid.iqm", "[0,0,0]", 0);
    clearWorld();
    puts("PASS: exact map/surface/shader/bounds, transformed static model and material validation/fallback");
    puts("PASS: atomic group validation, union envelope boundaries, overlap, order and resource fallback");
    return 0;
}
