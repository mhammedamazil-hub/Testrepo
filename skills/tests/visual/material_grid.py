"""Visual proof for the material skills: a grid of spheres/panels, one per material.

Renders a single contact sheet so the *rendered result* - not just the script exit
code - can be inspected. Run through tools/bpy_run.py:

  python tools/bpy_run.py skills/tests/visual/material_grid.py -- --out /tmp/matgrid.png
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
SK = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(SK, "local", "_shared"))
sys.path.insert(0, os.path.join(SK, "local", "materials-glass", "scripts"))
sys.path.insert(0, os.path.join(SK, "local", "materials-automotive-paint", "scripts"))
sys.path.insert(0, os.path.join(SK, "local", "materials-surfaces", "scripts"))
sys.path.insert(0, os.path.join(SK, "local", "materials-imperfections", "scripts"))

import skill_common as sc  # noqa: E402
import glass_materials  # noqa: E402
import car_paint  # noqa: E402
import surface_materials  # noqa: E402
import imperfections  # noqa: E402


def build_items():
    """(label, material) - glass/paint/surface families plus an imperfection demo."""
    items = [
        ("glass architectural", glass_materials.build("architectural", tint=(0.92, 0.97, 1.0))),
        ("glass thin", glass_materials.build("thin")),
        ("glass frosted", glass_materials.build("frosted")),
        ("paint metallic blue", car_paint.build((0.015, 0.05, 0.16), "metallic", flake=0.45)),
        ("paint pearl white", car_paint.build((0.72, 0.73, 0.74), "pearl", flake=0.35)),
        ("paint matte black", car_paint.build((0.02, 0.02, 0.022), "matte")),
        ("paint chrome", car_paint.build(kind="chrome")),
        ("rubber", surface_materials.build("rubber")),
        ("leather", surface_materials.build("leather")),
        ("carbon twill", surface_materials.build("carbon_twill")),
        ("brushed alu", surface_materials.build("brushed")),
        ("anodised blue", surface_materials.build("anodised", color=(0.03, 0.09, 0.32))),
        ("powdercoat", surface_materials.build("powdercoat")),
        ("worn paint", None),   # filled below: metallic + imperfections
        ("aged primer", None),
    ]
    worn = car_paint.build((0.35, 0.06, 0.05), "solid", name="paint_worn")
    imperfections.add_imperfections(worn, wear=0.8, dust=0.35, scratches=0.5,
                                    fingerprints=0.25, grime=0.5)
    aged = surface_materials.build("powdercoat", color=(0.45, 0.44, 0.42), name="aged_primer")
    imperfections.add_imperfections(aged, wear=0.9, dust=0.6, scratches=0.7, grime=0.8)
    items[-2] = ("worn paint + imperfections", worn)
    items[-1] = ("aged primer + imperfections", aged)
    return items


def main(out="/tmp/matgrid.png", res=(1500, 900), samples=48):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    items = build_items()
    cols = 5
    # backdrop: a large cyclorama-ish plane so glass has something to refract
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "Backdrop"
    fm = bpy.data.materials.new("BackdropMat")
    fm.use_nodes = True
    b = sc.principled(fm)
    sc.set_input(b, "Base Color", (0.32, 0.33, 0.35, 1))
    sc.set_input(b, "Roughness", 0.45)
    floor.data.materials.append(fm)
    # a backdrop wall with a dark/light checker for reflection readability
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 4.0, 6.0),
                                     rotation=(math.radians(90), 0, 0))
    wall = bpy.context.object
    wm = bpy.data.materials.new("WallMat")
    wm.use_nodes = True
    b = sc.principled(wm)
    chk = wm.node_tree.nodes.new("ShaderNodeTexChecker")
    chk.inputs["Scale"].default_value = 6.0
    wm.node_tree.links.new(chk.outputs["Color"], b.inputs["Base Color"])
    sc.set_input(b, "Roughness", 0.6)
    wall.data.materials.append(wm)

    for i, (label, mat) in enumerate(items):
        cx = (i % cols - (cols - 1) / 2) * 1.02
        cy = (i // cols) * 0.86
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.36, segments=48, ring_count=24,
                                             location=(cx, cy, 0.42))
        ob = bpy.context.object
        ob.name = "M_" + label.replace(" ", "_").replace("+", "plus")
        bpy.ops.object.shade_smooth()
        ob.data.materials.append(mat)
        if "glass" in label:  # glass needs something inside/behind it to read
            bpy.ops.mesh.primitive_cube_add(size=0.28, location=(cx, cy + 0.12, 0.34))
            cube = bpy.context.object
            cm = surface_materials.build("powdercoat", color=(0.62, 0.61, 0.58),
                                         name=f"inside_{i}")
            cube.data.materials.append(cm)

    # studio lighting: key + rim + fill, plus a soft world
    world = bpy.data.worlds.new("W")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.37, 0.42, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.35
    for name, loc, energy, size in (("key", (3.2, -3.6, 4.6), 900, 3.0),
                                    ("rim", (-3.8, 2.2, 3.4), 500, 2.5),
                                    ("fill", (-2.0, -4.0, 1.6), 220, 4.0)):
        lg = bpy.data.lights.new(name, "AREA")
        lg.energy, lg.size = energy, size
        ob = bpy.data.objects.new(name, lg)
        scene.collection.objects.link(ob)
        ob.location = loc
        from mathutils import Vector
        ob.rotation_euler = (Vector((0.0, -1.0, 0.4)) - Vector(loc)).to_track_quat(
            '-Z', 'Y').to_euler()
    cam = sc.camera("cam", (0.0, -3.2, 9.0), (0.0, 0.42, 0.30), lens=50,
                    ortho_scale=6.4)
    scene.camera = cam
    sc.look_transform(scene, "AgX - Medium High Contrast")
    sc.render(out, res=res, samples=samples, cam=cam)
    sc.emit({"ok": True, "image": out, "materials": [i[0] for i in items]})
    print("labels:", [(i, l) for i, (l, _) in enumerate(items)])


if __name__ == "__main__":
    p = sc.parser(__doc__)
    p.add_argument("--out", default="/tmp/matgrid.png")
    p.add_argument("--samples", type=int, default=48)
    a = p.parse_args(sc.argv())
    main(a.out, samples=a.samples)
