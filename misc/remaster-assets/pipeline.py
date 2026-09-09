#!/usr/bin/env python3
"""Origin Gateway production runner. Private immutable receipts, explicit stages."""

import argparse
import base64
import contextlib
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save(path, value):
    atomic(path, json.dumps(value, indent=2, sort_keys=True).encode() + b"\n")


def image_info(data):
    # Pillow is a CLI dependency, not required for pure state-machine tests.
    from PIL import Image
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        if image.format not in {"PNG", "JPEG", "WEBP"} or getattr(image, "is_animated", False):
            raise ValueError("Unsupported prototype image")
        w, h = image.size
        if len(data) > 8 * 1024**2 or not (16 <= w <= 4096 and 16 <= h <= 4096) or w*h > 16000000:
            raise ValueError("Prototype exceeds Hunyuan limits")
        return {"mime": Image.MIME[image.format], "width": w, "height": h}


def check_glb(data):
    import struct
    if len(data) < 20:
        raise ValueError("Truncated GLB")
    magic, version, length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("Invalid GLB header or length")
    offset, chunks = 12, []
    while offset < length:
        size, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        if size % 4 or offset + size > length:
            raise ValueError("Invalid GLB chunk")
        chunks.append((kind, data[offset:offset+size]))
        offset += size
    if offset != length or not chunks or chunks[0][0] != 0x4E4F534A:
        raise ValueError("Missing GLB JSON")
    doc = json.loads(chunks[0][1])
    if not doc.get("meshes"):
        raise ValueError("GLB contains no meshes")
    for resource in doc.get("buffers", []) + doc.get("images", []):
        if resource.get("uri") and not resource["uri"].startswith("data:"):
            raise ValueError("GLB external resources forbidden before Blender import")
    return doc


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Gateway:
    def __init__(self, identity, environ=None, credential="publisher"):
        environ = os.environ if environ is None else environ
        creator = json.loads(Path(identity).read_text())["creator"]
        if not re.fullmatch(r"[a-z0-9-]{2,32}", creator):
            raise ValueError("Invalid creator identity")
        publisher_key_name = "OG_CREATOR_KEY_" + creator.replace("-", "_").upper()
        self.key_name = publisher_key_name if credential == "publisher" else "OG_API_KEY"
        self.key = environ.get(self.key_name)
        if not self.key:
            raise ValueError("Missing named credential: " + self.key_name)
        self.same_as_publisher = self.key == environ.get(publisher_key_name)
        self.origin = environ.get("OG_AI_GATEWAY", "https://api.origingame.dev").rstrip("/")
        parsed = urllib.parse.urlsplit(self.origin)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
            raise ValueError("OG_AI_GATEWAY must be an HTTPS origin")
        self.scope = digest((self.origin + "\0" + self.key).encode())
        self.opener = urllib.request.build_opener(NoRedirect())

    def account(self):
        status, _, raw = self.request("GET", "/v1/origin/studio-account")
        if status != 200:
            raise ValueError(f"Account lookup HTTP {status}; generation identity unverified")
        account = json.loads(raw)
        status, _, raw = self.request("GET", "/api/usage/token/")
        if status != 200:
            raise ValueError(f"Token usage HTTP {status}")
        usage = json.loads(raw)
        if usage.get("code") is not True:
            raise ValueError("Token usage unavailable")
        self.account_info = {k: account[k] for k in ("id", "username")}
        return {"account": self.account_info, "user_quota": account["quota"],
                "credential_variable": self.key_name, "same_as_publisher_key": self.same_as_publisher,
                "token": {k: usage["data"].get(k) for k in ("total_available", "unlimited_quota", "expires_at", "model_limits_enabled", "model_limits")}}

    def request(self, method, path, body=None, operation=None):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Gateway path must be local")
        headers = {"Authorization": "Bearer " + self.key, "Content-Type": "application/json"}
        if operation:
            headers["Idempotency-Key"] = operation
        req = urllib.request.Request(self.origin + path, data=body, headers=headers, method=method)
        try:
            response = self.opener.open(req, timeout=240)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read(64 * 1024**2 + 1)
            if len(data) > 64 * 1024**2:
                raise ValueError("Response exceeds 64 MiB; retained task must be downloaded separately")
            return response.status, dict(response.headers.items()), data


