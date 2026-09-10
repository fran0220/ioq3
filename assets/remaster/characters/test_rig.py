"""Offline paid-operation recovery tests. Header-only GLB is TEST ONLY input."""
import contextlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import rig


class FakeGateway:
    scope = 'test-credential'
    calls = 0
    timeout = False

    def __init__(self, *args, **kwargs):
        pass

    def account(self):
        return {'account': {'id': 1, 'username': 'TEST ONLY'}}

    def request(self, method, path, body=None, operation=None):
        self.__class__.calls += 1
        if self.timeout:
            raise TimeoutError('TEST ONLY ambiguous transport')
        return 202, {'x-request-id':'test-request'}, b'{"result":"test-task"}'


class RigRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.work = self.root / 'character-test'
        self.work.mkdir()
        payload = b'{"meshes":[{}]}'
        payload += b' ' * (-len(payload) % 4)
        self.glb = struct.pack('<4sIIII',b'glTF',2,20+len(payload),len(payload),0x4e4f534a) + payload
        (self.work / 'generated.glb').write_bytes(self.glb)
        FakeGateway.calls = 0
        FakeGateway.timeout = False

    def run_create(self, sha=None):
        argv = ['rig.py','create','--work',str(self.work),'--approved-sha256',sha or rig.digest(self.glb)]
        with patch.object(rig,'Gateway',FakeGateway), patch.object(rig,'ROOT',self.root), patch('sys.argv',argv), contextlib.redirect_stdout(io.StringIO()):
            rig.main()

    def test_unknown_submission_durable_and_never_retried(self):
        FakeGateway.timeout = True
        with self.assertRaises(TimeoutError):
            self.run_create()
        self.assertEqual(json.loads((self.work/'rig-state.json').read_text())['status'],'submission_unknown')
        FakeGateway.timeout = False
        with self.assertRaisesRegex(ValueError,'reconcile'):
            self.run_create()
        self.assertEqual(FakeGateway.calls,1)

    def test_successful_repeat_is_not_another_paid_request(self):
        self.run_create()
        self.run_create()
        self.assertEqual(FakeGateway.calls,1)
        self.assertEqual(json.loads((self.work/'rig-state.json').read_text())['task_id'],'test-task')

    def test_receipt_is_offline_and_does_not_export_private_state(self):
        self.run_create()
        state_path = self.work/'rig-state.json'
        state = json.loads(state_path.read_text())
        state['private_response'] = 'TEST SECRET MUST NOT EXPORT'
        state_path.write_text(json.dumps(state))
        argv = ['rig.py','receipt','--work',str(self.work)]
        with patch.object(rig,'Gateway',side_effect=AssertionError('offline only')), patch.object(rig,'ROOT',self.root), patch('sys.argv',argv):
            rig.main()
        receipt = json.loads((self.root/'assets/remaster/receipts/character-test-rig.json').read_text())
        self.assertEqual(receipt['task_id'],'test-task')
        self.assertFalse(receipt['runtime_accepted'])
        self.assertNotIn('credential_scope',receipt)
        self.assertNotIn('private_response',receipt)
        self.assertEqual(json.loads(state_path.read_text()),state)

    def test_review_hash_and_missing_state_receipt_fail_before_post(self):
        with self.assertRaisesRegex(ValueError,'inspected'):
            self.run_create('0'*64)
        receipts = self.root/'assets/remaster/receipts'
        receipts.mkdir(parents=True)
        (receipts/'character-test-rig.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'restore private state'):
            self.run_create()
        self.assertEqual(FakeGateway.calls,0)


if __name__ == '__main__':
    unittest.main()
