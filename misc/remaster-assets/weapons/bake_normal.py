"""Blender CLI: -- weapon-work-directory. Bake actual generated high mesh detail.

Preserves the immutable processed stage and its UV atlas. Outputs a separate
material-stage normal map and provenance, without manufacturing flat normals.
"""
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def bake(work):
    config = json.loads((work / 'process-config.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(work / 'processed/cleaned.blend'))
    low = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    original = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(work / 'generated.glb'))
    imported = set(bpy.context.scene.objects) - original
    meshes = [o for o in imported if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    high = bpy.context.object
    matrix = high.matrix_world.copy()
    high.parent = None
    high.matrix_world = matrix
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    high.rotation_euler.z = math.radians(config['rotation_z_degrees'])
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    vertices = high.data.vertices
    lo = Vector(tuple(min(v.co[i] for v in vertices) for i in range(3)))
    hi = Vector(tuple(max(v.co[i] for v in vertices) for i in range(3)))
    center = Vector(((lo.x + hi.x)/2, (lo.y + hi.y)/2, lo.z))
    for vertex in vertices:
        vertex.co = (vertex.co - center) * (config['height_meters'] / (hi.z - lo.z))
    # Match rig_weapon's final smooth shading before calculating tangent space.
    low.data.use_auto_smooth = True
    low.data.auto_smooth_angle = math.pi / 4
    for polygon in low.data.polygons:
        polygon.use_smooth = True
    image = bpy.data.images.new('weapon_normal', config['texture_edge'], config['texture_edge'], alpha=False)
    image.colorspace_settings.name = 'Non-Color'
    for material in low.data.materials:
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
    scene.render.bake.cage_extrusion = .003
    scene.render.bake.max_ray_distance = .015
    scene.render.bake.margin = 8
    scene.render.bake.normal_space = 'TANGENT'
    bpy.ops.object.bake(type='NORMAL')
    output = work / 'material'
    output.mkdir(exist_ok=True)
    image.filepath_raw = str(output / 'normal.tga')
    image.file_format = 'TARGA'
    image.save()
    report = {'kind': 'generated high-to-low tangent +Y normal bake', 'runtime_accepted': False,
              'cage_extrusion_m': .003, 'max_ray_distance_m': .015,
              'hashes': {str(p.relative_to(work)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                         (work / 'generated.glb', work / 'processed/cleaned.blend', output / 'normal.tga')},
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (output / 'normal-bake.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    bake(Path(sys.argv[sys.argv.index('--') + 1]).resolve())
