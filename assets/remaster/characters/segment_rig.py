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
from mathutils.geometry import intersect_ray_tri

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
    palm = {}
    for side in ('Left','Right'):
        bone = names[side+'Hand']
        points = [Vector(v['position']) for m in source['meshes'] for v in m['vertices']
                  if sum(w for j,w in v['influences'] if j == bone) > .75]
        palm[side] = rest[bone].inverted() @ (sum(points,Vector())/len(points))

    def socket(pose, part):
        return pose[names['Hips']] @ hip_offset if part == 'upper' else pose[names['Head']] @ head_offset

    def ik(pose, side, target):
        a,b,h = (names[side+n] for n in ('Arm','ForeArm','Hand'))
        shoulder = pose[a].translation.copy()
        # Targets refer to the actual palm mass, not the wrist joint. Right
        # fingers follow the vertical grip; left fingers cross underneath it.
        hand_rotation = rest[h].to_quaternion()
        if side == 'Left':
            hand_rotation = Quaternion((1,0,0),-math.pi/2) @ hand_rotation
        target = Vector(target) - hand_rotation @ palm[side]
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
        pose[h] = Matrix.Translation(target) @ hand_rotation.to_matrix().to_4x4()

    firearm = 'machinegun'
    def holding(recoil=0, lowered=0, jab=0, wave=0):
        pose = [m.copy() for m in rest]
        grip, support = ((9,-4,27),(7.6,0,-1)) if firearm == 'machinegun' else ((11,-3,28),(15.2,0,-1.8))
        # Protract the shoulders for the heavier forward hold so the launcher
        # rear clears the chest without stretching either forearm length.
        protraction = 1 if firearm == 'machinegun' else 3
        for side in ('Left','Right'):
            for name in ('Shoulder','Arm','ForeArm','Hand'):
                pose[names[side+name]].translation.x += protraction
        ik(pose,'Right',(grip[0]-recoil+12*jab,grip[1]-4*lowered,grip[2]-14*lowered+recoil))
        ik(pose,'Left',(grip[0]+support[0]-recoil,grip[1]+support[1]+6*wave,grip[2]+support[2]-14*lowered+18*wave))
        return pose

    def sample(name,count):
        frames = source_clips[name]
        return [copy.deepcopy(frames[round(i*(len(frames)-1)/max(1,count-1))]) for i in range(count)]

    upper = []
    for firearm in ('machinegun','rocket'):
        upper += sample('death1',30)+sample('death2',30)+sample('death3',30)
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
    # Backward takeoff uses the paid neutral jump with authored forward leg
    # counterbalance. This changes only skin poses, never player displacement.
    backjump = sample('jump',8)
    for i,pose in enumerate(backjump):
        for side in ('Left','Right'):
            pivot = pose[names[side+'UpLeg']].translation.copy()
            change = Matrix.Translation(pivot) @ Matrix.Rotation(-.16*math.sin(math.pi*i/7),4,'Y') @ Matrix.Translation(-pivot)
            for suffix in ('UpLeg','Leg','Foot','ToeBase'):
                index = names[side+suffix]
                pose[index] = change @ pose[index]
    lower += backjump+[copy.deepcopy(jump[-1])]
    lower += [[m.copy() for m in rest] for _ in range(10)]
    lower += [copy.deepcopy(source_clips['crouch'][0]) for _ in range(8)]
    # A planted, alternating knee/ankle shuffle rather than a truncated walk.
    # CG_PlayerAngles supplies turning yaw; no extra root yaw is authored here.
    for i in range(7):
        pose = [m.copy() for m in rest]
        for side,phase in (('Left',0),('Right',math.pi)):
            swing = math.sin(i*2*math.pi/7+phase)
            hip, knee = .06*swing, .14*max(0,swing)
            chain = ('UpLeg','Leg','Foot','ToeBase')
            for first,angle in ((0,hip),(1,knee),(2,-hip-knee)):
                pivot = pose[names[side+chain[first]]].translation.copy()
                change = Matrix.Translation(pivot) @ Matrix.Rotation(angle,4,'Y') @ Matrix.Translation(-pivot)
                for suffix in chain[first:]:
                    index = names[side+suffix]
                    pose[index] = change @ pose[index]
        lower.append(pose)
    assert len(upper) == 306 and len(lower) == 191
    out = work/'segmented'
    out.mkdir(parents=True,exist_ok=True)
    report = {'classification':'generated-segmented-combat-test-candidate','runtime_accepted':False,
              'source':'prepared/iqm/source.json','authoring':'Paid rig; paid source locomotion/deaths/jump/crouch; explicit hand-authored two-bone IK upper gesture/recoil/jab/drop/raise/stance; lower flutter kick, static planted idle, backward-jump leg counterbalance and alternating turn shuffle. Complete engine motion review still required.',
              'waist':list(waist.translation),'neck':list(neck.translation),'parts':{},
              'weapon_frame_offsets':{'2':0,'5':153},
              'grip_targets':{'machinegun':{'right':[9,-4,27],'left':[16.6,-4,26]},
                              'rocket':{'right':[11,-3,28],'left':[26.2,-3,26.2]}},
              'palm_local_anchors':{key:list(value) for key,value in palm.items()}}
    for part,poses,origin in (('lower',lower,Matrix.Identity(4)),('upper',upper,waist),('head',[rest],neck)):
        inverse = origin.inverted()
        bind = [inverse @ p for p in rest]
        segment_joints = [{**j,**t} for j,t in zip(joints,locals_for(joints,bind))]
        tags = ['tag_torso'] if part == 'lower' else ['tag_head','tag_weapon'] if part == 'upper' else []
        tag_parents = [names['Hips']] if part == 'lower' else [names['Head'],names['RightHand']] if part == 'upper' else []
        def tags_for(pose):
            if part == 'lower':
                return [socket(pose,'upper')]
            if part == 'upper':
                return [socket(pose,'head'), Matrix.Translation(pose[names['RightHand']] @ palm['Right'])]
            return []
        for name,parent,tag in zip(tags,tag_parents,tags_for(rest)):
            segment_joints.append({'name':name,'parent':parent,**trs(rest[parent].inverted() @ tag)})
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
                    # Project ID plate corners onto the paid armor rather than
                    # guessing an X/Y depth that can bury the rear insignia.
                    direction = Vector(normal)
                    hits = []
                    for source_mesh in source['meshes']:
                        for triangle in source_mesh['triangles']:
                            points = [Vector(source_mesh['vertices'][i]['position']) for i in triangle]
                            hit = intersect_ray_tri(*points,-direction,position+direction*100,True)
                            if hit is not None:
                                hits.append(hit)
                    if not hits:
                        raise ValueError('Insignia corner misses generated armor')
                    position = max(hits,key=lambda p:p.dot(direction))+direction*.12
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
            frame += [trs(pose[parent].inverted() @ tag) for parent,tag in zip(tag_parents,tags_for(pose))]
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
