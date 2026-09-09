"""TEST ONLY: procedural asymmetric colored mesh, never a production asset."""

from pathlib import Path
import sys
import bpy

output = Path(sys.argv[sys.argv.index("--")+1]).resolve()
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=1)
obj = bpy.context.object
obj.name = "TEST_ONLY_NOT_GENERATED"
obj.scale = (0.65, 0.45, 1.6)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
obj.data.vertices[0].co.x += 0.1
for name, color in [("orange", (0.85, 0.12, 0.015, 1)), ("cyan", (0.01, 0.5, 0.85, 1))]:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = color
    mat.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1 if name == "cyan" else 0
    obj.data.materials.append(mat)
for face in obj.data.polygons:
    face.material_index = face.index % 2
bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB", use_selection=True)
