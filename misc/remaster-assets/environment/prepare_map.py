"""Private reference-map visual adaptation. Output is NOT redistributable content."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile

from package import SOURCE_SHA, material


def adapt(data):
    out = bytearray(data)
    lumps = [struct.unpack_from('<ii', data, 8 + i * 8) for i in range(17)]
    offset, length = lumps[1]
    for start in range(offset, offset + length, 72):
        name = data[start:start + 64].split(b'\0')[0].decode()
        tile = material(name)
        if tile:
            replacement = ('textures/remaster_environment/' + tile).encode()
            out[start:start + 64] = replacement.ljust(64, b'\0')
    # Preserve strongest-channel intensity and shadow boundaries, remove red cast.
    # Luminance grayscale made red-lit areas much darker; this is an art revision,
    # not a claim that original illumination or HDR radiometry is preserved.
    offset, length = lumps[14]
    for start in range(offset, offset + length, 3):
        r, g, b = data[start:start + 3]
        value = max(r, g, b)
        out[start:start + 3] = bytes((value, value, value))
    hashes = []
    for i, (offset, length) in enumerate(lumps):
        old, new = data[offset:offset + length], out[offset:offset + length]
        if i not in (1, 14):
            assert old == new, f'Logic/geometry lump {i} changed'
        hashes.append({'lump': i, 'before': hashlib.sha256(old).hexdigest(),
                       'after': hashlib.sha256(new).hexdigest(), 'identical': old == new})
    return bytes(out), hashes


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('reference', type=Path)
    p.add_argument('private_output', type=Path)
    args = p.parse_args()
    if hashlib.sha256(args.reference.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Unreviewed input')
    args.private_output.mkdir(parents=True, exist_ok=True)
    report = {}
    with zipfile.ZipFile(args.reference) as source, zipfile.ZipFile(
            args.private_output / 'zzzz-environment-private-maps.pk3', 'w', zipfile.ZIP_DEFLATED) as target:
        for name in ['q3dm1', 'q3dm7', 'q3dm17', 'q3tourney2']:
            path = f'maps/{name}.bsp'
            data, report[name] = adapt(source.read(path))
            target.writestr(path, data)
    (args.private_output / 'logic-invariants.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Private visual maps written; 15/17 lumps unchanged per map; no AAS or logic changes')
