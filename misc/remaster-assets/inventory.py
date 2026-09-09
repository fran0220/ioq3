"""Offline authorized PK3 inventory, dependency graph and bounded coverage report.

Never extracts ZIP members, invokes generators, or infers full-game completeness.
Input order is explicit low-to-high VFS priority, not guessed filesystem order.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
import wave
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def qpath(value):
    value = value.replace('\\', '/').lower()
    if not value or value.startswith('/') or ':' in value or any(p in {'', '.', '..'} for p in value.split('/')):
        raise ValueError('Unsafe virtual path: ' + value)
    return value


def section(data, offset, size):
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError('Binary section outside file')
    return data[offset:offset + size]


def cstring(data):
    return data.split(b'\0', 1)[0].decode('ascii')


def tokens(text):
    # Comments are tokens too, so // inside a quoted string is preserved.
    pattern = r'"([^"\n]*)"|//[^\n]*|/\*[\s\S]*?\*/|([{}])|([^\s{}"]+)'
    return [next(v for v in m.groups() if v is not None)
            for m in re.finditer(pattern, text) if any(v is not None for v in m.groups())]


def shader_blocks(text):
    ts = tokens(text)
    i = 0
    while i < len(ts):
        name = qpath(ts[i]); i += 1
        if i >= len(ts) or ts[i] != '{':
            raise ValueError('Shader missing opening brace')
        depth, body = 1, []
        i += 1
        while i < len(ts) and depth:
            t = ts[i]; i += 1
            depth += (t == '{') - (t == '}')
            if depth:
                body.append(t)
        if depth:
            raise ValueError('Unclosed shader')
        yield name, body


def shader_refs(body):
    refs = []
    commands = {'map', 'clampmap', 'animmap', 'videomap', 'skyparms', 'qer_editorimage', 'q3map_lightimage', 'normalmap', 'specularmap'}
    for i, token in enumerate(body):
        command = token.lower()
        if command not in commands or i + 1 >= len(body):
            continue
        if command == 'skyparms':
            for at in (i + 1, i + 3):
                if at < len(body) and body[at] not in {'-', 'full'}:
                    refs.extend((body[at] + '_' + side, 'sky') for side in ('rt', 'lf', 'bk', 'ft', 'up', 'dn'))
        elif command == 'animmap':
            # Frames stop at the next stage directive, even when lines are folded.
            for value in body[i + 2:]:
                if '/' not in value and not re.search(r'\.(tga|jpg|png)$', value, re.I):
                    break
                refs.append((value, 'animmap'))
        else:
            refs.append((body[i + 1], command))
    return refs


def inspect(path, data):
    """Return metadata and (reference, reason) pairs; not full format validation."""
    ext = PurePosixPath(path).suffix
    meta, refs = {}, []
    if ext == '.bsp':
        if section(data, 0, 8) != b'IBSP' + struct.pack('<i', 46):
            raise ValueError('Expected Q3 IBSP46')
        lumps = [section(data, *struct.unpack_from('<2i', section(data, 8, 136), i * 8)) for i in range(17)]
        if len(lumps[1]) % 72 or len(lumps[7]) % 40:
            raise ValueError('Malformed BSP shader/model lump')
        refs += [(cstring(lumps[1][i:i + 64]), 'bsp-shader') for i in range(0, len(lumps[1]), 72)]
        entities, entity = [], None
        ts = tokens(lumps[0].decode('latin1').rstrip('\0'))
        i = 0
        while i < len(ts):
            t = ts[i]; i += 1
            if t == '{':
                if entity is not None:
                    raise ValueError('Nested BSP entity')
                entity = {}
            elif t == '}':
                if entity is None:
                    raise ValueError('Unexpected BSP entity close')
                entities.append(entity); entity = None
            else:
                if entity is None or i >= len(ts) or ts[i] in {'{', '}'}:
                    raise ValueError('Malformed BSP entity')
                entity[t] = ts[i]; i += 1
        if entity is not None:
            raise ValueError('Unclosed BSP entity')
        for e in entities:
            for k in ('model', 'model2', 'noise', 'music', 'shader', 'targetShaderName', 'targetShaderNewName'):
                for value in e.get(k, '').split():
                    if not value.startswith('*'):
                        refs.append((value, 'entity-' + k))
        models = []
        for i in range(0, len(lumps[7]), 40):
            bounds = struct.unpack_from('<6f', lumps[7], i)
            if not all(math.isfinite(v) for v in bounds) or any(bounds[a] > bounds[a + 3] for a in range(3)):
                raise ValueError('Invalid BSP bounds')
            models.append({'inline_model': '*' + str(i // 40), 'bounds_q3': bounds,
                           'size_q3': [bounds[a + 3] - bounds[a] for a in range(3)]})
        meta = {'entities': entities, 'model_bounds': models,
                'measurement_basis': 'compiled BSP units; bounds are not connector dimensions',
                'logic_lump_hashes': {str(i): sha(lumps[i]) for i in (0, 2, 3, 4, 6, 7, 8, 9, 16)}}
        refs.append((path[:-4] + '.aas', 'bot-navigation-companion'))
    elif ext == '.md3':
        h = struct.unpack('<4si64s9i', section(data, 0, 108))
        # Tag-only first-person hand/attachment models legitimately have no surfaces.
        if h[:2] != (b'IDP3', 15) or h[-1] != len(data) or not 0 <= h[6] <= 32 or not 1 <= h[4] <= 1024 or not 0 <= h[5] <= 16:
            raise ValueError('Invalid MD3 header')
        frames, tags, offset = h[4], h[5], h[10]
        framedata = section(data, h[8], frames * 56)
        tagdata = section(data, h[9], frames * tags * 112)
        meta = {'frames': frames, 'tags': [cstring(tagdata[i * 112:i * 112 + 64]) for i in range(tags)], 'surfaces': []}
        meta['frame_bounds_q3'] = [struct.unpack_from('<6f', framedata, i * 56) for i in range(frames)]
        meta['first_frame_tag_origin_axis'] = [struct.unpack_from('<12f', tagdata, i * 112 + 64) for i in range(tags)]
        for _ in range(h[6]):
            s = struct.unpack('<4s64s10i', section(data, offset, 108))
            if s[0] != b'IDP3' or s[-1] < 108:
                raise ValueError('Invalid MD3 surface')
            block = section(data, offset, s[-1])
            shaders = section(block, s[8], s[4] * 68)
            refs += [(cstring(shaders[i:i + 64]), 'md3-shader') for i in range(0, len(shaders), 68) if cstring(shaders[i:i + 64])]
            meta['surfaces'].append({'vertices': s[5], 'triangles': s[6], 'runtime_count_ok': s[5] < 1000 and s[6] * 3 < 6000})
            offset += s[-1]
        if offset != len(data):
            raise ValueError('Invalid MD3 end')
        if path.startswith('models/players/'):
            refs.append((str(PurePosixPath(path).parent / 'animation.cfg'), 'player-animation-convention'))
    elif ext == '.iqm':
        h = struct.unpack('<16s27I', section(data, 0, 124))
        if h[0] != b'INTERQUAKEMODEL\0' or h[1] != 2 or h[2] != len(data):
            raise ValueError('Invalid IQM2 header')
        text = section(data, h[5], h[4])
        def name(at):
            return cstring(section(text, at, len(text) - at))
        meshes = section(data, h[7], h[6] * 24)
        for i in range(h[6]):
            refs.append((name(struct.unpack_from('<I', meshes, i * 24 + 4)[0]), 'iqm-material'))
        anims = section(data, h[19], h[18] * 20)
        animations = []
        for i in range(h[18]):
            n, first, count, rate, flags = struct.unpack_from('<3IfI', anims, i * 20)
            animations.append({'name': name(n), 'first': first, 'frames': count, 'fps': rate, 'loop': bool(flags & 1)})
        meta = {'joints': h[14], 'frames': h[20], 'animations': animations}
    elif ext == '.skin':
        for line in data.decode('latin1').splitlines():
            line = line.split('//')[0].strip()
            if ',' in line:
                surface, material = line.split(',', 1)
                if material.strip() and not surface.startswith('tag_'):
                    refs.append((material.strip(), 'skin-material'))
    elif ext == '.wav':
        with wave.open(io.BytesIO(data)) as sound:
            meta = {'channels': sound.getnchannels(), 'sample_rate': sound.getframerate(),
                    'sample_width': sound.getsampwidth(), 'frames': sound.getnframes()}
    elif ext == '.aas':
        if section(data, 0, 4) != b'EAAS':
            raise ValueError('Invalid AAS magic')
        meta = {'version': struct.unpack('<i', section(data, 4, 4))[0], 'validation': 'header-only; BSP checksum and bot reachability require engine'}
    elif path.endswith('animation.cfg'):
        rows = []
        for line in data.decode('latin1').splitlines():
            values = line.split('//')[0].split()
            if len(values) >= 4 and all(re.fullmatch(r'-?\d+(?:\.\d+)?', v) for v in values[:4]):
                rows.append([float(v) for v in values[:4]])
        meta = {'animation_rows_first_count_loop_fps': rows, 'semantic_names_require_game_code': True}
    return meta, refs


def category(path):
    if path.startswith('maps/'):
        return 'map-logic'
    if path.startswith('models/players/'):
        return 'characters'
    if path.startswith(('models/weapons', 'sound/weapons')):
        return 'weapons' if path.startswith('models/') else 'audio'
    if path.startswith(('sound/', 'music/')):
        return 'audio'
    if path.startswith(('gfx/', 'sprites/')):
        return 'effects'
    if path.startswith(('textures/', 'models/mapobjects/', 'env/')):
        return 'environment'
    return 'shared-or-unclassified'


def scan(spec, base):
    if spec.get('scope') not in {'demo', 'full-user-declared', 'partial'} or not spec.get('authorization'):
        raise ValueError('Explicit scope and authorization required')
    if not spec.get('archives'):
        raise ValueError('No authorized input archives')
    files, sources, contents, warnings = {}, [], {}, []
    for priority, source in enumerate(spec['archives']):
        path = (base / source['path']).resolve()
        if not source.get('provenance') or not re.fullmatch('[0-9a-f]{64}', source.get('sha256', '')):
            raise ValueError('Every source requires provenance and pinned SHA256')
        if sha(path.read_bytes()) != source['sha256']:
            raise ValueError('Source SHA256 mismatch: ' + path.name)
        sources.append({'priority': priority, 'filename': path.name, 'sha256': source['sha256'], 'provenance': source['provenance']})
        with zipfile.ZipFile(path) as archive:
            seen = set()
            if sum(z.file_size for z in archive.infolist()) > 4 * 1024**3:
                raise ValueError('Archive exceeds 4 GiB uncompressed budget')
            for z in archive.infolist():
                if z.is_dir():
                    continue
                name = qpath(z.filename)
                if name in seen:
                    raise ValueError('Ambiguous case/duplicate entry in archive: ' + name)
                seen.add(name)
                if z.file_size > 256 * 1024**2:
                    raise ValueError('Entry exceeds 256 MiB budget: ' + name)
                data = archive.read(z)
                version = {'source': priority, 'sha256': sha(data), 'bytes': len(data)}
                old = files.get(name, {}).get('versions', [])
                files[name] = {'path': name, 'category': category(name), **version, 'versions': old + [version]}
                contents[name] = data
    definitions = {}
    edges = []
    for path, data in contents.items():
        try:
            meta, refs = inspect(path, data)
            files[path]['metadata'] = meta
            if path.endswith('.shader'):
                for name, body in shader_blocks(data.decode('latin1')):
                    definitions.setdefault(name, []).append(path)
                    edges.extend({'from': 'shader:' + name, 'reference': ref, 'reason': reason} for ref, reason in shader_refs(body))
            edges.extend({'from': path, 'reference': ref, 'reason': reason} for ref, reason in refs)
        except (ValueError, struct.error, UnicodeError, wave.Error, EOFError) as error:
            warnings.append({'path': path, 'error': str(error)})
    for name, scripts in definitions.items():
        if len(scripts) > 1:
            warnings.append({'shader': name, 'error': 'Multiple shader definitions; engine script ordering must be checked', 'scripts': scripts})
    for edge in edges:
        ref = edge['reference']
        if ref.startswith(('$', '*')) or ref == '-':
            edge.update(status='builtin', targets=[])
            continue
        try:
            ref = qpath(ref)
        except ValueError:
            edge.update(status='invalid-reference', targets=[])
            continue
        targets = []
        # Shader directives resolve images, not another shader with that name.
        stem = str(PurePosixPath(ref).with_suffix('')) if PurePosixPath(ref).suffix else ref
        material = edge['reason'] in {'bsp-shader', 'md3-shader', 'iqm-material', 'skin-material',
                                     'entity-shader', 'entity-targetShaderName', 'entity-targetShaderNewName'}
        # R_FindShaderEx strips extensions before looking up shader text.
        if material and stem in definitions:
            targets = ['shader:' + stem]
        elif ref in files:
            targets = [ref]
        elif PurePosixPath(ref).suffix in {'', '.tga', '.jpg', '.jpeg', '.png', '.pcx', '.bmp'}:
            targets = [stem + ext for ext in ('.tga', '.jpg', '.jpeg', '.png', '.pcx', '.bmp') if stem + ext in files]
        edge.update(status='resolved' if len(targets) == 1 else 'ambiguous' if targets else 'missing', targets=targets)
    for name, scripts in definitions.items():
        edges.append({'from': 'shader:' + name, 'reference': name, 'reason': 'shader-definition',
                      'status': 'resolved' if len(scripts) == 1 else 'ambiguous', 'targets': sorted(set(scripts))})
    return {'schema_version': 1, 'scope': spec['scope'], 'authorization': spec['authorization'],
            'full_game_complete': False, 'coverage_denominator': 'only supplied archives; never proves full game',
            'sources': sources, 'files': sorted(files.values(), key=lambda v: v['path']),
            'shaders': definitions, 'dependencies': edges, 'warnings': warnings,
            'limitations': ['Dynamic code/QVM registrations, skin selection, sound aliases and runtime shader remaps require engine capture.',
                            'Unknown formats are hashed but not parsed. Dependency graph is conservative, not a complete runtime trace.',
                            'BSP bounds/entity origins provide reference units, not inferred connector sizes or a new collision mesh.',
                            'Demo/partial inputs cannot satisfy the full-source production gate.']}


def dependencies(inventory, roots):
    valid = {f['path'] for f in inventory['files']} | {'shader:' + n for n in inventory['shaders']}
    if not roots or any(r not in valid for r in roots):
        raise ValueError('Dependency roots must exist in this inventory')
    pending, visited, edges = list(roots), set(), []
    by_source = {}
    for edge in inventory['dependencies']:
        by_source.setdefault(edge['from'], []).append(edge)
    while pending:
        node = pending.pop()
        if node in visited:
            continue
        visited.add(node)
        for edge in by_source.get(node, []):
            edges.append(edge)
            pending.extend(edge['targets'])
    return {'roots': roots, 'nodes': sorted(visited), 'dependencies': edges,
            'unresolved': [e for e in edges if e['status'] not in {'resolved', 'builtin'}],
            'full_game_complete': False, 'scope': inventory['scope']}


def coverage(inventory, replacements):
    known = {f['path']: f for f in inventory['files']}
    if replacements.get('inventory_sha256') != sha(json.dumps(inventory, sort_keys=True).encode()):
        raise ValueError('Coverage mapping must pin this exact canonical inventory SHA256')
    mapped = {}
    gates = {'provenance', 'prototype', 'blender', 'format', 'visual', 'web-hdr', 'web-ldr', 'gameplay'}
    for entry in replacements.get('replacements', []):
        path = qpath(entry['source_path'])
        if path not in known or path in mapped:
            raise ValueError('Unknown or duplicate replacement source: ' + path)
        if entry.get('source_sha256') != known[path]['sha256']:
            raise ValueError('Replacement source hash mismatch')
        approved = entry.get('gates', {})
        # Evidence is a reference to actual review, not an automatic visual judgment.
        passed = {k for k, v in approved.items() if isinstance(v, dict) and v.get('passed') is True and v.get('evidence')}
        mapped[path] = {'asset_id': entry['asset_id'], 'accepted': gates <= passed,
                        'missing_gates': sorted(gates - passed)}
    accepted = sum(v['accepted'] for v in mapped.values())
    return {'scope': inventory['scope'], 'full_game_complete': False, 'inventoried_files': len(known),
            'mapped_files': len(mapped), 'accepted_files': accepted, 'unmapped': sorted(known.keys() - mapped.keys()),
            'replacements': mapped, 'missing_dependencies': [e for e in inventory['dependencies'] if e['status'] != 'resolved' and e['status'] != 'builtin'],
            'note': 'Counts cover supplied archives only; evidence references still require human audit.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('scan'); p.add_argument('--sources', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('coverage'); p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--replacements', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('dependencies'); p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--root', action='append', required=True); p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'scan':
        report = scan(json.loads(args.sources.read_text()), args.sources.resolve().parent)
        report['canonical_sha256'] = sha(json.dumps(report, sort_keys=True).encode())
    else:
        inv = json.loads(args.inventory.read_text()); inv.pop('canonical_sha256', None)
        report = dependencies(inv, args.root) if args.command == 'dependencies' else coverage(inv, json.loads(args.replacements.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'output': str(args.output), 'full_game_complete': False, 'warnings': len(report.get('warnings', []))}))


if __name__ == '__main__':
    main()
