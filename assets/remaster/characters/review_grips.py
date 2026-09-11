"""Inspect real exported character/weapon geometry; never exports a game asset.

Blender CLI: -- character-work-directory output-directory
Reads current generated weapon candidates from the repository runtime directory.
"""
from pathlib import Path
import sys
import zipfile

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'misc/remaster-assets'))
from iqm_validate import read_iqm, skin_positions, matrices


def add_mesh(model, positions, texture, name, output, frame=0, rotation=None):
    mesh = bpy.data.meshes.new(name)
    # IQM/Q3 clockwise -> Blender counter-clockwise.
    mesh.from_pydata([Vector(p)/40 for p in positions],[],[(a,c,b) for a,b,c in model['triangles']])
    mesh.update()
    bind = [Matrix(m) for m in matrices(model['joints'],model['joints'])]
    animated = [Matrix(m) for m in matrices(model['joints'],model['frames'][frame])]
    skin = [(a @ b.inverted()).to_3x3() for a,b in zip(animated,bind)]
    normals = []
    for normal,indices,weights in zip(model['arrays'][2],model['arrays'][4],model['arrays'][5]):
        value = sum(((skin[j] @ Vector(normal))*(w/255) for j,w in zip(indices,weights)),Vector())
        normals.append((rotation @ value if rotation is not None else value).normalized())
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    if hasattr(mesh,'use_auto_smooth'):
        mesh.use_auto_smooth = True
    mesh.normals_split_custom_set_from_vertices(normals)
    obj = bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    image_path = output/(name+'.tga')
    image_path.write_bytes(texture)
    image = bpy.data.images.load(str(image_path)); image.pack(); image_path.unlink()
    material = bpy.data.materials.new(name); material.use_nodes = True
    nodes = material.node_tree.nodes
    tex = nodes.new('ShaderNodeTexImage'); tex.image = image
    shader = nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = .7
    material.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
    mesh.materials.append(material)
    uv = mesh.uv_layers.new(name='runtime_uv')
    for loop in mesh.loops:
        u,v = model['arrays'][1][loop.vertex_index]
        uv.data[loop.index].uv = (u,1-v)
    return obj


def main():
    work,output = [Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
    output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(work/'zz-character-sarge-v2-segmented.pk3') as package:
        body = read_iqm(package.read('models/players/sarge/upper.iqm'))
        texture = package.read('models/remaster/characters/sarge_default.tga')
    for weapon,frame in (('machinegun',151),('rocket',304)):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        body_pose = skin_positions(body,frame)
        origin = Vector((.55,-.12,20))
        body_pose = [Vector(p)+origin for p in body_pose]
        add_mesh(body,body_pose,texture,'character',output,frame)
        joint = next(i for i,j in enumerate(body['joints']) if j['name']=='tag_weapon')
        tag = Matrix(matrices(body['joints'],body['frames'][frame])[joint])
        tag.translation += origin
        with zipfile.ZipFile(ROOT/f'assets/remaster/runtime/weapon-{weapon}-v1-candidate.pk3') as package:
            gun = read_iqm(package.read(f'models/remaster/weapons/{weapon}/weapon.iqm'))
            gun_texture = package.read(f'models/remaster/weapons/{weapon}/body.tga')
            if weapon == 'machinegun':
                barrel = read_iqm(package.read('models/remaster/weapons/machinegun/barrel.iqm'))
                index = next(i for i,j in enumerate(gun['joints']) if j['name']=='tag_barrel')
                barrel_tag = tag @ Matrix(matrices(gun['joints'],gun['frames'][0])[index])
                add_mesh(barrel,[barrel_tag @ Vector(p) for p in skin_positions(barrel,0)],
                         gun_texture,'barrel',output,rotation=barrel_tag.to_3x3())
        add_mesh(gun,[tag @ Vector(p) for p in skin_positions(gun,0)],gun_texture,'weapon',output,rotation=tag.to_3x3())
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'; scene.cycles.samples = 32; scene.cycles.use_denoising = False
        scene.render.resolution_x = scene.render.resolution_y = 1024
        scene.render.resolution_percentage = 100
        scene.world = bpy.data.worlds.new('ReviewWorld'); scene.world.use_nodes = True
        scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.25,.25,.25,1)
        scene.world.node_tree.nodes['Background'].inputs[1].default_value = .8
        scene.view_settings.view_transform = 'Standard'
        target = Vector((18,-4,27))/40
        for position in ((30,-30,60),(30,30,60)):
            bpy.ops.object.light_add(type='AREA',location=Vector(position)/40)
            light = bpy.context.object; light.data.energy = 30; light.data.size = .7
            light.rotation_euler = (target-light.location).to_track_quat('-Z','Y').to_euler()
        bpy.ops.object.camera_add(); camera = bpy.context.object; scene.camera = camera
        camera.data.type = 'ORTHO'; camera.data.ortho_scale = .85
        for view,position in (('right',(25,-50,32)),('left',(25,50,32)),('below',(30,-4,0))):
            camera.location = Vector(position)/40
            camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
            scene.render.filepath = str(output/f'{weapon}-{view}.png')
            bpy.ops.render.render(write_still=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output/f'{weapon}-inspection.blend'))


if __name__ == '__main__':
    main()
