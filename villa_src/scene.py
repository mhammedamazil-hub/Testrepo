"""Assemble the whole villa scene."""
import math

import bpy

from . import kit, layout, lighting, mats, shell


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    return sc


def build(with_site=True):
    sc = reset()
    colls = shell.build_all()
    colls["furniture"] = kit.collection("Furniture")
    colls["lights"] = kit.collection("Lights")
    colls["extra"] = kit.collection("Site")
    layout.furnish(colls)
    lighting.sky(sc, 1.0)
    lighting.sun(sc)
    lighting.interior(sc, colls)
    if with_site:
        lighting.exterior_props(colls)
    setup_render(sc)
    return sc, colls


def setup_render(sc, res=(1280, 720), samples=128, denoise=True):
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = denoise
    sc.cycles.max_bounces = 8
    sc.cycles.diffuse_bounces = 4
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 6
    sc.cycles.transparent_max_bounces = 6
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.015
    sc.cycles.use_light_tree = True
    sc.cycles.sample_clamp_indirect = 8.0
    sc.cycles.blur_glossy = 1.0
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.use_persistent_data = True
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    sc.view_settings.exposure = -0.15
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_depth = '8'
    return sc


def camera(name, loc, target, lens=24.0, sensor=36.0, dof=None, fstop=5.6):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.sensor_width = sensor
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    from mathutils import Vector
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    if dof:
        cam_data.dof.use_dof = True
        cam_data.dof.focus_distance = dof
        cam_data.dof.aperture_fstop = fstop
    return cam


def render(sc, cam, path, res=(1280, 720), samples=128, denoise=True):
    import time
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.cycles.samples = samples
    sc.cycles.use_denoising = denoise
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - t
