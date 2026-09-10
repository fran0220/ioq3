import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from package_crest import package
from md3_static import write_md3


class CrestPlacementTests(unittest.TestCase):
    def test_asymmetric_rotation_scale_and_both_envelope_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = 'models/remaster/environment_wall_crest'
            triangle = [[(p, (0, 0), (0, 0, 1)) for p in [(-2, -1, 0), (4, -1, 0), (0, 3, 2)]]]
            source = root / 'source.pk3'
            with zipfile.ZipFile(source, 'w') as archive:
                archive.writestr(model + '.md3', write_md3(triangle, model))
                archive.writestr(model + '.tga', b'TEST ONLY')
                archive.writestr('scripts/remaster_environment_wall_crest_v1.shader', b'TEST ONLY')
            receipt = root / 'receipt.json'
            receipt.write_text(json.dumps({'package': {'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}}))
            spec = {'schemaVersion': 1, 'map': 'q3dm1', 'replacements': [{
                'surface': 2050, 'model': model + '.md3', 'angles': [0, 180, 0],
                'scale': .5, 'origin': [10, 20, 30], 'bounds': [[8, 18.5, 30], [11, 20.5, 31]]}]}
            placement = root / 'placement.json'
            placement.write_text(json.dumps(spec))
            with contextlib.redirect_stdout(io.StringIO()):
                package(source, receipt, placement, root / 'result.pk3')
            result = json.loads((root / 'result.json').read_text())
            self.assertEqual(result['world_bounds'], [[8, 18.5, 30], [11, 20.5, 31]])
            for delta in (-.01, .01):
                spec['replacements'][0]['origin'][0] = 10 + delta
                placement.write_text(json.dumps(spec))
                with self.assertRaisesRegex(ValueError, 'protrudes'):
                    package(source, receipt, placement, root / 'bad.pk3')
            source.write_bytes(source.read_bytes() + b'drift')
            with self.assertRaisesRegex(ValueError, 'receipt'):
                package(source, receipt, placement, root / 'bad.pk3')


if __name__ == '__main__':
    unittest.main()
