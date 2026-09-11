"""Private controlled MD3 winding probe: triangle indices only, no art changes."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from md3_static import HEADER, SURFACE, read_md3


def probe(source, output, mode):
    changes = []
    with zipfile.ZipFile(source) as z:
        files = {name: z.read(name) for name in z.namelist()}
    for name, original in list(files.items()):
        if not name.endswith('.md3') or 'lantern' not in name:
            continue
        out = bytearray(original)
        header = HEADER.unpack_from(original)
        offset = header[10]
        changed = 0
        for _ in range(header[6]):
            fields = SURFACE.unpack_from(original, offset)
            shader = original[offset+fields[8]:offset+fields[8]+64].split(b'\0')[0].decode()
            if mode == 'all' or shader == 'models/remaster/environment_fx/lamp_glow':
                for triangle in range(fields[6]):
                    pos = offset + fields[7] + triangle * 12
                    a, b, c = struct.unpack_from('<3i', original, pos)
                    struct.pack_into('<3i', out, pos, a, c, b)
                    changed += 1
            offset += fields[11]
        read_md3(out)
        files[name] = out
        changes.append({'model': name, 'triangles_flipped': changed,
                        'before': sha256(original).hexdigest(), 'after': sha256(out).hexdigest()})
    with zipfile.ZipFile(output, 'w') as z:
        for name, data in sorted(files.items()):
            z.writestr(zipfile.ZipInfo(name, (2026, 9, 11, 0, 0, 0)), data, compress_type=zipfile.ZIP_DEFLATED)
    output.with_suffix('.json').write_text(json.dumps({'mode': mode, 'changes': changes,
        'source_sha256': sha256(source.read_bytes()).hexdigest(), 'output_sha256': sha256(output.read_bytes()).hexdigest()}, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('mode', choices=['glow', 'all'])
    a = p.parse_args()
    probe(a.source, a.output, a.mode)
