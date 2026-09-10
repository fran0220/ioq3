"""Bake paid high-resolution character normals onto its reduced rig mesh."""
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix


def main():
    work = Path(sys.argv[sys.argv.index('--')+1]).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(work/'prepared/source.blend'))
    arm = bpy.data.objects['SargeRig']
    arm.animation_data_clear()
    for bone in arm.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    low = bpy.data.objects['SargeBody']
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(work/'rigged.glb'))
    imported = set(bpy.data.objects)-before
    high = next(o for o in imported if o.type == 'MESH')
    high_arm = next(o for o in imported if o.type == 'ARMATURE')
    high_arm.animation_data_clear()
    for bone in high_arm.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    # Match prepare_rig's source basis and ground offset before decimation.
    high.data.transform(Matrix.Translation((0,0,-.6)) @ Matrix.Rotation(math.pi/2,4,'Z') @ high.matrix_world)
    high.modifiers.clear()
    high.parent = None
    high.matrix_world = Matrix.Identity(4)
    image = bpy.data.images.new('SargeBakedNormal',1024,1024,alpha=False)
    image.colorspace_settings.name = 'Non-Color'
    material = low.data.materials[0]
    node = material.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = image
    material.node_tree.nodes.active = node
    bpy.ops.object.select_all(action='DESELECT')
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = .035
    scene.render.bake.max_ray_distance = .15
    scene.render.bake.margin = 8
    scene.render.bake.normal_space = 'TANGENT'
    bpy.ops.object.bake(type='NORMAL')
    image.filepath_raw = str(work/'prepared/normal.tga')
    image.file_format = 'TARGA'
    image.save()
    report = {'source_rig_sha256':hashlib.sha256((work/'rigged.glb').read_bytes()).hexdigest(),
              'normal_sha256':hashlib.sha256((work/'prepared/normal.tga').read_bytes()).hexdigest(),
              'kind':'Blender selected high-to-low tangent +Y normal bake',
              'resolution':[1024,1024], 'cage_extrusion_m':.035, 'max_ray_distance_m':.15,
              'runtime_accepted':False}
    (work/'prepared/material-bake.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
