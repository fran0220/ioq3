"""Render decoded IQM fixture endpoint poses, not original Blender rig.

CLI -- test-only.pk3 output-dir. Images are inspection only, not an engine draw.
"""
import math
from pathlib import Path
import sys
import zipfile

import bpy
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).parent))
from iqm_validate import read_iqm, skin_positions, matrices


def review(package, output):
    output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(package) as z:
        if 'README_IQM_TEST_ONLY.txt' not in z.namelist():
            raise ValueError('Expected synthetic test fixture package')
        model=read_iqm(z.read('models/remaster/iqm_fixture.iqm'))
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        materials=[]
        # Texture files are decoded by Blender, then packed; no asset regeneration.
        for m in model['meshes']:
            filename=output/(Path(m['material']).name+'.tga'); filename.write_bytes(z.read(m['material']+'.tga'))
            image=bpy.data.images.load(str(filename)); image.pack(); filename.unlink()
            mat=bpy.data.materials.new(m['material']);mat.use_nodes=True
            tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
            shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.7
            mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);materials.append(mat)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=False
    scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.18,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
    scene.view_settings.view_transform='Standard'
    target=Vector((.3,.7,1.1))
    bpy.ops.object.camera_add(location=(5,-7,4));camera=bpy.context.object;scene.camera=camera
    camera.data.type='ORTHO';camera.data.ortho_scale=3.6
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    for pos,energy in [((3,-4,5),500),((-3,2,4),300)]:
        bpy.ops.object.light_add(type='AREA',location=pos);light=bpy.context.object;light.data.energy=energy;light.data.size=4
        light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
    mesh=bpy.data.meshes.new('decoded_iqm');mesh.from_pydata([v for v in model['arrays'][0]],[],model['triangles']);mesh.update()
    obj=bpy.data.objects.new('TEST_ONLY_IQM',mesh);bpy.context.collection.objects.link(obj)
    for mat in materials: mesh.materials.append(mat)
    uv=mesh.uv_layers.new(name='runtime_uv')
    for mindex,m in enumerate(model['meshes']):
        for i in range(m['first_triangle'],m['first_triangle']+m['triangles']):mesh.polygons[i].material_index=mindex
    for loop in mesh.loops:
        u,v=model['arrays'][1][loop.vertex_index];uv.data[loop.index].uv=(u,1-v)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=.055)
    marker=bpy.context.object;marker.name='INSPECTION_ONLY_attachment_not_exported'
    mat=bpy.data.materials.new('socket_marker');mat.diffuse_color=(1,.05,.1,1);marker.data.materials.append(mat)
    for frame in [0,2,3,4]:
        for vertex,position in zip(mesh.vertices,skin_positions(model,frame)):vertex.co=Vector(position)/40
        mesh.update()
        tag=matrices(model['joints'],model['frames'][frame])[2]
        marker.location=[tag[i][3]/40 for i in range(3)]
        scene.render.filepath=str(output/f'frame-{frame}.png');bpy.ops.render.render(write_still=True)


if __name__=='__main__':
    package,output=sys.argv[sys.argv.index('--')+1:]
    review(Path(package).resolve(),Path(output).resolve())
