import json
from pathlib import Path
import tempfile
import unittest

from archive import restore, snapshot, verify
from inventory import sha


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.work = self.root / 'work'; self.work.mkdir()
        self.store = self.root / 'store'
        self.receipt = {'asset_id': 'test', 'manifest_sha256': 'manifest', 'stages': {'image': {
            'task_id': 'paid-task', 'request_id': 'paid-request', 'operation_id': 'operation', 'submissions': 1,
            'status': 'downloaded', 'artifact': {'path': 'prototype.png', 'bytes': 5, 'sha256': sha(b'image')}}}}
        (self.work / 'prototype.png').write_bytes(b'image')
        (self.work / 'state.json').write_text(json.dumps(self.receipt))
        (self.work / 'image-request.json').write_text('{"private": "test data only"}')

    def test_restore_exact_recovery_without_regeneration_and_dedup(self):
        first = snapshot(self.work, self.receipt, self.store)
        self.assertEqual(snapshot(self.work, self.receipt, self.store), first)
        manifest = json.loads(first.read_text())
        self.assertEqual(verify(self.store, manifest)['verified_files'], 3)
        dest = self.root / 'restored'
        restore(self.store, manifest, dest); restore(self.store, manifest, dest)
        self.assertEqual((dest / 'state.json').read_bytes(), (self.work / 'state.json').read_bytes())
        self.assertEqual((dest / 'prototype.png').read_bytes(), b'image')
        self.assertEqual(len(list((self.store / 'blobs').iterdir())), 3)
        self.assertFalse(manifest['regeneration_allowed'])

    def test_corrupt_source_blob_and_restore_conflict_fail_closed(self):
        file = snapshot(self.work, self.receipt, self.store); manifest = json.loads(file.read_text())
        dest = self.root / 'restored'; dest.mkdir(); (dest / 'prototype.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'replace changed'): restore(self.store, manifest, dest)
        self.assertFalse((dest / 'state.json').exists())
        (self.store / 'blobs' / sha(b'image')).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'Corrupt'): verify(self.store, manifest)
        (self.work / 'prototype.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash/size'): snapshot(self.work, self.receipt, self.store)

    def test_stale_receipt_and_symlink_escape_refused(self):
        stale = json.loads(json.dumps(self.receipt)); stale['stages']['image']['task_id'] = 'other-task'
        with self.assertRaisesRegex(ValueError, 'Stale'): snapshot(self.work, stale, self.store)
        (self.work / 'prototype.png').unlink()
        (self.root / 'outside').write_bytes(b'image')
        (self.work / 'prototype.png').symlink_to(self.root / 'outside')
        with self.assertRaisesRegex(ValueError, 'escape'): snapshot(self.work, self.receipt, self.store)


if __name__ == '__main__':
    unittest.main()
