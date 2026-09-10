"""Check actual exported waist/neck continuity across independent clip clocks."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'misc/remaster-assets'))
from iqm_validate import read_iqm, skin_positions, matrices


def point(matrix, value):
    return [sum(matrix[i][j]*value[j] for j in range(3))+matrix[i][3] for i in range(3)]


def main():
    root = Path(sys.argv[1])
    models = {part:read_iqm((root/(part+'.iqm')).read_bytes()) for part in ('lower','upper','head')}
    report = json.loads((root/'authoring.json').read_text())
    errors = {}
    for child,parent,socket,offset,height in [('upper','lower','tag_torso',report['waist'],20),
                                             ('head','upper','tag_head',report['neck'],37.3)]:
        p,c = models[parent],models[child]
        # Recover bind-space source coordinates solely from the public origin
        # contract, then pair cut vertices; no expected values from posing code.
        parent_offset = [0,0,0] if parent == 'lower' else report['waist']
        parent_vertices = {}
        for i,v in enumerate(p['arrays'][0]):
            source = [v[j]+parent_offset[j] for j in range(3)]
            if abs(source[2]-height)<1e-4:
                parent_vertices[tuple(round(x,3) for x in source)] = i
        pairs = []
        for i,v in enumerate(c['arrays'][0]):
            source = [v[j]+offset[j] for j in range(3)]
            key = tuple(round(x,3) for x in source)
            if abs(source[2]-height)<1e-4 and key in parent_vertices:
                pairs.append((parent_vertices[key],i))
        if len(pairs)<20:
            raise ValueError('Too few matching cut vertices to verify '+child)
        tag = next(i for i,j in enumerate(p['joints']) if j['name']==socket)
        cases = [(0,0),(29,29),(59,59),(89,89),(110,130),(90,147),(141,151)] if child=='upper' else [(0,0),(29,0),(89,0),(130,0),(147,0),(151,0)]
        if report.get('weapon_frame_offsets',{}).get('5') == 153:
            cases += [(110,283),(90,300),(141,304)] if child=='upper' else [(283,0),(300,0),(304,0)]
        maximum = 0
        for pf,cf in cases:
            parent_points = skin_positions(p,pf)
            child_points = skin_positions(c,cf)
            tag_matrix = matrices(p['joints'],p['frames'][pf])[tag]
            for a,b in pairs:
                placed = point(tag_matrix,child_points[b])
                maximum = max(maximum,max(abs(x-y) for x,y in zip(parent_points[a],placed)))
        if maximum>.02:
            raise ValueError(f'{child} seam mismatch {maximum} Q3 units')
        errors[child] = {'pairs':len(pairs),'max_error_q3_units':maximum,'frame_pairs':cases}
    print(json.dumps({'runtime_accepted':False,'seam_checks':errors},indent=2))


if __name__ == '__main__':
    main()
