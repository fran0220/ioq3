"""Import an inspected Painter prototype; reuse durable Hunyuan production.

No static MD3 processing: the output is a candidate GLB awaiting character rigging.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "misc/remaster-assets"))
from pipeline import Gateway, Production, digest, image_info, lock


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["import-painter", "shape", "resume", "billing", "receipt"])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--credential", choices=["default", "publisher"], default="default")
    parser.add_argument("--wait", type=int, default=0)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    work = ROOT / "assets/remaster/work" / manifest["asset_id"]
    with lock(work):
        gateway = Gateway(ROOT / ".origingame-deploy.json", credential=args.credential) if args.command in {"shape", "resume", "billing"} else None
        production = Production(manifest, work, gateway)
        if args.command == "import-painter":
            path = work / "prototype.png"
            data = path.read_bytes()
            if production.state["stages"].get("image"):
                production.require_artifact("image")
                return
            production.state["stages"]["image"] = {
                "model": "amp-painter", "status": "downloaded",
                "artifact": production.artifact(path), "image": image_info(data),
                "cost": {"status": "not-exposed-by-tool", "actual_usd": None},
                "source": manifest["prototype"]["attachment"]}
            production.save()
            production.approve("character-thread", "Inspected full body: recognizable silver flat-top veteran, clean waist/collar seams, separated limbs, coherent ivory/olive armor; rear geometry remains unverified")
            print(digest(data))
        else:
            if args.command == "shape":
                gateway.account()
            result = production.resume(args.wait) if args.command == "resume" else getattr(production, args.command)()
            print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
