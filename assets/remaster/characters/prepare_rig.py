"""Prepare the paid character rig/motion sources for existing IQM export.

This is a whole-rig inspection master, not the final segmented cgame package.
Missing motion sources are not replaced with synthetic production animations.
Run in Blender: -- work-directory. Keeps the original downloaded GLBs untouched.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = set(bpy.data.objects) - before
    return next(o for o in objects if o.type == 'ARMATURE'), objects


def rigid(matrix):
    t, q, scale = matrix.decompose()
    return Matrix.Translation(t) @ q.to_matrix().to_4x4()


def main():
    work = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    out = work / 'prepared'
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm, objects = load(work / 'rigged.glb')
    mesh = next(o for o in objects if o.type == 'MESH')
    # Provider GLB is +Z forward; Blender import is -Y forward. Only authoring
    # changes coordinate basis; the engine's player physics are untouched.
    basis = Matrix.Translation((0,0,-.6)) @ Matrix.Rotation(math.pi/2, 4, 'Z')
    mesh_world = mesh.matrix_world.copy()
    arm_world = arm.matrix_world.copy()
    arm.animation_data_clear()
    for b in arm.pose.bones:
        b.matrix_basis = Matrix.Identity(4)
    mesh.data.transform(basis @ mesh_world)
    mesh.parent = None
    mesh.matrix_world = Matrix.Identity(4)
    arm.data.transform(basis @ arm_world)
    arm.matrix_world = Matrix.Identity(4)
    arm.name = 'SargeRig'
    mesh.name = 'SargeBody'
    activate(mesh)
    decimate = mesh.modifiers.new('Web triangle budget', 'DECIMATE')
    decimate.ratio = .25
    decimate.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    # Imported split normals no longer describe the reduced topology (one
    # observed loop produced a zero tangent). Recompute on the actual mesh.
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    # Decimation can interpolate >4 weights. Explicit authoring pruning and
    # normalization is recorded here; the IQM writer itself still rejects >4.
    for vertex in mesh.data.vertices:
        weights = sorted(((g.group,g.weight) for g in vertex.groups if g.weight > 0), key=lambda p:-p[1])[:4]
        if not weights:
            raise ValueError('Unweighted generated vertex')
        for group in mesh.vertex_groups:
            group.remove([vertex.index])
        total = sum(w for _,w in weights)
        for index, weight in weights:
            mesh.vertex_groups[index].add([vertex.index], weight/total, 'REPLACE')
    for modifier in mesh.modifiers:
        if modifier.type == 'ARMATURE':
            modifier.use_deform_preserve_volume = False
    # Keep the provider base texture. The source has no authored normal/F0 map;
    # this inspection diffuse shader makes no PBR or final-material claim.
    material = mesh.data.materials[0]
    texture = next(n.image for n in material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image)
    texture.filepath_raw = str(out / 'body.tga')
    texture.file_format = 'TARGA'
    texture.save()
    material.name = 'SargeDiffuseReview'
    material.node_tree.nodes.clear()
    nodes = material.node_tree.nodes
    output = nodes.new('ShaderNodeOutputMaterial')
    diffuse = nodes.new('ShaderNodeBsdfDiffuse')
    image = nodes.new('ShaderNodeTexImage')
    image.image = texture
    material.node_tree.links.new(image.outputs['Color'], diffuse.inputs['Color'])
    material.node_tree.links.new(diffuse.outputs[0], output.inputs[0])
    clips = []
    specs = [('death1','motion-183',30,20,False),('death2','motion-184',30,20,False),
             ('death3','motion-188',30,20,False),('crouch','motion-616',8,20,True),
             ('walk','walking',12,20,True),('run','running',11,21,True),('jump','motion-466',16,18,False)]
    names = [b.name for b in arm.data.bones]
    arm.animation_data_create()
    for name, filename, count, fps, loop in specs:
        source, imported = load(work / (filename + '.glb'))
        if [b.name for b in source.data.bones] != names:
            raise ValueError('Motion rig hierarchy/name mismatch')
        first,last = source.animation_data.action.frame_range
        frames = []
        anchor = None
        for index in range(count):
            f = first + (last-first)*index/(count if loop else count-1)
            bpy.context.scene.frame_set(math.floor(f), subframe=f-math.floor(f))
            bpy.context.view_layer.update()
            evaluated = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
            pose = {b.name:rigid(basis @ source.matrix_world @ b.matrix) for b in evaluated.pose.bones}
            if anchor is None:
                anchor = pose['Hips'].translation.copy()
            if name in ('walk','run','crouch','jump'):
                delta = pose['Hips'].translation - anchor
                correction = Matrix.Translation((-delta.x,-delta.y,0))
                pose = {key:correction @ value for key,value in pose.items()}
            frames.append(pose)
        for obj in imported:
            bpy.data.objects.remove(obj, do_unlink=True)
        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        arm.animation_data.action = action
        for index, poses in enumerate(frames, 1):
            bpy.context.scene.frame_set(index)
            for bone_name in names:
                bone = arm.pose.bones[bone_name]
                bone.rotation_mode = 'QUATERNION'
                bone.matrix = poses[bone_name]
                bpy.context.view_layer.update()
                for channel in ('location','rotation_quaternion','scale'):
                    bone.keyframe_insert(channel, frame=index, group=bone_name)
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        clips.append({'name':name,'action':action.name,'start':1,'end':count,'fps':fps,'loop':loop})
    arm.animation_data.action = bpy.data.actions['walk']
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'source.blend'))
    config = {'classification':'generated-character-incomplete-runtime-review',
              'coordinate_system':'q3-x-forward-y-left-z-up','units_per_meter':40,
              'armature':arm.name,'meshes':[mesh.name],
              'materials':{material.name:'models/remaster/characters/sarge_review'},
              'attachments':[], 'clips':clips}
    (out / 'config.json').write_text(json.dumps(config,indent=2)+'\n')
    print('Prepared paid rig and seven source motions; NOT final cgame character')


if __name__ == '__main__':
    main()
