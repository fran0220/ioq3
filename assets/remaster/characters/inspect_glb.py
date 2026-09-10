"""Blender candidate inspection only: preserve generated mesh and materials.

-- candidate.glb output-directory; render all cardinal views without guessing
which direction the provider regards as front. Cameras/lights are not exported.
"""
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    source, output = map(Path, args[:2])
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if source.suffix == '.blend':
        bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
    else:
        bpy.ops.import_scene.gltf(filepath=str(source.resolve()))
    if len(args) == 4:
        arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
        arm.animation_data.action = bpy.data.actions[args[2]]
        bpy.context.scene.frame_set(int(args[3]))
    bpy.context.view_layer.update()
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    deps = bpy.context.evaluated_depsgraph_get()
    points = [o.matrix_world @ Vector(c) for o in meshes for c in o.evaluated_get(deps).bound_box]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    center = (lo + hi) / 2
    size = max(hi - lo)
    report = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'bounds': [list(lo), list(hi)], 'meshes': [],
              'armatures': [o.name for o in bpy.context.scene.objects if o.type == 'ARMATURE'],
              'runtime_accepted': False, 'blender_version': bpy.app.version_string}
    for obj in meshes:
        obj.data.calc_loop_triangles()
        report['meshes'].append({'name': obj.name, 'vertices': len(obj.data.vertices),
                                'triangles': len(obj.data.loop_triangles),
                                'uv_layers': len(obj.data.uv_layers),
                                'materials': [s.material.name if s.material else None for s in obj.material_slots]})
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 600
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'Medium High Contrast'
    world = bpy.data.worlds.new('ReviewWorld')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.14, .14, .14, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .6
    scene.world = world
    for i, offset in enumerate([(1,-2,2),(-2,1,1),(1,2,2)]):
        data = bpy.data.lights.new('ReviewLight' + str(i), 'AREA')
        data.energy = 300 * size * size
        data.size = size * 2
        light = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(light)
        light.location = center + Vector(offset) * size
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
    data = bpy.data.cameras.new('ReviewCamera')
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    data.type = 'ORTHO'
    data.ortho_scale = size * 1.5
    scene.camera = camera
    for name, direction in [('minus-y',(0,-1,0)),('plus-y',(0,1,0)),('minus-x',(-1,0,0)),('plus-x',(1,0,0))]:
        camera.location = center + Vector(direction) * size * 4
        camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str((output / (name + '.png')).resolve())
        bpy.ops.render.render(write_still=True)
    (output / 'inspection.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
