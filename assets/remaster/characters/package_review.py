"""Package real generated character for renderer inspection, never client override."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'misc/remaster-assets'))
from iqm_validate import read_iqm


def main():
    work = Path(sys.argv[1]).resolve()
    source = work / 'prepared'
    model = (source / 'iqm/model.iqm').read_bytes()
    decoded = read_iqm(model)
    shader = 'models/remaster/characters/sarge_review'
    if any(m['material'] != shader for m in decoded['meshes']):
        raise ValueError('Unexpected material in character inspection export')
    config = json.loads((source / 'config.json').read_text())
    if config['classification'] != 'generated-character-incomplete-runtime-review':
        raise ValueError('This packager is not a final cgame production packager')
    report = {'classification':config['classification'], 'runtime_accepted':False,
              'model_sha256':hashlib.sha256(model).hexdigest(),
              'clips':decoded['clips'], 'joints':len(decoded['joints']),
              'triangles':len(decoded['triangles']),
              'limitations':['whole-rig inspection only; no lower/upper/head cgame binding',
                             'no weapon socket or team skins; incomplete action library',
                             'diffuse-only review material, not final normal/F0 material']}
    files = {'models/remaster/characters/sarge_review.iqm':model,
             'models/remaster/characters/sarge_review.tga':(source/'body.tga').read_bytes(),
             'scripts/character_sarge_review.shader':('''models/remaster/characters/sarge_review
{
    {
        stage diffuseMap
        map models/remaster/characters/sarge_review.tga
        rgbGen lightingDiffuse
    }
}
''').encode(), 'character-review.json':(json.dumps(report,indent=2)+'\n').encode()}
    path = work / 'character-sarge-v2-review.pk3'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(files.items()):
            info = zipfile.ZipInfo(name,(2026,9,10,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info,data)
    print(json.dumps({'path':str(path), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(), **report},indent=2))


if __name__ == '__main__':
    main()
