"""Blender CLI: -- cleaned-generated-arm.blend output-directory.

Right-arm candidate for the rocket grip. All visible mesh comes from Painter /
Hunyuan; this authors the 15-frame presentation controller, not game fire events.
Finger articulation and two-handed support are still separate production work.
"""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blender_iqm import export


def prepare(source, output):
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    obj.data.use_auto_smooth = True
    obj.data.auto_smooth_angle = .78539816339
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    # Cleaned hand runs diagonally through XYZ; align the forearm along +X
    # before placing its measured grip region on the view socket (meters).
    palm = Vector((.155, .08, .212))
    alignment = Matrix.Rotation(.372, 3, 'Y') @ Matrix.Rotation(-.584, 3, 'Z')
    socket = Vector((.45, -.15, -.35))
    for vertex in obj.data.vertices:
        vertex.co = alignment @ (vertex.co - palm) + socket
    rig_data = bpy.data.armatures.new('view_rig')
    rig = bpy.data.objects.new('view_rig', rig_data)
    bpy.context.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    root = rig_data.edit_bones.new('root')
    root.head = (0, 0, 0)
    root.tail = (0, .05, 0)
    tag = rig_data.edit_bones.new('tag_weapon')
    tag.head = socket
    tag.tail = socket + Vector((0, .05, 0))
    tag.parent = root
    tag.use_deform = False
    bpy.ops.object.mode_set(mode='OBJECT')
    group = obj.vertex_groups.new(name='root')
    group.add(list(range(len(obj.data.vertices))), 1, 'REPLACE')
    obj.modifiers.new('view_arm', 'ARMATURE').object = rig
    rig.animation_data_create()
    action = bpy.data.actions.new('q3_hands')
    action.use_fake_user = True
    rig.animation_data.action = action
    # Q3 units. Frame6 is shared between attack-end and drop-start.
    offsets = [(0,0),(-1.2,-.3),(-.8,-.2),(-.4,-.1),(-.15,0),(0,0),(0,0),
               (0,-3),(0,-6),(0,-9),(0,-12),(0,-12),(0,-8),(0,-4),(0,0)]
    for frame, (x, z) in enumerate(offsets, 1):
        rig.pose.bones['root'].location = (x/40, 0, z/40)
        rig.pose.bones['root'].keyframe_insert('location', frame=frame)
    for curve in action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    config = {
        'classification': 'generated-right-arm-rocket-candidate-not-complete-two-handed-set',
        'coordinate_system': 'q3-x-forward-y-left-z-up', 'units_per_meter': 40,
        'armature': rig.name, 'meshes': [obj.name], 'attachments': ['tag_weapon'],
        'materials': {obj.data.materials[0].name: 'models/remaster/weapons/hands/arm'},
        'clips': [{'name': 'q3_hands', 'action': 'q3_hands', 'start': 1, 'end': 15,
                   'fps': 20, 'loop': False, 'semantic': 'stock-torso-mapped-frames-no-fire-events'}],
    }
    bpy.context.scene.frame_set(1)
    master = output / 'hands.blend'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(master))
    (output / 'iqm-config.json').write_text(json.dumps(config, indent=2) + '\n')
    export(master, config, output / 'iqm')


if __name__ == '__main__':
    source, output = sys.argv[sys.argv.index('--') + 1:]
    prepare(Path(source).resolve(), Path(output).resolve())
