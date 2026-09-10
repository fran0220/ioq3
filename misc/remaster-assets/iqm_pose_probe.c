/* TEST ONLY. Compile production pose/tag math, not a reimplementation.
 * R_LoadIQM/OpenGL are not called here; binary input must first pass iqm_validate.
 * Link with -ffunction-sections -Wl,--gc-sections to discard unused renderer code.
 */
#include <assert.h>
#include "../../code/renderergl2/tr_model_iqm.c"

int main(int argc, char **argv) {
    FILE *file;
    long size;
    byte *bytes;
    iqmHeader_t *h;
    iqmData_t data = {0};
    iqmJoint_t *joints;
    iqmPose_t *poses;
    unsigned short *channels;
    float *positions = NULL;
    byte *indices = NULL, *weights = NULL;
    int i, j, k, frame;
    assert(argc == 2);
    file = fopen(argv[1], "rb"); assert(file);
    fseek(file, 0, SEEK_END); size = ftell(file); rewind(file);
    bytes = malloc(size); assert(bytes && fread(bytes, 1, size, file) == (size_t)size); fclose(file);
    h = (iqmHeader_t *)bytes;
    assert(h->version == 2 && h->filesize == size && h->num_joints <= 128 && h->num_poses == h->num_joints);
    data.num_joints = h->num_joints; data.num_poses = h->num_poses; data.num_frames = h->num_frames;
    data.jointParents = calloc(h->num_joints, sizeof(int));
    data.bindJoints = calloc(h->num_joints * 12, sizeof(float));
    data.invBindJoints = calloc(h->num_joints * 12, sizeof(float));
    data.poses = calloc(h->num_frames * h->num_poses, sizeof(iqmTransform_t));
    data.jointNames = calloc(h->num_joints, 64);
    joints = (iqmJoint_t *)(bytes + h->ofs_joints);
    {
        char *name = data.jointNames;
        for (i = 0; i < data.num_joints; i++) {
            float local[12], inverse[12];
            const char *source = (char *)bytes + h->ofs_text + joints[i].name;
            strcpy(name, source); name += strlen(source) + 1;
            data.jointParents[i] = joints[i].parent;
            JointToMatrix(joints[i].rotate, joints[i].scale, joints[i].translate, local);
            Matrix34Invert(local, inverse);
            if (joints[i].parent >= 0) {
                Matrix34Multiply(data.bindJoints + 12*joints[i].parent, local, data.bindJoints + 12*i);
                Matrix34Multiply(inverse, data.invBindJoints + 12*joints[i].parent, data.invBindJoints + 12*i);
            } else {
                memcpy(data.bindJoints + 12*i, local, sizeof(local));
                memcpy(data.invBindJoints + 12*i, inverse, sizeof(inverse));
            }
        }
    }
    poses = (iqmPose_t *)(bytes + h->ofs_poses); channels = (unsigned short *)(bytes + h->ofs_frames);
    for (frame = 0; frame < data.num_frames; frame++) {
        for (j = 0; j < data.num_joints; j++) {
            float v[10]; iqmTransform_t *pose = &data.poses[frame*data.num_poses + j];
            for (k = 0; k < 10; k++) {
                v[k] = poses[j].channeloffset[k];
                if (poses[j].mask & (1 << k)) v[k] += *channels++ * poses[j].channelscale[k];
            }
            memcpy(pose->translate, v, 3*sizeof(float));
            QuatNormalize2(v+3, pose->rotate);
            memcpy(pose->scale, v+7, 3*sizeof(float));
        }
    }
    for (i = 0; i < (int)h->num_vertexarrays; i++) {
        iqmVertexArray_t *a = (iqmVertexArray_t *)(bytes+h->ofs_vertexarrays)+i;
        if (a->type == IQM_POSITION) positions = (float *)(bytes+a->offset);
        if (a->type == IQM_BLENDINDEXES) indices = bytes+a->offset;
        if (a->type == IQM_BLENDWEIGHTS) weights = bytes+a->offset;
    }
    assert(positions && indices && weights);
    for (frame = 0; frame < data.num_frames; frame++) {
        float skin[128*12]; orientation_t tag;
        ComputePoseMats(&data, frame, frame, 0, skin);
        assert(R_IQMLerpTag(&tag, &data, frame, frame, 0, "tag_weapon"));
        printf("{\"frame\":%d,\"tag\":[%.9g,%.9g,%.9g],\"positions\":[", frame, tag.origin[0], tag.origin[1], tag.origin[2]);
        for (i = 0; i < (int)h->num_vertexes; i++) {
            float out[3] = {0};
            for (j = 0; j < 4; j++) {
                float *m = skin + 12*indices[4*i+j];
                for (k = 0; k < 3; k++)
                    out[k] += weights[4*i+j]/255.0f * (DotProduct(m+4*k, positions+3*i)+m[4*k+3]);
            }
            printf("%s[%.9g,%.9g,%.9g]", i ? "," : "", out[0],out[1],out[2]);
        }
        puts("]}");
    }
    if (data.num_frames >= 3) {
        orientation_t tag;
        assert(R_IQMLerpTag(&tag, &data, 0, 2, .25f, "tag_weapon"));
        printf("{\"interpolation_fraction\":0.25,\"tag\":[%.9g,%.9g,%.9g]}\n",tag.origin[0],tag.origin[1],tag.origin[2]);
        assert(!R_IQMLerpTag(&tag, &data, 0, 2, .25f, "TAG_WEAPON"));
        assert(tag.origin[0] == 0 && tag.origin[1] == 0 && tag.origin[2] == 0);
    }
    free(data.jointParents); free(data.bindJoints); free(data.invBindJoints); free(data.poses); free(data.jointNames); free(bytes);
    return 0;
}
