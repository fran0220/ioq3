"""Package an audited static derivative of the approved closed Sarge master."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from md3_static import read_md3


def topology(model):
    edges = Counter()
    for surface in model['surfaces']:
        for triangle in surface['triangles']:
            points = [tuple(round(c * 64) for c in surface['positions'][i]) for i in triangle]
            for a, b in zip(points, points[1:] + points[:1]):
                edges[tuple(sorted((a, b)))] += 1
    return {'boundary_edges': sum(n == 1 for n in edges.values()),
            'nonmanifold_edges': sum(n > 2 for n in edges.values()),
            'measurement': 'Exact decoded MD3 1/64 coordinate lattice; geometric seams identified, UVs unchanged'}


def package(work, receipt):
    derivation = json.loads((work / 'derivation.json').read_text())
    for name, expected in derivation['files'].items():
        if sha256((work / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Derivative source hash mismatch')
    processed = work / 'processed'
    report = json.loads((processed / 'geometry-report.json').read_text())
    data = (processed / 'model.md3').read_bytes()
    if (report['source_sha256'] != derivation['files']['sculpture.glb'] or
            sha256(data).hexdigest() != report['md3_sha256'] or
            report['winding']['runtime'] != 'Q3 CW'):
        raise ValueError('Processing provenance mismatch')
    model = read_md3(data)
    audit = topology(model)
    if audit['boundary_edges'] or audit['nonmanifold_edges']:
        raise ValueError(f'Sculpture is not closed: {audit}')
    shader = 'models/remaster/environment_sarge_statue'
    if any(s['shader'] != shader for s in model['surfaces']):
        raise ValueError('Unexpected statue shader')
    files = {shader + '.md3': data, shader + '.tga': (processed / 'diffuse.tga').read_bytes(),
             'scripts/remaster_environment_sarge_statue.shader': (processed / 'remaster.shader').read_bytes()}
    target = work / (work.name + '.pk3')
    with zipfile.ZipFile(target, 'w') as z:
        for name, value in sorted(files.items()):
            z.writestr(zipfile.ZipInfo(name, (2026, 9, 11, 0, 0, 0)), value, compress_type=zipfile.ZIP_DEFLATED)
    result = {'asset_id': work.name, 'derivation': derivation, 'processing': report,
              'decoded_topology': audit, 'new_paid_submissions': 0, 'runtime_accepted': False,
              'files': {name: sha256(value).hexdigest() for name, value in files.items()},
              'package': {'path': target.name, 'sha256': sha256(target.read_bytes()).hexdigest(),
                          'bytes': target.stat().st_size}}
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'package': result['package'], 'topology': audit}))


if __name__ == '__main__':
    package(Path(sys.argv[1]), Path(sys.argv[2]))
