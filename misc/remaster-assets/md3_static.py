"""Small one-frame MD3 writer/reader for static props, matching qfiles.h v15.

Input is evaluated, triangulated geometry in engine units; UV v is already flipped.
No rig, animation, tags, PBR conversion or implicit coordinate-system conversion.
"""

import math
import struct

HEADER = struct.Struct("<4si64s9i")
SURFACE = struct.Struct("<4s64s10i")
FRAME = struct.Struct("<10f16s")
# R_LoadMD3 rejects counts >= SHADER_MAX_VERTEXES/SHADER_MAX_INDEXES
# (qfiles.h: 1000 and 6000). These are stricter than the MD3 format limits.
RUNTIME_MAX_VERTS = 999
RUNTIME_MAX_INDEXES = 5999


def name_bytes(value, size=64):
    raw = value.encode("ascii")
    if not raw or len(raw) >= size or b"\0" in raw:
        raise ValueError("MD3 name must be nonempty ASCII fitting its field")
    return raw.ljust(size, b"\0")


def normal_word(normal):
    if len(normal) != 3 or not all(math.isfinite(v) for v in normal):
        raise ValueError("Invalid normal")
    length = math.sqrt(sum(v*v for v in normal))
    if length < 1e-12:
        raise ValueError("Zero normal")
    x, y, z = (v/length for v in normal)
    lat = round(math.atan2(y, x) * 128 / math.pi) & 255
    lng = round(math.acos(max(-1, min(1, z))) * 128 / math.pi) & 255
    return lat << 8 | lng


def encode_vertex(vertex):
    position, uv, normal = vertex
    if len(position) != 3 or len(uv) != 2 or not all(math.isfinite(v) for v in (*position, *uv)):
        raise ValueError("Invalid vertex")
    if any(v < -512 or v > 32767/64 for v in position):
        raise ValueError("MD3 coordinate outside signed-short range")
    return tuple(round(v*64) for v in position), tuple(uv), normal_word(normal)


def encode_triangle(triangle):
    if len(triangle) != 3:
        raise ValueError("Only triangles are supported")
    encoded = [encode_vertex(v) for v in triangle]
    xyz = [v[0] for v in encoded]
    a = [xyz[1][i]-xyz[0][i] for i in range(3)]
    b = [xyz[2][i]-xyz[0][i] for i in range(3)]
    cross = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    return encoded if any(cross) else None


def clean_quantized_triangles(triangles):
    """Explicit offline hook: drop only zero-area faces on MD3's 1/64 lattice.

    Retained corners/UV seams/normals/winding are untouched. Invalid input still
    raises; this does not repair arbitrary meshes or change strict writer policy.
    """
    kept, removed = [], []
    for index, triangle in enumerate(triangles):
        if encode_triangle(triangle) is None:
            removed.append(index)
        else:
            kept.append(triangle)
    if not kept:
        raise ValueError("Quantized cleaning would remove every triangle")
    return kept, {"input_triangles": len(kept) + len(removed),
                  "output_triangles": len(kept), "removed_triangle_indices": removed,
                  "coordinate_step_q3": 1/64}


