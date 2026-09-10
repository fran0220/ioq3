/* Production CPU mip and picmip data-map regression. */
#include <assert.h>
#include "../../../code/renderergl2/tr_image.c"

refimport_t ri;
glconfig_t glConfig = { .maxTextureSize = 4096 };
static cvar_t zero, one = { .integer = 1 };
cvar_t *r_picmip = &one, *r_roundImagesDown = &zero;
cvar_t *r_imageUpsample = &zero, *r_imageUpsampleMaxSize = &zero;
cvar_t *r_imageUpsampleType = &zero;

int main(void)
{
    byte data[] = {0,40,80,120, 100,140,180,220, 20,60,100,140, 120,160,200,240};
    byte color[sizeof(data)], *input = data, *allocated = NULL;
    const byte expected[] = {60,100,140,180};
    int width = 2, height = 2;
    memcpy(color, data, sizeof(data));
    assert(RawImage_ScaleToPower2(&input, &width, &height, IMGTYPE_SPECULAR,
           IMGFLAG_MIPMAP | IMGFLAG_PICMIP, &allocated));
    assert(width == 1 && height == 1 && allocated == NULL);
    assert(memcmp(data, expected, 4) == 0);
    R_MipMapsRGB(color, 2, 2);
    assert(color[0] > 60); // legacy sRGB operation changes data, not equivalent
    {
        byte row[] = {0,20,40,60, 100,120,140,160, 20,40,60,80, 120,140,160,180};
        byte column[sizeof(row)];
        const byte pair[] = {50,70,90,110, 70,90,110,130};
        memcpy(column, row, sizeof(row));
        R_MipMapLinear(row, 4, 1);
        R_MipMapLinear(column, 1, 4);
        assert(memcmp(row, pair, 8) == 0 && memcmp(column, pair, 8) == 0);
        R_MipMapLinear(row, 2, 1);
        assert(memcmp(row, expected, 4) != 0); // independent chain result below
        assert(row[0] == 60 && row[1] == 80 && row[2] == 100 && row[3] == 120);
        R_MipMapLinear(row, 1, 1);
        assert(row[0] == 60 && row[3] == 120);
    }
    puts("PASS: specular picmip averages linear RGBA; asymmetric 2D, 1D and 1x1 tails");
    return 0;
}
