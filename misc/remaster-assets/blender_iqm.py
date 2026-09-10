"""Blender CLI: -- source.blend config.json output-directory.

Export preprocessed/weighted meshes and explicitly selected baked action ranges.
This is not a rig generator or GLB auto-retargeter. Material names map to already
prepared Q3 shaders; source materials/textures are preserved in the Blender file.
"""
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).parent))
from iqm_export import write_iqm
from iqm_validate import read_iqm, skin_positions


def identity(matrix):
    return all(abs(matrix[r][c] - (1 if r == c else 0)) < 1e-5 for r in range(4) for c in range(4))


def trs(matrix, units):
    t, q, s = matrix.decompose()
    rebuilt = Matrix.Translation(t) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((*s, 1))
    if any(abs(matrix[r][c]-rebuilt[r][c]) > 1e-5 for r in range(4) for c in range(4)):
        raise ValueError('Shear is not an IQM TRS; bake/retopologize before export')
    return {'translate': [v*units for v in t], 'rotate': [q.x,q.y,q.z,q.w], 'scale': list(s)}


def export(source, config, output):
    units = config['units_per_meter']
    if not isinstance(units, (float, int)) or not 0 < units <= 100:
        raise ValueError('Explicit positive units_per_meter <=100 required')
    bpy.ops.wm.open_mainfile(filepath=str(source))
    arm = bpy.data.objects[config['armature']]
    if arm.type != 'ARMATURE' or not identity(arm.matrix_world):
        raise ValueError('Apply armature object transforms before export')
    if any(b.bbone_segments != 1 for b in arm.data.bones):
        raise ValueError('B-bone deformation is not supported; bake to explicit rigid joints')
    bones = []
    def walk(bone):
        bones.append(bone)
        for child in sorted(bone.children, key=lambda b: b.name):
            walk(child)
    for root in sorted((b for b in arm.data.bones if b.parent is None), key=lambda b: b.name):
        walk(root)
    index = {b.name: i for i, b in enumerate(bones)}
    if len(config['meshes']) != len(set(config['meshes'])):
        raise ValueError('Duplicate mesh selection')
    document = {'schema_version': 1, 'coordinate_system': config['coordinate_system'], 'joints': [], 'meshes': [],
                'clips': [], 'attachments': config.get('attachments', [])}
    for bone in bones:
        local = bone.parent.matrix_local.inverted() @ bone.matrix_local if bone.parent else bone.matrix_local
        document['joints'].append({'name': bone.name, 'parent': index[bone.parent.name] if bone.parent else -1, **trs(local, units)})
    sources = []
    for object_name in config['meshes']:
        obj = bpy.data.objects[object_name]
        if obj.type != 'MESH' or not identity(obj.matrix_world) or obj.data.shape_keys or obj.animation_data:
            raise ValueError('Need applied mesh transforms, no object animation or shape keys')
        modifiers = list(obj.modifiers)
        if len(modifiers) != 1 or modifiers[0].type != 'ARMATURE' or modifiers[0].object != arm:
            raise ValueError('Apply geometry modifiers; require one armature modifier bound to selected rig')
        modifier = modifiers[0]
        if (modifier.use_deform_preserve_volume or modifier.use_bone_envelopes or not modifier.use_vertex_groups
                or modifier.vertex_group or not modifier.show_viewport or not modifier.show_render):
            raise ValueError('Require active unmasked linear vertex-group skinning, not dual-quaternion/envelopes')
        mesh = obj.data
        if not mesh.uv_layers.active:
            raise ValueError('UV atlas required before tangent export')
        mesh.calc_loop_triangles(); mesh.calc_normals_split(); mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
        material_meshes = {}
        for triangle in mesh.loop_triangles:
            mat = obj.material_slots[triangle.material_index].material
            if mat is None or mat.name not in config['materials']:
                raise ValueError('Explicit Q3 shader mapping required for every material')
            if triangle.material_index not in material_meshes:
                part = {'name': obj.name + '_' + str(triangle.material_index), 'material': config['materials'][mat.name],
                        'vertices': [], 'triangles': []}
                material_meshes[triangle.material_index] = (part, {})
                document['meshes'].append(part)
            part, lookup = material_meshes[triangle.material_index]
            corners = []
            for loop_index in triangle.loops:
                loop = mesh.loops[loop_index]; v = mesh.vertices[loop.vertex_index]
                uv = mesh.uv_layers.active.data[loop_index].uv
                influences = []
                for group in v.groups:
                    name = obj.vertex_groups[group.group].name
                    if group.weight > 0 and name in index:
                        if not arm.data.bones[name].use_deform:
                            raise ValueError('Positive weight assigned to non-deforming bone')
                        influences.append([index[name], group.weight])
                # Flip V for Q3; tangent handedness changes with it.
                vertex = {'position': [c*units for c in v.co], 'normal': list(loop.normal), 'uv': [uv.x, 1-uv.y],
                          'tangent': [*loop.tangent, -loop.bitangent_sign], 'influences': influences,
                          'source_vertex': loop.vertex_index}
                key = json.dumps(vertex, sort_keys=True)
                if key not in lookup:
                    lookup[key] = len(part['vertices']); part['vertices'].append(vertex)
                corners.append(lookup[key])
            part['triangles'].append(corners)
        sources.append({'object': obj.name, 'materials': [slot.material.name if slot.material else None for slot in obj.material_slots]})
    arm.animation_data_create()
    arm.animation_data.use_nla = False
    # Actions are explicitly named and sampled. Constraints are evaluated/baked;
    # reset unkeyed channels between clips so previous action state cannot leak.
    for clip in config['clips']:
        start, end = clip['start'], clip['end']
        if type(start) is not int or type(end) is not int or start > end:
            raise ValueError('Integer inclusive action frame range required')
        arm.animation_data.action = None
        for bone in arm.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
        arm.animation_data.action = bpy.data.actions[clip['action']]
        frames = []
        for frame in range(start, end+1):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            evaluated = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
            if not identity(evaluated.matrix_world):
                raise ValueError('Animated armature object transforms must be baked into root joint')
            values = []
            for bone in bones:
                pose = evaluated.pose.bones[bone.name]
                local = pose.parent.matrix.inverted() @ pose.matrix if pose.parent else pose.matrix
                values.append(trs(local, units))
            frames.append(values)
        document['clips'].append({'name': clip['name'], 'fps': clip['fps'], 'loop': clip['loop'], 'frames': frames})
    data = write_iqm(document); decoded = read_iqm(data)
    for frame, bound in enumerate(decoded['bounds']):
        if any(not bound[i] <= pos[i] <= bound[i+3] for pos in skin_positions(decoded, frame) for i in range(3)):
            raise ValueError('Exported animation outside conservative bounds')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'model.iqm').write_bytes(data)
    (output / 'source.json').write_text(json.dumps(document, indent=2)+'\n')
    sidecar = {'schema_version': 1, 'classification': config['classification'], 'source_blend_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'model_sha256': hashlib.sha256(data).hexdigest(), 'units_per_meter': units,
               'coordinate_system': document['coordinate_system'], 'materials': config['materials'], 'source_meshes': sources,
               'joints': [{'name': j['name'], 'parent': j['parent']} for j in decoded['joints']],
               'attachments': document['attachments'], 'clips': decoded['clips'], 'clip_bindings': config['clips'],
               'bounds_policy': 'conservative rigid-joint sphere covers arbitrary frame-pair interpolation; tighten only with verified culling tests',
               'vertex_weights': 'linear UBYTE4 sum255; quantized, never silently prune >4 influences',
               'cgame_binding_required': True, 'runtime_accepted': False, 'blender_version': bpy.app.version_string}
    (output / 'animation-contract.json').write_text(json.dumps(sidecar, indent=2)+'\n')
    print('IQM export:', len(data), 'bytes;', len(decoded['frames']), 'frames;', len(decoded['joints']), 'joints')


if __name__ == '__main__':
    source, config, output = sys.argv[sys.argv.index('--')+1:]
    export(Path(source).resolve(), json.loads(Path(config).read_text()), Path(output).resolve())
