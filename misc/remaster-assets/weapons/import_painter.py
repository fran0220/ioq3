#!/usr/bin/env python3
"""Import an inspected Amp Painter prototype into the existing paid-task ledger.

No network or paid operation. Shape/resume/billing remain owned by pipeline.py.
Painter does not expose billing IDs: retain unknown cost rather than invent zero.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import Production, atomic, digest, image_info, lock


def import_image(manifest, work, source, note):
    if manifest["image_model"] != "amp-painter":
        raise ValueError("Only explicit Amp Painter manifests can import prototypes")
    data = Path(source).read_bytes()
    info = image_info(data)
    with lock(work):
        production = Production(manifest, work, None)
        existing = production.state["stages"].get("image")
        if existing:
            if production.require_artifact("image").read_bytes() != data:
                raise ValueError("Prototype drift; retain paid input and create an explicit revision")
            return production.require_artifact("image")
        suffix = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[info["mime"]]
        output = Path(work) / ("prototype." + suffix)
        atomic(output, data)
        production.state["stages"]["image"] = {
            "model": "amp-painter", "status": "downloaded",
            "artifact": production.artifact(output), "image": info,
            "source_url": manifest["prototype_url"],
            "cost": {"status": "not-exposed-by-amp-painter", "actual_usd": None},
        }
        production.save()
        production.approve("Amp weapon production visual review", note)
        return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("--note", required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    work = Path("assets/remaster/work") / manifest["asset_id"]
    print(import_image(manifest, work, args.source, args.note))
