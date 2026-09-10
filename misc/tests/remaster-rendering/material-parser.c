/* Execute the production stage parser; image loading is captured, not mocked
 * into success based on the desired flags. No GL context or game data needed. */
#include <assert.h>
#include "../../../code/renderergl2/tr_shader.c"

refimport_t ri;
trGlobals_t tr;
static cvar_t enabled = { .integer = 1, .value = 1.0f }, disabled;
cvar_t *r_pbr = &disabled, *r_genNormalMaps = &enabled;
cvar_t *r_baseNormalX = &enabled, *r_baseNormalY = &enabled;
cvar_t *r_baseParallax = &disabled, *r_parallaxMapping = &disabled;
cvar_t *r_ignoreDstAlpha = &disabled;
static imgFlags_t loadedFlags;
static imgType_t loadedType;
static image_t image;

image_t *R_FindImageFile(const char *name, imgType_t type, imgFlags_t flags)
{
    loadedType = type;
    loadedFlags = flags;
    return &image;
}

void QDECL Com_Error(int level, const char *format, ...) { abort(); }
void QDECL Com_Printf(const char *format, ...) { abort(); }
static void QDECL unexpected(int level, const char *format, ...) { abort(); }

int main(void)
{
    const char *commands[] = { "map test.tga", "clampmap test.tga", "animMap 2 test.tga" };
    int i;
    ri.Printf = unexpected;
    for (i = 0; i < 3; i++) {
        char text[256], *cursor = text;
        shaderStage_t stage = {0};
        Com_sprintf(text, sizeof(text), "stage specularMap\n%s\n}\n", commands[i]);
        assert(ParseStage(&stage, &cursor));
        assert(loadedType == IMGTYPE_SPECULAR);
        assert(loadedFlags & IMGFLAG_NOLIGHTSCALE);
        assert(!(loadedFlags & IMGFLAG_GENNORMALMAP));
        assert(loadedFlags & IMGFLAG_MIPMAP);
        assert(!!(loadedFlags & IMGFLAG_CLAMPTOEDGE) == (i == 1));
    }
    {
        char text[] = "stage diffuseMap\nmap color.tga\n}\n", *cursor = text;
        shaderStage_t stage = {0};
        assert(ParseStage(&stage, &cursor));
        assert(!(loadedFlags & IMGFLAG_NOLIGHTSCALE));
        assert(loadedFlags & IMGFLAG_GENNORMALMAP);
    }
    {
        char text[] = "stage normalMap\nmap normal.tga\n}\n", *cursor = text;
        shaderStage_t stage = {0};
        assert(ParseStage(&stage, &cursor));
        assert(loadedType == IMGTYPE_NORMAL);
        assert(loadedFlags & IMGFLAG_NOLIGHTSCALE);
    }
    puts("PASS: specular data preserved for map/clampmap/animMap; color/normal unchanged");
    return 0;
}
