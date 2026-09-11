"""Measured per-surface production ledger; never emits original geometry/images."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import struct
import zipfile

from package import SOURCE_SHA, material


def batch(name):
    if name.startswith('textures/sfx/flame'):
        return 'effects-owner-handoff'
    if '/storch/' in name:
        return 'E2-standing-lanterns'
    if '/gratelamp/' in name:
        return 'E3-wall-lantern-groups'
    if '/wallhead/lion' in name:
        return 'E4-paired-wall-reliefs'
    if name == 'models/mapobjects/wallhead/wallhead02':
        return 'E1-wall-crest'
    if name.startswith(('models/mapobjects/visor', 'models/mapobjects/major')):
        return 'E6-statues-owner-coordination'
    if '/gothic_door/' in name:
        return 'E5-portals-and-arches'
    if '/skies/' in name:
        return 'E7-sky'
    if '/liquids/' in name:
        return 'E8-hazard-surface-art'
    return 'E9-structural-surfaces'


def inventory(source, output, scene=None):
    replacements = {2050}
    if scene:
        with zipfile.ZipFile(scene) as archive:
            bindings = json.loads(archive.read('maps/q3dm1.remaster.json'))
        replacements = {member['surface'] for entry in bindings['replacements']
                        for member in entry.get('surfaces', [entry])}
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Unreviewed reference')
    with zipfile.ZipFile(source) as archive:
        data = archive.read('maps/q3dm1.bsp')
    lumps = [struct.unpack_from('<ii', data, 8 + i * 8) for i in range(17)]
    offset, length = lumps[1]
    names = [data[i:i + 64].split(b'\0')[0].decode() for i in range(offset, offset + length, 72)]
    offset, length = lumps[13]
    rows = []
    for index, start in enumerate(range(offset, offset + length, 104)):
        slot, _, kind, _, vertices, _, indexes = struct.unpack_from('<7i', data, start)
        name = names[slot]
        rows.append({'surface': index, 'source_slot': name, 'surface_type': kind,
                     'vertices': vertices, 'indices': indexes, 'batch': batch(name),
                     'material_candidate': material(name),
                     'original_geometry_retained': index not in replacements,
                     'geometry_status': 'generated-candidate-bound-not-final-art' if index in replacements else 'original-reference-remains',
                     'material_status': 'candidate-not-full-room-approved' if material(name) else 'other-owner-or-nondrawn',
                     'moving_visibility_accepted': False, 'final_art_accepted': False})
    result = {'map': 'q3dm1', 'source_scope': 'private-demo-reference',
              'source_bsp_sha256': hashlib.sha256(data).hexdigest(),
              'surface_count': len(rows), 'batches': dict(collections.Counter(row['batch'] for row in rows)),
              'original_geometry_surface_count': sum(row['original_geometry_retained'] for row in rows),
              'full_map_complete': False, 'full_game_complete': False,
              'scene_sha256': hashlib.sha256(scene.read_bytes()).hexdigest() if scene else None,
              'note': 'Material candidates do not count as geometry remakes. Bound candidates are not full visibility or art acceptance. Flame ownership requires explicit handoff; existing original effects must not be credited as new.',
              'surfaces': rows}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'surfaces'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--scene', type=Path)
    args = parser.parse_args()
    inventory(args.reference, args.output, args.scene)
