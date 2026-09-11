"""blender -b --factory-startup --python-exit-code 1 --python this.py -- input.glb out config.json"""

import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from md3_static import RUNTIME_MAX_INDEXES, RUNTIME_MAX_VERTS, clean_quantized_triangles, read_md3, write_md3


def selected(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def render(obj, output, height):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.device = "CPU"
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.13, 0.15, 0.19, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = height * 1.5
    scene.camera = camera
    for pos, energy, size in [((3, -4, 5), 500, 4), ((-3, 1, 3), 350, 3)]:
        bpy.ops.object.light_add(type="AREA", location=tuple(v*height/2 for v in pos))
        light = bpy.context.object
        light.data.energy = energy
        light.data.size = size
        light.rotation_euler = (Vector((0, 0, height/2)) - light.location).to_track_quat("-Z", "Y").to_euler()
    for view, direction in [("front", (2, -3, 1.8)), ("back", (-2, 3, 1.8))]:
        camera.location = Vector(direction) * height
        camera.rotation_euler = (Vector((0, 0, height/2))-camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(output / ("review-" + view + ".png"))
        bpy.ops.render.render(write_still=True)


def main(source, output, config):
    output.mkdir(parents=True, exist_ok=True)
    shader = config["shader"]
    if not shader.startswith("models/remaster/") or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_/-" for c in shader):
        raise ValueError("Unsafe runtime shader name")
    height, units = config["height_meters"], config["units_per_meter"]
    if not (0 < height <= 10 and 0 < units <= 100 and 1 <= config["target_triangles"] <= 8192):
        raise ValueError("Invalid static sample limits")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))
    objects = list(bpy.context.scene.objects)
    if any(o.type == "ARMATURE" or o.animation_data or (o.type == "MESH" and o.data.shape_keys) for o in objects):
        raise ValueError("Static exporter refuses animated, skinned or morph assets; use IQM character pipeline")
    meshes = [o for o in objects if o.type == "MESH"]
    if not meshes:
        raise ValueError("No generated geometry")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    # Bake world placement before detaching import hierarchy.
    matrix = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = matrix
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for other in list(bpy.context.scene.objects):
        if other != obj:
            bpy.data.objects.remove(other, do_unlink=True)
    obj.name = "generated_static_sample"
    obj.rotation_euler.z = math.radians(config["rotation_z_degrees"])
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    zmin = min(v.co.z for v in obj.data.vertices)
    zmax = max(v.co.z for v in obj.data.vertices)
    if zmax-zmin <= 1e-6:
        raise ValueError("Degenerate model height")
    center = Vector(((min(v.co.x for v in obj.data.vertices)+max(v.co.x for v in obj.data.vertices))/2,
                     (min(v.co.y for v in obj.data.vertices)+max(v.co.y for v in obj.data.vertices))/2, zmin))
    for vertex in obj.data.vertices:
        vertex.co = (vertex.co-center) * (height/(zmax-zmin))
    before = len(obj.data.polygons)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.00001)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=0.000001)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    if len(obj.data.polygons) > config["target_triangles"]:
        modifier = obj.modifiers.new("runtime_triangle_budget", "DECIMATE")
        modifier.ratio = config["target_triangles"] / len(obj.data.polygons)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    modifier = obj.modifiers.new("runtime_triangulate", "TRIANGULATE")
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    if not obj.data.uv_layers:
        raise ValueError("No generated UV/material: geometry-only output needs an explicit texture stage")
    source_uv = obj.data.uv_layers.active
    source_uv.name = "generated_uv"
    materials = [slot.material for slot in obj.material_slots]
    if not materials or any(mat is None or not mat.use_nodes for mat in materials):
        raise ValueError("Generated material missing")
    # Pin old UV lookup, then unwrap a fresh nonoverlapping runtime atlas.
    for mat in set(materials):
        tree = mat.node_tree
        uv_node = tree.nodes.new("ShaderNodeUVMap")
        uv_node.uv_map = source_uv.name
        for node in list(tree.nodes):
            if node.type == "TEX_IMAGE" and not node.inputs["Vector"].is_linked:
                tree.links.new(uv_node.outputs["UV"], node.inputs["Vector"])
    obj.data.uv_layers.new(name="runtime_uv")
    obj.data.uv_layers.active_index = len(obj.data.uv_layers)-1
    obj.data.uv_layers.active.active_render = True
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.025)
    bpy.ops.object.mode_set(mode="OBJECT")
    texture = bpy.data.images.new("runtime_diffuse", width=config["texture_edge"], height=config["texture_edge"], alpha=False)
    for mat in set(materials):
        tree = mat.node_tree
        # Bake base color via emission, not diffuse BSDF: fully metallic areas
        # have no diffuse lobe and would otherwise bake black.
        principled = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if principled is None:
            raise ValueError("Unsupported generated material: missing Principled base color")
        emission = tree.nodes.new("ShaderNodeEmission")
        base_color = principled.inputs["Base Color"]
        if base_color.is_linked:
            tree.links.new(base_color.links[0].from_socket, emission.inputs["Color"])
        else:
            emission.inputs["Color"].default_value = base_color.default_value
        material_output = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
        tree.links.new(emission.outputs[0], material_output.inputs["Surface"])
        node = tree.nodes.new("ShaderNodeTexImage")
        node.image = texture
        tree.nodes.active = node
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.cycles.use_denoising = False
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    scene.render.bake.use_pass_color = True
    scene.render.bake.margin = 16
    selected(obj)
    bpy.ops.object.bake(type="EMIT")
    texture.filepath_raw = str(output / "diffuse.tga")
    texture.file_format = "TARGA"
    texture.save()
    mat = bpy.data.materials.new("traditional_baked_diffuse")
    mat.use_nodes = True
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = texture
    mat.node_tree.links.new(node.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.material_index = 0
    obj.data.calc_normals_split()
    triangles = []
    uv = obj.data.uv_layers.active.data
    for polygon in obj.data.polygons:
        triangles.append([(tuple(c*units for c in obj.data.vertices[obj.data.loops[i].vertex_index].co),
                           (uv[i].uv.x, 1-uv[i].uv.y), tuple(obj.data.loops[i].normal)) for i in polygon.loop_indices])
    cleaning = None
    if config.get("drop_quantized_degenerates") is True:
        triangles, cleaning = clean_quantized_triangles(triangles)
    # Blender outward faces are CCW. Q3 front-sided shaders cull GL_FRONT,
    # requiring CW indices while normals, UVs and source geometry stay intact.
    triangles = [(a, c, b) for a, b, c in triangles]
    md3 = write_md3(triangles, shader)
    (output / "model.md3").write_bytes(md3)
    parsed = read_md3(md3)
    (output / "remaster.shader").write_text(shader + "\n{\n    {\n        map " + shader + ".tga\n        rgbGen lightingDiffuse\n    }\n}\n")
    # Save source/baked master before making a *decoded MD3* inspection mesh.
    texture.pack()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "cleaned.blend"))
    mesh = bpy.data.meshes.new("md3_roundtrip")
    positions, faces, uvs, normals = [], [], [], []
    for surface in parsed["surfaces"]:
        base = len(positions)
        positions.extend(tuple(c/units for c in v) for v in surface["positions"])
        # Decoded engine CW geometry returns to Blender's CCW convention only
        # for inspection; never reverse the exported normals to compensate.
        faces.extend((base+a, base+c, base+b) for a, b, c in surface["triangles"])
        uvs.extend(surface["uvs"])
        normals.extend(surface["normals"])
    mesh.from_pydata(positions, [], faces)
    mesh.update()
    layer = mesh.uv_layers.new(name="runtime_uv")
    for loop in mesh.loops:
        u, v = uvs[loop.vertex_index]
        layer.data[loop.index].uv = (u, 1-v)
    # Smooth faces use the decoded custom normals below, rather than replacing
    # the engine's per-vertex lighting with Blender's flat triangle normals.
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mesh.use_auto_smooth = True
    mesh.normals_split_custom_set_from_vertices(normals)
    obj.data = mesh
    obj.data.materials.append(mat)
    report = {"blender_version": bpy.app.version_string, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "input_polygons": before, "output_triangles": len(faces), "output_vertices": len(positions),
              "surfaces": len(parsed["surfaces"]), "bounds_q3": parsed["bounds"],
              "surface_counts": [{"vertices": len(s["positions"]), "triangles": len(s["triangles"]),
                                  "indices": len(s["triangles"]) * 3} for s in parsed["surfaces"]],
              "runtime_surface_limits": {"vertices": RUNTIME_MAX_VERTS, "indices": RUNTIME_MAX_INDEXES},
              "md3_sha256": hashlib.sha256(md3).hexdigest(), "frames": 1,
              "render_source": "decoded exported MD3 + baked runtime TGA", "runtime_accepted": False,
              "winding": {"source": "Blender CCW", "runtime": "Q3 CW", "decoded_preview": "Blender CCW"},
              "material_limitations": "Diffuse only; no PBR/emission preservation claim", "units_per_meter": units}
    if cleaning is not None:
        report["quantized_cleaning"] = cleaning
        report["quantized_cleaning"]["source"] = "Pre-export triangulated cleaned.blend; indices are polygon indices"
    (output / "geometry-report.json").write_text(json.dumps(report, indent=2)+"\n")
    render(obj, output, height)


if __name__ == "__main__":
    source, output, config = sys.argv[sys.argv.index("--")+1:]
    main(Path(source).resolve(), Path(output).resolve(), json.loads(Path(config).read_text()))
