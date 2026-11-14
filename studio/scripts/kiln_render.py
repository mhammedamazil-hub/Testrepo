"""
KILN — brand plates rendered in Blender/Cycles (bpy).

Why this exists: the previous pass drew its art with a hand-rolled JS ray-tracer, which is
why everything looked like a "3D illustration" rather than a photograph of an object. This
script builds actual geometry, plaster and terracotta shaders, a three-light rig and a
35 mm lens with depth of field, and renders with Cycles GI + denoise.

Run headless (the libX stubs are only needed because this box has no X/GL):
    LD_LIBRARY_PATH=/tmp/xstub python3 scripts/kiln_render.py

Outputs go to brand/renders/.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "brand", "renders")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- palette
INK = (0.014, 0.016, 0.021)
PLASTER = (0.87, 0.845, 0.80)
TERRACOTTA = (0.62, 0.20, 0.09)
SAGE = (0.28, 0.34, 0.28)
EMBER = (1.0, 0.42, 0.16)


# ---------------------------------------------------------------- helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.use_denoising = True
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    return sc


def material(name, base, rough=0.62, bump=0.006, scale=14.0, spec=0.35, metal=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec

    # subtle casting-scale surface noise so the plaster catches light unevenly
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = 6.0
    tex.inputs["Roughness"].default_value = 0.62
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.18
    bmp.inputs["Distance"].default_value = bump
    nt.links.new(tex.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])

    # faint mottling in the base colour
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*[c * 0.88 for c in base], 1)
    ramp.color_ramp.elements[1].color = (*[min(1, c * 1.06) for c in base], 1)
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def box(name, loc, size, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    ob.rotation_euler = rot
    ob.data.materials.append(mat)
    bpy.ops.object.shade_flat()
    return ob


def arched_wall(name, loc, w, h, d, mat, rot=(0, 0, 0), opening_w=1.2, opening_h=1.5, seg=128):
    """A slab with a true arched opening cut through it — the kiln mouth.

    Built from a box plus two boolean cutters (a box for the straight jambs and a
    cylinder for the semicircular head) so the reveal has real thickness and the
    light rakes across it.
    """
    bpy.ops.mesh.primitive_cube_add(size=1, location=(loc[0], loc[1], loc[2] + h / 2))
    wall = bpy.context.object
    wall.name = name
    wall.scale = (w, d, h)
    wall.rotation_euler = rot
    wall.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # straight jambs
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(loc[0], loc[1], loc[2] + opening_h / 2)
    )
    jamb = bpy.context.object
    jamb.scale = (opening_w, d * 3, opening_h)
    jamb.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # semicircular head
    r = opening_w / 2
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=seg,
        radius=r,
        depth=d * 3,
        location=(loc[0], loc[1], loc[2] + opening_h),
        rotation=(math.pi / 2, 0, 0),
    )
    head = bpy.context.object
    if rot[2]:
        head.rotation_euler = (math.pi / 2, 0, rot[2])

    # keep only the upper half of the disc (the arch head)
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(loc[0], loc[1], loc[2] + opening_h + r * 0.75)
    )
    clip = bpy.context.object
    clip.scale = (r * 3, d * 3, r * 1.5)
    clip.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bpy.context.view_layer.objects.active = head
    m = head.modifiers.new("clip", "BOOLEAN")
    m.operation = "INTERSECT"
    m.object = clip
    bpy.ops.object.modifier_apply(modifier="clip")
    bpy.data.objects.remove(clip, do_unlink=True)

    for cutter in (jamb, head):
        bpy.context.view_layer.objects.active = wall
        m = wall.modifiers.new("cut", "BOOLEAN")
        m.operation = "DIFFERENCE"
        m.object = cutter
        m.solver = "EXACT"
        bpy.ops.object.modifier_apply(modifier="cut")
        bpy.data.objects.remove(cutter, do_unlink=True)

    bpy.ops.object.select_all(action="DESELECT")
    wall.select_set(True)
    bpy.context.view_layer.objects.active = wall
    bpy.ops.object.shade_flat()
    return wall


def cam(name, loc, look, lens=35, fstop=2.8):
    bpy.ops.object.camera_add(location=loc)
    c = bpy.context.object
    c.name = name
    c.data.lens = lens
    c.data.sensor_width = 36
    d = Vector(look) - Vector(loc)
    c.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    c.data.dof.use_dof = True
    c.data.dof.focus_distance = d.length
    c.data.dof.aperture_fstop = fstop
    bpy.context.scene.camera = c
    return c


def light(name, kind, loc, energy, size=2.0, color=(1, 0.95, 0.88)):
    bpy.ops.object.light_add(type=kind, location=loc)
    lt = bpy.context.object
    lt.name = name
    lt.data.energy = energy
    lt.data.color = color
    if kind == "AREA":
        lt.data.size = size
    d = Vector((0, 0, 1.0)) - Vector(loc)
    lt.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return lt


def world(dark=INK, strength=0.35):
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*dark, 1)
    bg.inputs["Strength"].default_value = strength


def render(path, w, h, samples=48):
    sc = bpy.context.scene
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.max_bounces = 6
    sc.cycles.transparent_max_bounces = 4
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", os.path.basename(path), w, "x", h)


# ---------------------------------------------------------------- scenes
def scene_vessel():
    """Hero still life — a kiln mouth, two plaster masses, one unfired vessel.

    Asymmetric by intent: mass to the right of centre, a small warm form low left,
    open dark space top-left where the wordmark will sit.
    """
    reset()
    world(strength=0.28)
    plaster = material("plaster", PLASTER, rough=0.74, bump=0.003, scale=7)
    terra = material("terracotta", TERRACOTTA, rough=0.64, bump=0.009, scale=20)
    slate = material("slate", (0.048, 0.052, 0.062), rough=0.38, metal=0.06)

    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
    bpy.context.object.data.materials.append(slate)

    # architecture: a thick plaster wall with an arched kiln mouth
    arched_wall(
        "kiln", (1.55, 3.10, 0.0), 5.2, 3.9, 0.55, plaster,
        rot=(0, 0, math.radians(-16)), opening_w=1.55, opening_h=1.45,
    )

    # tall stele — the quiet vertical, slightly forward of the wall
    box("stele", (-0.95, 0.10, 1.95), (1.05, 1.05, 3.9), plaster, rot=(0, 0, math.radians(9)))

    # low bench, the horizontal that stops the eye
    box("bench", (1.35, -0.75, 0.29), (3.0, 1.35, 0.58), plaster, rot=(0, 0, math.radians(-6)))

    # the only saturated object: an unfired terracotta vessel on the bench
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=128, radius=0.42, depth=1.05, location=(1.28, -0.72, 1.11)
    )
    cyl = bpy.context.object
    cyl.data.materials.append(terra)
    bpy.ops.object.shade_smooth()
    bev = cyl.modifiers.new("bev", "BEVEL")
    bev.width = 0.03
    bev.segments = 4
    bpy.ops.object.modifier_apply(modifier="bev")

    # a small warm sphere at the base of the stele — the single "alive" note
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=64, ring_count=32, radius=0.17, location=(-1.42, -0.62, 0.17)
    )
    bpy.context.object.data.materials.append(terra)
    bpy.ops.object.shade_smooth()

    # rig — warm key, cool fill, hard ember rim from behind the wall
    light("key", "AREA", (-6.2, -5.0, 6.0), 2400, size=4.4, color=(1.0, 0.845, 0.66))
    light("fill", "AREA", (6.4, -6.4, 3.0), 150, size=7.0, color=(0.72, 0.78, 0.88))
    light("rim", "AREA", (1.2, 4.6, 3.2), 900, size=2.0, color=(1.0, 0.46, 0.18))

    cam("hero", (7.6, -11.8, 2.35), (-0.30, 0.60, 1.45), lens=68, fstop=2.8)
    render(os.path.join(OUT, "hero-2400x1600.png"), 2400, 1600, samples=64)

    cam("portrait", (6.0, -10.2, 2.55), (-0.10, 0.55, 1.55), lens=60, fstop=2.2)
    render(os.path.join(OUT, "keyart-1600x2000.png"), 1600, 2000, samples=64)

    cam("square", (7.0, -10.6, 2.5), (0.20, 0.45, 1.35), lens=56, fstop=2.2)
    render(os.path.join(OUT, "square-1600x1600.png"), 1600, 1600, samples=56)


def scene_detail():
    """Macro detail — the tile/poster image. Shallow focus, dust, warm ember light."""
    reset()
    world(strength=0.22)
    plaster = material("plaster2", PLASTER, rough=0.8, bump=0.005, scale=26)
    terra = material("terra2", TERRACOTTA, rough=0.62, bump=0.012, scale=34)
    slate = material("slate2", (0.05, 0.055, 0.065), rough=0.35, metal=0.1)

    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    bpy.context.object.data.materials.append(slate)

    box("step1", (0, 0, 0.18), (4.4, 2.6, 0.36), plaster, rot=(0, 0, math.radians(3)))
    box("step2", (0.1, 0.05, 0.55), (3.0, 1.7, 0.38), plaster, rot=(0, 0, math.radians(-2)))
    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=0.62, depth=0.9, location=(0.25, 0.0, 1.18))
    bpy.context.object.data.materials.append(terra)
    bpy.ops.object.shade_smooth()

    light("key", "AREA", (-3.4, -3.0, 4.2), 900, size=3.0, color=(1.0, 0.83, 0.62))
    light("rim", "AREA", (2.0, 3.4, 2.2), 300, size=1.6, color=(1.0, 0.45, 0.2))

    cam("macro", (2.9, -3.6, 1.35), (0.15, 0.1, 0.95), lens=85, fstop=1.8)
    render(os.path.join(OUT, "detail-2400x1350.png"), 2400, 1350, samples=64)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "vessel"):
        scene_vessel()
    if which in ("all", "detail"):
        scene_detail()
    print("KILN_PLATES_DONE")
