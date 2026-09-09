import json
from pathlib import Path
import tempfile
import unittest

from pipeline import Gateway, Production, encoded, lock


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


if __name__ == "__main__":
    unittest.main()
