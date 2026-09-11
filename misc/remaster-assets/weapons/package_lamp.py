"""Package Painter's lamp glow as an additive companion surface, never a light.

CLI: package_lamp.py downloaded-painter.png
Requires renderer support for opaque replacement + strictly additive companion.
This pack does not hide source surfaces or install any world entity.
"""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

from PIL import Image, ImageEnhance


def package(source):
    original = source.read_bytes()
    output = Path('assets/remaster/effects')
    output.mkdir(parents=True, exist_ok=True)
    image = Image.open(source).convert('RGB').resize((448, 448), Image.Resampling.LANCZOS)
    # Intensity is authored into the additive image; renderer's strict companion
    # shader can use identity. Padding adds zero light, not an alpha channel.
    image = ImageEnhance.Brightness(image).enhance(.25)
    padded = Image.new('RGB', (512, 512), (0, 0, 0))
    padded.paste(image, (32, 32))
    texture = output / 'environment_lamp_glow.tga'
    padded.save(texture)
    shader = output / 'environment_lamp_glow.shader'
    shader.write_text('''models/remaster/environment_fx/lamp_glow
{
    cull disable
    {
        map textures/remaster_environment_fx/lamp_glow.tga
        blendFunc GL_ONE GL_ONE
        rgbGen identity
    }
}
''')
    files = {'textures/remaster_environment_fx/lamp_glow.tga': texture.read_bytes(),
             'scripts/remaster_environment_lamp_glow.shader': shader.read_bytes()}
    target = Path('assets/remaster/runtime/effect-environment-lamp-v1-candidate.pk3')
    with zipfile.ZipFile(target, 'w') as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 9, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    receipt = {
        'asset_id': 'effect-environment-lamp-v1', 'runtime_accepted': False,
        'source': 'Original Amp Painter cyan capsule, no game texture input',
        'source_url': 'https://ampcode.com/user-content/attachments/830a1a6e0a2dbbd76f2206163b6b30af7694763d500361bf0cb8c209bcf9ac1d-file.png',
        'prototype_sha256': hashlib.sha256(original).hexdigest(),
        'cost': {'status': 'not-exposed-by-amp-painter', 'actual_usd': None},
        'review': 'Inspected cyan filament/capsule with narrow halo, no flame, sparks or text; runtime pending',
        'derivation': 'RGB Lanczos 448 square, quarter intensity, 32px exact-black padding to 512 square',
        'integration': 'Independent quad in opaque replacement MD3; ONE/ONE, identity, default depth test, no depthWrite/equal; wait for renderer atomic companion support',
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        'package_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    Path('assets/remaster/receipts/effect-environment-lamp-v1.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(target)


if __name__ == '__main__':
    package(Path(sys.argv[1]))
