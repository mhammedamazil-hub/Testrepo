#!/usr/bin/env python3
"""Offline beauty render of the villa, in Blender's Cycles, at 1080p.

This is the "ultra realistic model" pass: the same GLB the game ships, rendered by a real
path tracer instead of by the hand-written GLES2 rasteriser. Nothing here runs on the phone.
What it is for:

  * a 1920x1080 reference frame of what the model actually is, at any quality we like,
    because time is free offline (time is *not* free at 60 Hz on a Mali-G57);
  * a target to match: tools/game_sim.cpp renders the same camera, same sun, same exposure,
    so the difference between `cycles` and `sim` output is the honest list of what the phone
    renderer is still faking;
  * the source of the baked light the game consumes (`--bake-ao`), which replaces the numpy
    voxel marcher in tools/villa_pack.py with Cycles' ray tracer.

Run it through the repo's headless runner (the bpy wheel needs the X/GL stubs):

    .venv/bin/python tools/bpy_run.py tools/villa_cycles.py -- \
        villa_v2/villa_v2_lite.glb /tmp/beauty.png 1920 1080 64
"""

import json
import math
import sys

import bpy
from mathutils import Vector

MARK = "@@JSON@@"

# The game's constants. tools/game_sim.cpp: kFovY = 62 deg; game_shade.h: sun azimuth 236 deg,
# elevation 30 deg. Keeping them identical is the whole point of the comparison.
GAME_FOV_Y_DEG = 62.0
SUN_AZ_DEG = 236.0
SUN_EL_DEG = 30.0


def parse_argv():
    argv = sys.argv[1:]
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    if len(argv) < 2:
        raise SystemExit("usage: villa_cycles.py <glb> <out.png> [w h samples] [--bake-ao <json>]")
    glb, out = argv[0], argv[1]
    w = int(argv[2]) if len(argv) > 2 else 1920
    h = int(argv[3]) if len(argv) > 3 else 1080
    spp = int(argv[4]) if len(argv) > 4 else 64
    bake = None
    if "--bake-ao" in argv:
        bake = argv[argv.index("--bake-ao") + 1]
    cam = None
    if "--cam" in argv:                        # x y z yaw_deg pitch_deg, game space (Y-up)
        i = argv.index("--cam")
        cam = [float(v) for v in argv[i + 1:i + 6]]
    return glb, out, w, h, spp, bake, cam


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    bpy.ops.import_scene.gltf(filepath=path)
    n_tris = 0
    for ob in bpy.context.scene.objects:
        if ob.type == "MESH" and ob.data:
            n_tris += len(ob.data.loop_triangles) or sum(
                max(0, len(p.vertices) - 2) for p in ob.data.polygons)
    return n_tris


def setup_world(strength=1.0):
    """Physically based sky: a Nishita atmosphere with the game's sun, plus a sun lamp.

    Nishita gives the real blue-to-white gradient and the horizon haze for free; the sharp
    shadows come from the sun lamp, because the sky texture's own sun disc is too soft to
    cast the hard-edged tree shadows that make a garden read as sunny.
    """
    world = bpy.data.worlds.new("sky")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(SUN_EL_DEG)
    sky.sun_rotation = math.radians(180.0 - SUN_AZ_DEG)
    sky.altitude = 50.0
    sky.air_density = 1.0
    sky.dust_density = 2.2                   # a garden has haze; pure air looks like space
    bg.inputs["Strength"].default_value = strength
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    # sun lamp, direction = the game's sun vector
    el = math.radians(SUN_EL_DEG)
    az = math.radians(SUN_AZ_DEG)
    d = Vector((math.sin(az) * math.cos(el), math.sin(el), -math.cos(az) * math.cos(el)))
    sun_data = bpy.data.lights.new("sun", type="SUN")
    sun_data.energy = 4.2
    sun_data.angle = math.radians(0.55)      # the sun's real angular size: soft-ish shadows
    sun_data.color = (1.0, 0.95, 0.87)
    sun = bpy.data.objects.new("sun", sun_data)
    bpy.context.scene.collection.objects.link(sun)
    # a sun lamp shines along -Z of its own space; aim it along -d
    sun.rotation_mode = "QUATERNION"
    sun.rotation_quaternion = (-d).to_track_quat("-Z", "Y")
    return d


