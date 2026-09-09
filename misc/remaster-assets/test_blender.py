"""Opt-in local integration test: RUN_BLENDER_TESTS=1. Never uses Gateway."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from md3_static import read_md3

HERE = Path(__file__).resolve().parent


@unittest.skipUnless(os.environ.get("RUN_BLENDER_TESTS") == "1", "set RUN_BLENDER_TESTS=1 for real Blender fixture")
class BlenderIntegrationTests(unittest.TestCase):
    def test_asymmetric_two_material_fixture(self):
        from PIL import Image
        with tempfile.TemporaryDirectory(prefix="ioq3-blender-test-") as directory:
            root = Path(directory)
            config = root / "config.json"
            config.write_text(json.dumps({"shader": "models/remaster/test", "height_meters": 1.6,
                                         "units_per_meter": 40, "target_triangles": 100,
                                         "texture_edge": 128, "rotation_z_degrees": 0}))
            for script, args in [("blender_fixture.py", [str(root / "fixture.glb")]),
                                 ("blender_static.py", [str(root / "fixture.glb"), str(root / "out"), str(config)])]:
                result = subprocess.run(["blender", "--background", "--factory-startup", "--threads", "2",
                                         "--python-exit-code", "1", "--python", str(HERE / script), "--", *args],
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.assertEqual(result.returncode, 0, result.stdout[-10000:])
            report = json.loads((root / "out/geometry-report.json").read_text())
            self.assertEqual(report["output_triangles"], 12)
            self.assertEqual(report["bounds_q3"][2], 0)
            self.assertEqual(report["bounds_q3"][5], 64)
            self.assertFalse(report["runtime_accepted"])
            read_md3((root / "out/model.md3").read_bytes())
            with Image.open(root / "out/diffuse.tga") as image:
                colors = list(image.convert("RGB").getdata())
            self.assertGreater(sum(r > 150 and g < 150 and b < 80 for r, g, b in colors), 100)
            self.assertGreater(sum(r < 80 and g > 150 and b > 150 for r, g, b in colors), 100)
            for view in ("front", "back"):
                with Image.open(root / f"out/review-{view}.png") as preview:
                    self.assertEqual(preview.size, (640, 640))


if __name__ == "__main__":
    unittest.main()
