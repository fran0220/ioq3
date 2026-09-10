"""Split the generated machinegun at its receiver bearing and rig both pieces.

Blender CLI: -- cleaned.blend attachment-config.json output-directory
The visible surfaces remain the paid generated mesh. The cut is at the authored
bearing; no replacement gun/barrel geometry or game timing is manufactured.
"""
import json
from pathlib import Path
import sys

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rig_weapon import prepare


def split(source, config, output):
    output.mkdir(parents=True, exist_ok=True)
    for part in ('body', 'barrel'):
        bpy.ops.wm.open_mainfile(filepath=str(source))
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        if len(meshes) != 1:
            raise ValueError('Expected the single cleaned generated machinegun')
        obj = meshes[0]
        mesh = bmesh.new()
        mesh.from_mesh(obj.data)
        bmesh.ops.bisect_plane(
            mesh, geom=list(mesh.verts) + list(mesh.edges) + list(mesh.faces),
            plane_co=(config['barrel_cut_x_meters'], 0, 0), plane_no=(1, 0, 0),
            dist=1e-6, clear_outer=part == 'body', clear_inner=part == 'barrel')
        # The meeting ring stays open inside the bearing. Capping would invent
        # UVs across the packed atlas; it is not an exposed muzzle surface.
        bmesh.ops.triangulate(mesh, faces=list(mesh.faces))
        mesh.to_mesh(obj.data)
        mesh.free()
        if not obj.data.polygons:
            raise ValueError('Barrel cut removed the entire part')
        bpy.context.preferences.filepaths.save_version = 0
        part_source = output / (part + '-source.blend')
        bpy.ops.wm.save_as_mainfile(filepath=str(part_source))
        part_config = dict(config)
        if part == 'barrel':
            part_config['grip_meters'] = config['sockets_meters']['tag_barrel']
        prepare(part_source, part_config, output if part == 'body' else output / 'barrel')
    (output / 'split-config.json').write_text(json.dumps(config, indent=2) + '\n')


if __name__ == '__main__':
    source, config, output = sys.argv[sys.argv.index('--') + 1:]
    split(Path(source).resolve(), json.loads(Path(config).read_text()), Path(output).resolve())
