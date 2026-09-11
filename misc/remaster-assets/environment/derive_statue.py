"""Explicit authorized static sculpture derivative, never a character runtime export.

blender -b --factory-startup --python derive_statue.py -- SOURCE_BLEND OUTPUT
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def derive(source, output):
    expected = '6499e2558b63dab69a00dcc604d322673d8e8d0a1e3b1000e62568d91292022c'
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise ValueError('Unexpected shared character master')
    if output.exists():
        raise ValueError('Preserve earlier derivatives; use a new revision')
    output.mkdir(parents=True)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    rig = bpy.data.objects['SargeRig']
    body = bpy.data.objects['SargeBody']
    rig.animation_data.action = bpy.data.actions['walk']
    bpy.context.scene.frame_set(2)
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = bpy.data.meshes.new_from_object(evaluated)
    transform = evaluated.matrix_world.copy()
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    obj = bpy.data.objects.new('EnvironmentSargeSculpture', mesh)
    bpy.context.collection.objects.link(obj)
    obj.matrix_world = transform
    for vertex in mesh.vertices:
        vertex.co = transform @ vertex.co
    obj.matrix_world.identity()
    minimum = Vector([min(v.co[a] for v in mesh.vertices) for a in range(3)])
    maximum = Vector([max(v.co[a] for v in mesh.vertices) for a in range(3)])
    pivot = Vector(((minimum.x + maximum.x) / 2, (minimum.y + maximum.y) / 2, minimum.z))
    for vertex in mesh.vertices:
        vertex.co -= pivot
    keys = [tuple(round(c / .00001) for c in v.co) for v in mesh.vertices]
    edges = Counter()
    for poly in mesh.polygons:
        vertices = list(poly.vertices)
        for a, b in zip(vertices, vertices[1:] + vertices[:1]):
            if keys[a] != keys[b]:
                edges[tuple(sorted((keys[a], keys[b])))] += 1
    boundary = sum(n == 1 for n in edges.values())
    if boundary:
        raise ValueError(f'Statue source has {boundary} welded boundary edges')
    mesh.materials.clear()
    for name, color in [('ivory_stone', (.55, .50, .40, 1)), ('graphite_stone', (.065, .075, .08, 1))]:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        shader = mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = color
        shader.inputs['Roughness'].default_value = .87
        mesh.materials.append(mat)
    height = maximum.z - minimum.z
    for poly in mesh.polygons:
        z = sum(mesh.vertices[i].co.z for i in poly.vertices) / len(poly.vertices)
        poly.material_index = 1 if z < height * .14 else 0
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if mesh.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'posed-sculpture.blend'))
    bpy.ops.export_scene.gltf(filepath=str(output / 'sculpture.glb'), export_format='GLB',
                              use_selection=True, export_animations=False, export_skins=False)
    report = {'source_blend_sha256': expected, 'source_rig': 'SargeRig', 'source_mesh': 'SargeBody',
              'source_welded_boundary_edges': boundary, 'boundary_measurement_grid_m': .00001,
              'action': 'walk', 'frame': 2, 'derived_role': 'static-environment-sculpture-not-character',
              'pose_selection': 'Frame2 minimizes sampled left/right ankle height difference (.0094m); re-ground evaluated mesh',
              'new_generation_charge': 0, 'source_paid_generation': 'task_4Yklp9dnD3eQcKosUVthynuw71MEi0rK',
              'source_rig_task': '01a089c0-12f3-773d-b222-d45eda78da34',
              'grounding_translation_m': list(-pivot), 'original_body_texture_reused': False,
              'shading': 'Clear character custom split normals after pose evaluation; smooth stone normals',
              'material': 'original two-tone matte stone; no commercial textures',
              'runtime_accepted': False, 'exact_original_statue_replica': False}
    report['files'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
    (output / 'derivation.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    source, output = sys.argv[sys.argv.index('--')+1:]
    derive(Path(source).resolve(), Path(output).resolve())
