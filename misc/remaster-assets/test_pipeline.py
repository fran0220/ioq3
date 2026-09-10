import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from pipeline import Gateway, Production, check_glb, encoded, lock, digest
from md3_static import write_md3


class FakeGateway:
    scope = "test-token-scope"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def request(self, *args):
        self.calls.append(args)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.manifest = {"asset_id": "test", "classification": "test"}
        self.payload = {"model": "model-a", "image": "immutable-input"}

    def runner(self, gateway):
        return Production(self.manifest, self.work, gateway)

    def test_imported_painter_hash_provenance_and_no_paid_overwrite(self):
        from PIL import Image
        source = self.work / 'external.png'
        Image.new('RGB', (19, 23), (31, 127, 201)).save(source)
        sha = digest(source.read_bytes())
        runner = self.runner(FakeGateway([]))
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            runner.import_image(source, '0' * 64, 'attachment:test')
        self.assertFalse(runner.state['stages'])
        destination = runner.import_image(source, sha, 'attachment:test')
        state = runner.state_path.read_bytes()
        self.assertEqual(destination.read_bytes(), source.read_bytes())
        self.assertEqual(runner.import_image(source, sha, 'attachment:test'), destination)
        self.assertEqual(runner.state_path.read_bytes(), state)
        self.assertEqual(runner.gateway.calls, [])
        self.assertNotIn('prototype_review', runner.state)
        self.assertIsNone(runner.state['stages']['image']['cost']['actual_usd'])
        with self.assertRaisesRegex(ValueError, 'Inspect prototype'):
            runner.shape()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            runner.import_image(source, sha, 'attachment:different')
        runner.state['stages']['image'] = {'status': 'submission_unknown', 'operation_id': 'paid-1'}
        runner.save()
        state = runner.state_path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            runner.import_image(source, sha, 'attachment:test')
        self.assertEqual(runner.state_path.read_bytes(), state)

    def test_image_timeout_is_never_resubmitted(self):
        gateway = FakeGateway([TimeoutError()])
        with self.assertRaises(TimeoutError):
            self.runner(gateway).submit("image", "/image", self.payload, False)
        with self.assertRaisesRegex(ValueError, "unknown/rejected"):
            self.runner(gateway).submit("image", "/image", self.payload, False)
        self.assertEqual(len(gateway.calls), 1)
        self.assertEqual(json.loads((self.work / "state.json").read_text())["stages"]["image"]["status"], "submission_unknown")

    def test_hunyuan_timeout_replays_exact_key_and_bytes(self):
        gateway = FakeGateway([TimeoutError(), (200, {}, encoded({"id": "task_saved"}))])
        with self.assertRaises(TimeoutError):
            self.runner(gateway).submit("shape", "/3d", self.payload, True)
        result = self.runner(gateway).submit("shape", "/3d", self.payload, True)
        self.assertEqual(result["id"], "task_saved")
        self.assertEqual(gateway.calls[0], gateway.calls[1])

    def test_saved_response_resumes_without_post(self):
        gateway = FakeGateway([(200, {}, encoded({"data": [{"b64_json": "payload"}]}))])
        result = self.runner(gateway).submit("image", "/image", self.payload, False)
        self.assertEqual(self.runner(gateway).submit("image", "/image", self.payload, False), result)
        self.assertEqual(len(gateway.calls), 1)

    def test_changed_input_or_token_cannot_replay(self):
        gateway = FakeGateway([TimeoutError()])
        with self.assertRaises(TimeoutError):
            self.runner(gateway).submit("shape", "/3d", self.payload, True)
        with self.assertRaisesRegex(ValueError, "Input or credential changed"):
            self.runner(gateway).submit("shape", "/3d", {**self.payload, "image": "changed"}, True)
        gateway.scope = "rotated-token"
        with self.assertRaisesRegex(ValueError, "Input or credential changed"):
            self.runner(gateway).submit("shape", "/3d", self.payload, True)
        self.assertEqual(len(gateway.calls), 1)

    def test_http_error_requires_inspection_not_automatic_paid_retry(self):
        gateway = FakeGateway([(503, {}, b"private-error")])
        with self.assertRaisesRegex(ValueError, "HTTP 503"):
            self.runner(gateway).submit("shape", "/3d", self.payload, True)
        with self.assertRaisesRegex(ValueError, "Recorded HTTP rejection"):
            self.runner(gateway).submit("shape", "/3d", self.payload, True)
        self.assertEqual(len(gateway.calls), 1)

    def test_receipt_omits_credential_and_raw_request(self):
        gateway = FakeGateway([(202, {"X-Request-Id": "req-1"}, encoded({"id": "task-1"}))])
        runner = self.runner(gateway)
        runner.submit("shape", "/3d", self.payload, True)
        receipt = runner.receipt()
        self.assertNotIn("credential_scope", json.dumps(receipt))
        self.assertNotIn("immutable-input", json.dumps(receipt))
        self.assertFalse(receipt["runtime_accepted"])
        self.assertEqual(receipt["stages"]["shape"]["request_id"], "req-1")

    def test_billing_matches_request_not_recent_same_model(self):
        entries = [
            {"request_id": "unrelated", "model_name": "model-a", "type": 2, "quota": 999999},
            {"request_id": "ours", "model_name": "model-a", "type": 2, "quota": 250000},
            {"request_id": "ours", "model_name": "model-a", "type": 6, "quota": 50000},
        ]
        gateway = FakeGateway([(202, {"x-request-id": "ours"}, encoded({"id": "task-1"})),
                               (200, {}, encoded({"success": True, "data": entries}))])
        runner = self.runner(gateway)
        runner.submit("shape", "/3d", self.payload, True)
        costs = runner.billing()
        self.assertEqual(costs["shape"]["quota"], 200000)
        self.assertEqual(costs["shape"]["actual_usd"], 0.4)

    def test_lock_excludes_another_runner(self):
        with lock(self.work):
            with self.assertRaisesRegex(ValueError, "Another runner"):
                with lock(self.work):
                    self.fail("acquired twice")

    def test_named_identity_does_not_fall_back_to_bare_key(self):
        identity = self.work / "identity.json"
        identity.write_text('{"creator":"og-atlas"}')
        with self.assertRaisesRegex(ValueError, "Missing named"):
            Gateway(identity, {"OG_API_KEY": "not-the-creator-key"})
        with self.assertRaisesRegex(ValueError, "HTTPS origin"):
            Gateway(identity, {"OG_CREATOR_KEY_OG_ATLAS": "test", "OG_AI_GATEWAY": "https://example.com/unsafe"})

    def test_default_generation_identity_is_explicitly_distinct(self):
        identity = self.work / "identity.json"
        identity.write_text('{"creator":"og-atlas"}')
        env = {"OG_API_KEY": "generation-key", "OG_CREATOR_KEY_OG_ATLAS": "publisher-key"}
        default = Gateway(identity, env, credential="default")
        publisher = Gateway(identity, env, credential="publisher")
        self.assertFalse(default.same_as_publisher)
        self.assertNotEqual(default.scope, publisher.scope)
        self.assertEqual(default.key_name, "OG_API_KEY")
        self.assertEqual(identity.read_text(), '{"creator":"og-atlas"}')

    def test_fresh_checkout_with_receipt_cannot_regenerate(self):
        receipt = self.work / "assets/remaster/receipts/test.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text('{"stages":{"image":{"status":"downloaded"}}}')
        with patch("pipeline.ROOT", self.work), self.assertRaisesRegex(ValueError, "Committed receipt exists"):
            Production(self.manifest, self.work / "new-work", FakeGateway([]))

    def test_glb_rejects_external_resources_and_corrupt_lengths(self):
        def glb(doc):
            raw = encoded(doc)
            raw += b" " * (-len(raw) % 4)
            return struct.pack("<4sIIII", b"glTF", 2, 20+len(raw), len(raw), 0x4E4F534A) + raw
        good = glb({"meshes": [{}]})
        self.assertEqual(check_glb(good)["meshes"], [{}])
        with self.assertRaisesRegex(ValueError, "external"):
            check_glb(glb({"meshes": [{}], "images": [{"uri": "file:///private"}]}))
        with self.assertRaisesRegex(ValueError, "length"):
            check_glb(good[:-4])

    def test_completed_task_download_recovery_uses_only_get(self):
        doc = encoded({"meshes": [{}]})
        doc += b" " * (-len(doc) % 4)
        glb = struct.pack("<4sIIII", b"glTF", 2, 20+len(doc), len(doc), 0x4E4F534A) + doc
        gateway = FakeGateway([(200, {}, encoded({"status": "completed"})), (503, {}, b"failure"),
                               (200, {}, encoded({"status": "completed"})), (200, {}, glb)])
        runner = self.runner(gateway)
        runner.state["stages"]["shape"] = {"task_id": "task_1", "credential_scope": gateway.scope}
        runner.save()
        with self.assertRaisesRegex(ValueError, "Download HTTP"):
            runner.resume()
        path = self.runner(gateway).resume()
        self.assertEqual(path.read_bytes(), glb)
        self.assertTrue(all(c[0] == "GET" for c in gateway.calls))
        self.runner(gateway).resume()
        self.assertEqual(len(gateway.calls), 4)

    def test_package_is_deterministic_and_rejects_modified_outputs(self):
        self.manifest["processing"] = {"shader": "models/remaster/test"}
        runner = self.runner(None)
        shape = self.work / "test-source.glb"
        shape.write_bytes(b"fixture source marker, not production GLB")
        runner.state["stages"]["shape"] = {"artifact": runner.artifact(shape)}
        output = self.work / "processed"
        output.mkdir()
        triangle = [((0, 0, 0), (0, 0), (0, 0, 1)), ((2, 0, 0), (1, 0), (0, 0, 1)), ((0, 3, 0), (0, 1), (0, 0, 1))]
        (output / "model.md3").write_bytes(write_md3([triangle], "models/remaster/test"))
        (output / "diffuse.tga").write_bytes(b"test texture")
        (output / "remaster.shader").write_bytes(b"test shader")
        runner.state["processing"] = {"files": [runner.artifact(p) for p in output.iterdir()]}
        first = runner.package().read_bytes()
        self.assertEqual(first, runner.package().read_bytes())
        with zipfile.ZipFile(runner.package()) as archive:
            self.assertEqual(archive.namelist(), ["models/remaster/test.md3", "models/remaster/test.tga", "scripts/remaster_test.shader"])
        (output / "diffuse.tga").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "artifact changed"):
            runner.package()


if __name__ == "__main__":
    unittest.main()
