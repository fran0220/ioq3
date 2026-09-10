/* Actual IQM tag code, deliberately asymmetric poses; no loader/GL claim. */
#include <assert.h>
#include "../../../code/renderergl2/tr_model_iqm.c"

int main(void) {
    iqmData_t data = {0};
    orientation_t tag;
    int parent = -1;
    float bind[12] = {1,0,0,0, 0,1,0,0, 0,0,1,0};
    iqmTransform_t poses[2] = {
        {{2,3,5}, {0,0,0,1}, {1,1,1}},
        {{10,19,29}, {0,0,0,1}, {1,1,1}}
    };
    int bad[] = {-1, 2, 1000000};
    int i;
    data.num_joints = data.num_poses = 1;
    data.num_frames = 2;
    data.jointNames = "tag_weapon";
    data.jointParents = &parent;
    data.bindJoints = data.invBindJoints = bind;
    data.poses = poses;
    assert(R_IQMLerpTag(&tag, &data, 0, 1, .25f, "tag_weapon"));
    assert(tag.origin[0] == 4 && tag.origin[1] == 7 && tag.origin[2] == 11);
    for (i = 0; i < ARRAY_LEN(bad); i++) {
        assert(R_IQMLerpTag(&tag, &data, bad[i], 1, .25f, "tag_weapon"));
        assert(tag.origin[0] == 2 && tag.origin[1] == 3 && tag.origin[2] == 5);
        assert(R_IQMLerpTag(&tag, &data, 1, bad[i], .75f, "tag_weapon"));
        assert(tag.origin[0] == 2 && tag.origin[1] == 3 && tag.origin[2] == 5);
    }
    assert(!R_IQMLerpTag(&tag, &data, -1, 2, .25f, "TAG_WEAPON"));
    assert(tag.origin[0] == 0 && tag.axis[0][0] == 1);
    data.num_poses = data.num_frames = 0;
    assert(R_IQMLerpTag(&tag, &data, -1, 2, .25f, "tag_weapon"));
    assert(tag.origin[0] == 0 && tag.axis[2][2] == 1);
    puts("PASS: IQM tag interpolation, both invalid frame boundaries, case, static bind pose");
    return 0;
}
