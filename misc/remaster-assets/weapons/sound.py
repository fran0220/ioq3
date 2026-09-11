"""Produce one original weapon SFX, retaining ambiguous requests without retry.

CLI: sound.py effect-MANIFEST.json [--billing]
Uses the existing private ledger/public receipt projection. Unlike Hunyuan,
ElevenLabs SFX has no confirmed replay contract: never retry a submitted stage.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import Gateway, Production, atomic, digest, encoded, lock


def run(manifest, billing=False):
    work = Path('assets/remaster/work') / manifest['asset_id']
    gateway = Gateway(Path('.origingame-deploy.json'), credential='default')
    with lock(work):
        production = Production(manifest, work, gateway)
        if billing:
            production.billing()
        elif 'sound' not in production.state['stages']:
            gateway.account()
            body = encoded({'model_id': 'eleven_text_to_sound_v2',
                            'text': manifest['prompt'], 'duration_seconds': manifest['duration_seconds'],
                            'loop': manifest.get('loop', False)})
            record = {'operation_id': str(uuid.uuid4()), 'model': 'eleven_text_to_sound_v2',
                      'status': 'submission_unknown', 'submissions': 1,
                      'request_sha256': digest(body), 'credential_scope': gateway.scope,
                      'generator_identity': gateway.account_info, 'created_at': int(time.time()),
                      'cost': {'status': 'unreconciled', 'actual_usd': None}}
            production.state['stages']['sound'] = record
            atomic(work / 'sound-request.json', body)
            production.save()
            status, headers, data = gateway.request('POST', '/v1/sound-generation', body)
            atomic(work / 'sound-response.bin', data)
            lower = {k.lower(): v for k, v in headers.items()}
            record.update(http_status=status, response_sha256=digest(data),
                          request_id=lower.get('x-request-id'), content_type=lower.get('content-type'))
            record['status'] = 'response_received' if status == 200 else 'http_error'
            production.save()
        record = production.state['stages']['sound']
        if not billing and record['status'] == 'response_received':
            source = work / 'sound-response.bin'
            if digest(source.read_bytes()) != record['response_sha256']:
                raise ValueError('Sound response drift')
            output = work / 'sound.wav'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-ac', '1',
                            '-ar', '22050', '-c:a', 'pcm_s16le', str(output)], check=True)
            record.update(status='downloaded', artifact=production.artifact(output))
            production.save()
        receipt = Path('assets/remaster/receipts') / (manifest['asset_id'] + '.json')
        atomic(receipt, encoded(production.receipt()) + b'\n')
        print(record['status'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--billing', action='store_true')
    args = parser.parse_args()
    run(json.loads(args.manifest.read_text()), args.billing)