class Production:
    def __init__(self, manifest, work, gateway):
        self.manifest = manifest
        self.work = Path(work)
        self.work.mkdir(parents=True, exist_ok=True)
        self.gateway = gateway
        self.state_path = self.work / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {
            "schema_version": 1, "asset_id": manifest["asset_id"],
            "manifest_sha256": digest(encoded(manifest)), "stages": {},
            "runtime_accepted": False,
        }
        if self.state["manifest_sha256"] != digest(encoded(manifest)):
            raise ValueError("Manifest changed; use a new revision/work directory, never overwrite paid provenance")

    def save(self):
        save(self.state_path, self.state)

    def artifact(self, path):
        data = path.read_bytes()
        return {"path": str(path.relative_to(self.work)), "sha256": digest(data), "bytes": len(data)}

    def require_artifact(self, stage):
        item = self.state["stages"][stage]["artifact"]
        path = self.work / item["path"]
        if digest(path.read_bytes()) != item["sha256"]:
            raise ValueError("Artifact hash mismatch: " + stage)
        return path

    def submit(self, stage, path, payload, idempotent):
        body = encoded(payload)
        record = self.state["stages"].get(stage)
        if record is None:
            record = {"operation_id": str(uuid.uuid4()), "request_sha256": digest(body),
                      "credential_scope": self.gateway.scope, "model": payload["model"],
                      "generator_identity": getattr(self.gateway, "account_info", None),
                      "status": "prepared", "created_at": int(time.time()), "submissions": 0,
                      "cost": {"status": "unreconciled", "actual_usd": None}}
            self.state["stages"][stage] = record
            atomic(self.work / (stage + "-request.json"), body)
            self.save()
        if record["request_sha256"] != digest(body) or record["credential_scope"] != self.gateway.scope:
            raise ValueError("Input or credential changed; refusing a potentially new paid operation")
        response_path = self.work / (stage + "-response.json")
        if response_path.exists():
            return json.loads(response_path.read_text())
        if record.get("task_id") or record.get("artifact"):
            raise ValueError("Stage already accepted; resume instead")
        if record["status"] != "prepared" and not idempotent:
            raise ValueError("Image submission unknown/rejected; recover saved response, do not resubmit")
        if record["status"] == "http_error":
            raise ValueError("Recorded HTTP rejection; inspect private response before any retry")
        record["status"] = "submission_unknown"
        record["submissions"] += 1
        self.save()  # durable before paid request, including process-kill window
        status, headers, raw = self.gateway.request("POST", path, body, record["operation_id"])
        record["http_status"] = status
        lower = {k.lower(): v for k, v in headers.items()}
        record["request_id"] = lower.get("x-oneapi-request-id") or lower.get("x-request-id")
        if status not in {200, 202}:
            atomic(self.work / (stage + "-error-response.bin"), raw)
            record["status"] = "http_error"
            self.save()
            raise ValueError(f"{stage}: HTTP {status}; response retained privately, no new paid retry")
        atomic(response_path, raw)  # recover image bytes even if parsing/process dies below
        record["response_sha256"] = digest(raw)
        self.save()
        return json.loads(raw)

    def image(self):
        if self.state["stages"].get("image", {}).get("artifact"):
            return self.require_artifact("image")
        payload = {"model": self.manifest["image_model"], "prompt": self.manifest["prompt"],
                   "n": 1, "response_format": "b64_json"}
        response = self.submit("image", "/v1/images/generations", payload, False)
        value = response["data"][0].get("b64_json")
        if not value:
            raise ValueError("Expected requested b64_json; response retained. Download URL separately without Bearer; do not regenerate")
        data = base64.b64decode(value.split(",", 1)[-1] if value.startswith("data:") else value, validate=True)
        info = image_info(data)
        extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[info["mime"]]
        path = self.work / ("prototype." + extension)
        atomic(path, data)
        self.state["stages"]["image"].update(status="downloaded", artifact=self.artifact(path), image=info)
        self.save()
        return path

    def approve(self, reviewer, note):
        path = self.require_artifact("image")
        self.state["prototype_review"] = {"reviewer": reviewer, "note": note,
                                           "sha256": digest(path.read_bytes()), "at": int(time.time())}
        self.save()

    def shape(self):
        path = self.require_artifact("image")
        if self.state.get("prototype_review", {}).get("sha256") != digest(path.read_bytes()):
            raise ValueError("Inspect prototype then approve its hash before image-to-3D (art gate, not budget gate)")
        stage = self.state["stages"].get("shape", {})
        if stage.get("task_id"):
            return stage["task_id"]
        data = path.read_bytes()
        payload = {"model": self.manifest["shape_model"],
                   "image": "data:" + image_info(data)["mime"] + ";base64," + base64.b64encode(data).decode()}
        response = self.submit("shape", "/v1/3d/tasks", payload, True)
        task_id = response.get("id")
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", task_id):
            raise ValueError("Invalid task id in saved response")
        self.state["stages"]["shape"].update(task_id=task_id, status=response["status"])
        self.save()
        return task_id

    def resume(self, wait=0):
        record = self.state["stages"]["shape"]
        if record.get("artifact"):
            return self.require_artifact("shape")
        if record["credential_scope"] != self.gateway.scope:
            raise ValueError("Credential changed; resume under original credential")
        task_id = record["task_id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", task_id):
            raise ValueError("Invalid task id")
        path = "/v1/3d/tasks/" + task_id
        deadline = time.monotonic() + wait
        while True:
            status, _, raw = self.gateway.request("GET", path)
            if status != 200:
                raise ValueError(f"Poll HTTP {status}; task retained, rerun resume")
            response = json.loads(raw)
            state = response["status"]
            if state not in {"queued", "in_progress", "completed", "failed"}:
                raise ValueError("Unknown task state; refusing create")
            record["status"] = state
            record["report"] = response.get("report")
            record["error_code"] = response.get("error_code")
            self.save()
            if state == "failed":
                raise ValueError("Generation failed: " + str(record["error_code"]) + "; reconcile refund, no new automatic create")
            if state == "completed":
                status, _, data = self.gateway.request("GET", path + "/content")
                if status != 200:
                    raise ValueError(f"Download HTTP {status}; task retained")
                check_glb(data)
                output = self.work / "generated.glb"
                atomic(output, data)
                record.update(status="downloaded", artifact=self.artifact(output))
                self.save()
                return output
            if time.monotonic() >= deadline:
                return state
            time.sleep(10)

    def billing(self):
        status, _, raw = self.gateway.request("GET", "/api/log/token")
        if status != 200:
            raise ValueError(f"Billing HTTP {status}; costs remain unreconciled")
        response = json.loads(raw)
        if not response.get("success") or not isinstance(response.get("data"), list):
            raise ValueError("Billing records unavailable")
        for record in self.state["stages"].values():
            request_id = record.get("request_id")
            matches = [r for r in response["data"] if request_id and r.get("request_id") == request_id
                       and r.get("model_name") == record["model"] and r.get("type") in {2, 6}]
            charges = [r for r in matches if r["type"] == 2]
            refunds = [r for r in matches if r["type"] == 6]
            if len(charges) == 1 and len(refunds) <= 1:
                quota = charges[0]["quota"] - sum(r["quota"] for r in refunds)
                record["cost"] = {"status": "matched_request_id", "quota": quota,
                                  "actual_usd": quota / 500000,
                                  "records": [{k: r.get(k) for k in ("request_id", "model_name", "type", "quota", "created_at")} for r in matches]}
        self.save()
        return {k: v["cost"] for k, v in self.state["stages"].items()}

    def process(self):
        source = self.require_artifact("shape")
        source_hash = digest(source.read_bytes())
        scripts = {name: digest(Path(__file__).with_name(name).read_bytes())
                   for name in ("blender_static.py", "md3_static.py")}
        prior = self.state.get("processing")
        if prior and prior["source_sha256"] == source_hash and prior.get("scripts") == scripts:
            self.verify_processed()
            return self.work / "processed"
        config = self.work / "process-config.json"
        save(config, self.manifest["processing"])
        output = self.work / "processed"
        output.mkdir(exist_ok=True)
        subprocess.run(["blender", "--background", "--factory-startup", "--threads", "2",
                        "--python-exit-code", "1", "--python", str(Path(__file__).with_name("blender_static.py")),
                        "--", str(source), str(output), str(config)], check=True)
        self.state["processing"] = {"source_sha256": source_hash, "scripts": scripts,
                                    "files": [self.artifact(p) for p in sorted(output.iterdir()) if p.is_file()]}
        self.save()
        return output

    def verify_processed(self):
        from md3_static import read_md3
        record = self.state.get("processing")
        if not record:
            raise ValueError("Process must finish before packaging")
        self.require_artifact("shape")
        for item in record["files"]:
            if digest((self.work / item["path"]).read_bytes()) != item["sha256"]:
                raise ValueError("Processed artifact changed; rebuild locally before packaging")
        parsed = read_md3((self.work / "processed/model.md3").read_bytes())
        if any(s["shader"] != self.manifest["processing"]["shader"] for s in parsed["surfaces"]):
            raise ValueError("Model/shader mismatch")
        return parsed

    def package(self):
        self.verify_processed()
        shader = self.manifest["processing"]["shader"]
        asset_id = self.manifest["asset_id"]
        files = {shader + ".md3": "model.md3", shader + ".tga": "diffuse.tga",
                 "scripts/remaster_" + asset_id.replace("-", "_") + ".shader": "remaster.shader"}
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, source in sorted(files.items()):
                info = zipfile.ZipInfo(name, (2026, 9, 9, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, (self.work / "processed" / source).read_bytes())
        output = self.work / (asset_id + ".pk3")
        atomic(output, buffer.getvalue())
        self.state["package"] = self.artifact(output)
        self.save()
        return output

    def receipt(self):
        # Explicit public projection, never dump private responses/URLs/credential scope.
        return {"asset_id": self.manifest["asset_id"], "classification": self.manifest["classification"],
                "manifest_sha256": self.state["manifest_sha256"],
                "prototype_review": self.state.get("prototype_review"),
                "runtime_accepted": False,
                "stages": {k: {field: v.get(field) for field in
                           ("operation_id", "task_id", "request_id", "request_sha256", "response_sha256", "generator_identity", "model", "status", "submissions", "artifact", "image", "report", "error_code", "cost")}
                           for k, v in self.state["stages"].items()},
                "processing": self.state.get("processing"), "package": self.state.get("package")}


@contextlib.contextmanager
def lock(work):
    Path(work).mkdir(parents=True, exist_ok=True)
    with open(Path(work) / ".lock", "w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another runner owns this asset; do not submit concurrently") from None
        yield


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["account", "image", "approve", "shape", "resume", "billing", "process", "package", "receipt"])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--identity", type=Path, default=ROOT / ".origingame-deploy.json")
    parser.add_argument("--credential", choices=["default", "publisher"], default="default",
                        help="Generation identity only; never changes the root publishing identity")
    parser.add_argument("--work", type=Path)
    parser.add_argument("--wait", type=int, default=0)
    parser.add_argument("--reviewer")
    parser.add_argument("--note")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("schema_version") != 1 or not re.fullmatch(r"[a-z0-9-]+", manifest["asset_id"]):
        parser.error("Invalid manifest schema/id")
    if manifest["shape_model"] not in {"hunyuan3d-2", "hunyuan3d-2-shape"}:
        parser.error("Unsupported shape model")
    work = args.work or ROOT / "assets/remaster/work" / manifest["asset_id"]
    with lock(work):
        gateway = Gateway(args.identity, credential=args.credential) if args.command in {"account", "image", "shape", "resume", "billing"} else None
        if args.command == "account":
            print(json.dumps(gateway.account(), indent=2))
            return
        if args.command in {"image", "shape"}:
            gateway.account()  # record actual generating account, not publishing attribution
        runner = Production(manifest, work, gateway)
        if args.command == "approve":
            if not args.reviewer or not args.note:
                parser.error("approve needs --reviewer and --note after visual inspection")
            runner.approve(args.reviewer, args.note)
            result = "Prototype art review recorded"
        elif args.command == "resume":
            result = runner.resume(args.wait)
        else:
            result = getattr(runner, args.command)()
        print(json.dumps(result, indent=2) if isinstance(result, dict) else result)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        # Never print network exception repr/body: it can contain URLs or input.
        if isinstance(error, (ValueError, KeyError)):
            print("Stopped:", str(error))
        else:
            print("Stopped:", type(error).__name__, "— state retained; resume the existing operation")
        raise SystemExit(1)
