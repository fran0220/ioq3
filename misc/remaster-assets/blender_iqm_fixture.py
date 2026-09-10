"""Create a TEST ONLY asymmetric two-material, three-joint .blend and reference.

No generated/commercial character art. CLI -- output-directory.
Reference positions come from Blender's evaluated armature modifier, not IQM code.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix


def create(output):
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    rig_data = bpy.data.armatures.new('test_rig')
    rig = bpy.data.objects.new('test_rig', rig_data); bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig; rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    root = rig_data.edit_bones.new('root'); root.head=(0,0,0); root.tail=(0,1,0)
    arm = rig_data.edit_bones.new('arm'); arm.head=(0,0,1); arm.tail=(0,1,1); arm.parent=root
    tag = rig_data.edit_bones.new('tag_weapon'); tag.head=(0,1.5,1); tag.tail=(0,2,1); tag.parent=arm; tag.use_deform=False
    bpy.ops.object.mode_set(mode='OBJECT')
    vertices = [(0,-.3,0),(0,.5,0),(.5,0,0),(0,0,1), (0,0,1),(0,0,2),(0,2,1),(.4,0,1)]
    faces = [(0,2,1),(0,1,3),(1,2,3),(2,0,3),(4,5,6),(4,7,5),(5,7,6),(6,7,4)]
    mesh = bpy.data.meshes.new('asymmetric_test_only'); mesh.from_pydata(vertices,[],faces); mesh.update()
    obj = bpy.data.objects.new('asymmetric_test_only',mesh); bpy.context.collection.objects.link(obj)
    for name, color in [('fixture_cyan',(0.03,.7,.9,1)),('fixture_orange',(1,.2,.025,1))]:
        mat=bpy.data.materials.new(name); mat.diffuse_color=color; mesh.materials.append(mat)
    for polygon in mesh.polygons:
        polygon.material_index = 0 if polygon.index < 4 else 1
    uv = mesh.uv_layers.new(name='test_uv')
    for poly in mesh.polygons:
        for corner, loop in enumerate(poly.loop_indices):
            uv.data[loop].uv = [(0,0),(1,0),(0,1)][corner]
    root_group = obj.vertex_groups.new(name='root'); child_group=obj.vertex_groups.new(name='arm')
    root_group.add([0,1,2,3],1,'REPLACE'); child_group.add([5,6,7],1,'REPLACE')
    root_group.add([4],.2,'REPLACE'); child_group.add([4],.8,'REPLACE')
    modifier=obj.modifiers.new('linear_skin','ARMATURE'); modifier.object=rig
    rig.animation_data_create()
    for pb in rig.pose.bones:
        pb.rotation_mode='QUATERNION'
    swing=bpy.data.actions.new('test_swing'); swing.use_fake_user=True; rig.animation_data.action=swing
    for frame, dx, angle in [(1,0,0),(2,.2,30),(3,.6,60)]:
        rig.pose.bones['root'].location=(dx,0,0)
        rig.pose.bones['root'].keyframe_insert('location',frame=frame)
        radians=math.radians(angle)/2
        rig.pose.bones['arm'].rotation_quaternion=(math.cos(radians),math.sin(radians),0,0)
        rig.pose.bones['arm'].keyframe_insert('rotation_quaternion',frame=frame)
    idle=bpy.data.actions.new('test_idle'); idle.use_fake_user=True; rig.animation_data.action=idle
    for frame, dy in [(7,.1),(8,.25)]:
        rig.pose.bones['root'].location=(0,dy,0); rig.pose.bones['root'].keyframe_insert('location',frame=frame)
    for action in (swing,idle):
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation='LINEAR'
    config = {'classification':'TEST ONLY synthetic rig, not production character', 'coordinate_system':'q3-x-forward-y-left-z-up',
              'units_per_meter':40, 'armature':rig.name, 'meshes':[obj.name], 'attachments':['tag_weapon'],
              'materials':{'fixture_cyan':'models/remaster/iqm_test_cyan','fixture_orange':'models/remaster/iqm_test_orange'},
              'clips':[{'name':'swing','action':'test_swing','start':1,'end':3,'fps':20,'loop':False,'semantic':'TEST_SWING', 'events':[{'frame':1,'name':'test_event'}]},
                       {'name':'idle','action':'test_idle','start':7,'end':8,'fps':12,'loop':True,'semantic':'TEST_IDLE', 'events':[{'frame':1,'name':'idle_event'}]}]}
    reference=[]
    for clip in config['clips']:
        rig.animation_data.action=None
        for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
        rig.animation_data.action=bpy.data.actions[clip['action']]
        for frame in range(clip['start'],clip['end']+1):
            bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()
            deps=bpy.context.evaluated_depsgraph_get()
            evaluated=obj.evaluated_get(deps); geometry=evaluated.to_mesh()
            tag=rig.evaluated_get(deps).pose.bones['tag_weapon'].matrix
            reference.append({'positions':[[c*40 for c in v.co] for v in geometry.vertices],
                              'tag_origin':[tag[i][3]*40 for i in range(3)], 'tag_axis':[[tag[r][c] for c in range(3)] for r in range(3)]})
            evaluated.to_mesh_clear()
    rig.animation_data.action=swing; bpy.context.scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'fixture.blend'))
    (output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    (output/'blender-reference.json').write_text(json.dumps(reference,indent=2)+'\n')


if __name__ == '__main__':
    create(Path(sys.argv[sys.argv.index('--')+1]).resolve())
