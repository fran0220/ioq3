"""Deterministic IQM2 writer for baked rigid-joint animation (ioq3 GL2).

Input: explicit model-space vertices and parent-local bind/frame TRS in Q3 units.
No rig inference, retargeting, material baking, cgame binding or paid API calls.
"""
import argparse
import json
import math
from pathlib import Path
import struct


def vector(value, size):
    if len(value) != size or not all(math.isfinite(x) for x in value):
        raise ValueError('Invalid finite vector')
    return list(map(float, value))


def unit(value):
    length = math.sqrt(sum(x * x for x in value))
    if length < 1e-10:
        raise ValueError('Zero vector/quaternion')
    return [x / length for x in value]


def transform(value):
    t = vector(value['translate'], 3)
    q = unit(vector(value['rotate'], 4))  # xyzw, not Blender's wxyz
    s = vector(value.get('scale', [1, 1, 1]), 3)
    if any(abs(x - 1) > 1e-5 for x in s):
        raise ValueError('Apply/bake bone scale: export supports unit-scale rigid joints only')
    return t + q + [1., 1., 1.]


def rotate(q, v):
    # Quaternion sandwich specialized for a unit quaternion.
    x, y, z, w = q
    tx, ty, tz = 2*(y*v[2]-z*v[1]), 2*(z*v[0]-x*v[2]), 2*(x*v[1]-y*v[0])
    return [v[0]+w*tx+y*tz-z*ty, v[1]+w*ty+z*tx-x*tz, v[2]+w*tz+x*ty-y*tx]


def multiply(a, b):
    x, y, z, w = a; X, Y, Z, W = b
    return [w*X+x*W+y*Z-z*Y, w*Y-x*Z+y*W+z*X, w*Z+x*Y-y*X+z*W, w*W-x*X-y*Y-z*Z]


def packed_weights(influences, joints):
    merged = {}
    for index, weight in influences:
        if type(index) is not int or not 0 <= index < joints or not math.isfinite(weight) or weight < 0:
            raise ValueError('Invalid bone influence')
        if weight:
            merged[index] = merged.get(index, 0) + weight
    if not 1 <= len(merged) <= 4:
        raise ValueError('Require 1..4 positive influences; prune/approve in Blender explicitly')
    values = sorted(merged.items(), key=lambda p: (-p[1], p[0]))
    total = sum(w for _, w in values)
    exact = [w / total * 255 for _, w in values]
    weights = [math.floor(w) for w in exact]
    for i in sorted(range(len(values)), key=lambda i: (-(exact[i]-weights[i]), i))[:255-sum(weights)]:
        weights[i] += 1
    # CPU path stops at first zero; GPU accesses every index, even zero slots.
    pairs = sorted(((index, weight) for (index, _), weight in zip(values, weights)), key=lambda p: (-p[1], p[0]))
    pairs += [(0, 0)] * (4 - len(pairs))
    return [p[0] for p in pairs], [p[1] for p in pairs]


