import json
from pathlib import Path
import unittest

from batches import gate, plan
from inventory import sha


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((Path(__file__).resolve().parents[2] / 'assets/remaster/manifests/production-batches.json').read_text())
        self.inv = {'scope': 'demo', 'files': [
            {'path': 'maps/test.bsp', 'sha256': 'map-hash', 'source': 0, 'metadata': {'model_bounds': [{'size_q3': [4, 8, 12]}]}},
            {'path': 'models/players/a/animation.cfg', 'sha256': 'animation-hash', 'source': 0},
            {'path': 'gfx/2d/menu.tga', 'sha256': 'ui-hash', 'source': 0},
            {'path': 'unknown.bin', 'sha256': 'unknown-hash', 'source': 0}], 'shaders': {}, 'dependencies': []}

    def test_actual_bounds_nested_animation_and_ui_separation(self):
        p = plan(self.inv, self.manifest, 'maps/test.bsp')
        self.assertEqual(p['first_map']['measurements']['model_bounds'][0]['size_q3'], [4, 8, 12])
        self.assertEqual(p['excluded'], ['gfx/2d/menu.tga'])
        self.assertEqual(p['unclassified'], ['unknown.bin'])
        char = next(b for b in p['batches'] if b['id'] == 'characters')
        self.assertEqual(char['inputs'][0]['source_path'], 'models/players/a/animation.cfg')
        self.assertFalse(p['paid_submission_enabled'])

    def test_demo_fails_even_with_all_human_gates_claimed(self):
        p = plan(self.inv, self.manifest, 'maps/test.bsp')
        evidence = {'plan_sha256': sha(json.dumps(p, sort_keys=True).encode()), 'batches': {
            b['id']: {g: {'passed': True, 'evidence': 'TEST ONLY', 'reviewer': 'test'} for g in b['gates']} for b in p['batches']}}
        result = gate(p, evidence)
        self.assertFalse(result['passed'])
        self.assertIn('demo/partial', result['failures'][0])
        self.inv['scope'] = 'full-user-declared'; self.inv['files'].pop()
        p = plan(self.inv, self.manifest, 'maps/test.bsp')
        evidence['plan_sha256'] = sha(json.dumps(p, sort_keys=True).encode())
        self.assertTrue(gate(p, evidence)['passed'])
        evidence['batches']['characters']['visual'].pop('reviewer')
        self.assertFalse(gate(p, evidence)['passed'])

    def test_cycle_unknown_map_and_no_measurements_rejected(self):
        self.manifest['batches'][0]['depends_on'] = ['audio']
        with self.assertRaisesRegex(ValueError, 'Cyclic'): plan(self.inv, self.manifest, 'maps/test.bsp')
        self.manifest['batches'][0]['depends_on'] = []
        with self.assertRaises(ValueError): plan(self.inv, self.manifest, 'maps/absent.bsp')
        self.inv['files'][0]['metadata'] = {}
        with self.assertRaisesRegex(ValueError, 'parsed BSP bounds'): plan(self.inv, self.manifest, 'maps/test.bsp')


if __name__ == '__main__':
    unittest.main()
