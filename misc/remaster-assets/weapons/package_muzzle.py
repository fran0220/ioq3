"""Derive an additive rocket muzzle sprite from an inspected Painter image.

Black is zero light, not fabricated transparency. This is a 2D effect branch,
not a generated 3D mesh or a replacement for the full combat VFX set.
"""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

from PIL import Image

source = Path(sys.argv[1])
original = source.read_bytes()
output = Path('assets/remaster/effects')
output.mkdir(parents=True, exist_ok=True)
image = Image.open(source).convert('RGB')
image = image.resize((256, 256), Image.Resampling.LANCZOS)
texture = output / 'rocket_muzzle.tga'
image.save(texture)
shader = output / 'rocket_muzzle.shader'
shader.write_text('''gfx/remaster/rocket_muzzle
{
    cull disable
    sort additive
    {
        clampmap gfx/remaster/rocket_muzzle.tga
        blendFunc add
        rgbGen vertex
        alphaGen vertex
    }
}
''')
files = {'gfx/remaster/rocket_muzzle.tga': texture.read_bytes(),
         'scripts/remaster_rocket_muzzle.shader': shader.read_bytes()}
package = Path('assets/remaster/runtime/effect-rocket-muzzle-v1-candidate.pk3')
with zipfile.ZipFile(package, 'w') as archive:
    for name, data in sorted(files.items()):
        info = zipfile.ZipInfo(name, (2026, 9, 10, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, data)
receipt = {
    'asset_id': 'effect-rocket-muzzle-v1', 'runtime_accepted': False,
    'source': 'Amp Painter; newly authored combustion sprite, no original game texture',
    'source_url': 'https://ampcode.com/user-content/attachments/b911d12c1e5f0514a6745509fdf3e6b494480d9d343581bfeaf5f9ec3e05d96b-file.png',
    'prototype_sha256': hashlib.sha256(original).hexdigest(),
    'review': 'Inspected compact four-lobed orange/ivory ignition, black padding; additive-only, no alpha claim',
    'cost': {'status': 'not-exposed-by-amp-painter', 'actual_usd': None},
    'derivation': 'Pillow RGB Lanczos 256x256 TGA; zero-light black additive blend, no depthWrite',
    'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
    'package_sha256': hashlib.sha256(package.read_bytes()).hexdigest(),
}
Path('assets/remaster/receipts/effect-rocket-muzzle-v1.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(package)