def setup_camera(cam):
    sc = bpy.context.scene
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens_unit = "FOV"
    cam_data.angle_y = math.radians(GAME_FOV_Y_DEG)
    cam_data.sensor_fit = "VERTICAL"
    ob = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(ob)
    sc.camera = ob
    if cam is None:
        # the game's spawn, looking north at the house: game space is Y-up, +z forward
        cam = [11.75, 1.62, -13.85, 0.0, -2.0]
    x, y, z, yaw, pitch = cam
    # glTF Y-up -> Blender Z-up: (x, y, z)_game -> (x, -z, y)_blender; forward +z -> -y
    ob.location = (x, -z, y)
    ob.rotation_mode = "XYZ"
    ob.rotation_euler = (math.radians(90.0) + math.radians(pitch),
                         0.0,
                         math.radians(-yaw) + math.radians(180.0))
    return ob


def setup_render(w, h, spp, out):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = spp
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.015
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
        sc.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    except Exception:
        pass
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 4
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.use_fast_gi = True
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.filepath = out
    # AgX is Blender 4.x's filmic curve: it keeps the sun disc and the white plaster from
    # clipping to flat white, which is exactly the failure the game's ACES fit has to fight.
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Punchy"
    except Exception:
        sc.view_settings.view_transform = "Filmic"
    sc.view_settings.exposure = 0.35
    sc.view_settings.gamma = 1.0


def bake_ao(output_json):
    """Bake Cycles ambient occlusion and sun visibility into vertex colours.

    `tools/villa_pack.py` computes the same two channels with a voxel marcher; that is fast
    but it is a box approximation of the geometry. Cycles ray-traces the real triangles, so
    contact shadows under the hedges and the eaves are actually correct. The two channels are
    written as a JSON of per-vertex float lists keyed by object, for the packer to merge.
    """
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 24
    sc.cycles.use_denoising = False
    result = {}
    for ob in [o for o in sc.objects if o.type == "MESH"]:
        me = ob.data
        if not me.vertex_colors:
            me.vertex_colors.new(name="ao")
        # a Cycles bake needs an image node even for vertex colours in 4.x
        img = bpy.data.images.new("ao_bake_" + ob.name, 4, 4, alpha=False)
        mat = ob.active_material or bpy.data.materials.new("ao_tmp")
        mat.use_nodes = True
        nt = mat.node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        nt.nodes.active = node
        ob.active_material = mat
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        try:
            bpy.ops.object.bake(type="AO", target="VERTEX_COLORS", width=4, height=4)
        except Exception as e:                        # noqa: BLE001
            result[ob.name] = {"error": str(e)[:120]}
            continue
        col = me.vertex_colors["ao"]
        vals = []
        for i in range(len(me.vertices)):
            vals.append(0.0)
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                vals[vi] = col.data[li].color[0]
        result[ob.name] = {"ao": [round(v, 3) for v in vals]}
    with open(output_json, "w") as f:
        json.dump(result, f)
    print(f"baked AO for {len(result)} objects -> {output_json}")


def main():
    glb, out, w, h, spp, bake, cam = parse_argv()
    clear_scene()
    n_tris = import_glb(glb)
    d = setup_world()
    setup_camera(cam)
    setup_render(w, h, spp, out)
    print(f"scene: {n_tris} triangles, sun dir ({d.x:.3f}, {d.y:.3f}, {d.z:.3f})")
    if bake:
        bake_ao(bake)
    else:
        bpy.ops.render.render(write_still=True)
    print(MARK + json.dumps({"tris": n_tris, "out": out, "w": w, "h": h, "spp": spp}))


main()