def write_iqm(document):
    if document.get('schema_version') != 1 or document.get('coordinate_system') != 'q3-x-forward-y-left-z-up':
        raise ValueError('Explicit schema_version and Q3 coordinate_system required')
    joints = document['joints']
    if not 1 <= len(joints) <= 128:
        raise ValueError('IQM supports 1..128 joints')
    strings, text = {}, bytearray()
    def name(value):
        raw = value.encode('ascii')
        if not raw or len(raw) >= 64 or b'\0' in raw:
            raise ValueError('Names/material paths must be nonempty ASCII <64 bytes')
        if value not in strings:
            strings[value] = len(text); text.extend(raw + b'\0')
        return strings[value]
    bind, joint_records, names = [], [], set()
    for index, joint in enumerate(joints):
        if type(joint['parent']) is not int or not -1 <= joint['parent'] < index or joint['name'] in names:
            raise ValueError('Unique names and parent-before-child hierarchy required')
        names.add(joint['name']); bind.append(transform(joint))
        joint_records.append(struct.pack('<Ii10f', name(joint['name']), joint['parent'], *bind[-1]))
    for attachment in document.get('attachments', []):
        if attachment not in names:
            raise ValueError('Attachment must be an exact exported joint name')
    frames, anim_records = [], []
    clips = document['clips']
    if not clips or len({c['name'] for c in clips}) != len(clips):
        raise ValueError('Nonempty uniquely named clips required')
    for clip in clips:
        if not clip['frames'] or not math.isfinite(clip['fps']) or clip['fps'] <= 0:
            raise ValueError('Clip frames and positive FPS required')
        anim_records.append(struct.pack('<3IfI', name(clip['name']), len(frames), len(clip['frames']), clip['fps'], int(bool(clip['loop']))))
        previous = bind
        for frame in clip['frames']:
            if len(frame) != len(joints):
                raise ValueError('Every frame must contain every joint')
            converted = [transform(t) for t in frame]
            for j, pose in enumerate(converted):
                if sum(a*b for a, b in zip(pose[3:7], previous[j][3:7])) < 0:
                    pose[3:7] = [-v for v in pose[3:7]]
            frames.append(converted); previous = converted
    if len(frames) > 65535:
        raise ValueError('Work-package frame limit exceeded')
    # Float32 offsets/scales must be used for quantization as well as storage.
    f32 = lambda x: struct.unpack('<f', struct.pack('<f', x))[0]
    poses, offsets, scales, masks = [], [], [], []
    for j, joint in enumerate(joints):
        lo = [f32(min(f[j][c] for f in frames)) for c in range(10)]
        hi = [max(f[j][c] for f in frames) for c in range(10)]
        scale = [f32((hi[c]-lo[c])/65535) if hi[c]-lo[c] > 1e-7 else 0. for c in range(10)]
        mask = sum(1 << c for c in range(10) if scale[c])
        poses.append(struct.pack('<iI20f', joint['parent'], mask, *lo, *scale))
        offsets.append(lo); scales.append(scale); masks.append(mask)
    channels = sum(m.bit_count() for m in masks)
    frame_bytes = bytearray()
    for frame in frames:
        for j, pose in enumerate(frame):
            for c in range(10):
                if masks[j] & (1 << c):
                    value = max(0, min(65535, round((pose[c]-offsets[j][c])/scales[j][c])))
                    frame_bytes.extend(struct.pack('<H', value))
    verts, tris, meshes = [], [], []
    for mesh in document['meshes']:
        source = mesh['vertices']
        converted = []
        for v in source:
            p, n, uv, t = vector(v['position'], 3), unit(vector(v['normal'], 3)), vector(v['uv'], 2), vector(v['tangent'], 4)
            t[:3] = unit(t[:3])
            if abs(sum(n[i]*t[i] for i in range(3))) > 1e-4 or abs(abs(t[3])-1) > 1e-5:
                raise ValueError('Tangent must be orthogonal to normal with sign +/-1')
            indices, weights = packed_weights(v['influences'], len(joints))
            converted.append((p, n, uv, t, indices, weights))
        lookup, local, faces, part = {}, [], [], 0
        def flush():
            nonlocal part
            if not faces:
                return
            first = len(verts)
            meshes.append(struct.pack('<6I', name(mesh['name'] + '_' + str(part)), name(mesh['material']), first, len(local), len(tris), len(faces)))
            verts.extend(local); tris.extend(tuple(first+i for i in tri) for tri in faces)
            lookup.clear(); local.clear(); faces.clear(); part += 1
        for tri in mesh['triangles']:
            if len(tri) != 3 or any(type(i) is not int or not 0 <= i < len(source) for i in tri) or len(set(tri)) != 3:
                raise ValueError('Invalid triangle indices')
            a, b, c = (converted[i][0] for i in tri)
            u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
            if sum(x*x for x in (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])) < 1e-16:
                raise ValueError('Degenerate triangle')
            if len(local) + len(set(tri)-lookup.keys()) > 999 or len(faces) >= 1999:
                flush()
            indices = []
            for i in tri:
                if i not in lookup:
                    lookup[i] = len(local); local.append(converted[i])
                indices.append(lookup[i])
            # Blender inputs are CCW; Q3 front-sided surfaces use clockwise
            # winding (GL_Cull(CT_FRONT_SIDED) culls GL_FRONT).
            faces.append((indices[0], indices[2], indices[1]))
        flush()
    if not meshes:
        raise ValueError('At least one nonempty skinned mesh required')
    # Rigid-joint sphere bounds cover arbitrary frame-to-frame SLERP, not merely
    # endpoint AABBs (which can miss a rotating limb midway and cause culling).
    bind_global, reach = [], []
    for j, joint in enumerate(joints):
        parent = joint['parent']; t, q = bind[j][:3], bind[j][3:7]
        if parent >= 0:
            pt, pq = bind_global[parent]
            t = [a+b for a, b in zip(pt, rotate(pq, t))]; q = multiply(pq, q)
        bind_global.append((t, q))
        radius = max(math.sqrt(sum(x*x for x in frame[j][:3])) for frame in frames)
        reach.append(radius + (reach[parent] if parent >= 0 else 0))
    radius = max(reach[j] + math.dist(v[0], bind_global[j][0]) for v in verts for j, w in zip(v[4], v[5]) if w)
    radius = f32(radius + 0.01 + radius * 1e-4)  # quantization/float32 margin
    bounds = struct.pack('<8f', *([-radius]*3), *([radius]*3), radius, radius) * len(frames)
    data = bytearray(124)
    def add(block):
        data.extend(b'\0' * (-len(data) % 4))
        offset = len(data); data.extend(block)
        return offset
    h = [0]*27; h[0] = 2
    h[3:7] = [len(text), add(text), len(meshes), add(b''.join(meshes))]
    arrays = []
    for kind, fmt, count, at in [(0,7,3,0),(1,7,2,2),(2,7,3,1),(3,7,4,3),(4,1,4,4),(5,1,4,5)]:
        block = b''.join(struct.pack('<' + ('f' if fmt == 7 else 'B')*count, *v[at]) for v in verts)
        arrays.append(struct.pack('<5I', kind, 0, fmt, count, add(block)))
    h[7:10] = [6, len(verts), add(b''.join(arrays))]
    h[10:12] = [len(tris), add(b''.join(struct.pack('<3I', *t) for t in tris))]
    h[13:17] = [len(joints), add(b''.join(joint_records)), len(joints), add(b''.join(poses))]
    h[17:23] = [len(clips), add(b''.join(anim_records)), len(frames), channels, add(frame_bytes or b'\0\0'), add(bounds)]
    h[1] = len(data)
    if len(data) > 16 << 20:
        raise ValueError('IQM exceeds actual 16 MiB loader limit')
    data[:124] = struct.pack('<16s27I', b'INTERQUAKEMODEL\0', *h)
    return bytes(data)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args()
    data = write_iqm(json.loads(a.source.read_text()))
    from iqm_validate import read_iqm
    result = read_iqm(data)
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_bytes(data)
    print(json.dumps({'output': str(a.output), 'joints': len(result['joints']), 'frames': len(result['frames']), 'bytes': len(data)}))


if __name__ == '__main__':
    main()
