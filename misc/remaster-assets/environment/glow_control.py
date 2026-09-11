"""Remove only additive MD3 companion surfaces; retain transforms and frame bounds."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from md3_static import HEADER, SURFACE, read_md3


def control(source, output):
    with zipfile.ZipFile(source) as z:
        files = {name: z.read(name) for name in z.namelist()}
    changes = []
    for name, data in list(files.items()):
        if not name.endswith('.md3'):
            continue
        header = list(HEADER.unpack_from(data))
        offset = header[10]
        blocks, removed = [], 0
        for _ in range(header[6]):
            fields = SURFACE.unpack_from(data, offset)
            shader = data[offset+fields[8]:offset+fields[8]+64].split(b'\0')[0].decode()
            if shader == 'models/remaster/environment_fx/lamp_glow':
                removed += 1
            else:
                blocks.append(data[offset:offset+fields[11]])
            offset += fields[11]
        if not removed:
            continue
        if not blocks:
            raise ValueError('Would remove entire model')
        header[6] = len(blocks)
        header[-1] = header[10] + sum(map(len, blocks))
        derived = HEADER.pack(*header) + data[HEADER.size:header[10]] + b''.join(blocks)
        assert read_md3(derived)['bounds'] == read_md3(data)['bounds']
        files[name] = derived
        changes.append({'model': name, 'removed_companion_surfaces': removed,
                        'before_sha256': sha256(data).hexdigest(), 'after_sha256': sha256(derived).hexdigest(),
                        'frame_bounds_and_opaque_blocks_unchanged': True})
    if not changes:
        raise ValueError('No glow surfaces found')
    with zipfile.ZipFile(output, 'w') as z:
        for name, data in sorted(files.items()):
            z.writestr(zipfile.ZipInfo(name, (2026, 9, 11, 0, 0, 0)), data, compress_type=zipfile.ZIP_DEFLATED)
    output.with_suffix('.json').write_text(json.dumps({'source_sha256': sha256(source.read_bytes()).hexdigest(),
        'control_sha256': sha256(output.read_bytes()).hexdigest(), 'changes': changes}, indent=2)+'\n')


if __name__ == '__main__':
    control(Path(sys.argv[1]), Path(sys.argv[2]))
