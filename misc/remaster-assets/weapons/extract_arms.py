"""Blender CLI: -- paid-character-source.blend output-directory.

Extract generated forearms/hands for topology inspection and further rigging.
Not a completed first-person hand set. No finger meshes are fabricated here.
"""
import json
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector


def extract(source, output):
    output.mkdir(parents=True, exist_ok=True)
    for side in ('Left', 'Right'):
        bpy.ops.wm.open_mainfile(filepath=str(source))
        arm = bpy.data.objects['SargeRig']
        arm.animation_data_clear()
        for bone in arm.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
        obj = bpy.data.objects['SargeBody']
        groups = {obj.vertex_groups[side + name].index for name in ('ForeArm', 'Hand')}
        keep = {v.index for v in obj.data.vertices if sum(g.weight for g in v.groups if g.group in groups) >= .5}
        mesh = bmesh.new()
        mesh.from_mesh(obj.data)
        mesh.verts.ensure_lookup_table()
        bmesh.ops.delete(mesh, geom=[v for v in mesh.verts if v.index not in keep], context='VERTS')
        mesh.to_mesh(obj.data)
        mesh.free()
        bpy.context.view_layer.update()
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(output / (side.lower() + '-source.blend')))
        bounds = [obj.matrix_world @ v.co for v in obj.data.vertices]
        lo = Vector(tuple(min(v[i] for v in bounds) for i in range(3)))
        hi = Vector(tuple(max(v[i] for v in bounds) for i in range(3)))
        center = (lo + hi) / 2
        extent = max(hi - lo)
        scene = bpy.context.scene
        scene.render.engine = 'BLENDER_EEVEE'
        scene.eevee.use_gtao = True
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'Medium High Contrast'
        scene.world = bpy.data.worlds.new('ArmInspectionWorld')
        scene.world.use_nodes = True
        scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.15,.15,.15,1)
        scene.world.node_tree.nodes['Background'].inputs[1].default_value = .7
        scene.render.resolution_x = 800
        scene.render.resolution_y = 800
        scene.render.resolution_percentage = 100
        bpy.ops.object.camera_add()
        scene.camera = bpy.context.object
        scene.camera.data.type = 'ORTHO'
        scene.camera.data.ortho_scale = extent * 1.25
        for direction in ((2,-2,3), (-2,2,2)):
            bpy.ops.object.light_add(type='AREA', location=center+Vector(direction)*extent)
            light = bpy.context.object
            light.data.energy = 40
            light.data.size = extent*2
            light.rotation_euler = (center-light.location).to_track_quat('-Z','Y').to_euler()
        for name, direction in [('front',(2,-2,1)),('back',(-2,2,1))]:
            scene.camera.location = center+Vector(direction)*extent
            scene.camera.rotation_euler = (center-scene.camera.location).to_track_quat('-Z','Y').to_euler()
            scene.render.filepath = str(output / (side.lower()+'-'+name+'.png'))
            bpy.ops.render.render(write_still=True)
        (output / (side.lower()+'-inspection.json')).write_text(json.dumps({
            'vertices': len(obj.data.vertices), 'faces': len(obj.data.polygons),
            'bounds_m': [list(lo), list(hi)], 'cut': 'weight sum forearm+hand >= .5; open proximal cut',
            'status': 'topology inspection only, fingers not rigged'}, indent=2)+'\n')


if __name__ == '__main__':
    source, output = sys.argv[sys.argv.index('--')+1:]
    extract(Path(source).resolve(), Path(output).resolve())
