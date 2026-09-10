/* Test the production projection radius without a renderer or GPU context. */
#include <assert.h>
#include "../../../code/renderergl2/tr_main.c"

int main(void)
{
    float bounds[] = { -1, -2, 0, 3, 4, 12, -5, -1, -2, 2, 8, 9 };
    iqmData_t data = {0};
    refEntity_t ent = {0};
    assert(R_IQMShadowRadius(&data, &ent) == 0); // optional absent bounds
    data.bounds = bounds;
    data.num_frames = 2;
    assert(fabsf(R_IQMShadowRadius(&data, &ent) - 13.0f) < 0.00001f);
    ent.oldframe = 1;
    assert(fabsf(R_IQMShadowRadius(&data, &ent) - sqrtf(233.0f)) < 0.00001f);
    ent.frame = 200;
    ent.oldframe = -1;
    assert(fabsf(R_IQMShadowRadius(&data, &ent) - 13.0f) < 0.00001f);
    ent.renderfx = RF_WRAP_FRAMES;
    ent.frame = ent.oldframe = 3;
    assert(fabsf(R_IQMShadowRadius(&data, &ent) - sqrtf(170.0f)) < 0.00001f);
    data.num_frames = 0; // static IQM: one loader-computed bounds record
    assert(fabsf(R_IQMShadowRadius(&data, &ent) - 13.0f) < 0.00001f);
    puts("PASS: IQM shadow optional bounds, origin-centered pose union, frame validation/wrap");
    return 0;
}
