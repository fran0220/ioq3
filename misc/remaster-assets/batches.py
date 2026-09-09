"""Expand production batch selectors against a pinned local inventory. No POSTs."""
import argparse
import fnmatch
import json
from pathlib import Path

from inventory import dependencies, sha


def plan(inventory, manifest, map_path):
    batches = manifest['batches']
    ids = [b['id'] for b in batches]
    if len(ids) != len(set(ids)) or any(d not in ids for b in batches for d in b['depends_on']):
        raise ValueError('Duplicate batch or unknown prerequisite')
    visiting, done = set(), set()
    def visit(name):
        if name in visiting:
            raise ValueError('Cyclic batch dependencies')
        if name in done:
            return
        visiting.add(name)
        for d in next(b for b in batches if b['id'] == name)['depends_on']:
            visit(d)
        visiting.remove(name); done.add(name)
    for name in ids:
        visit(name)
    graph = dependencies(inventory, [map_path])
    map_record = next(f for f in inventory['files'] if f['path'] == map_path)
    if not map_path.endswith('.bsp') or not map_record.get('metadata', {}).get('model_bounds'):
        raise ValueError('First-map plan requires parsed BSP bounds, not a guessed scale')
    assigned = {name: [] for name in ids}; excluded, unclassified = [], []
    for file in inventory['files']:
        path = file['path']
        # Pure filename glob for root patterns; fnmatch otherwise treats * as /.
        matches = lambda pattern: fnmatch.fnmatchcase(path, pattern) and ('/' in pattern or '/' not in path)
        if any(matches(p) for p in manifest['excluded_selectors']):
            excluded.append(path); continue
        owners = [b['id'] for b in batches if any(matches(p) for p in b['selectors'])
                  and not any(matches(p) for p in b.get('exclude_selectors', []))]
        if not owners:
            unclassified.append(path)
        for name in owners:
            assigned[name].append({'source_path': path, 'source_sha256': file['sha256'],
                                   'source_archive': file['source'], 'first_map_dependency': path in graph['nodes'],
                                   'status': 'reference-only' if inventory['scope'] == 'demo' else 'needs-production-spec'})
    return {'schema_version': 1, 'inventory_sha256': sha(json.dumps(inventory, sort_keys=True).encode()),
            'batch_manifest_sha256': sha(json.dumps(manifest, sort_keys=True).encode()),
            'source_scope': inventory['scope'], 'full_game_complete': False, 'paid_submission_enabled': False,
            'first_map': {'path': map_path, 'sha256': map_record['sha256'], 'measurements': map_record['metadata'],
                          'dependency_closure': graph},
            'batches': [{**b, 'inputs': assigned[b['id']], 'gates': {g: {'passed': False, 'evidence': None}
                        for g in manifest['required_gates']}} for b in batches],
            'excluded': excluded, 'unclassified': unclassified,
            'next_action': 'Obtain full authorized baseline; select measured module family and inspect prototypes before commissioning. Demo plans are parser rehearsals only.'}


def gate(report, evidence):
    if evidence.get('plan_sha256') != sha(json.dumps(report, sort_keys=True).encode()):
        raise ValueError('Evidence must pin exact canonical plan SHA256')
    failures = []
    if report['source_scope'] != 'full-user-declared':
        failures.append('demo/partial source cannot pass full-production gate')
    if report['unclassified']:
        failures.append('unclassified source assets remain')
    for edge in report['first_map']['dependency_closure']['unresolved']:
        edge_id = sha(json.dumps(edge, sort_keys=True).encode())
        disposition = evidence.get('dependency_dispositions', {}).get(edge_id, {})
        if (disposition.get('classification') not in {'compile-only', 'baked-into-bsp', 'runtime-resolved'}
                or not disposition.get('evidence') or not disposition.get('reviewer')):
            failures.append('unresolved-dependency:' + edge_id)
    for batch in report['batches']:
        supplied = evidence.get('batches', {}).get(batch['id'], {})
        for name in batch['gates']:
            item = supplied.get(name, {})
            if item.get('passed') is not True or not item.get('evidence') or not item.get('reviewer'):
                failures.append(batch['id'] + ':' + name)
    return {'passed': not failures, 'failures': failures, 'paid_submission_enabled': False,
            'note': 'References are auditable attestations, not automatic image/audio/gameplay QA; no release or generation is triggered.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('plan'); a.add_argument('--inventory', type=Path, required=True)
    a.add_argument('--manifest', type=Path, required=True); a.add_argument('--map', required=True)
    a.add_argument('--output', type=Path, required=True)
    a = sub.add_parser('gate'); a.add_argument('--plan', type=Path, required=True)
    a.add_argument('--evidence', type=Path, required=True); a.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.command == 'plan':
        inv = json.loads(args.inventory.read_text()); inv.pop('canonical_sha256', None)
        result = plan(inv, json.loads(args.manifest.read_text()), args.map)
    else:
        result = gate(json.loads(args.plan.read_text()), json.loads(args.evidence.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'output': str(args.output), 'paid_submission_enabled': False, 'passed': result.get('passed')}))
    if args.command == 'gate' and not result['passed']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
