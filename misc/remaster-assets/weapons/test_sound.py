"""Paid SFX requests cannot be replayed after ambiguous transport failure."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave
import zipfile

import sound


class SoundTests(unittest.TestCase):
    def test_package_preserves_pcm_and_rejects_source_drift(self):
        manifest = {'asset_id': 'effect-test-only', 'classification': 'test-only',
                    'runtime_target': 'sound/remaster/test/fire.wav'}
        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            work = Path('assets/remaster/work/effect-test-only')
            work.mkdir(parents=True)
            data = io.BytesIO()
            with wave.open(data, 'wb') as audio:
                audio.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
                audio.writeframes(b'\x01\x02\x03\x04\x05\x06')
            source = work / 'sound.wav'
            source.write_bytes(data.getvalue())
            production = sound.Production(manifest, work, None)
            production.state['stages']['sound'] = {'status': 'downloaded',
                'artifact': production.artifact(source)}
            production.save()
            with patch.object(sound, 'Gateway', side_effect=AssertionError('offline only')):
                output = sound.package(manifest)
                first = output.read_bytes()
                self.assertEqual(sound.package(manifest).read_bytes(), first)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.namelist(), [manifest['runtime_target']])
                self.assertEqual(archive.read(manifest['runtime_target']), data.getvalue())
            receipt = json.loads(Path('assets/remaster/receipts/effect-test-only.json').read_text())
            self.assertEqual(receipt['sound_export']['frames'], 3)
            self.assertFalse(receipt['sound_export']['runtime_accepted'])
            source.write_bytes(data.getvalue()[:-2])
            with self.assertRaises(ValueError):
                sound.package(manifest)
            self.assertEqual(output.read_bytes(), first)
            for target in ['sound/remaster/../original.wav', '/sound/remaster/fire.wav',
                           'sound/remaster//fire.wav', 'sound/weapons/fire.wav']:
                with self.assertRaisesRegex(ValueError, 'canonical'):
                    sound.package({**manifest, 'runtime_target': target})

    def test_ambiguous_request_is_durable_and_not_resubmitted(self):
        manifest = {'asset_id': 'effect-test-only', 'classification': 'test-only',
                    'prompt': 'test input never sent to network', 'duration_seconds': .7}
        with tempfile.TemporaryDirectory() as directory, patch.object(sound, 'Gateway') as factory:
            gateway = factory.return_value
            gateway.scope = 'test-scope'
            gateway.account_info = {'id': 'test-only'}
            gateway.request.side_effect = OSError('simulated ambiguous response')
            previous = Path.cwd()
            try:
                os.chdir(directory)
                with self.assertRaises(OSError):
                    sound.run(manifest)
                state_path = Path('assets/remaster/work/effect-test-only/state.json')
                first = state_path.read_bytes()
                state = json.loads(first)['stages']['sound']
                self.assertEqual(state['status'], 'submission_unknown')
                self.assertEqual(state['submissions'], 1)
                with contextlib.redirect_stdout(None):
                    sound.run(manifest)
                self.assertEqual(gateway.request.call_count, 1)
                self.assertEqual(state_path.read_bytes(), first)
                self.assertTrue(Path('assets/remaster/receipts/effect-test-only.json').exists())
                with self.assertRaisesRegex(ValueError, 'Manifest changed'):
                    sound.run({**manifest, 'prompt': 'changed input'})
                self.assertEqual(gateway.request.call_count, 1)
            finally:
                os.chdir(previous)


if __name__ == '__main__':
    unittest.main()
