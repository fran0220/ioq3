#!/usr/bin/env python3
"""Reproducible VFS texture-only UI pack. No game data, models, shaders or VM."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
ATLASES = {
    "atlas": "gauntlet machinegun shotgun grenade rocket lightning railgun plasma bfg grapple armor health unused_red unused_blue award stopwatch".split(),
    "powerups": "quad haste invis envirosuit regen flight medkit teleporter noammo invulnerability ammo_regen doubler guard scout kamikaze portal".split(),
    "ammunition": "ammo_machinegun ammo_shotgun ammo_grenade ammo_rocket ammo_lightning ammo_railgun ammo_plasma ammo_bfg ammo_nailgun ammo_proxlauncher ammo_chaingun nailgun proxlauncher chaingun impressive excellent".split(),
    "status": "red1 red2 red3 blu1 blu2 blu3 neutral1 neutral2 neutral3 skull_red skull_blue disconnected defer lag assist defend".split(),
}


def mappings():
    result = {}
    for weapon in "gauntlet machinegun shotgun grenade rocket lightning railgun plasma bfg grapple nailgun proxlauncher chaingun".split():
        result[f"icons/iconw_{weapon}.tga"] = (weapon, None)
    for ammo in "machinegun shotgun grenade rocket lightning railgun plasma bfg nailgun proxlauncher chaingun".split():
        result[f"icons/icona_{ammo}.tga"] = (f"ammo_{ammo}", None)
    for name in ATLASES["powerups"]:
        result[f"icons/{name}.tga"] = (name, None)
    for color, tint in [("green", "#95edaa"), ("yellow", "#f3d36e"), ("red", "#f08474"), ("mega", "#90c8fc")]:
        result[f"icons/iconh_{color}.tga"] = ("health", tint)
    for color, tint in [("yellow", "#f3d36e"), ("red", "#f08474"), ("shard", "#e0e6df")]:
        result[f"icons/iconr_{color}.tga"] = ("armor", tint)
    for name in "red1 red2 red3 blu1 blu2 blu3 neutral1 neutral2 neutral3".split():
        result[f"icons/iconf_{name}.tga"] = (name, None)
    for name in ["skull_red", "skull_blue"]:
        result[f"icons/{name}.tga"] = (name, None)
    result["icons/iconh_rorb.tga"] = ("skull_red", None)
    result["icons/iconh_borb.tga"] = ("skull_blue", None)
    for name, tile in [("impressive", "impressive"), ("excellent", "excellent"), ("gauntlet", "gauntlet"), ("defend", "defend"), ("assist", "assist"), ("capture", "red2")]:
        result[f"menu/medals/medal_{name}.tga"] = (tile, None)
    for name, tile in [("net", "disconnected"), ("defer", "defer"), ("lag", "lag")]:
        result[f"gfx/2d/{name}.tga"] = (tile, None)
    for name, tile in [("flag_in_base", "neutral1"), ("flag_capture", "neutral2"), ("flag_missing", "neutral3")]:
        result[f"ui/assets/statusbar/{name}.tga"] = (tile, None)
    return result


def prepare():
    # Segmentation belongs to rembg, not a hand-rolled color/alpha threshold.
    from rembg import new_session, remove
    session = new_session("u2net")
    (ROOT / "tiles").mkdir(exist_ok=True)
    for atlas, names in ATLASES.items():
        image = Image.open(ROOT / f"{atlas}-source.png").convert("RGB")
        for i, name in enumerate(names):
            if name.startswith("unused_"):
                continue
            output = ROOT / "tiles" / f"{name}.png"
            if output.exists():
                continue
            x, y = i % 4, i // 4
            crop = image.crop((x * image.width // 4, y * image.height // 4,
                               (x + 1) * image.width // 4, (y + 1) * image.height // 4))
            remove(crop, session=session).resize((128, 128), Image.Resampling.LANCZOS).save(output)
            print(f"Prepared {name}", flush=True)


def package(output):
    files = {}
    for path, (name, tint) in mappings().items():
        image = Image.open(ROOT / "tiles" / f"{name}.png").convert("RGBA")
        if tint:
            alpha = image.getchannel("A")
            image = ImageOps.colorize(ImageOps.grayscale(image), "#10191d", tint).convert("RGBA")
            image.putalpha(alpha)
        buffer = io.BytesIO()
        image.save(buffer, format="TGA")
        files[path] = buffer.getvalue()
    # Reuse existing authorized Painter hangar rather than generate a duplicate.
    image = Image.open(ROOT.parent / "hangar.webp").convert("RGB")
    image = ImageOps.fit(image, (1024, 768), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    files["ui/remaster/loading.jpg"] = buffer.getvalue()
    source = (REPO / "code/game/bg_misc.c").read_text()
    required = set(re.findall(r'"(icons/[^"\n]+)"', source))
    missing = sorted(path for path in required if f"{path}.tga" not in files)
    if missing:
        raise ValueError(f"Uncovered bg_itemlist icons: {missing}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, data in sorted(files.items()):
            info = zipfile.ZipInfo(path, date_time=(2026, 9, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    receipt = {"schemaVersion": 1, "package": output.name,
               "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
               "files": {path: hashlib.sha256(data).hexdigest() for path, data in sorted(files.items())},
               "bgItemIconCoverage": len(required), "missing": missing,
               "scope": "UI textures only. Player portraits are character workstream owned. No source game data or gameplay modifications."}
    (ROOT / "package-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"PASS: {len(files)} UI textures; all {len(required)} bg_itemlist icon paths covered; {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="segment generated source cells once using rembg/u2net")
    parser.add_argument("--output", type=Path, default=ROOT / "ui-icons-v1.pk3")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    package(args.output)
