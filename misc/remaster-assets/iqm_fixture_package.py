"""Package only the synthetic Blender IQM test fixture for engine integration.

Never ships production/commercial source or invokes a generator. CLI: fixture-dir.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
import zipfile

from iqm_validate import read_iqm


def package(root):
    contract=json.loads((root/'out/animation-contract.json').read_text())
    data=(root/'out/model.iqm').read_bytes(); model=read_iqm(data)
    if not contract['classification'].startswith('TEST ONLY') or contract['model_sha256'] != hashlib.sha256(data).hexdigest():
        raise ValueError('Only pinned TEST ONLY fixture may use synthetic materials')
    colors={'models/remaster/iqm_test_cyan':(8,179,230), 'models/remaster/iqm_test_orange':(255,51,6)}
    if {m['material'] for m in model['meshes']} != set(colors):
        raise ValueError('Unexpected fixture material contract')
    files={'models/remaster/iqm_fixture.iqm':data,
           'README_IQM_TEST_ONLY.txt':b'Synthetic asymmetric rig fixture. Not a remastered character. No commercial assets. No gameplay acceptance.\n'}
    shaders=[]
    for name, color in colors.items():
        # TGA 4x4 uncompressed RGB, top-left origin; white upper-left and dark
        # lower-right corners deliberately make UV orientation visible.
        header=struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,4,4,24,32)
        pixels=[]
        for y in range(4):
            for x in range(4):
                rgb=(255,255,255) if (x,y)==(0,0) else (20,20,20) if (x,y)==(3,3) else color
                pixels.extend(reversed(rgb))
        files[name+'.tga']=header+bytes(pixels)
        shaders.append(name+'\n{\n {\n  map '+name+'.tga\n  rgbGen lightingDiffuse\n }\n}\n')
    files['scripts/remaster_iqm_fixture.shader']='\n'.join(shaders).encode()
    destination=root/'iqm-fixture-test-only.pk3'
    with zipfile.ZipFile(destination,'w') as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o644<<16
            z.writestr(info,data)
    with zipfile.ZipFile(destination) as z:
        if z.testzip() is not None:
            raise ValueError('Fixture ZIP CRC failed')
    report={'classification':'TEST ONLY', 'pk3_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
            'bytes':destination.stat().st_size, 'files':{name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())},
            'model_path':'models/remaster/iqm_fixture.iqm','frames':len(model['frames']),'clips':model['clips'],
            'runtime_accepted':False}
    (root/'fixture-package.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return destination


if __name__=='__main__':
    package(Path(sys.argv[1]).resolve())
