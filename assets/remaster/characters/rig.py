"""Durably journal one Meshy rig operation; never retry an unknown create.

Uses the existing Gateway identity/client and GLB validation. Native Meshy bodies
do not contain a model field, and its ambiguous-submission semantics differ from
Hunyuan's durable outbox. Status/download are read-only after task acceptance.
"""
import argparse
import base64
import json
from pathlib import Path
import sys
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'misc/remaster-assets'))
from pipeline import Gateway, atomic, check_glb, digest, encoded, lock, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['create', 'status', 'download', 'billing', 'receipt'])
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--approved-sha256')
    parser.add_argument('--action-id', type=int)
    args = parser.parse_args()
    work = args.work.resolve()
    prefix = 'rig' if args.action_id is None else 'motion-' + str(args.action_id)
    model = 'meshy-rigging' if args.action_id is None else 'meshy-animation'
    with lock(work):
        path = work / (prefix + '-state.json')
        state = json.loads(path.read_text()) if path.exists() else None
        if args.command == 'receipt':
            if not state:
                raise ValueError('Restore private state before publishing receipt')
            fields = ('operation_id', 'task_id', 'request_id', 'request_sha256',
                      'response_sha256', 'source_sha256', 'generator_identity',
                      'model', 'action_id', 'created_at', 'status', 'http_status',
                      'cost', 'artifacts')
            receipt = {key: state.get(key) for key in fields}
            receipt.update(asset_id=work.name, runtime_accepted=False)
            save(ROOT / 'assets/remaster/receipts' / (work.name + '-' + prefix + '.json'), receipt)
            return
        gateway = Gateway(ROOT / '.origingame-deploy.json', credential='default')
        if state is None and (ROOT / 'assets/remaster/receipts' / (work.name + '-' + prefix + '.json')).exists():
            raise ValueError('Committed rig receipt exists; restore private state, do not regenerate')
        if args.command == 'create':
            source = (work / ('generated.glb' if args.action_id is None else 'rigged.glb')).read_bytes()
            if digest(source) != args.approved_sha256:
                raise ValueError('Explicit inspected source GLB hash required')
            check_glb(source)
            if args.action_id is None:
                endpoint = '/meshy/openapi/v1/rigging'
                payload = {'model_url': 'data:model/gltf-binary;base64,' + base64.b64encode(source).decode(),
                           'height_meters': 1.8}
            else:
                rig = json.loads((work / 'rig-state.json').read_text())
                if rig['status'] != 'SUCCESS' or rig['credential_scope'] != gateway.scope or args.action_id < 0:
                    raise ValueError('Successful same-identity rig and valid action ID required')
                endpoint = '/meshy/openapi/v1/animations'
                payload = {'rig_task_id': rig['task_id'], 'action_id': args.action_id}
            body = encoded(payload)
            if state:
                if state['request_sha256'] != digest(body) or state['credential_scope'] != gateway.scope:
                    raise ValueError('Immutable rig input/credential changed')
                if state.get('task_id'):
                    print('Already submitted:', state['task_id'])
                    return
                raise ValueError('Prior rig operation exists without task ID; reconcile, never blindly resubmit')
            account = gateway.account()['account']
            state = {'operation_id': str(uuid.uuid4()), 'request_sha256': digest(body),
                     'source_sha256': digest(source), 'credential_scope': gateway.scope,
                     'generator_identity': account, 'model': model, 'action_id': args.action_id,
                     'created_at': int(time.time()), 'status': 'submission_unknown',
                     'cost': {'status': 'unreconciled', 'actual_usd': None}}
            atomic(work / (prefix + '-request.json'), body)
            save(path, state)
            status, headers, raw = gateway.request('POST', endpoint, body, state['operation_id'])
            atomic(work / (prefix + '-response.json'), raw)
            headers = {k.lower(): v for k,v in headers.items()}
            state.update(http_status=status, response_sha256=digest(raw),
                         request_id=headers.get('x-oneapi-request-id') or headers.get('x-request-id'))
            if status not in (200, 202):
                state['status'] = 'http_error'
                save(path, state)
                raise ValueError('Rig HTTP ' + str(status) + '; retained privately, no retry')
            task = json.loads(raw).get('result')
            if not isinstance(task, str) or not task or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in task):
                save(path, state)
                raise ValueError('Unrecognized rig result; inspect saved response')
            state.update(task_id=task, status='SUBMITTED')
            save(path, state)
            print(task)
            return
        if not state or state['credential_scope'] != gateway.scope:
            raise ValueError('Restore original rig state/credential')
        if args.command == 'billing':
            status, _, raw = gateway.request('GET', '/api/log/token')
            if status != 200:
                raise ValueError('Billing unavailable')
            rows = [r for r in json.loads(raw).get('data', [])
                    if r.get('request_id') == state.get('request_id') and r.get('model_name') == model and r.get('type') in (2,6)]
            if len([r for r in rows if r['type'] == 2]) == 1 and len([r for r in rows if r['type'] == 6]) <= 1:
                quota = sum(r['quota'] * (1 if r['type'] == 2 else -1) for r in rows)
                state['cost'] = {'status': 'matched_request_id', 'quota': quota, 'actual_usd': quota / 500000}
                save(path, state)
            print(json.dumps(state['cost']))
            return
        status, _, raw = gateway.request('GET', '/meshy/tasks/' + state['task_id'])
        if status != 200:
            raise ValueError('Rig status HTTP ' + str(status))
        atomic(work / (prefix + '-status.json'), raw)
        result = json.loads(raw)
        state['status'] = result['status']
        save(path, state)
        if args.command == 'status':
            print(json.dumps({k: result.get(k) for k in ('task_id','status','progress','fail_reason')}))
            return
        if state['status'] != 'SUCCESS':
            raise ValueError('Rig not successful; no new submission')
        data = result['data']
        if isinstance(data, str):
            data = json.loads(data)
        artifacts = ({'rigged': data['result']['rigged_character_glb_url']} if args.action_id is None
                     else {prefix: data['result']['animation_glb_url']})
        basic = data['result'].get('basic_animations', {})
        for name in ('walking', 'running'):
            if basic.get(name + '_glb_url'):
                artifacts[name] = basic[name + '_glb_url']
        state.setdefault('artifacts', {})
        for name, url in artifacts.items():
            target = work / (name + '.glb')
            prior = state['artifacts'].get(name) or (state.get('artifact') if name == 'rigged' else None)
            if prior and target.exists():
                if digest(target.read_bytes()) != prior['sha256']:
                    raise ValueError('Downloaded rig artifact changed')
                state['artifacts'][name] = prior
                continue
            if not url.startswith('https://'):
                raise ValueError('Expected HTTPS rig artifact')
            # No Gateway bearer is sent to the provider/CDN.
            with urllib.request.urlopen(url, timeout=240) as response:
                content = response.read(64 * 1024**2 + 1)
            if len(content) > 64 * 1024**2:
                raise ValueError('Rig artifact exceeds 64MiB')
            check_glb(content)
            atomic(target, content)
            state['artifacts'][name] = {'path': target.name, 'bytes': len(content), 'sha256': digest(content)}
            save(path, state)
        save(path, state)
        print(json.dumps(state['artifacts']))


if __name__ == '__main__':
    main()
