import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parent


class IconPackageTests(unittest.TestCase):
    def test_reproducible_art_package_and_sources(self):
        receipt = json.loads((ROOT / "package-receipt.json").read_text())
        archive = ROOT / "ui-icons-v1.pk3"
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), receipt["sha256"])
        provenance = json.loads((ROOT / "provenance.json").read_text())
        for source in [provenance, *provenance["additionalSources"]]:
            self.assertEqual(hashlib.sha256((ROOT / source["asset"]).read_bytes()).hexdigest(), source["sha256"])
        with tempfile.TemporaryDirectory() as tmp:
            rebuilt = Path(tmp) / archive.name
            subprocess.run([sys.executable, str(ROOT / "package.py"), "--output", str(rebuilt)], check=True)
            self.assertEqual(archive.read_bytes(), rebuilt.read_bytes())

    def test_actual_vfs_coverage_alpha_and_distinct_semantics(self):
        with zipfile.ZipFile(ROOT / "ui-icons-v1.pk3") as archive:
            paths = archive.namelist()
            self.assertTrue(all(path.endswith((".tga", ".jpg")) or path == "scripts/remaster_ui.shader" for path in paths))
            self.assertFalse(any(".." in path or path.startswith("/") for path in paths))
            required = set(re.findall(r'"(icons/[^"\n]+)"', (ROOT.parents[3] / "code/game/bg_misc.c").read_text()))
            self.assertTrue(required)
            for path in required:
                self.assertIn(path + ".tga", paths)
            for path in paths:
                if path.endswith(".shader"):
                    aliases = re.findall(r'^medal_(\w+)$', archive.read(path).decode(), re.M)
                    self.assertEqual(aliases, ['impressive', 'excellent', 'gauntlet', 'defend', 'assist', 'capture'])
                    continue
                image = Image.open(io.BytesIO(archive.read(path)))
                if path.endswith(".tga"):
                    self.assertEqual(image.size, (128, 128), path)
                    alpha = image.convert("RGBA").getchannel("A")
                    self.assertEqual(alpha.getextrema(), (0, 255), path)
                    self.assertGreater(sum(value > 128 for value in alpha.tobytes()), 300, path)
            for weapon in ["machinegun", "rocket", "plasma", "railgun"]:
                self.assertNotEqual(archive.read(f"icons/iconw_{weapon}.tga"), archive.read(f"icons/icona_{weapon}.tga"))
            flags = [archive.read(f"icons/iconf_{team}{state}.tga") for team in ["red", "blu", "neutral"] for state in [1, 2, 3]]
            self.assertEqual(len(set(flags)), 9, "team or flag-state artwork silently duplicated")


if __name__ == "__main__":
    unittest.main()
