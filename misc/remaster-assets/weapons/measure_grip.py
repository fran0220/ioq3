"""Blender CLI: -- cleaned.blend attachment.json section-z-m output.json.

Measure the positive-X foregrip at a reviewed height using actual triangle-edge
intersections, not screen pixels. Centerline is a fitting reference, not a palm
surface or final hand-pose acceptance. Never changes source geometry.
"""
import hashlib
import json
from pathlib import Path
import sys

import bpy


def measure(source, config_path, height, output):
    config = json.loads(config_path.read_text())
    bpy.ops.wm.open_mainfile(filepath=str(source))
    obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    points = []
    for edge in obj.data.edges:
        a, b = (obj.data.vertices[i].co for i in edge.vertices)
        if (a.z < height <= b.z) or (b.z < height <= a.z):
            point = a.lerp(b, (height - a.z) / (b.z - a.z))
            if point.x > 0:
                points.append(point)
    if not points:
        raise ValueError('No foregrip intersects selected height')
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    scale = config.get('fit_scale', 1) * 40
    origin = config['grip_meters']
    runtime = [[(bound[i] - origin[i]) * scale for i in range(3)] for bound in (lo, hi)]
    report = {
        'classification': 'measured-foregrip-section-not-approved-palm-pose',
        'source_blend_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'attachment_config_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(),
        'section_z_m': height, 'selection': 'edge intersections at z, x > 0',
        'intersection_count': len(points), 'cleaned_bounds_m': [lo, hi],
        'weapon_local_bounds_q3': runtime,
        'weapon_local_centerline_q3': [(runtime[0][i]+runtime[1][i])/2 for i in range(3)],
        'weapon_local_section_size_q3': [(hi[i]-lo[i])*scale for i in range(3)],
        'note': 'Surface contact requires palm orientation/offset outside section; centerline lies inside grip',
    }
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    source, config, height, output = sys.argv[sys.argv.index('--')+1:]
    measure(Path(source).resolve(), Path(config).resolve(), float(height), Path(output).resolve())
