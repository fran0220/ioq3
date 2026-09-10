"""Prepare a generated, cleaned rigid weapon for the shared Blender IQM exporter.

CLI: -- cleaned.blend attachment-config.json output-directory
Never fabricates visible geometry. Coordinates in the config are measured in
the cleaned Blender mesh, meters; they must be visually reviewed per candidate.
"""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blender_iqm import export


def prepare(source, config, output):
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if len(meshes) != 1:
        raise ValueError('Expected the single generated cleaned mesh')
    obj = meshes[0]
    obj.data.use_auto_smooth = True
    obj.data.auto_smooth_angle = .78539816339
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    grip = Vector(config['grip_meters'])
    for vertex in obj.data.vertices:
        vertex.co -= grip
    rig_data = bpy.data.armatures.new('weapon_rig')
    rig = bpy.data.objects.new('weapon_rig', rig_data)
    bpy.context.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    root = rig_data.edit_bones.new('root')
    root.head = (0, 0, 0)
    root.tail = (0, .05, 0)
    for name, position in config['sockets_meters'].items():
        bone = rig_data.edit_bones.new(name)
        bone.head = Vector(position) - grip
        bone.tail = bone.head + Vector((0, .05, 0))
        bone.parent = root
        bone.use_deform = False
    bpy.ops.object.mode_set(mode='OBJECT')
    group = obj.vertex_groups.new(name='root')
    group.add(list(range(len(obj.data.vertices))), 1, 'REPLACE')
    obj.modifiers.new('rigid_weapon', 'ARMATURE').object = rig
    rig.animation_data_create()
    action = bpy.data.actions.new('rigid')
    action.use_fake_user = True
    rig.animation_data.action = action
    rig.pose.bones['root'].keyframe_insert('location', frame=1)
    export_config = {
        'classification': 'generated-remaster-weapon-candidate',
        'coordinate_system': 'q3-x-forward-y-left-z-up',
        'units_per_meter': 40, 'armature': rig.name, 'meshes': [obj.name],
        'attachments': list(config['sockets_meters']),
        'materials': {obj.data.materials[0].name: config['shader']},
        'clips': [{'name': 'rigid', 'action': 'rigid', 'start': 1, 'end': 1, 'fps': 1, 'loop': True}],
    }
    master = output / 'weapon.blend'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(master))
    (output / 'iqm-config.json').write_text(json.dumps(export_config, indent=2) + '\n')
    export(master, export_config, output / 'iqm')

    # Full-object neutral inspection, independent of the pillar's height camera.
    obj = bpy.data.objects[export_config['meshes'][0]]
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.use_gtao = True
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'Medium High Contrast'
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.18, .18, .18, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .8
    bounds = [Vector(c) for c in obj.bound_box]
    center = sum(bounds, Vector()) / 8
    extent = max(obj.dimensions)
    scene.render.resolution_x = 960
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = extent * 1.3
    for pos in [(1, -2, 3), (-2, 1, 2)]:
        bpy.ops.object.light_add(type='AREA', location=center + Vector(pos) * extent)
        light = bpy.context.object
        light.data.energy = 25
        light.data.size = extent * 2
        light.rotation_euler = (center-light.location).to_track_quat('-Z', 'Y').to_euler()
    for name, direction in [('front', (1, -3, 1.2)), ('back', (-1, 3, 1.2)), ('side', (0, -3, 0))]:
        scene.camera.location = center + Vector(direction) * extent
        scene.camera.rotation_euler = (center-scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(output / ('review-' + name + '.png'))
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    source, config, output = sys.argv[sys.argv.index('--') + 1:]
    prepare(Path(source).resolve(), json.loads(Path(config).read_text()), Path(output).resolve())
