/* Exercise production leaf traversal and entity submission, not a copied predicate. */
#include <assert.h>
#include "../../../code/renderergl2/tr_main.c"
#include "../../../code/renderergl2/tr_world.c"
#include "../../../code/renderergl2/tr_scene.c"

cvar_t *r_drawworld, *r_nocull, *r_nocurves, *r_facePlaneCull;
cvar_t *r_drawentities, *r_lockpvs, *r_showcluster, *r_novis;
static backEndData_t storage;
backEndData_t *backEndData = &storage;
static void QDECL quiet(int level, const char *format, ...) {}
static int submitted;
static model_t model = { .type = MOD_MESH };
model_t *R_GetModelByHandle(qhandle_t handle) { return &model; }
void R_AddMD3Surfaces(trRefEntity_t *entity) { submitted++; }
void R_MDRAddAnimSurfaces(trRefEntity_t *entity) { abort(); }
void R_AddIQMSurfaces(trRefEntity_t *entity) { abort(); }
void R_SetupEntityLighting(const trRefdef_t *refdef, trRefEntity_t *entity) {}
void R_DlightBmodel(bmodel_t *model) {}
shader_t *R_GetShaderByHandle(qhandle_t handle) { abort(); }

int main(void)
{
    world_t world = {0};
    mnode_t leaf = {0};
    trRefEntity_t entities[2] = {0};
    int marks[] = {1}, views[2] = {0}, lights[2] = {0}, shadows[2] = {0};
    int owners[] = {0, 1};
    worldSurfaceReplacement_t group = { .numSurfaces = 2, .surfaceIndices = owners };
    cvar_t draw = { .integer = 1 }, nocull = { .integer = 0 };
    tr.world = &world; tr.refdef.entities = entities;
    world.numSurfaceReplacements = 1; world.surfaceReplacements = &group;
    r_drawworld = &draw; r_nocull = &nocull;
    world.marksurfaces = marks; world.surfacesViewCount = views;
    world.surfacesDlightBits = lights; world.surfacesPshadowBits = shadows;
    leaf.nummarksurfaces = 1; leaf.visCounts[0] = 7;
    VectorSet(leaf.mins, -10, -20, -30); VectorSet(leaf.maxs, 10, 20, 30);
    tr.visCounts[0] = 7; tr.viewCount = 11;
    entities[0].worldReplacement = 0; entities[0].e.reType = RT_MODEL;
    AxisClear(entities[0].e.axis);
    entities[1] = entities[0]; entities[1].worldReplacement = -1;

    R_RecursiveWorldNode(&leaf, 0, 2, 4);
    assert(views[1] == 11 && views[0] == 0);
    assert(lights[1] == 2 && shadows[1] == 4);
    R_AddEntitySurface(0); assert(submitted == 1);

    // Moving to another PVS must not retain last view's owner visibility.
    tr.viewCount++; tr.visCounts[0]++;
    R_RecursiveWorldNode(&leaf, 0, 0, 0);
    R_AddEntitySurface(0); assert(submitted == 1);
    R_AddEntitySurface(1); assert(submitted == 2); // unrelated cgame entity unaffected

    // Return to the owning PVS, including another view of the same frame.
    tr.viewCount++; leaf.visCounts[0] = tr.visCounts[0];
    R_RecursiveWorldNode(&leaf, 0, 8, 0);
    R_AddEntitySurface(0); assert(submitted == 3);
    assert(lights[1] == 8 && shadows[1] == 0); // no stale light masks

    draw.integer = 0;
    R_AddEntitySurface(0); assert(submitted == 3);
    draw.integer = 1; tr.refdef.rdflags = RDF_NOWORLDMODEL;
    R_AddEntitySurface(0); assert(submitted == 3);
    tr.refdef.rdflags = 0;

    // Depth shadow traversal intentionally ignores camera PVS.
    tr.viewCount++; tr.visCounts[0]++; tr.viewParms.flags = VPF_DEPTHSHADOW;
    R_RecursiveWorldNode(&leaf, 0, 0, 0);
    assert(views[1] == tr.viewCount);
    R_AddEntitySurface(0); assert(submitted == 4);

    // Turning the frustum away must invalidate this view even within one PVS.
    tr.viewParms.flags = 0; tr.viewCount++; leaf.visCounts[0] = tr.visCounts[0];
    VectorSet(tr.viewParms.frustum[0].normal, 1, 0, 0);
    tr.viewParms.frustum[0].dist = 50;
    R_RecursiveWorldNode(&leaf, 1, 0, 0);
    R_AddEntitySurface(0); assert(submitted == 4);
    tr.viewCount++; tr.viewParms.frustum[0].dist = -50;
    R_RecursiveWorldNode(&leaf, 1, 0, 0);
    R_AddEntitySurface(0); assert(submitted == 5);

    // The other member alone must also own visibility (not first-only/last-only).
    tr.viewCount++; marks[0] = 0;
    R_RecursiveWorldNode(&leaf, 0, 0, 0);
    R_AddEntitySurface(0); assert(submitted == 6);

    // Actual scene capacity failure must submit the original draw surface,
    // not merely set a sentinel that nobody consumes.
    {
        worldSurfaceReplacement_t replacement = { .numSurfaces = 2, .surfaceIndices = owners };
        int bothMarks[] = {0, 1};
        msurface_t surfaces[2] = {0};
        surfaceType_t surface = SF_FACE;
        shader_t shader = {0};
        drawSurf_t draws[4];
        cvar_t yes = { .integer = 1 }, no = {0};
        ri.Printf = quiet; tr.registered = qtrue;
        world.nodes = &leaf; world.numWorldSurfaces = 2; world.surfaces = surfaces;
        world.marksurfaces = bothMarks; leaf.nummarksurfaces = 2;
        world.numSurfaceReplacements = 1; world.surfaceReplacements = &replacement;
        replacement.entity = entities[0].e;
        surfaces[1].replacementIndex = 1; surfaces[1].data = &surface; surfaces[1].shader = &shader;
        surfaces[0] = surfaces[1];
        tr.refdef.drawSurfs = draws;
        r_nocull = r_lockpvs = r_drawentities = &yes;
        r_novis = r_showcluster = r_nocurves = r_facePlaneCull = &no;
        r_numentities = MAX_REFENTITIES;
        R_AddWorldReplacementsToScene();
        assert(replacement.entityNum == -1);
        R_AddWorldSurfaces();
        assert(tr.refdef.numDrawSurfs == 2 && draws[0].surface == &surface && draws[1].surface == &surface);
        r_numentities = 0;
        R_AddWorldReplacementsToScene();
        assert(replacement.entityNum == 0);
        tr.refdef.numDrawSurfs = 0;
        R_AddWorldSurfaces();
        assert(tr.refdef.numDrawSurfs == 0);
        r_drawentities = &no;
        R_AddWorldSurfaces();
        assert(tr.refdef.numDrawSurfs == 2 && draws[0].surface == &surface && draws[1].surface == &surface);
    }
    // The PVS diagnostic must really expose hidden leaves and invalidate the
    // cached cluster on both toggle edges without changing the camera.
    {
        mnode_t nodes[3] = {0};
        cplane_t plane = { .normal = {1, 0, 0} };
        byte vis[2] = {1, 2};
        cvar_t no = {0}, novis = {0};
        world.nodes = nodes; world.numnodes = 3;
        world.vis = vis; world.numClusters = 2; world.clusterBytes = 1;
        nodes[0].contents = CONTENTS_NODE; nodes[0].cluster = -1;
        nodes[0].plane = &plane;
        nodes[0].children[0] = &nodes[1]; nodes[0].children[1] = &nodes[2];
        nodes[1].cluster = 0; nodes[2].cluster = 1;
        nodes[1].parent = nodes[2].parent = &nodes[0];
        VectorSet(tr.viewParms.pvsOrigin, 1, 0, 0);
        memset(tr.refdef.areamask, 0, sizeof(tr.refdef.areamask));
        for (int i = 0; i < MAX_VISCOUNTS; i++) tr.visClusters[i] = -2;
        r_lockpvs = r_showcluster = &no; r_novis = &novis;
        R_MarkLeaves();
        assert(nodes[1].visCounts[tr.visIndex] == tr.visCounts[tr.visIndex]);
        assert(nodes[2].visCounts[tr.visIndex] != tr.visCounts[tr.visIndex]);
        novis.integer = 1; novis.modified = qtrue;
        R_MarkLeaves();
        assert(nodes[2].visCounts[tr.visIndex] == tr.visCounts[tr.visIndex]);
        novis.integer = 0; novis.modified = qtrue;
        R_MarkLeaves();
        assert(nodes[2].visCounts[tr.visIndex] != tr.visCounts[tr.visIndex]);
    }
    puts("PASS: production PVS exit/reentry, per-view ownership, masks, world disable and depth shadows");
    puts("PASS: frustum turn and actual original draw submission on capacity failure/entities disabled");
    puts("PASS: r_novis exposes occluded leaves and invalidates cached visibility on both toggle edges");
    return 0;
}
