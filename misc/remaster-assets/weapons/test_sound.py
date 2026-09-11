"""Paid SFX requests cannot be replayed after ambiguous transport failure."""
import contextlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sound


class SoundTests(unittest.TestCase):
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
