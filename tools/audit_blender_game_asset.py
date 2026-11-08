"""Bounded Blender -> baked PBR -> GLB/FBX export proof, NOT a finished game.

Run after tools/audit_software_graphics.py with optional bpy==4.2.23 installed.
The default command launches Blender in a separate process with real local
Mesa libraries. --eevee additionally tests an actual software-GL Eevee still.
No original production scene, requirements or render workflow is modified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/research-assets/game-ready-wall'


def asset_proof():
    import bpy
    from mathutils import Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    OUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 8
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.bake.margin = 8
    bpy.ops.mesh.primitive_cube_add(size=1)
    wall = bpy.context.object
    wall.name = 'Proof_Wall_4m_x_3m_NOT_A_FULL_GAME'
    wall.dimensions = (4, .25, 3)
    wall.location.z = 1.5
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = wall.modifiers.new('Small real bevels', 'BEVEL')
    bevel.width = .018
    bevel.segments = 2
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(island_margin=.035)
    bpy.ops.object.mode_set(mode='OBJECT')
    material = bpy.data.materials.new('Portable_Baked_Brick_PBR')
    material.use_nodes = True
    material.use_backface_culling = True
    wall.data.materials.append(material)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = .78
    coordinate = nodes.new('ShaderNodeTexCoord')
    bricks = nodes.new('ShaderNodeTexBrick')
    bricks.inputs['Scale'].default_value = 10
    bricks.inputs['Color1'].default_value = (.30,.065,.025,1)
    bricks.inputs['Color2'].default_value = (.12,.025,.009,1)
    bricks.inputs['Mortar'].default_value = (.13,.12,.10,1)
    bricks.inputs['Mortar Size'].default_value = .025
    bricks.inputs['Mortar Smooth'].default_value = .012
    links.new(coordinate.outputs['UV'], bricks.inputs['Vector'])
    links.new(bricks.outputs['Color'], bsdf.inputs['Base Color'])
    bump = nodes.new('ShaderNodeBump')
    bump.invert = True
    bump.inputs['Distance'].default_value = .025
    links.new(bricks.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    images = {}
    for name, bake_type in [('basecolor','DIFFUSE'), ('normal','NORMAL')]:
        image = bpy.data.images.new('wall_'+name, width=512, height=512, alpha=False)
        if name == 'normal':
            image.colorspace_settings.name = 'Non-Color'
        target = nodes.new('ShaderNodeTexImage')
        target.image = image
        nodes.active = target
        scene.render.bake.use_pass_direct = False
        scene.render.bake.use_pass_indirect = False
        scene.render.bake.use_pass_color = True
        bpy.ops.object.bake(type=bake_type)
        image.filepath_raw = str(OUT / ('wall_'+name+'.png'))
        image.file_format = 'PNG'
        image.save()
        images[name] = image
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = .78
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    albedo = nodes.new('ShaderNodeTexImage')
    albedo.image = images['basecolor']
    links.new(albedo.outputs['Color'], bsdf.inputs['Base Color'])
    normals = nodes.new('ShaderNodeTexImage')
    normals.image = images['normal']
    normal_map = nodes.new('ShaderNodeNormalMap')
    links.new(normals.outputs['Color'], normal_map.inputs['Color'])
    links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
    bpy.ops.export_scene.gltf(filepath=str(OUT/'wall.glb'), export_format='GLB',
        use_selection=True, export_tangents=True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/'wall.fbx'), use_selection=True,
        object_types={'MESH'}, path_mode='COPY', embed_textures=True,
        add_leaf_bones=False, axis_forward='-Z', axis_up='Y')
    world = bpy.data.worlds.new('Proof_Environment')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.3,.35,.4,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .6
    bpy.ops.object.light_add(type='SUN', location=(2,-4,6))
    bpy.context.object.rotation_euler = (.55,-.35,-.4)
    bpy.context.object.data.energy = 2
    bpy.ops.object.camera_add(location=(4.6,-6,3.6))
    camera = bpy.context.object
    camera.rotation_euler = (Vector((0,0,1.5))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 5.8
    scene.camera = camera
    scene.render.resolution_x = 480
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    for image in images.values():
        image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'wall.blend'), compress=True)
    raw = (OUT/'wall.glb').read_bytes()
    magic, version, length = struct.unpack_from('<4sII',raw)
    if magic != b'glTF' or version != 2 or length != len(raw):
        raise RuntimeError('Invalid GLB header')
    json_length, json_type = struct.unpack_from('<I4s',raw,12)
    if json_type != b'JSON':
        raise RuntimeError('Missing GLB JSON chunk')
    data = json.loads(raw[20:20+json_length])
    exported_material = data['materials'][0]
    assert 'baseColorTexture' in exported_material['pbrMetallicRoughness']
    assert 'normalTexture' in exported_material
    assert exported_material['pbrMetallicRoughness']['roughnessFactor'] > .7
    assert len(data['images']) == 2
    assert all('bufferView' in image for image in data['images'])
    assert all('TEXCOORD_0' in primitive['attributes'] and 'NORMAL' in primitive['attributes']
               and 'TANGENT' in primitive['attributes']
               for mesh in data['meshes'] for primitive in mesh['primitives'])
    triangles = sum(data['accessors'][p['indices']]['count']//3
                    for m in data['meshes'] for p in m['primitives'])
    summary = {
        'status':'BLENDER_CPU_BAKE_GLB_FBX_EXPORT_PASS',
        'blender_version':bpy.app.version_string, 'baking_device':'CPU',
        'asset':'One deliberately small wall/material pipeline test; not a photoreal city',
        'triangles':triangles, 'texture_resolution':[512,512],
        'embedded_glb_textures':len(data['images']),
        'portable_material':['base color texture','tangent-space normal texture','roughness factor'],
        'glb_reimport':'Pending separate-process validation',
        'fbx':'Exported successfully; Unity import not tested',
        'godot_import_tested':False, 'unity_import_tested':False,
        'performance_benchmarked':False,
        'native_bpy_finalization':'Reproducible SIGSEGV after completed baking/exports; unresolved',
        'worker_shutdown':'Explicit process exit after validated writes; bypasses native/interpreter cleanup',
        'integration_stability_proven':False,
        'files':{path.name:{'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                 for path in [OUT/name for name in ('wall_basecolor.png','wall_normal.png','wall.glb','wall.fbx','wall.blend')]},
    }
    (OUT/'proof.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


def roundtrip_proof():
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(OUT/'wall.glb'))
    imported = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    assert len(imported) == 1 and imported[0].data.uv_layers
    assert len(imported[0].data.materials) == 1
    assert all(abs(a-b)<.001 for a,b in zip(imported[0].dimensions,(4,.25,3)))
    summary = json.loads((OUT/'proof.json').read_text())
    summary['status'] = 'ASSET_OUTPUT_AND_GLB_ROUNDTRIP_PASS_WITH_BPY_SHUTDOWN_WORKAROUND'
    summary['glb_reimport'] = 'Separate Blender process: mesh count, material, UVs and dimensions verified'
    (OUT/'proof.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('Separate-process GLB roundtrip PASS')


def eevee_proof():
    import time
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'wall.blend'))
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(OUT/'eevee-software-proof.png')
    start = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    seconds = time.perf_counter()-start
    import gpu
    from PIL import Image
    image_path = Path(scene.render.filepath)
    with Image.open(image_path) as image:
        assert image.size == (480,360)
        assert len(set(image.convert('RGB').resize((32,18)).tobytes())) > 20
    renderer = gpu.platform.renderer_get()
    if 'llvmpipe' not in renderer.lower():
        raise RuntimeError('Eevee did not report the expected CPU llvmpipe backend')
    summary = json.loads((OUT/'proof.json').read_text())
    summary['eevee_software_render'] = {
        'status':'PASS', 'renderer':renderer,
        'seconds_one_still':round(seconds,3), 'resolution':[480,360],
        'samples':64, 'realtime_gameplay_tested':False,
        'image_sha256':hashlib.sha256(image_path.read_bytes()).hexdigest(),
    }
    (OUT/'proof.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('Eevee software-GL still written:',scene.render.filepath,renderer,seconds)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', choices=['asset','roundtrip','eevee'])
    parser.add_argument('--eevee', action='store_true')
    args = parser.parse_args()
    if args.worker == 'asset':
        asset_proof()
        # The embedded bpy CPU-bake process repeatedly SIGSEGVs in native
        # finalization, including with wm.quit_blender() and NumPy 1.26/2.4.
        # This is an EXPLICITLY REPORTED workaround, not a stability claim.
        # asset_proof() already asserted outputs and closed all written files;
        # failures above still raise and cannot reach this success-only exit.
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)
    elif args.worker == 'roundtrip':
        roundtrip_proof()
    elif args.worker == 'eevee':
        eevee_proof()
    else:
        from audit_software_graphics import software_environment
        # Keep CPU baking, import validation and preview in separate processes.
        # The bake worker's documented cleanup workaround is not needed by the
        # import or Eevee workers; reject any nonzero worker exit status.
        subprocess.run([sys.executable,__file__,'--worker','asset'], env=software_environment(),check=True)
        subprocess.run([sys.executable,__file__,'--worker','roundtrip'], env=software_environment(),check=True)
        if args.eevee:
            subprocess.run([sys.executable,__file__,'--worker','eevee'], env=software_environment(),check=True)
