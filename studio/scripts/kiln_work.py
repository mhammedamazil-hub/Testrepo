"""
KILN — case-study plates, rendered in Blender/Cycles.

Each plate is its own set: commerce (a stepped gallery of objects), property (a
massing model on a board), launch (a single form on a turning plinth). All share
the house light rig so the site reads as one studio rather than three stock images.

    LD_LIBRARY_PATH=/tmp/xstub python3 -u scripts/kiln_work.py
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kiln_render import (  # noqa: E402
    EMBER, INK, PLASTER, TERRACOTTA, arched_wall, box, cam, light, material, render, reset, world,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "brand", "renders")
os.makedirs(OUT, exist_ok=True)

W, H = 1400, 1750  # 4:5 portrait plates, matching the site grid


def house_light(key=2100, rim=900, fill=150):
    light("key", "AREA", (-6.2, -5.0, 6.0), key, size=4.4, color=(1.0, 0.845, 0.66))
    light("fill", "AREA", (6.4, -6.4, 3.0), fill, size=7.0, color=(0.72, 0.78, 0.88))
    light("rim", "AREA", (1.2, 4.6, 3.2), rim, size=2.0, color=(1.0, 0.46, 0.18))


def atelier():
    """Commerce — a stepped plinth with three vessels, like a gallery display."""
    reset()
    world(strength=0.26)
    plaster = material("pl", PLASTER, rough=0.76, bump=0.003, scale=8)
    terra = material("te", TERRACOTTA, rough=0.6, bump=0.008, scale=22)
    slate = material("sl", (0.05, 0.054, 0.064), rough=0.36, metal=0.06)

    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
    bpy.context.object.data.materials.append(slate)

    box("step_a", (0, 1.6, 0.22), (4.2, 3.0, 0.44), plaster)
    box("step_b", (0.1, 1.5, 0.62), (3.1, 2.1, 0.36), plaster, rot=(0, 0, math.radians(-3)))

    specs = [
        ((0.75, 1.45, 1.30), 0.40, 0.92, terra),
        ((-0.55, 1.75, 1.18), 0.30, 0.68, plaster),
        ((0.05, 1.05, 1.06), 0.20, 0.48, terra),
    ]
    for i, (loc, r, d, mat) in enumerate(specs):
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=r, depth=d, location=loc)
        ob = bpy.context.object
        ob.data.materials.append(mat)
        bpy.ops.object.shade_smooth()

    # sliver of wall behind for depth
    box("back", (2.6, 4.2, 1.6), (3.2, 0.3, 3.2), plaster, rot=(0, 0, math.radians(-18)))

    house_light(key=2300, rim=700, fill=140)
    cam("atelier", (5.0, -7.4, 3.5), (0.15, 1.5, 1.15), lens=62, fstop=2.2)
    render(os.path.join(OUT, "work-atelier.png"), W, H, samples=56)


def meridian():
    """Property — one tower, seen from the street: podium, punched windows, dusk key."""
    reset()
    world(strength=0.30)
    plaster = material("pl2", (0.82, 0.80, 0.765), rough=0.72, bump=0.0025, scale=6)
    stone = material("st3", (0.56, 0.545, 0.515), rough=0.76, bump=0.004, scale=12)
    glass = material("gl", (0.028, 0.038, 0.052), rough=0.16, metal=0.35, spec=0.6)
    lit = material("litwin", (0.96, 0.60, 0.30), rough=0.55)
    board = material("bd", (0.022, 0.024, 0.030), rough=0.30, metal=0.10)
    back = material("bk", (0.030, 0.031, 0.034), rough=0.85, bump=0.004, scale=8)

    bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 0, 0))
    bpy.context.object.data.materials.append(board)

    # ground slab
    box("plinth", (0, 0, 0.10), (16, 14, 0.20), board)


    TX, TY = -0.55, 0.35           # tower centre
    TW, TD, TH = 2.5, 1.9, 8.4     # width, depth, height
    FLOORS, BAYS = 7, 3

    # podium
    box("podium", (TX + 0.15, TY - 0.55, 1.05), (5.0, 3.6, 1.9), plaster)
    box("podiumcap", (TX + 0.15, TY - 0.55, 2.02), (5.15, 3.75, 0.14), stone)
    # lobby glazing: a recessed dark band with mullions, so the base reads as inhabited
    box("lobby", (TX + 0.15, TY - 2.36, 0.92), (4.7, 0.06, 1.30), glass)
    for m in range(6):
        box(f"mull{m}", (TX - 2.10 + m * 0.94, TY - 2.38, 0.92), (0.07, 0.06, 1.34), stone)

    # tower shaft
    box("tower", (TX, TY, 2.10 + TH / 2), (TW, TD, TH), plaster)

    # vertical fins on the two visible faces: reads as structure, not texture
    for b in range(BAYS + 1):
        x = TX - TW / 2 + b * TW / BAYS
        for face in (-1, 1):
            if face < 0:
                box(f"fin{b}{face}", (x, TY - TD / 2 - 0.06, 2.10 + TH / 2),
                    (0.055, 0.11, TH), stone)
            else:
                box(f"fin{b}{face}", (x, TY + TD / 2 + 0.06, 2.10 + TH / 2),
                    (0.055, 0.11, TH), stone)
    for face in (-1, 1):
        x = TX + face * (TW / 2 + 0.06)
        box(f"finS{face}", (x, TY, 2.10 + TH / 2), (0.11, TD, TH), stone)

    # windows: recessed dark panes between the fins, a few of them lit
    for f in range(FLOORS):
        for b in range(BAYS):
            x = TX - TW / 2 + (b + 0.5) * TW / BAYS
            z = 2.55 + f * (TH - 0.9) / FLOORS
            for face in (-1, 1):
                y = TY + face * (TD / 2 + 0.005)
                mat = lit if (face < 0 and z > 5.4 and (b + f) % 4 == 0) else glass
                box(f"w{f}{b}{face}", (x, y, z), (TW / BAYS - 0.18, 0.05, 0.44), mat)
            # short face
            x2 = TX + face * (TW / 2 + 0.005)
            box(f"ws{f}{b}", (x2, TY - TD / 2 + (b + 0.5) * TD / BAYS, z),
                (0.05, TD / BAYS - 0.22, 0.44), glass if face > 0 else lit if (b + f) % 5 == 0 else glass)

    # floor slab bands, the horizontal rhythm
    for f in range(1, FLOORS):
        z = 2.55 + f * (TH - 0.9) / FLOORS - 0.26
        box(f"slab{f}", (TX, TY, z), (TW + 0.14, TD + 0.14, 0.08), stone)

    # crown
    box("crown", (TX, TY, 2.10 + TH + 0.22), (TW + 0.4, TD + 0.4, 0.44), stone)

    # a lower neighbour for depth
    box("nb", (TX + 3.9, TY + 1.4, 1.9), (2.2, 3.0, 3.8), stone, rot=(0, 0, math.radians(-6)))
    for f in range(4):
        for b in range(2):
            box(f"nbw{f}{b}", (TX + 3.9 - 0.55 + b * 1.1, TY + 1.4 - 1.55, 0.85 + f * 0.85),
                (0.62, 0.05, 0.34), glass)

    # ember signage line at the podium — the only saturated element
    box("strip", (TX + 0.2, TY - 2.42, 1.42), (2.6, 0.05, 0.05), material("emb2", EMBER, rough=0.4))

    house_light(key=3400, rim=1900, fill=70)
    light("up", "AREA", (0.0, -3.2, 0.4), 420, size=3.0, color=(1.0, 0.55, 0.28))
    cam("meridian", (10.6, -17.4, 3.4), (-0.05, 0.3, 5.4), lens=40, fstop=3.4)
    render(os.path.join(OUT, "work-meridian.png"), W, H, samples=56)


def kinetic():
    """Launch — one turned form on a plinth, extreme rim light, product-shot framing."""
    reset()
    world(strength=0.2)
    terra = material("te3", (0.66, 0.22, 0.10), rough=0.42, bump=0.004, scale=30, metal=0.06)
    plaster = material("pl3", PLASTER, rough=0.8, bump=0.003, scale=7)
    slate = material("sl3", (0.045, 0.048, 0.056), rough=0.28, metal=0.12)

    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
    bpy.context.object.data.materials.append(slate)

    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=1.15, depth=0.5, location=(0, 0, 0.25))
    bpy.context.object.data.materials.append(plaster)

    # the hero form: a twisted stack of slabs — reads as "kinetic" without a showreel gimmick
    for i in range(11):
        z = 0.55 + i * 0.185
        t = i / 10.0
        w = 1.30 - 0.55 * t
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0.10 * math.sin(t * 3.0), 0.10 * math.cos(t * 3.0), z))
        slab = bpy.context.object
        slab.scale = (w, w * 0.46, 0.082)
        slab.rotation_euler = (0, 0, math.radians(i * 13.5))
        slab.data.materials.append(terra if i % 2 == 0 else plaster)
        bpy.ops.object.modifier_add(type='BEVEL')
        slab.modifiers["Bevel"].width = 0.012
        slab.modifiers["Bevel"].segments = 3
        bpy.ops.object.shade_smooth()

    # a slab behind, catching the rim
    box("slab", (-2.4, 2.0, 1.5), (0.4, 2.6, 3.0), plaster, rot=(0, 0, math.radians(20)))

    house_light(key=1500, rim=1600, fill=110)
    cam("kinetic", (4.4, -6.6, 3.0), (0.0, 0.1, 1.55), lens=76, fstop=2.0)
    render(os.path.join(OUT, "work-kinetic.png"), W, H, samples=64)


def hero_variants():
    """Square social plate + the wide OG card, from the house set."""
    reset()
    world(strength=0.28)
    plaster = material("pl4", PLASTER, rough=0.74, bump=0.003, scale=7)
    terra = material("te4", TERRACOTTA, rough=0.64, bump=0.009, scale=20)
    slate = material("sl4", (0.048, 0.052, 0.062), rough=0.38, metal=0.06)

    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
    bpy.context.object.data.materials.append(slate)
    arched_wall("kiln2", (1.35, 2.4, 0.0), 5.6, 4.0, 0.5, plaster,
              rot=(0, 0, math.radians(-16)), opening_w=1.6, opening_h=1.45)
    box("stele2", (-0.9, 0.2, 1.9), (1.05, 1.05, 3.8), plaster, rot=(0, 0, math.radians(9)))
    box("bench2", (1.3, -0.6, 0.28), (2.9, 1.3, 0.56), plaster, rot=(0, 0, math.radians(-6)))
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=0.42, depth=1.0, location=(1.25, -0.55, 1.06))
    bpy.context.object.data.materials.append(terra)
    bpy.ops.object.shade_smooth()

    house_light()
    cam("sq", (6.4, -8.6, 3.0), (0.2, 0.3, 1.35), lens=44, fstop=2.4)
    render(os.path.join(OUT, "square-1600x1600.png"), 1600, 1600, samples=48)

    cam("og", (6.0, -9.6, 2.4), (0.0, 0.5, 1.25), lens=42, fstop=2.6)
    render(os.path.join(OUT, "og-2400x1260.png"), 2400, 1260, samples=48)


JOBS = {"atelier": atelier, "meridian": meridian, "kinetic": kinetic, "hero": hero_variants}

if __name__ == "__main__":
    which = sys.argv[1:] or list(JOBS)
    for name in which:
        JOBS[name]()
    print("KILN_WORK_DONE")
