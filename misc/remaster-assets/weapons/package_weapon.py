#!/usr/bin/env python3
"""Package a generated rigid IQM candidate; no reference-game data is copied."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from iqm_validate import read_iqm
from pipeline import Production, atomic, lock


def package(manifest, work, output):
    with lock(work):
        production = Production(manifest, work, None)
        production.require_artifact('image')
        production.require_artifact('shape')
        production.verify_processed()
        rigged = work / 'rigged'
        iqm = (rigged / 'iqm/model.iqm').read_bytes()
        model = read_iqm(iqm)
        config = json.loads((rigged / 'iqm-config.json').read_text())
        if config['attachments'] != ['tag_flash', 'tag_barrel']:
            raise ValueError('Rigid weapon requires explicit flash and barrel sockets')
        if len(model['frames']) != 1:
            raise ValueError('Weapon body must be a single rigid frame; animate the hands')
        shader = manifest['processing']['shader']
        directory = shader.rsplit('/', 1)[0]
        files = {
            directory + '/weapon.iqm': iqm,
            shader + '.tga': (work / 'processed/diffuse.tga').read_bytes(),
            'scripts/remaster_' + manifest['asset_id'].replace('-', '_') + '.shader': (
                shader + '\n{\n    {\n        stage diffuseMap\n        map ' + shader +
                '.tga\n        rgbGen lightingDiffuse\n    }\n}\n').encode(),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'w') as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(name, (2026, 9, 10, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        receipt = production.receipt()
        receipt['weapon_export'] = {
            'runtime_accepted': False,
            'material': 'diffuse-only candidate; normal/specular/emission not yet baked',
            'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
            'source_files': {str(p.relative_to(work)): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in [rigged / 'weapon.blend', rigged / 'iqm-config.json',
                                       rigged / 'iqm/source.json', rigged / 'iqm/animation-contract.json']},
            'package_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        }
        receipt_path = Path('assets/remaster/receipts') / (manifest['asset_id'] + '.json')
        atomic(receipt_path, json.dumps(receipt, indent=2).encode() + b'\n')
        print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    package(manifest, Path('assets/remaster/work') / manifest['asset_id'],
            Path('assets/remaster/runtime') / (manifest['asset_id'] + '-candidate.pk3'))
