/* Real scene allocation, backend lifetime and capacity fallback. */
#include <assert.h>
#include "../../../code/renderergl2/tr_scene.c"

trGlobals_t tr;
refimport_t ri;
static backEndData_t storage;
backEndData_t *backEndData = &storage;
static void QDECL quiet(int level, const char *format, ...) {}

int main(void)
{
    world_t world = {0};
    worldSurfaceReplacement_t replacements[2] = {0};
    refEntity_t entity = {0};
    ri.Printf = quiet;
    tr.registered = qtrue; tr.world = &world;
    world.numSurfaceReplacements = 2; world.surfaceReplacements = replacements;
    replacements[0].surfaceIndex = 7; replacements[1].surfaceIndex = 21;
    replacements[0].entity.reType = replacements[1].entity.reType = RT_MODEL;
    r_numentities = 5; r_firstSceneEntity = 3;
    R_AddWorldReplacementsToScene();
    assert(r_numentities == 7);
    assert(replacements[0].entityNum == 2 && replacements[1].entityNum == 3);
    assert(storage.entities[5].worldSurface == 7 && storage.entities[6].worldSurface == 21);
    r_numentities = MAX_REFENTITIES - 1; r_firstSceneEntity = 0;
    R_AddWorldReplacementsToScene();
    assert(r_numentities == MAX_REFENTITIES);
    assert(replacements[0].entityNum == MAX_REFENTITIES - 1);
    assert(replacements[1].entityNum == -1); // original surface must be kept
    R_InitNextFrame();
    entity.reType = RT_MODEL;
    RE_AddRefEntityToScene(&entity);
    assert(r_numentities == 1 && storage.entities[0].worldSurface == -1);
    RE_ClearScene();
    R_AddWorldReplacementsToScene();
    assert(replacements[0].entityNum == 0 && replacements[1].entityNum == 1);
    puts("PASS: scene-relative replacement entities, capacity fallback, next-frame/cgame reset");
    return 0;
}
