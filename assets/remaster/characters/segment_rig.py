"""Author a segmented candidate from the paid rig; run with Blender Python.

Keeps paid source motions and records hand-authored IK transitions separately.
This produces a combat-test candidate, not an automatic runtime acceptance.
"""
import copy
import json
import math
from pathlib import Path
import sys

from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'misc/remaster-assets'))
from iqm_export import write_iqm
from iqm_validate import read_iqm


def matrix(value):
    x,y,z,w = value['rotate']
    return Matrix.Translation(value['translate']) @ Quaternion((w,x,y,z)).to_matrix().to_4x4()


def trs(value):
    t,q,s = value.decompose()
    return {'translate':list(t), 'rotate':[q.x,q.y,q.z,q.w], 'scale':[1,1,1]}


def globals_for(joints, pose):
    result = []
    for joint,value in zip(joints,pose):
        local = matrix(value)
        result.append(result[joint['parent']] @ local if joint['parent'] >= 0 else local)
    return result


def locals_for(joints, pose):
    return [trs(pose[j['parent']].inverted() @ p if j['parent'] >= 0 else p)
            for j,p in zip(joints,pose)]


def cut_triangle(vertices, height, above):
    result = []
    for a,b in zip(vertices,vertices[1:]+vertices[:1]):
        inside_a = (a['position'][2] >= height) == above
        inside_b = (b['position'][2] >= height) == above
        if inside_a:
            result.append(a)
        if inside_a != inside_b:
            t = (height-a['position'][2])/(b['position'][2]-a['position'][2])
            c = {key:[x+(y-x)*t for x,y in zip(a[key],b[key])]
                 for key in ('position','normal','uv','tangent')}
            c['normal'] = list(Vector(c['normal']).normalized())
            normal, tangent = Vector(c['normal']), Vector(c['tangent'][:3])
            tangent = (tangent-normal*tangent.dot(normal)).normalized()
            c['tangent'] = [*tangent, a['tangent'][3]]
            weights = {}
            for vertex,amount in ((a,1-t),(b,t)):
                for bone,weight in vertex['influences']:
                    weights[bone] = weights.get(bone,0)+weight*amount
            weights = sorted(weights.items(),key=lambda item:-item[1])[:4]
            total = sum(w for _,w in weights)
            c['influences'] = [[bone,w/total] for bone,w in weights]
            result.append(c)
    return result


