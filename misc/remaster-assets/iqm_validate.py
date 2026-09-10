"""Independent binary IQM2 work-package decoder/validator; no writer imports.

Stricter than the engine loader: rejects out-of-range indices, overlapping binary
sections, invalid hierarchy/weights/poses and unsupported non-rigid scale.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


def read_iqm(data):
    if len(data) < 124 or len(data) > 16*1024*1024 or data[:16] != b'INTERQUAKEMODEL\0':
        raise ValueError('Invalid IQM size/magic')
    h = struct.unpack_from('<27I', data, 16)
    if h[0] != 2 or h[1] != len(data) or any(h[i] for i in (2,12,23,24,25,26)):
        raise ValueError('Unsupported IQM header/profile')
    nt, ot, nm, om, na, nv, oa, ntri, otri = h[3:12]
    nj, oj, np, op, nc, oc, nf, nch, of, ob = h[13:23]
    if not (1 <= nj <= 128 and np == nj and 1 <= nf <= 65535 and nm > 0 and nv > 0 and ntri > 0 and nc > 0 and na == 6):
        raise ValueError('Invalid IQM counts')
    occupied = [(0,124)]
    def block(offset, size):
        if offset < 124 or offset % 4 or size < 0 or offset+size > len(data):
            raise ValueError('IQM section out of range/alignment')
        if size:
            if any(offset < end and offset+size > start for start, end in occupied):
                raise ValueError('Overlapping IQM sections')
            occupied.append((offset, offset+size))
        return data[offset:offset+size]
    def rows(offset, count, fmt):
        size = struct.calcsize(fmt)
        return list(struct.iter_unpack(fmt, block(offset, count*size)))
    text = block(ot, nt)
    def name(offset):
        if offset >= len(text) or b'\0' not in text[offset:]:
            raise ValueError('String offset/terminator invalid')
        value = text[offset:text.index(b'\0', offset)].decode('ascii')
        if not value or len(value) >= 64:
            raise ValueError('String outside Q3 name limit')
        return value
    arrays = {}
    for kind, flags, fmt, count, offset in rows(oa, na, '<5I'):
        expected = {0:(7,3),1:(7,2),2:(7,3),3:(7,4),4:(1,4),5:(1,4)}
        if kind not in expected or (fmt,count) != expected[kind] or kind in arrays or flags:
            raise ValueError('Invalid/duplicate required vertex array')
        arrays[kind] = rows(offset, nv, '<' + ('f' if fmt == 7 else 'B')*count)
    triangles = rows(otri, ntri, '<3I')
    meshes = []
    vertex_end, tri_end = 0, 0
    for n, mat, first, count, ft, tc in rows(om, nm, '<6I'):
        if not (1 <= count <= 999 and 1 <= tc <= 1999 and first == vertex_end and ft == tri_end and first+count <= nv and ft+tc <= ntri):
            raise ValueError('Mesh ranges/runtime limits invalid')
        if any(not first <= index < first+count for t in triangles[ft:ft+tc] for index in t):
            raise ValueError('Triangle index outside mesh')
        vertex_end += count; tri_end += tc
        meshes.append({'name': name(n), 'material': name(mat), 'first_vertex': first, 'vertices': count, 'first_triangle': ft, 'triangles': tc})
    if vertex_end != nv or tri_end != ntri:
        raise ValueError('Unowned geometry')
    def trs(values):
        if not all(math.isfinite(v) for v in values) or any(abs(v-1) > 1e-5 for v in values[7:10]):
            raise ValueError('Nonfinite or non-rigid transform')
        length = math.sqrt(sum(v*v for v in values[3:7]))
        if abs(length-1) > 0.001:
            raise ValueError('Non-unit quaternion')
        return {'translate': list(values[:3]), 'rotate': [v/length for v in values[3:7]], 'scale': list(values[7:10])}
    joints, names = [], set()
    for i, record in enumerate(rows(oj, nj, '<Ii10f')):
        n, parent = record[:2]
        joint_name = name(n)
        if not -1 <= parent < i or joint_name in names:
            raise ValueError('Joint hierarchy/name invalid')
        names.add(joint_name)
        joints.append({'name': joint_name, 'parent': parent, **trs(record[2:])})
    poses = rows(op, np, '<iI20f')
    if any(p[0] != joints[i]['parent'] or p[1] & ~1023 for i, p in enumerate(poses)):
        raise ValueError('Pose parent/mask invalid')
    if sum(p[1].bit_count() for p in poses) != nch:
        raise ValueError('Frame channel count mismatch')
    packed = rows(of, nf*nch, '<H')
    frames, cursor = [], 0
    for _ in range(nf):
        frame = []
        for p in poses:
            values = list(p[2:12]); scales = p[12:22]
            if not all(math.isfinite(x) and x >= 0 for x in scales):
                raise ValueError('Invalid pose channel scale')
            for c in range(10):
                if p[1] & (1 << c):
                    values[c] += packed[cursor][0]*scales[c]; cursor += 1
            frame.append(trs(values))
        frames.append(frame)
    clips, frame_end = [], 0
    for n, first, count, fps, flags in rows(oc, nc, '<3IfI'):
        if first != frame_end or not 0 < count <= nf-first or not math.isfinite(fps) or fps <= 0 or flags & ~1:
            raise ValueError('Animation range/FPS invalid')
        frame_end += count
        clips.append({'name': name(n), 'first_frame': first, 'num_frames': count, 'fps': fps, 'loop': bool(flags & 1)})
    if frame_end != nf or len({c['name'] for c in clips}) != nc:
        raise ValueError('Unowned frames or duplicate clips')
    bounds = rows(ob, nf, '<8f')
    for b in bounds:
        if not all(math.isfinite(x) for x in b) or any(b[i] > b[i+3] for i in range(3)) or b[6] < 0 or b[7] < b[6]:
            raise ValueError('Invalid frame bounds')
    for i in range(nv):
        if not all(math.isfinite(x) for kind in (0,1,2,3) for x in arrays[kind][i]):
            raise ValueError('Nonfinite vertex data')
        n, t, bi, bw = arrays[2][i], arrays[3][i], arrays[4][i], arrays[5][i]
        if abs(sum(x*x for x in n)-1) > 1e-4 or abs(sum(x*x for x in t[:3])-1) > 1e-4 or abs(sum(n[c]*t[c] for c in range(3))) > 1e-4 or abs(abs(t[3])-1) > 1e-5:
            raise ValueError('Invalid normal/tangent basis')
        if any(j >= nj for j in bi) or sum(bw) != 255 or any(bw[j] == 0 and any(bw[j+1:]) for j in range(3)):
            raise ValueError('Invalid packed blend indices/weights')
    return {'joints': joints, 'frames': frames, 'clips': clips, 'meshes': meshes, 'arrays': arrays,
            'triangles': triangles, 'bounds': bounds, 'frame_channels': nch}


def matrices(joints, pose):
    result = []
    for joint, p in zip(joints, pose):
        x,y,z,w = p['rotate']; tx,ty,tz = p['translate']
        m = [[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),tx],
             [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),ty],
             [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),tz], [0,0,0,1]]
        if joint['parent'] >= 0:
            a = result[joint['parent']]
            m = [[sum(a[r][k]*m[k][c] for k in range(4)) for c in range(4)] for r in range(4)]
        result.append(m)
    return result


def skin_positions(model, frame):
    """Independent CPU reference, rigid animated-global × inverse-bind-global."""
    bind = matrices(model['joints'], model['joints'])
    animated = matrices(model['joints'], model['frames'][frame])
    positions = []
    for pos, indices, weights in zip(model['arrays'][0], model['arrays'][4], model['arrays'][5]):
        out = [0.,0.,0.]
        for joint, weight in zip(indices, weights):
            b, a = bind[joint], animated[joint]
            local = [sum(b[k][r]*(pos[k]-b[k][3]) for k in range(3)) for r in range(3)]
            for r in range(3):
                out[r] += weight/255 * (sum(a[r][k]*local[k] for k in range(3)) + a[r][3])
        positions.append(out)
    return positions


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('model', type=Path); p.add_argument('--output', type=Path)
    a = p.parse_args(); data = a.model.read_bytes(); model = read_iqm(data)
    # Check skinned endpoint bounds; conservative interpolation policy is writer-specific.
    for frame in range(len(model['frames'])):
        bounds = model['bounds'][frame]
        if any(not bounds[i]-1e-4 <= v[i] <= bounds[i+3]+1e-4 for v in skin_positions(model, frame) for i in range(3)):
            raise ValueError('Skinned frame exceeds bounds')
    report = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'joints': [j['name'] for j in model['joints']],
              'frames': len(model['frames']), 'clips': model['clips'], 'meshes': model['meshes'],
              'frame_channels': model['frame_channels'], 'binary_and_skin_bounds_valid': True, 'runtime_accepted': False}
    if a.output:
        a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
