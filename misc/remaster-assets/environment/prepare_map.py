"""Private reference-map visual adaptation. Output is NOT redistributable content."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile

from package import SOURCE_SHA, material


def measure(data):
    """Per-surface bounds for authoring, not inferred connector/clearance data."""
    lumps = [struct.unpack_from('<ii', data, 8 + i * 8) for i in range(17)]
    offset, length = lumps[1]
    names = [data[i:i + 64].split(b'\0')[0].decode()
             for i in range(offset, offset + length, 72)]
    offset, length = lumps[10]
    vertices = [struct.unpack_from('<3f', data, i) for i in range(offset, offset + length, 44)]
    offset, length = lumps[13]
    result = []
    for index, start in enumerate(range(offset, offset + length, 104)):
        slot, _, kind, first, count = struct.unpack_from('<5i', data, start)
        points = vertices[first:first + count]
        if not points:
            continue
        result.append({'surface_index': index, 'shader': names[slot], 'surface_type': kind,
                       'minimum': [min(p[a] for p in points) for a in range(3)],
                       'maximum': [max(p[a] for p in points) for a in range(3)]})
    return result


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
        assert out[start + 64:start + 72] == data[start + 64:start + 72], 'Physics flags changed'
    # Preserve strongest-channel intensity and shadow boundaries, remove red cast.
    # Luminance grayscale made red-lit areas much darker; this is an art revision,
    # not a claim that original illumination or HDR radiometry is preserved.
    offset, length = lumps[14]
    for start in range(offset, offset + length, 3):
        r, g, b = data[start:start + 3]
        value = max(r, g, b)
        out[start:start + 3] = bytes((value, value, value))
    # Apply the same palette transform to vertex-lit BSP surfaces and model
    # lightgrid samples. Keep alpha, spatial data, and encoded directions exact.
    offset, length = lumps[10]
    for start in range(offset, offset + length, 44):
        value = max(data[start + 40:start + 43])
        out[start + 40:start + 43] = bytes((value, value, value))
        assert out[start:start + 40] == data[start:start + 40]
        assert out[start + 43] == data[start + 43]
    offset, length = lumps[15]
    for start in range(offset, offset + length, 8):
        for color in (start, start + 3):
            value = max(data[color:color + 3])
            out[color:color + 3] = bytes((value, value, value))
        assert out[start + 6:start + 8] == data[start + 6:start + 8]
    hashes = []
    for i, (offset, length) in enumerate(lumps):
        old, new = data[offset:offset + length], out[offset:offset + length]
        if i not in (1, 10, 14, 15):
            assert old == new, f'Logic/geometry lump {i} changed'
        hashes.append({'lump': i, 'before': hashlib.sha256(old).hexdigest(),
                       'after': hashlib.sha256(new).hexdigest(), 'identical': old == new})
        if i == 1:
            before_flags = b''.join(old[n + 64:n + 72] for n in range(0, len(old), 72))
            after_flags = b''.join(new[n + 64:n + 72] for n in range(0, len(new), 72))
            hashes[-1]['physics_flags_before_sha256'] = hashlib.sha256(before_flags).hexdigest()
            hashes[-1]['physics_flags_after_sha256'] = hashlib.sha256(after_flags).hexdigest()
        if i in (10, 15):
            stride = 44 if i == 10 else 8
            # Includes positions, both UV sets, normals and alpha for drawverts;
            # includes both encoded direction bytes for lightgrid samples.
            protected = lambda chunk, n: chunk[n:n + 40] + chunk[n + 43:n + 44] if i == 10 else chunk[n + 6:n + 8]
            before = b''.join(protected(old, n) for n in range(0, len(old), stride))
            after = b''.join(protected(new, n) for n in range(0, len(new), stride))
            assert before == after
            hashes[-1]['non_color_fields_before_sha256'] = hashlib.sha256(before).hexdigest()
            hashes[-1]['non_color_fields_after_sha256'] = hashlib.sha256(after).hexdigest()
    return bytes(out), hashes


def adapt_aas(data, original_checksum, new_checksum):
    # aasfile.h: 12-byte prefix + 14 offset/length pairs. be_aas_file.c:
    # AAS_DData XORs bytes after ident/version with (index * 119) mod 256.
    if len(data) < 124 or data[:4] != b'EAAS':
        raise ValueError('Invalid AAS header')
    version = struct.unpack_from('<I', data, 4)[0]
    if version not in (4, 5):
        raise ValueError('Unsupported AAS version')
    header = bytearray(data[:124])
    if version == 5:
        for i in range(116):
            header[8 + i] ^= (i * 119) & 255
    checksum = struct.unpack_from('<I', header, 8)[0]
    if checksum != original_checksum:
        raise ValueError('Source AAS already mismatches reference BSP')
    for i in range(14):
        offset, length = struct.unpack_from('<ii', header, 12 + i * 8)
        if offset < 0 or length < 0 or offset + length > len(data):
            raise ValueError('Invalid AAS lump bounds')
    struct.pack_into('<I', header, 8, new_checksum)
    if version == 5:
        for i in range(116):
            header[8 + i] ^= (i * 119) & 255
    out = bytes(header) + data[124:]
    changed = [i for i, (old, new) in enumerate(zip(data, out)) if old != new]
    assert set(changed) <= {8, 9, 10, 11}
    assert out[:8] == data[:8] and out[12:] == data[12:]
    return out, {'version': version, 'original_checksum_unsigned': checksum,
                 'new_checksum_unsigned': new_checksum, 'changed_byte_offsets': changed,
                 'before_sha256': hashlib.sha256(data).hexdigest(),
                 'after_sha256': hashlib.sha256(out).hexdigest(),
                 'navigation_payload_before_sha256': hashlib.sha256(data[124:]).hexdigest(),
                 'navigation_payload_after_sha256': hashlib.sha256(out[124:]).hexdigest(),
                 'encoded_lump_table_identical': data[12:124] == out[12:124]}


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('reference', type=Path)
    p.add_argument('private_output', type=Path)
    args = p.parse_args()
    if hashlib.sha256(args.reference.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Unreviewed input')
    args.private_output.mkdir(parents=True, exist_ok=True)
    report = {}
    measurements = {}
    aas_report = {}
    output_package = args.private_output / 'zzzz-environment-private-maps.pk3'
    previous_sha = hashlib.sha256(output_package.read_bytes()).hexdigest() if output_package.exists() else None
    root = Path(__file__).resolve().parents[3]
    # Reuse production checksum implementation, not a guessed MD4 variant.
    with tempfile.TemporaryDirectory() as temporary:
        library = Path(temporary) / 'checksum.so'
        subprocess.run(['cc', '-shared', '-fPIC', '-I' + str(root / 'code/qcommon'),
                        str(root / 'code/qcommon/md4.c'), '-o', str(library)], check=True)
        native = ctypes.CDLL(str(library))
    checksum = native.Com_BlockChecksum
    checksum.argtypes = [ctypes.c_void_p, ctypes.c_int]
    checksum.restype = ctypes.c_uint
    with zipfile.ZipFile(args.reference) as source, zipfile.ZipFile(
            output_package, 'w', zipfile.ZIP_DEFLATED) as target:
        for name in ['q3dm1', 'q3dm7', 'q3dm17', 'q3tourney2']:
            path = f'maps/{name}.bsp'
            original = source.read(path)
            measurements[name] = measure(original)
            data, report[name] = adapt(original)
            target.writestr(zipfile.ZipInfo(path, (2026, 9, 10, 0, 0, 0)), data, compress_type=zipfile.ZIP_DEFLATED)
            aas, aas_report[name] = adapt_aas(source.read(f'maps/{name}.aas'),
                                             checksum(original, len(original)), checksum(data, len(data)))
            target.writestr(zipfile.ZipInfo(f'maps/{name}.aas', (2026, 9, 10, 0, 0, 0)), aas, compress_type=zipfile.ZIP_DEFLATED)
    (args.private_output / 'logic-invariants.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.private_output / 'surface-measurements.json').write_text(json.dumps(measurements, indent=2) + '\n')
    (args.private_output / 'aas-invariants.json').write_text(json.dumps(aas_report, indent=2) + '\n')
    (args.private_output / 'package-hashes.json').write_text(json.dumps({
        'reference_package_sha256': SOURCE_SHA, 'previous_derived_package_sha256': previous_sha,
        'derived_package_sha256': hashlib.sha256(output_package.read_bytes()).hexdigest(),
        'checksum_source_sha256': hashlib.sha256((root / 'code/qcommon/md4.c').read_bytes()).hexdigest(),
    }, indent=2) + '\n')
    print('Private visual maps written; 13/17 BSP lumps unchanged; remaining changes only shader names and lighting RGB; AAS only checksum bytes 8–11 changed')
