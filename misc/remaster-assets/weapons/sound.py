"""Produce one original weapon SFX, retaining ambiguous requests without retry.

CLI: sound.py effect-MANIFEST.json [--billing]
Uses the existing private ledger/public receipt projection. Unlike Hunyuan,
ElevenLabs SFX has no confirmed replay contract: never retry a submitted stage.
"""
import argparse
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time
import uuid
import wave
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import Gateway, Production, atomic, digest, encoded, lock


def package(manifest):
    """Package already-reviewed PCM bytes offline, without another paid call."""
    target = manifest['runtime_target']
    path = PurePosixPath(target)
    if (not target.startswith('sound/remaster/') or path.suffix != '.wav'
            or '..' in path.parts or str(path) != target or '\\' in target):
        raise ValueError('Expected a canonical remaster WAV path')
    work = Path('assets/remaster/work') / manifest['asset_id']
    with lock(work):
        production = Production(manifest, work, None)
        data = production.require_artifact('sound').read_bytes()
        with wave.open(io.BytesIO(data), 'rb') as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getcomptype()) != (1, 2, 22050, 'NONE'):
                raise ValueError('Expected mono PCM16 22050Hz')
            frames = audio.getnframes()
            if frames <= 0 or len(audio.readframes(frames)) != frames * 2:
                raise ValueError('Empty or truncated sound')
        output = Path('assets/remaster/runtime') / (manifest['asset_id'] + '-candidate.pk3')
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            info = zipfile.ZipInfo(target, (2026, 9, 10, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
        atomic(output, buffer.getvalue())
        receipt = production.receipt()
        receipt['sound_export'] = {
            'runtime_accepted': False,
            'files': {target: digest(data)},
            'package_sha256': digest(buffer.getvalue()),
            'frames': frames, 'sample_rate': 22050, 'channels': 1, 'sample_bits': 16,
            'script_sha256': digest(Path(__file__).read_bytes()),
        }
        atomic(Path('assets/remaster/receipts') / (manifest['asset_id'] + '.json'), encoded(receipt) + b'\n')
        return output


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
    parser.add_argument('--package', action='store_true', help='Offline package of existing reviewed sound')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if args.package:
        if args.billing:
            parser.error('--package and --billing are separate operations')
        print(package(manifest))
    else:
        run(manifest, args.billing)
