"""Package generated segmented Sarge for private actual-player testing."""
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'misc/remaster-assets'))
from iqm_validate import read_iqm


def main():
    work = Path(sys.argv[1]).resolve()
    source = work/'segmented'
    report = json.loads((source/'authoring.json').read_text())
    files = {}
    # Numerical timing contract is deliberately authored independently of the
    # private copyrighted archive text; no Demo data is packaged here.
    rows = [(0,30,0,20),(29,1,0,20),(30,30,0,20),(59,1,0,20),(60,30,0,20),(89,1,0,20),
            (90,40,0,18),(130,6,0,15),(136,6,0,15),(142,5,0,20),(147,4,0,20),
            (151,1,0,15),(152,1,0,15),(153,8,8,20),(161,12,12,20),(173,11,11,21),
            (184,10,10,20),(194,10,10,15),(204,10,0,18),(214,6,0,20),(220,8,0,15),
            (228,1,0,15),(229,10,10,15),(239,8,8,15),(247,7,7,15)]
    files['models/players/sarge/animation.cfg'] = ('sex m\nfootsteps boot\n'+''.join(' '.join(map(str,r))+'\n' for r in rows)).encode()
    files['models/players/sarge/weapon_frames.cfg'] = ''.join(f'{weapon} {offset}\n' for weapon,offset in report['weapon_frame_offsets'].items()).encode()
    shaders = []
    image = Image.open(work/'prepared/body.tga').convert('RGB')
    normal = 'models/remaster/characters/sarge_normal'
    specular = 'models/remaster/characters/sarge_specular'
    files[normal+'.tga'] = (work/'prepared/normal.tga').read_bytes()
    # Authored coated armor/cloth dielectric response, not an ORM conversion.
    # RGB is linear F0=.04; alpha is 1-roughness (.28). No bare-metal claim.
    spec = Image.new('RGBA',(4,4),(10,10,10,71))
    data = io.BytesIO()
    spec.save(data,format='TGA')
    files[specular+'.tga'] = data.getvalue()
    report['material'] = {'normal':json.loads((work/'prepared/material-bake.json').read_text()),
                          'response':'authored dielectric F0 .04, roughness .72; coated armor/cloth; no metal or emission',
                          'renderer':'r_pbr 0 / r_glossType 1; specular RGB linear, A=1-roughness'}
    for skin, color in (('default',None),('red','#b42c20'),('blue','#2268c5'),('krusade','#786332')):
        texture = image if color is None else Image.blend(image,ImageOps.colorize(ImageOps.grayscale(image),'#12161c',color),.65)
        data = io.BytesIO()
        texture.save(data,format='TGA')
        name = 'models/remaster/characters/sarge_'+skin
        files[name+'.tga'] = data.getvalue()
        shaders.append(name+'\n{\n {\n stage diffuseMap\n map '+name+'.tga\n rgbGen lightingDiffuse\n }\n {\n stage normalMap\n map '+normal+'.tga\n normalScale 1 1\n }\n {\n stage specularMap\n map '+specular+'.tga\n }\n}\n')
        insignia = Image.new('RGB',(64,64),color or '#26322a')
        draw = ImageDraw.Draw(insignia)
        draw.rectangle((2,2,61,61),outline='#d6d1b2',width=3)
        if skin == 'blue':
            draw.rectangle((12,18,51,26),fill='#f5f2dd')
            draw.rectangle((12,38,51,46),fill='#f5f2dd')
        else:
            draw.polygon([(12,15),(32,33),(52,15),(52,31),(32,49),(12,31)],fill='#f5f2dd')
        data = io.BytesIO()
        insignia.save(data,format='TGA')
        symbol = 'models/remaster/characters/sarge_insignia_'+skin
        files[symbol+'.tga'] = data.getvalue()
        shaders.append(symbol+'\n{\n {\n stage diffuseMap\n map '+symbol+'.tga\n rgbGen lightingDiffuse\n }\n}\n')
        for part in ('lower','upper','head'):
            model = (source/(part+'.iqm')).read_bytes()
            decoded = read_iqm(model)
            files['models/players/sarge/'+part+'.iqm'] = model
            files['models/players/sarge/'+part+'_'+skin+'.skin'] = ''.join(m['name']+','+(symbol if m['name'].startswith('insignia_') else name)+'\n' for m in decoded['meshes']).encode()
    files['scripts/character_sarge_segmented.shader'] = ''.join(shaders).encode()
    report['limitations'] = ['Candidate awaiting actual player combat acceptance',
                             'Authored team insignia placement awaiting all-direction runtime review',
                             'High-to-low baked normal and authored dielectric material need pose/light review',
                             'Back jump still requires authored direction review',
                             'No Demo/QVM/sounds included; standalone game bundle is separate']
    files['character-segmented.json'] = (json.dumps(report,indent=2)+'\n').encode()
    # Must sort after original pak0: existing .skin/cfg otherwise wins even
    # though the newly named IQM itself loads, producing default-shader faces.
    path = work/'zz-character-sarge-v2-segmented.pk3'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(files.items()):
            info = zipfile.ZipInfo(name,(2026,9,10,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info,data)
    print(json.dumps({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),**report},indent=2))


if __name__ == '__main__':
    main()
