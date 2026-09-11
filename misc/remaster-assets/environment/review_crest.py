"""Render six measured orthographic views of exported MD3, not the source GLB.

blender -b --factory-startup --python review_crest.py -- PROCESSED OUTPUT [--legacy-ccw]
"""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from md3_static import read_md3


def review(processed, output, legacy_ccw=False):
    output.mkdir(parents=True, exist_ok=True)
    parsed = read_md3((processed / 'model.md3').read_bytes())
    positions, faces, uvs, normals = [], [], [], []
    for surface in parsed['surfaces']:
        base = len(positions)
        positions.extend(tuple(c / 40 for c in p) for p in surface['positions'])
        uvs.extend(surface['uvs'])
        normals.extend(surface['normals'])
        faces.extend(tuple(base + i for i in (tri if legacy_ccw else (tri[0], tri[2], tri[1])))
                     for tri in surface['triangles'])
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    mesh = bpy.data.meshes.new('exported_wall_crest')
    mesh.from_pydata(positions, [], faces)
    mesh.update()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mesh.use_auto_smooth = True
    mesh.normals_split_custom_set_from_vertices(normals)
    uv = mesh.uv_layers.new()
    for loop in mesh.loops:
        u, v = uvs[loop.vertex_index]
        uv.data[loop.index].uv = (u, 1 - v)
    obj = bpy.data.objects.new('exported_wall_crest', mesh)
    bpy.context.collection.objects.link(obj)
    material = bpy.data.materials.new('runtime_diffuse')
    material.use_nodes = True
    nodes = material.node_tree.nodes
    texture = nodes.new('ShaderNodeTexImage')
    texture.image = bpy.data.images.load(str(processed / 'diffuse.tga'))
    material.node_tree.links.new(texture.outputs['Color'], nodes['Principled BSDF'].inputs['Base Color'])
    nodes['Principled BSDF'].inputs['Roughness'].default_value = .8
    obj.data.materials.append(material)
    minimum = Vector(tuple(min(p[i] for p in positions) for i in range(3)))
    maximum = Vector(tuple(max(p[i] for p in positions) for i in range(3)))
    center = (minimum + maximum) / 2
    size = max(maximum - minimum)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.18, .19, .21, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .7
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'Medium High Contrast'
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = size * 1.2
    scene.camera = camera
    for direction in [(1, -2, 3), (-2, 1, 2), (1, 3, 1)]:
        bpy.ops.object.light_add(type='AREA', location=center + Vector(direction) * size)
        light = bpy.context.object
        light.data.energy = 180
        light.data.size = size * 2
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
    for label, direction in [('minus-y', (0, -1, 0)), ('plus-y', (0, 1, 0)),
                              ('minus-x', (-1, 0, 0)), ('plus-x', (1, 0, 0)),
                              ('top', (0, 0, 1)), ('perspective', (1, -2, 1))]:
        camera.location = center + Vector(direction).normalized() * size * 3
        camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.image_settings.file_format = 'JPEG'
        scene.render.image_settings.quality = 90
        scene.render.filepath = str(output / (label + '.jpg'))
        bpy.ops.render.render(write_still=True)
    (output / 'dimensions.json').write_text(json.dumps({
        'units_per_meter': 40, 'minimum_m': list(minimum), 'maximum_m': list(maximum),
        'size_m': list(maximum - minimum), 'render_source': 'decoded runtime MD3 and TGA',
        'input_winding': 'legacy-invalid-CCW' if legacy_ccw else 'engine-CW',
        'preview_winding': 'Blender-CCW', 'normals': 'decoded MD3 normals, smooth shaded',
        'note': 'Preview lights/cameras never exported; not an in-engine approval',
    }, indent=2) + '\n')


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    if len(args) not in (2, 3) or (len(args) == 3 and args[2] != '--legacy-ccw'):
        raise ValueError('Expected PROCESSED OUTPUT [--legacy-ccw]')
    review(Path(args[0]).resolve(), Path(args[1]).resolve(), len(args) == 3)
