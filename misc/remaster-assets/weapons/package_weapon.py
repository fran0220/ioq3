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


def package(manifest, work, output, rotating=False, hand_slots=('rocket',)):
    with lock(work):
        production = Production(manifest, work, None)
        production.require_artifact('image')
        production.require_artifact('shape')
        production.verify_processed()
        rigged = work / ('split' if rotating else 'rigged')
        iqm = (rigged / 'iqm/model.iqm').read_bytes()
        model = read_iqm(iqm)
        config = json.loads((rigged / 'iqm-config.json').read_text())
        hands = manifest['classification'] == 'remaster-first-person-arm-production-candidate'
        attachments = ['tag_weapon'] if hands else ['tag_flash', 'tag_barrel']
        if config['attachments'] != attachments:
            raise ValueError('Missing explicit weapon attachment contract')
        if len(model['frames']) != (15 if hands else 1):
            raise ValueError('Hands require 15 mapped frames; rigid weapons require one')
        shader = manifest['processing']['shader']
        directory = shader.rsplit('/', 1)[0]
        model_path = 'models/remaster/weapons/rocket/hands.iqm' if hands else directory + '/weapon.iqm'
        if any(mesh['material'] != shader for mesh in model['meshes']):
            raise ValueError('IQM shader does not match packaged material')
        if not set(attachments).issubset(joint['name'] for joint in model['joints']):
            raise ValueError('IQM bytes do not contain the declared sockets')
        files = {
            model_path: iqm,
            shader + '.tga': (work / 'processed/diffuse.tga').read_bytes(),
            'scripts/remaster_' + manifest['asset_id'].replace('-', '_') + '.shader': (
                shader + '\n{\n    {\n        stage diffuseMap\n        map ' + shader +
                '.tga\n        rgbGen lightingDiffuse\n    }\n}\n').encode(),
        }
        sources = [rigged / ('hands.blend' if hands else 'weapon.blend'), rigged / 'iqm-config.json',
                   rigged / 'iqm/source.json', rigged / 'iqm/animation-contract.json']
        if hands:
            for name in hand_slots:
                if name not in ('gauntlet', 'machinegun', 'shotgun', 'grenade', 'rocket',
                                'lightning', 'rail', 'plasma', 'bfg'):
                    raise ValueError('Unknown base Q3 weapon hand slot')
                files['models/remaster/weapons/' + name + '/hands.iqm'] = iqm
        if rotating:
            barrel = (rigged / 'barrel/iqm/model.iqm').read_bytes()
            decoded = read_iqm(barrel)
            if len(decoded['frames']) != 1 or any(mesh['material'] != shader for mesh in decoded['meshes']):
                raise ValueError('Barrel must be rigid and use the generated body material')
            files[directory + '/barrel.iqm'] = barrel
            sources += [rigged / 'split-config.json', rigged / 'barrel/weapon.blend',
                        rigged / 'barrel/iqm-config.json', rigged / 'barrel/iqm/source.json',
                        rigged / 'barrel/iqm/animation-contract.json']
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'w') as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(name, (2026, 9, 10, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        receipt = production.receipt()
        receipt['weapon_export'] = {
            'runtime_accepted': False,
            'rotating_barrel': rotating,
            'hand_slots': list(hand_slots) if hands else [],
            'material': 'diffuse-only candidate; normal/specular/emission not yet baked',
            'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
            'source_files': {str(p.relative_to(work)): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sources},
            'export_scripts': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                               [Path(__file__), Path(__file__).with_name('rig_hands.py' if hands else 'rig_weapon.py'),
                                Path(__file__).parent.parent / 'blender_iqm.py', Path(__file__).parent.parent / 'iqm_export.py']
                               + ([Path(__file__).with_name('rig_machinegun.py')] if rotating else [])},
            'package_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        }
        receipt_path = Path('assets/remaster/receipts') / (manifest['asset_id'] + '.json')
        atomic(receipt_path, json.dumps(receipt, indent=2).encode() + b'\n')
        print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--rotating-barrel', action='store_true')
    parser.add_argument('--hand-slots', nargs='+', default=['rocket'])
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    package(manifest, Path('assets/remaster/work') / manifest['asset_id'],
            Path('assets/remaster/runtime') / (manifest['asset_id'] + '-candidate.pk3'),
            args.rotating_barrel, args.hand_slots)
