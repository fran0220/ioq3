"""Local content-addressed source AND private recovery snapshot. No network.

Store outside Git, protect like credentials, back up externally separately.
Restore never overwrites differing files and never triggers generation.
"""
import argparse
import json
import os
from pathlib import Path
import re

from inventory import sha
from pipeline import atomic, lock


def contained(root, name):
    if Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('Unsafe archive path')
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError('Archive symlink/path escape')
    return path


def blob(store, digest):
    if not re.fullmatch('[0-9a-f]{64}', digest):
        raise ValueError('Invalid blob SHA256')
    return contained(store, 'blobs/' + digest)


def snapshot(work, receipt, store):
    store.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(store, 0o700)
    refs = []
    for stage in receipt.get('stages', {}).values():
        if stage.get('artifact'):
            refs.append(stage['artifact'])
    refs.extend((receipt.get('processing') or {}).get('files', []))
    if receipt.get('package'):
        refs.append(receipt['package'])
    records = {}
    with lock(work):
        state = json.loads((work / 'state.json').read_text())
        if state['asset_id'] != receipt['asset_id'] or state['manifest_sha256'] != receipt['manifest_sha256']:
            raise ValueError('Receipt does not match recovery state')
        for key, stage in receipt['stages'].items():
            if any(stage.get(field) != state['stages'][key].get(field) for field in ('operation_id', 'task_id', 'request_id', 'request_sha256', 'status', 'submissions')):
                raise ValueError('Stale receipt stage; export current receipt first')
        for ref in refs:
            data = contained(work, ref['path']).read_bytes()
            if sha(data) != ref['sha256'] or len(data) != ref['bytes']:
                raise ValueError('Source hash/size mismatch: ' + ref['path'])
            records[ref['path']] = {**ref, 'private': False}
        # Requests/responses may contain transient signed URLs or base64 source.
        # Preserve them to resume a paid operation, never expose in public manifest.
        for name in ('state.json', 'image-request.json', 'image-response.json', 'shape-request.json', 'shape-response.json', 'process-config.json'):
            path = contained(work, name)
            if path.exists():
                data = path.read_bytes()
                records[name] = {'path': name, 'sha256': sha(data), 'bytes': len(data), 'private': True}
        for name, ref in records.items():
            data = contained(work, name).read_bytes()
            if sha(data) != ref['sha256']:
                raise ValueError('Source changed during snapshot')
            target = blob(store, ref['sha256'])
            if target.exists() and sha(target.read_bytes()) != ref['sha256']:
                raise ValueError('Corrupt existing archive blob')
            if not target.exists():
                atomic(target, data)
        manifest = {'schema_version': 1, 'asset_id': receipt['asset_id'], 'receipt_sha256': sha(json.dumps(receipt, sort_keys=True).encode()),
                    'files': sorted(records.values(), key=lambda r: r['path']),
                    'private_recovery_included': True, 'external_backup_verified': False,
                    'regeneration_allowed': False}
        data = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
        destination = contained(store, 'snapshots/' + sha(data) + '.json')
        atomic(destination, data)
    return destination


def verify(store, manifest):
    names = set()
    for ref in manifest['files']:
        contained(Path('/tmp/archive-validation'), ref['path'])
        if ref['path'] in names:
            raise ValueError('Duplicate snapshot target')
        names.add(ref['path'])
        data = blob(store, ref['sha256']).read_bytes()
        if sha(data) != ref['sha256'] or len(data) != ref['bytes']:
            raise ValueError('Corrupt or missing archive blob')
    return {'asset_id': manifest['asset_id'], 'verified_files': len(names),
            'private_recovery_included': manifest['private_recovery_included'],
            'external_backup_verified': False, 'regeneration_allowed': False}


def restore(store, manifest, work):
    verify(store, manifest)
    with lock(work):
        # Preflight all collisions before writing anything; repeated restores are safe.
        for ref in manifest['files']:
            path = contained(work, ref['path'])
            if path.exists() and sha(path.read_bytes()) != ref['sha256']:
                raise ValueError('Refusing to replace changed recovery file: ' + ref['path'])
        for ref in manifest['files']:
            path = contained(work, ref['path'])
            if not path.exists():
                atomic(path, blob(store, ref['sha256']).read_bytes())
    return verify(store, manifest)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['snapshot', 'verify', 'restore'])
    p.add_argument('--store', required=True, type=Path)
    p.add_argument('--work', type=Path)
    p.add_argument('--receipt', type=Path)
    p.add_argument('--snapshot', type=Path)
    a = p.parse_args()
    if a.command == 'snapshot':
        if not a.work or not a.receipt:
            p.error('snapshot requires --work and --receipt')
        result = {'snapshot': str(snapshot(a.work, json.loads(a.receipt.read_text()), a.store))}
    else:
        if not a.snapshot or (a.command == 'restore' and not a.work):
            p.error('verify/restore require --snapshot; restore also requires --work')
        manifest = json.loads(a.snapshot.read_text())
        result = restore(a.store, manifest, a.work) if a.command == 'restore' else verify(a.store, manifest)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
