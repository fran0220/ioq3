"""Derive companion surfaces while retaining every opaque MD3 surface byte."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from md3_static import FRAME, HEADER, read_md3, write_md3

SHADER = 'models/remaster/environment_fx/lamp_glow'


def append_glow(data, floor):
    original = read_md3(data)
    triangles = []
    quads = []
    for yaw in ([0, 90, 180, 270] if floor else [0]):
        width, low, high, depth = (8, 12, 82, 12.78125) if floor else (10, 15, 55, -4.078125)
        angle = math.radians(yaw)
        c, s = math.cos(angle), math.sin(angle)
        local = [(-width, depth, low), (width, depth, low), (width, depth, high), (-width, depth, high)]
        points = [(c*x-s*y, s*x+c*y, z) for x, y, z in local]
        normal = (-s, c, 0) if floor else (s, -c, 0)
        uvs = [(0, 1), (1, 1), (1, 0), (0, 0)]
        # Engine-native CW: geometric cross is opposite the outward normal.
        for indices in ([(0, 1, 2), (0, 2, 3)] if floor else [(0, 2, 1), (0, 3, 2)]):
            triangles.append([(points[i], uvs[i], normal) for i in indices])
        quads.append({'positions': points, 'uvs': uvs, 'normal': normal})
    companion = write_md3(triangles, SHADER)
    glow = read_md3(companion)
    header = list(HEADER.unpack_from(data))
    extra = companion[HEADER.size + FRAME.size:]
    header[6] += len(glow['surfaces'])
    header[-1] += len(extra)
    frame = list(FRAME.unpack_from(data, HEADER.size))
    for a in range(3):
        frame[a] = min(original['bounds'][a], glow['bounds'][a])
        frame[a+3] = max(original['bounds'][a+3], glow['bounds'][a+3])
        frame[a+6] = (frame[a] + frame[a+3]) / 2
    frame[9] = math.sqrt(sum(((frame[a+3]-frame[a])/2)**2 for a in range(3)))
    opaque = data[HEADER.size + FRAME.size:]
    result = HEADER.pack(*header) + FRAME.pack(*frame) + opaque + extra
    parsed = read_md3(result)
    assert result[HEADER.size + FRAME.size:len(data)] == opaque
    assert parsed['surfaces'][:-len(glow['surfaces'])] == original['surfaces']
    return result, {'source_model_sha256': hashlib.sha256(data).hexdigest(),
                    'derived_model_sha256': hashlib.sha256(result).hexdigest(),
                    'opaque_surface_bytes_identical': True, 'winding': 'Q3 CW',
                    'bounds': parsed['bounds'], 'quads': quads}


def derive(root, asset, floor):
    source_receipt = json.loads((root / f'assets/remaster/receipts/{asset}.json').read_text())
    source = root / 'assets/remaster/work' / asset / source_receipt['package']['path']
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_receipt['package']['sha256']:
        raise ValueError('Original paid package changed')
    fx = root / 'assets/remaster/runtime/effect-environment-lamp-v1-candidate.pk3'
    if hashlib.sha256(fx.read_bytes()).hexdigest() != '5b6e8030ca2a09936760b44d7b0ea51d312253e82521f9b9683d1d2c33b5f42b':
        raise ValueError('Unreviewed FX source')
    derived_id = asset.replace('-v1', '-cw-glow-v1')
    output = root / 'assets/remaster/work' / derived_id
    output.mkdir(exist_ok=True)
    with zipfile.ZipFile(source) as z:
        files = {name: z.read(name) for name in z.namelist()}
    model = next(name for name in files if name.endswith('.md3'))
    files[model], report = append_glow(files[model], floor)
    # Shared FX shader/texture are packaged once at scene level, not per model.
    package = output / f'{derived_id}.pk3'
    with zipfile.ZipFile(package, 'w') as z:
        for name, data in sorted(files.items()):
            z.writestr(zipfile.ZipInfo(name, (2026, 9, 11, 0, 0, 0)), data, compress_type=zipfile.ZIP_DEFLATED)
    receipt = {'asset_id': derived_id, 'source_asset': asset,
               'source_receipt_sha256': hashlib.sha256((root / f'assets/remaster/receipts/{asset}.json').read_bytes()).hexdigest(),
               'fx_source_package_sha256': hashlib.sha256(fx.read_bytes()).hexdigest(),
               'derivation': report, 'new_paid_submissions': 0, 'runtime_accepted': False,
               'package': {'path': package.name, 'sha256': hashlib.sha256(package.read_bytes()).hexdigest(), 'bytes': package.stat().st_size}}
    (root / f'assets/remaster/receipts/{derived_id}.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(derived_id, receipt['package']['sha256'])


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[3]
    derive(root, 'environment-floor-lantern-v1', True)
    derive(root, 'environment-wall-lantern-v1', False)