def write_md3(triangles, shader, model_name="static-prop"):
    shader_bytes = name_bytes(shader)
    model_bytes = name_bytes(model_name)
    surfaces, vertices, indices, lookup = [], [], [], {}

    def flush():
        if indices:
            surfaces.append((list(vertices), list(indices)))
            vertices.clear()
            indices.clear()
            lookup.clear()

    for triangle in triangles:
        encoded = encode_triangle(triangle)
        if encoded is None:
            raise ValueError("Triangle collapses after MD3 quantization")
        missing = set(encoded) - lookup.keys()
        if len(vertices) + len(missing) > RUNTIME_MAX_VERTS or (len(indices) + 1) * 3 > RUNTIME_MAX_INDEXES:
            flush()
        tri_indices = []
        for vertex in encoded:
            if vertex not in lookup:
                lookup[vertex] = len(vertices)
                vertices.append(vertex)
            tri_indices.append(lookup[vertex])
        indices.append(tuple(tri_indices))
    flush()
    if not 1 <= len(surfaces) <= 32:
        raise ValueError("MD3 requires 1..32 surfaces")

    all_xyz = [tuple(c/64 for c in vertex[0]) for verts, _ in surfaces for vertex in verts]
    mins = [min(v[i] for v in all_xyz) for i in range(3)]
    maxs = [max(v[i] for v in all_xyz) for i in range(3)]
    radius = max(math.sqrt(sum(c*c for c in v)) for v in all_xyz)
    frame = FRAME.pack(*mins, *maxs, 0, 0, 0, radius, name_bytes("static", 16))
    blocks = []
    for index, (verts, tris) in enumerate(surfaces):
        triangle_data = b"".join(struct.pack("<3i", *tri) for tri in tris)
        shader_data = shader_bytes + struct.pack("<i", 0)
        uv_data = b"".join(struct.pack("<2f", *v[1]) for v in verts)
        vertex_data = b"".join(struct.pack("<3hH", *v[0], v[2]) for v in verts)
        ofs_tri = SURFACE.size
        ofs_shader = ofs_tri + len(triangle_data)
        ofs_uv = ofs_shader + len(shader_data)
        ofs_xyz = ofs_uv + len(uv_data)
        end = ofs_xyz + len(vertex_data)
        blocks.append(SURFACE.pack(b"IDP3", name_bytes(f"surface{index}"), 0, 1, 1, len(verts), len(tris),
                                   ofs_tri, ofs_shader, ofs_uv, ofs_xyz, end)
                      + triangle_data + shader_data + uv_data + vertex_data)
    offset = HEADER.size + len(frame)
    data = HEADER.pack(b"IDP3", 15, model_bytes, 0, 1, 0, len(surfaces), 0,
                       HEADER.size, offset, offset, offset + sum(map(len, blocks))) + frame + b"".join(blocks)
    return data


def read_md3(data):
    if len(data) < HEADER.size:
        raise ValueError("Truncated MD3")
    magic, version, name, flags, frames, tags, count, skins, ofs_frame, ofs_tags, offset, end = HEADER.unpack_from(data)
    if (magic, version, frames, tags) != (b"IDP3", 15, 1, 0) or not 1 <= count <= 32 or end != len(data):
        raise ValueError("Not a valid static MD3")
    if ofs_frame != HEADER.size or ofs_tags != HEADER.size + FRAME.size or offset != ofs_tags:
        raise ValueError("Invalid static frame offsets")
    bounds = FRAME.unpack_from(data, ofs_frame)
    result = {"name": name.split(b"\0")[0].decode("ascii"), "frames": frames, "bounds": list(bounds[:6]),
              "radius": bounds[9], "surfaces": []}
    for _ in range(count):
        if offset + SURFACE.size > end:
            raise ValueError("Truncated surface")
        ident, surface_name, flags, nframes, nshaders, nverts, ntris, ot, osh, ouv, ov, oe = SURFACE.unpack_from(data, offset)
        if ident != b"IDP3" or nframes != 1 or nshaders != 1 or not 1 <= nverts <= RUNTIME_MAX_VERTS or not 1 <= ntris * 3 <= RUNTIME_MAX_INDEXES:
            raise ValueError("Invalid surface counts")
        if not (ot == SURFACE.size and osh == ot + ntris*12 and ouv == osh+68 and ov == ouv+nverts*8 and oe == ov+nverts*8 and offset+oe <= end):
            raise ValueError("Invalid surface offsets")
        tris = [struct.unpack_from("<3i", data, offset+ot+i*12) for i in range(ntris)]
        if any(v < 0 or v >= nverts for tri in tris for v in tri):
            raise ValueError("Triangle index outside vertex array")
        uvs = [struct.unpack_from("<2f", data, offset+ouv+i*8) for i in range(nverts)]
        positions, normals = [], []
        for i in range(nverts):
            x, y, z, word = struct.unpack_from("<3hH", data, offset+ov+i*8)
            positions.append((x/64, y/64, z/64))
            lat, lng = (word >> 8)*math.pi/128, (word & 255)*math.pi/128
            normals.append((math.cos(lat)*math.sin(lng), math.sin(lat)*math.sin(lng), math.cos(lng)))
        result["surfaces"].append({"shader": data[offset+osh:offset+osh+64].split(b"\0")[0].decode("ascii"),
                                   "positions": positions, "uvs": uvs, "normals": normals, "triangles": tris})
        offset += oe
    if offset != end:
        raise ValueError("Trailing or missing MD3 surface")
    return result