def main():
    work = Path(sys.argv[sys.argv.index('--')+1]).resolve()
    source = json.loads((work/'prepared/iqm/source.json').read_text())
    joints = source['joints']
    names = {j['name']:i for i,j in enumerate(joints)}
    rest = globals_for(joints,joints)
    source_clips = {c['name']:[globals_for(joints,f) for f in c['frames']] for c in source['clips']}
    waist = Matrix.Translation((.55,-.12,20))
    neck = Matrix.Translation((1.47,-.02,37.3))
    hip_offset = rest[names['Hips']].inverted() @ waist
    head_offset = rest[names['Head']].inverted() @ neck

    def socket(pose, part):
        return pose[names['Hips']] @ hip_offset if part == 'upper' else pose[names['Head']] @ head_offset

    def ik(pose, side, target):
        a,b,h = (names[side+n] for n in ('Arm','ForeArm','Hand'))
        shoulder = pose[a].translation.copy()
        target = Vector(target)
        l1 = (rest[b].translation-rest[a].translation).length
        l2 = (rest[h].translation-rest[b].translation).length
        direction = target-shoulder
        distance = min(direction.length,l1+l2-.01)
        direction.normalize()
        target = shoulder+direction*distance
        across = Vector((0,1 if side == 'Left' else -1,-.45))
        across = (across-direction*across.dot(direction)).normalized()
        along = (l1*l1-l2*l2+distance*distance)/(2*distance)
        elbow = shoulder+direction*along+across*math.sqrt(max(0,l1*l1-along*along))
        for index,origin,end,old_end in ((a,shoulder,elbow,rest[b].translation),(b,elbow,target,rest[h].translation)):
            rotation = (old_end-rest[index].translation).rotation_difference(end-origin) @ rest[index].to_quaternion()
            pose[index] = Matrix.Translation(origin) @ rotation.to_matrix().to_4x4()
        pose[h] = Matrix.Translation(target) @ Vector((1,0,0)).to_track_quat('Y','Z').to_matrix().to_4x4()

    def holding(recoil=0, lowered=0, jab=0, wave=0):
        pose = [m.copy() for m in rest]
        ik(pose,'Right',(10-recoil+12*jab,-6-4*lowered,25-14*lowered+recoil))
        ik(pose,'Left',(18-recoil,3+6*wave,25-14*lowered+18*wave))
        return pose

    def sample(name,count):
        frames = source_clips[name]
        return [copy.deepcopy(frames[round(i*(len(frames)-1)/max(1,count-1))]) for i in range(count)]

    upper = sample('death1',30)+sample('death2',30)+sample('death3',30)
    upper += [holding(wave=math.sin(math.pi*i/39)**2) for i in range(40)]
    upper += [holding(recoil=v) for v in (0,1.4,2,.9,.3,0)]
    upper += [holding(jab=v) for v in (0,.35,1,.65,.15,0)]
    upper += [holding(lowered=i/4) for i in range(5)]
    upper += [holding(lowered=1-i/3) for i in range(4)]
    upper += [holding(),holding(jab=.1)]
    lower = sample('death1',30)+sample('death2',30)+sample('death3',30)
    lower += sample('crouch',8)+sample('walk',12)+sample('run',11)
    lower += list(reversed(sample('walk',10)))
    # Authored flutter kick: local hip flexion, independent of player origin.
    for i in range(10):
        pose = [m.copy() for m in rest]
        for side,phase in (('Left',0),('Right',math.pi)):
            index = names[side+'UpLeg']
            pivot = rest[index].translation
            change = Matrix.Translation(pivot) @ Matrix.Rotation(.22*math.sin(i*2*math.pi/10+phase),4,'Y') @ Matrix.Translation(-pivot)
            for child in range(index,index+4):
                pose[child] = change @ rest[child]
        lower.append(pose)
    jump = sample('jump',16)
    lower += jump
    lower += sample('jump',8)+[copy.deepcopy(jump[-1])]
    lower += [[m.copy() for m in rest] for _ in range(10)]
    lower += [copy.deepcopy(source_clips['crouch'][0]) for _ in range(8)]
    lower += sample('walk',7)
    assert len(upper) == 153 and len(lower) == 191
    out = work/'segmented'
    out.mkdir(parents=True,exist_ok=True)
    report = {'classification':'generated-segmented-combat-test-candidate','runtime_accepted':False,
              'source':'prepared/iqm/source.json','authoring':'Paid rig; paid source locomotion/deaths/jump/crouch; explicit hand-authored two-bone IK upper gesture/recoil/jab/drop/raise/stance and lower flutter kick/idle. Back jump currently retimed forward jump: must review and replace before final acceptance.',
              'waist':list(waist.translation),'neck':list(neck.translation),'parts':{}}
    for part,poses,origin in (('lower',lower,Matrix.Identity(4)),('upper',upper,waist),('head',[rest],neck)):
        inverse = origin.inverted()
        bind = [inverse @ p for p in rest]
        segment_joints = [{**j,**t} for j,t in zip(joints,locals_for(joints,bind))]
        tags = ['tag_torso'] if part == 'lower' else ['tag_head','tag_weapon'] if part == 'upper' else []
        def tags_for(pose):
            if part == 'lower':
                return [socket(pose,'upper')]
            if part == 'upper':
                return [socket(pose,'head'), Matrix.Translation(pose[names['RightHand']].translation)]
            return []
        for name,tag in zip(tags,tags_for(rest)):
            segment_joints.append({'name':name,'parent':-1,**trs(inverse @ tag)})
        meshes = []
        for mesh in source['meshes']:
            dest = {'name':part,'material':'models/remaster/characters/sarge_default','vertices':[],'triangles':[]}
            for triangle in mesh['triangles']:
                vertices = [copy.deepcopy(mesh['vertices'][i]) for i in triangle]
                arm_weight = sum(w for v in vertices for bone,w in v['influences'] if any(s in joints[bone]['name'] for s in ('Arm','Hand','Shoulder')))/3
                if part == 'lower':
                    if arm_weight > .5:
                        continue
                    vertices = cut_triangle(vertices,20,False)
                elif part == 'upper':
                    if arm_weight <= .5:
                        vertices = cut_triangle(vertices,20,True)
                    if vertices:
                        vertices = cut_triangle(vertices,37.3,False)
                else:
                    vertices = cut_triangle(vertices,37.3,True)
                if len(vertices) < 3:
                    continue
                for vertex in vertices:
                    z = vertex['position'][2]
                    if abs(z-20)<1e-4:
                        vertex['influences'] = [[names['Hips'],1]]
                    elif abs(z-37.3)<1e-4 or part == 'head':
                        vertex['influences'] = [[names['Head'],1]]
                    vertex['position'] = list(inverse @ Vector(vertex['position']))
                start = len(dest['vertices'])
                dest['vertices'] += vertices
                for i in range(1,len(vertices)-1):
                    a,b,c = (Vector(vertices[j]['position']) for j in (0,i,i+1))
                    # Clipping through existing vertices can create zero-area
                    # slivers. Remove those here, never weaken IQM validation.
                    if (b-a).cross(c-a).length_squared >= 1e-16:
                        dest['triangles'].append([start,start+i,start+i+1])
            meshes.append(dest)
        if part == 'upper':
            # Authored armor ID plates: front/rear and both shoulders. The
            # same geometry takes distinct red-chevron / blue-bars skins.
            plate = {'name':'insignia','material':'models/remaster/characters/sarge_insignia_default','vertices':[],'triangles':[]}
            for center,normal,right,bone in [((8,0,30),(1,0,0),(0,1,0),'Spine'),
                                            ((-7,0,30),(-1,0,0),(0,-1,0),'Spine'),
                                            ((0,10,32),(0,1,0),(-1,0,0),'LeftArm'),
                                            ((0,-10,32),(0,-1,0),(1,0,0),'RightArm')]:
                start = len(plate['vertices'])
                for x,z,uv in [(-2,-2,[0,1]),(2,-2,[1,1]),(2,2,[1,0]),(-2,2,[0,0])]:
                    position = Vector(center)+Vector(right)*x+Vector((0,0,z))
                    plate['vertices'].append({'position':list(inverse @ position),'normal':list(normal),
                                              'uv':uv,'tangent':[*right,-1],
                                              'influences':[[names[bone],1]]})
                # right cross up = outward normal for these four faces.
                plate['triangles'] += [[start,start+1,start+2],[start,start+2,start+3]]
            meshes.append(plate)
        frames = []
        for pose in poses:
            current_inverse = socket(pose,part).inverted() if part in ('upper','head') else Matrix.Identity(4)
            frame = locals_for(joints,[current_inverse @ p for p in pose])
            frame += [trs(current_inverse @ tag) for tag in tags_for(pose)]
            frames.append(frame)
        document = {'schema_version':1,'coordinate_system':'q3-x-forward-y-left-z-up',
                    'joints':segment_joints,'meshes':meshes,'attachments':tags,
                    'clips':[{'name':'cfg_indexed_'+part,'fps':20,'loop':False,'frames':frames}]}
        data = write_iqm(document)
        decoded = read_iqm(data)
        (out/(part+'.iqm')).write_bytes(data)
        (out/(part+'-source.json')).write_text(json.dumps(document))
        report['parts'][part] = {'frames':len(frames),'triangles':len(decoded['triangles']),'tags':tags,'bounds':len(decoded['bounds'])}
    (out/'authoring.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
