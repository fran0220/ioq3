"""Build original 2D environmental material overrides; never copy source BSP/data."""
import argparse
import collections
import hashlib
import io
import json
from pathlib import Path
import struct
import zipfile

from PIL import Image, ImageOps

SOURCE_SHA = 'e77abad2466f45a0a7ea018445528f9b95a0fe7789fa1abc1a7718bbf0754b08'
TILES = ['panel', 'ceramic', 'steel', 'plaster', 'floor', 'stone', 'tread',
         'ceiling', 'vent', 'arch', 'cyan', 'orange', 'lava', 'rock', 'sky', 'light']


def material(name):
    if name.startswith('textures/common/') or name == 'noshader':
        return None
    if name.startswith('textures/sfx/flame'):
        return None  # Owned by effects; preserve alpha/deformation instead of opaque quads.
    if '/skies/' in name:
        return 'sky'
    if '/liquids/' in name:
        return 'lava'
    if '/gothic_light/' in name:
        return 'light'
    if '/gothic_ceiling/' in name or 'roof' in name:
        return 'ceiling'
    if 'stairtop' in name or 'metalbridge' in name:
        return 'tread'
    if 'stepborder' in name:
        return 'orange'
    if '/gothic_floor/' in name:
        return 'floor'
    if '/gothic_door/' in name:
        return 'arch' if 'arch' in name or 'columna' in name else 'panel'
    if '/organics/' in name or '/skin/' in name:
        return 'rock'
    if 'supportborder_blue' in name or '/sfx/computer' in name:
        return 'cyan'
    if '/gothic_block/' in name:
        return 'ceramic'
    if 'baseboard' in name:
        return 'arch'
    if '/gothic_trim/' in name:
        return 'steel'
    if '/gothic_wall/' in name:
        return 'plaster'
    return 'panel'


def surfaces(data):
    if data[:8] != b'IBSP.\0\0\0':
        raise ValueError('Expected BSP46')
    lumps = [struct.unpack_from('<ii', data, 8 + i * 8) for i in range(17)]
    for offset, length in lumps:
        if offset < 0 or length < 0 or offset + length > len(data):
            raise ValueError('Invalid lump bounds')
    offset, length = lumps[1]
    names = [data[i:i + 64].split(b'\0')[0].decode('ascii')
             for i in range(offset, offset + length, 72)]
    offset, length = lumps[13]
    counts = collections.Counter(struct.unpack_from('<i', data, i)[0]
                                 for i in range(offset, offset + length, 104))
    return [(name, counts[i]) for i, name in enumerate(names)]


def shader(name, tile):
    texture = f'textures/remaster_environment/{tile}.tga'
    if tile == 'sky':
        return f'''{name}
{{
 surfaceparm sky
 surfaceparm noimpact
 surfaceparm nolightmap
 skyparms - 512 -
 {{ map {texture}
    tcMod scale 2 2
    tcMod scroll 0.002 0.001
    rgbGen identityLighting }}
}}
'''
    if tile == 'lava':
        return f'''{name}
{{
 surfaceparm lava
 surfaceparm trans
 cull disable
 {{ map {texture}
    tcMod scroll 0.015 0.008
    rgbGen identityLighting }}
}}
'''
    return f'''{name}
{{
 {{ map $lightmap
    rgbGen identity }}
 {{ map {texture}
    blendFunc GL_DST_COLOR GL_ZERO
    rgbGen identity }}
}}
'''


def build(source, atlas, output):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError('Reference hash differs; explicitly review new input before adapting')
    output.mkdir(parents=True, exist_ok=True)
    entries = {}
    image = Image.open(atlas).convert('RGB')
    for i, tile in enumerate(TILES):
        x, y = i % 4, i // 4
        crop = image.crop((round(x * image.width / 4), round(y * image.height / 4),
                           round((x + 1) * image.width / 4), round((y + 1) * image.height / 4)))
        if tile == 'sky':
            # Discard generated atlas frame, then mirror edges continuously.
            margin = round(min(crop.size) * .06)
            cloud = crop.crop((margin, margin, crop.width - margin, crop.height - margin))
            cloud = cloud.resize((256, 256), Image.Resampling.LANCZOS)
            crop = Image.new('RGB', (512, 512))
            crop.paste(cloud, (0, 0))
            crop.paste(ImageOps.mirror(cloud), (256, 0))
            crop.paste(ImageOps.flip(cloud), (0, 256))
            crop.paste(ImageOps.flip(ImageOps.mirror(cloud)), (256, 256))
        buffer = io.BytesIO()
        crop.resize((512, 512), Image.Resampling.LANCZOS).save(buffer, format='TGA')
        entries[f'textures/remaster_environment/{tile}.tga'] = buffer.getvalue()
    coverage = {}
    mapped_slots = set()
    with zipfile.ZipFile(source) as reference:
        for mapname in ['q3dm1', 'q3dm7', 'q3dm17', 'q3tourney2']:
            bsp = reference.read(f'maps/{mapname}.bsp')
            rows = []
            for name, count in surfaces(bsp):
                tile = material(name)
                if tile and count:
                    mapped_slots.add(name)
                rows.append({'slot': name, 'surfaces': count, 'material': tile,
                             'status': 'material-candidate' if tile and count else 'not-environment-or-not-drawn',
                             'geometry_remade': False})
            coverage[mapname] = {'source_bsp_sha256': hashlib.sha256(bsp).hexdigest(),
                                 'bsp_modified': False, 'slots': rows,
                                 'runtime_accepted': False}
    # Unique names avoid engine-dependent duplicate shader script ordering.
    entries['scripts/environment_materials_v1.shader'] = '\n'.join(
        shader('textures/remaster_environment/' + tile, tile) for tile in TILES).encode()
    package = output / 'environment-materials-v1.pk3'
    with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2026, 9, 10, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    report = {'source_scope': 'private-demo-reference-not-release', 'full_game_complete': False,
              'source_archive_sha256': SOURCE_SHA, 'atlas_sha256': hashlib.sha256(atlas.read_bytes()).hexdigest(),
              'package_sha256': hashlib.sha256(package.read_bytes()).hexdigest(),
              'entries': {k: hashlib.sha256(v).hexdigest() for k, v in entries.items()}, 'maps': coverage}
    (output / 'environment-coverage.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'package': str(package), 'bytes': package.stat().st_size,
                      'mapped_source_slots': len(mapped_slots), 'runtime_shaders': len(TILES), 'maps': list(coverage)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('atlas', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    build(args.source, args.atlas, args.output)
