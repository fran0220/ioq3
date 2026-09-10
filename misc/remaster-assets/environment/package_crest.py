"""Combine hash-pinned generated model and measured replacement configuration."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from md3_static import read_md3


def package(source, receipt_path, placement_path, output):
    receipt = json.loads(receipt_path.read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest() != receipt['package']['sha256']:
        raise ValueError('Model package differs from production receipt')
    placement = json.loads(placement_path.read_text())
    entry, = placement['replacements']
    if placement['schemaVersion'] != 1 or placement['map'] != 'q3dm1' or entry['surface'] != 2050:
        raise ValueError('Unreviewed placement target')
    if entry['angles'] != [0, 0, 0] or not 0 < entry['scale'] <= 1:
        raise ValueError('This engine-reviewed placement expects zero yaw and uniform scale')
    expected = {'models/remaster/environment_wall_crest.md3',
                'models/remaster/environment_wall_crest.tga',
                'scripts/remaster_environment_wall_crest_v1.shader'}
    with zipfile.ZipFile(source) as archive:
        if set(archive.namelist()) != expected or len(archive.namelist()) != 3:
            raise ValueError('Unexpected production package entries')
        files = {name: archive.read(name) for name in archive.namelist()}
    model = read_md3(files[entry['model']])
    points = [p for surface in model['surfaces'] for p in surface['positions']]
    # Actual engine front-view acceptance fixes AnglesToAxis(0,0,0).
    transformed = [[entry['origin'][a] + p[a] * entry['scale']
                    for a in range(3)] for p in points]
    bounds = [[min(p[a] for p in transformed) for a in range(3)],
              [max(p[a] for p in transformed) for a in range(3)]]
    for a in range(3):
        if bounds[0][a] < entry['bounds'][0][a] or bounds[1][a] > entry['bounds'][1][a]:
            raise ValueError('Replacement protrudes beyond original visual envelope')
    files['maps/q3dm1.remaster.json'] = placement_path.read_bytes()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            archive.writestr(zipfile.ZipInfo(name, (2026, 9, 10, 0, 0, 0)), content,
                             compress_type=zipfile.ZIP_DEFLATED)
    report = {'source_package_sha256': receipt['package']['sha256'],
              'placement_sha256': hashlib.sha256(placement_path.read_bytes()).hexdigest(),
              'runtime_package_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'local_bounds': model['bounds'], 'world_bounds': bounds,
              'inside_original_bounds': True, 'runtime_accepted': False,
              'content': sorted(files), 'contains_original_bsp_or_aas': False}
    output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    package(*(Path(p) for p in sys.argv[1:]))
