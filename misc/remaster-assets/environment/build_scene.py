"""Package measured environmental instances; no source BSP/AAS or extracted images."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

from package import material
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from md3_static import read_md3


def fit(bounds, target, margin):
    if not 0 < margin < 1:
        raise ValueError('Strict envelope margin required')
    spans = [bounds[3 + a] - bounds[a] for a in range(3)]
    if min(spans) <= 0:
        raise ValueError('Nonvolumetric replacement')
    scale = margin * min((target[1][a] - target[0][a]) / spans[a] for a in range(3))
    if scale <= 0:
        raise ValueError('Cannot replace zero-thickness source with solid geometry')
    origin = [(target[0][a] + target[1][a] - scale * (bounds[a] + bounds[a + 3])) / 2 for a in range(3)]
    actual = [[origin[a] + scale * bounds[c * 3 + a] for a in range(3)] for c in range(2)]
    assert all(target[0][a] < actual[0][a] < actual[1][a] < target[1][a] for a in range(3))
    return origin, scale, actual


def build(root, spec_path, measurements_path, output):
    spec = json.loads(spec_path.read_text())
    measurements = {s['surface_index']: s for s in json.loads(measurements_path.read_text())[spec['map']]}
    placement = json.loads((root / spec['existing_crest_placement']).read_text())
    used = {s['surface'] for s in placement['replacements']}
    with zipfile.ZipFile(root / 'assets/remaster/environment/environment-wall-crest-q3dm1-v1.pk3') as archive:
        files = {name: archive.read(name) for name in archive.namelist() if name != 'maps/q3dm1.remaster.json'}
    reports = []
    for asset in spec['assets']:
        if asset['yaw'] != 0:
            raise ValueError('Only measured unrotated instances are supported in this batch')
        receipt = json.loads((root / f"assets/remaster/receipts/{asset['asset_id']}.json").read_text())
        source = root / 'assets/remaster/work' / asset['asset_id'] / receipt['package']['path']
        if hashlib.sha256(source.read_bytes()).hexdigest() != receipt['package']['sha256']:
            raise ValueError('Source receipt hash mismatch')
        with zipfile.ZipFile(source) as archive:
            additions = {name: archive.read(name) for name in archive.namelist()}
        if any(not name.startswith(('models/remaster/', 'scripts/remaster_')) for name in additions):
            raise ValueError('Unexpected runtime source')
        if files.keys() & additions.keys():
            raise ValueError('Asset path collision')
        files.update(additions)
        model = read_md3(files[asset['model']])
        for group in asset['groups']:
            if len(set(group)) != len(group) or used.intersection(group):
                raise ValueError('Overlapping replacement group')
            used.update(group)
            members = [{'surface': index, 'shader': 'textures/remaster_environment/' + material(measurements[index]['shader']),
                        'bounds': [measurements[index]['minimum'], measurements[index]['maximum']]} for index in group]
            target = [[min(m['bounds'][0][a] for m in members) for a in range(3)],
                      [max(m['bounds'][1][a] for m in members) for a in range(3)]]
            origin, scale, actual = fit(model['bounds'], target, asset['fit_margin'])
            entry = {'model': asset['model'], 'origin': origin, 'angles': [0, 0, 0], 'scale': scale}
            entry.update(members[0] if len(members) == 1 else {'surfaces': members})
            placement['replacements'].append(entry)
            reports.append({'asset_id': asset['asset_id'], 'surfaces': group, 'world_bounds': actual,
                            'target_union': target, 'source_package_sha256': receipt['package']['sha256'],
                            'runtime_accepted': False})
    files['maps/q3dm1.remaster.json'] = (json.dumps(placement, indent=2) + '\n').encode()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(zipfile.ZipInfo(name, (2026, 9, 11, 0, 0, 0)), data, compress_type=zipfile.ZIP_DEFLATED)
    report = {'package_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'source_spec_sha256': hashlib.sha256(spec_path.read_bytes()).hexdigest(),
              'source_measurements_sha256': hashlib.sha256(measurements_path.read_bytes()).hexdigest(),
              'instances': reports, 'full_map_complete': False}
    output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'instances': len(placement['replacements']), 'sha256': report['package_sha256']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('spec', type=Path)
    parser.add_argument('measurements', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    build(Path(__file__).resolve().parents[3], args.spec, args.measurements, args.output)
