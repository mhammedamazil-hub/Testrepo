"""Villa v2 exterior architecture: real facade articulation, not one white box.

What was wrong with v1
----------------------
Rendered from the garden, the house was a single white volume with a black fascia and
a flat roof. Nothing caught light, nothing cast a shadow onto anything else, and the
eye had no scale reference. That is *why* it read as bad CG, more than any texture
issue.

What this adds
--------------
* **material zoning** - a lime-render upper volume over a **board-formed concrete**
  plinth, with **travertine** piers and a **timber-slat** soffit/entry;
* **relief** - a projecting roof with a deep overhang, a shadow gap between volumes,
  window reveals with sills, downpipes, an entry canopy, a chimney/mast;
* **a real roofscape**: parapet coping, roof upstands, a plant/secondary volume;
* **a site that reads**: terrace with paving joints, a pool with a coping and water,
  gravel margins, planting beds, a driveway with cars absent but garage bay, a low
  garden wall and a gate - so the house sits *in* a place.

All of it is in metres, built by the same `kit` primitives, and named so it can be
found and edited.
"""
import math
import random

import bmesh
import bpy

from . import kit as K  # noqa: F401  (re-exported: build_v2 uses A.K)
from . import mats

H = 3.0
W, D = 19.0, 12.5


def _mat(name):
    return mats.build(name)


# --------------------------------------------------------------------- facade
def facade_extras(coll):
    """Everything between the shell and the detail pass: plinth, piers, sills, reveals."""
    out = []
    ext = 0.30
    x0, x1 = -0.02, W + 0.02
    y0, y1 = -0.02, D + 0.02

    # ---- board-formed concrete plinth wrapping the base (0.0 - 0.85 m)
    plinth_h = 0.85
    out.append(K.slab("plinth_s", x0, y0 - 0.06, x1, y0 + 0.04, 0.0, plinth_h, "board_concrete",
                      bevel=0.008, coll=coll))
    out.append(K.slab("plinth_n", x0, y1 - 0.04, x1, y1 + 0.06, 0.0, plinth_h, "board_concrete",
                      bevel=0.008, coll=coll))
    out.append(K.slab("plinth_w", x0 - 0.06, y0, x0 + 0.04, y1, 0.0, plinth_h, "board_concrete",
                      bevel=0.008, coll=coll))
    out.append(K.slab("plinth_e", x1 - 0.04, y0, x1 + 0.06, y1, 0.0, plinth_h, "board_concrete",
                      bevel=0.008, coll=coll))
    # shadow gap: a dark recess just above the plinth so the upper volume floats
    for name, sl in (("gap_s", (x0, y0, x1, y0 + 0.02)),
                     ("gap_n", (x0, y1 - 0.02, x1, y1)),
                     ("gap_w", (x0, y0, x0 + 0.02, y1)),
                     ("gap_e", (x1 - 0.02, y0, x1, y1))):
        out.append(K.slab(name, sl[0], sl[1], sl[2], sl[3], plinth_h + 0.02, plinth_h + 0.075,
                          "black_steel", coll=coll))

    # ---- travertine piers framing the south glazing, and at the corners
    for i, cx in enumerate((0.30, 6.55, 6.90, 12.35, 12.70, 18.55)):
        out.append(K.box(f"pier_s{i}", (0.36, 0.46, H - 0.30), (cx, -0.10, (H - 0.30) / 2 + 0.85),
                         mat="travertine_clad", bevel=0.012, coll=coll))
    # west corner pier (the "bookend" of the composition)
    out.append(K.box("pier_w1", (0.46, 0.36, H - 0.12), (-0.12, 5.4, (H - 0.12) / 2),
                     mat="travertine_clad", bevel=0.012, coll=coll))
    # ---- window sills + reveals on the north bedrooms
    for i, (a, b) in enumerate(((1.40, 4.20), (8.40, 11.00), (14.20, 16.20), (17.10, 18.20))):
        out.append(K.box(f"sill_n{i}", (b - a + 0.16, 0.24, 0.05), ((a + b) / 2, D + 0.06, 0.45),
                         mat="travertine_clad", bevel=0.006, coll=coll))
        out.append(K.box(f"head_n{i}", (b - a + 0.16, 0.20, 0.06), ((a + b) / 2, D + 0.04, 2.44),
                         mat="lime_render", bevel=0.004, coll=coll))
    # ---- entry: a recessed, lined doorway under a real canopy on two posts.
    # The v1 entrance was a flat walnut panel stuck on a blank wall - that is what made
    # the front of the house read as a garage. A doorway reads as an entrance when it has
    # (a) depth, (b) a lining that catches light differently from the render, (c) a
    # shadow across the head, and (d) something to touch: hardware.
    # `door_front` now sits closed and 0.19 m inside the outer wall face (shell.py).
    for i, (y0, y1) in enumerate(((4.45, 4.51), (5.89, 5.95))):
        out.append(K.slab(f"entry_jamb{i}", 18.74, y0, W, y1, 0.0, 2.36, "cedar",
                          bevel=0.005, coll=coll))
    out.append(K.slab("entry_head", 18.74, 4.45, W, 5.95, 2.29, 2.36, "cedar",
                      bevel=0.005, coll=coll))
    out.append(K.slab("entry_thresh", 18.62, 4.45, W, 5.95, 0.0, 0.028, "black_steel",
                      coll=coll))
    # long vertical pull bar + its standoffs (a pivot-door handle)
    out.append(K.cyl("entry_pull", 0.019, 1.10, (18.85, 5.78, 1.15),
                     mat="black_steel", seg=16, coll=coll))
    for i, z in enumerate((0.64, 1.66)):
        out.append(K.box(f"entry_pull_mtg{i}", (0.055, 0.028, 0.028), (18.83, 5.78, z),
                         mat="black_steel", coll=coll))
    # canopy: 1.45 m deep slab over the door, dark fascia, timber soffit, steel posts
    out.append(K.slab("entry_canopy", W, 4.00, W + 1.45, 6.40, 2.62, 2.78, "lime_render",
                      bevel=0.01, coll=coll))
    out.append(K.slab("canopy_fascia_e", W + 1.37, 4.00, W + 1.46, 6.40, 2.55, 2.78,
                      "black_steel", bevel=0.006, coll=coll))
    for nm, y0, y1 in (("s", 4.00, 4.09), ("n", 6.31, 6.40)):
        out.append(K.slab(f"canopy_fascia_{nm}", W, y0, W + 1.46, y1, 2.55, 2.78,
                          "black_steel", bevel=0.006, coll=coll))
    n_bat = 14
    for i in range(n_bat):
        y = 4.12 + i * (2.16 / (n_bat - 1))
        out.append(K.box(f"canopy_batten{i}", (1.30, 0.085, 0.045),
                         (W + 0.70, y, 2.575), mat="timber_slat", coll=coll))
    for i, y in enumerate((4.13, 6.27)):
        out.append(K.box(f"canopy_post{i}", (0.085, 0.085, 2.62),
                         (W + 1.32, y, 1.31), mat="black_steel", bevel=0.004,
                         coll=coll))
    out.append(K.box("entry_step", (1.05, 2.40, 0.09), (W + 0.38, 5.20, 0.045),
                     mat="stone_paving", bevel=0.01, coll=coll))

    # ---- timber-slat soffit under the roof overhang (south + entry sides)
    soffit_w = 1.75
    n = int((W + 1.8) / 0.145)
    for i in range(n):
        x = -0.5 + i * 0.145
        out.append(K.box(f"soffit_{i}", (0.105, soffit_w, 0.05), (x, -0.62 - soffit_w / 2 + 0.75,
                                                                 H + 0.05),
                         mat="timber_slat", coll=coll))

    # ---- downpipes and a roof drainage expression
    for i, (x, y) in enumerate(((-0.18, -0.18), (W + 0.18, -0.18), (W + 0.18, D + 0.18),
                                (8.30, -0.20))):
        out.append(K.cyl(f"downpipe{i}", 0.055, H + 0.35, (x, y, (H + 0.35) / 2),
                         mat="downpipe", seg=12, coll=coll))
        out.append(K.cyl(f"hoppergr{i}", 0.11, 0.16, (x, y, H + 0.30), mat="downpipe",
                         seg=12, coll=coll))

    # ---- chimney / services mast (a vertical accent; the house had no verticals)
    out.append(K.box("chimney", (0.70, 0.70, 1.10), (13.90, 8.90, H + 0.75),
                     mat="board_concrete", bevel=0.01, coll=coll))
    out.append(K.box("chimney_cap", (0.86, 0.86, 0.07), (13.90, 8.90, H + 1.33),
                     mat="black_steel", bevel=0.006, coll=coll))
    return out


def roof(current_roof):
    """Replace the single slab with a parapet-coped, layered roof build-up."""
    out = []
    # membrane deck sits inside the parapet
    out.append(K.slab("roof_deck", -0.30, -0.30, W + 0.30, D + 0.30, H + 0.16, H + 0.22,
                      "roof_membrane", coll=current_roof))
    # parapet: four upstands, 0.35 high, with an aluminium coping
    ph = 0.42
    for name, x0, y0, x1, y1 in (("par_s", -0.34, -0.34, W + 0.34, -0.22),
                                 ("par_n", -0.34, D + 0.22, W + 0.34, D + 0.34),
                                 ("par_w", -0.34, -0.22, -0.22, D + 0.22),
                                 ("par_e", W + 0.22, -0.22, W + 0.34, D + 0.22)):
        out.append(K.slab(name, x0, y0, x1, y1, H + 0.20, H + 0.20 + ph, "board_concrete",
                          bevel=0.006, coll=current_roof))
        out.append(K.slab(name + "_cope", x0 - 0.02, y0 - 0.02, x1 + 0.02, y1 + 0.02,
                          H + 0.20 + ph, H + 0.24 + ph, "alu_trim", bevel=0.006,
                          coll=current_roof))
    # roof upstands for the chimneys / flues so nothing pokes through a flat plane
    for i, (x, y, r) in enumerate(((13.90, 8.90, 0.42), (4.20, 10.20, 0.16))):
        out.append(K.cyl(f"upstand{i}", r, 0.50, (x, y, H + 0.35), mat="roof_membrane",
                         seg=20, coll=current_roof))
    return out


# ----------------------------------------------------------------- roof plant
def roof_plant(coll):
    """Everything a real flat roof carries, so the aerial is not an empty tray.

    A bare membrane reads as a missing object from above; the fix is ballast, rooflights,
    plant, a hatch and an aerial - the same clutter that tells you a building is used.
    """
    out = []
    z = H + 0.22                                    # top of the membrane deck
    # ballast: 20/40 washed gravel over the membrane, stopping at the parapet
    out.append(K.slab("roof_ballast", -0.24, -0.24, W + 0.24, D + 0.24, z, z + 0.035,
                      "gravel", coll=coll))
    # two rooflights over the living/kitchen with aluminium kerbs
    for i, (x, y, sx, sy) in enumerate(((6.4, 9.4, 1.30, 1.00), (11.2, 4.2, 1.05, 0.85))):
        out.append(K.slab(f"roof_light_kerb{i}", x - sx / 2, y - sy / 2, x + sx / 2,
                          y + sy / 2, z, z + 0.26, "alu_trim", bevel=0.006, coll=coll))
        out.append(K.slab(f"roof_light_glass{i}", x - sx / 2 + 0.07, y - sy / 2 + 0.07,
                          x + sx / 2 - 0.07, y + sy / 2 - 0.07, z + 0.20, z + 0.245,
                          "glass_ribbed", coll=coll))
    # condenser / plant units on anti-vibration feet, with louvred faces
    for i, (x, y, rot) in enumerate(((2.30, 2.10, 0.0), (3.45, 2.10, 0.0),
                                     (16.55, 9.55, 1.5708))):
        out.append(K.box(f"ac_unit{i}", (1.00, 0.62, 0.72), (x, y, z + 0.40),
                         rot=(0, 0, rot), mat="alu_trim", bevel=0.008, coll=coll))
        for k in range(7):
            out.append(K.box(f"ac_louvre{i}_{k}", (0.86, 0.02, 0.045),
                             (x, y - 0.32, z + 0.14 + k * 0.075), rot=(0, 0, rot),
                             mat="black_steel", coll=coll))
        for k in range(4):
            out.append(K.box(f"ac_foot{i}_{k}", (0.10, 0.10, 0.10),
                             (x + (0.4 if k % 2 else -0.4), y + (0.22 if k < 2 else -0.22),
                              z + 0.05), rot=(0, 0, rot), mat="black_steel", coll=coll))
    # roof access hatch near the service corner
    out.append(K.slab("roof_hatch", 17.20, 2.10, 18.00, 2.90, z, z + 0.24, "alu_trim",
                      bevel=0.006, coll=coll))
    # drainage outlets at each corner, with a dark leaf guard
    for i, (x, y) in enumerate(((0.55, 0.55), (W - 0.55, 0.55), (0.55, D - 0.55),
                                (W - 0.55, D - 0.55))):
        out.append(K.cyl(f"roof_outlet{i}", 0.11, 0.05, (x, y, z + 0.045),
                         mat="black_steel", seg=14, coll=coll))
        out.append(K.slab(f"roof_leafguard{i}", x - 0.14, y - 0.14, x + 0.14, y + 0.14,
                          z + 0.06, z + 0.08, "gravel", coll=coll))
    # an aerial mast: the house had no verticals at all from above
    out.append(K.cyl("roof_mast", 0.028, 2.30, (9.10, 10.60, z + 1.15), mat="alu_trim",
                     seg=10, coll=coll))
    for i, (dz, ln) in enumerate(((1.55, 0.62), (1.30, 0.48), (1.05, 0.36))):
        out.append(K.box(f"roof_mast_bar{i}", (0.035, ln, 0.02),
                         (9.10, 10.60 - ln / 2, z + dz), mat="alu_trim", coll=coll))
    # service sleeves where the flues leave the deck (roofs are never seamless)
    for i, (x, y) in enumerate(((13.90, 8.90), (4.20, 10.20))):
        out.append(K.cyl(f"roof_sleeve{i}", 0.20, 0.10, (x, y, z + 0.06),
                         mat="black_steel", seg=18, coll=coll))
    return out


# ------------------------------------------------------- terrace + entry detail
def terrace_detail(coll, veg_coll):
    """Outdoor furniture, planters and small fittings.

    An empty paving slab is the single strongest cue that a render is unoccupied. Two
    loungers, a side table and planted pots also give the eye a known size to compare the
    house against - scale cues are half of what "realistic" means.
    """
    from . import vegetation as V
    out = []
    zt = 0.06                                   # terrace surface
    # two low teak loungers with canvas pads, along the pool side of the terrace
    for i, (x, y) in enumerate(((11.30, -3.05, ), (12.75, -3.05))):
        out.append(K.box(f"lounger{i}_frame", (0.74, 1.92, 0.10), (x, y, zt + 0.16),
                         mat="teak_outdoor", bevel=0.006, coll=coll))
        for k in range(4):
            out.append(K.box(f"lounger{i}_leg{k}", (0.07, 0.07, 0.20),
                             (x + (0.30 if k % 2 else -0.30), y + (0.82 if k < 2 else -0.82),
                              zt + 0.10), mat="teak_outdoor", coll=coll))
        # pad: flat seat + raised back
        out.append(K.box(f"lounger{i}_pad", (0.66, 1.24, 0.09), (x, y + 0.30, zt + 0.26),
                         mat="canvas_cream", bevel=0.02, coll=coll))
        back = K.box(f"lounger{i}_back", (0.66, 0.78, 0.09), (x, y - 0.52, zt + 0.36),
                     rot=(-0.62, 0, 0), mat="canvas_cream", bevel=0.02, coll=coll)
        out.append(back)
        out.append(K.box(f"lounger{i}_towel", (0.42, 0.30, 0.05),
                         (x, y + 0.62, zt + 0.32), rot=(0, 0, 0.2), mat="towel",
                         bevel=0.01, coll=coll))
    # side table between the loungers
    out.append(K.cyl("terrace_table_top", 0.30, 0.05, (12.02, -4.15, zt + 0.52),
                     mat="teak_outdoor", seg=24, coll=coll))
    out.append(K.cyl("terrace_table_stem", 0.05, 0.50, (12.02, -4.15, zt + 0.27),
                     mat="black_steel", seg=12, coll=coll))
    out.append(K.cyl("terrace_table_base", 0.20, 0.03, (12.02, -4.15, zt + 0.02),
                     mat="black_steel", seg=20, coll=coll))
    out.append(K.cyl("terrace_glass", 0.045, 0.13, (12.02, -4.15, zt + 0.60),
                     mat="glass_ribbed", seg=14, coll=coll))

    # ---- planted pots: three against the glazing, two flanking the front door
    def pot(name, x, y, r, h, seed, scale=1.0):
        out.append(K.cyl(name + "_pot", r, h, (x, y, zt + h / 2), mat="plant_pot",
                         seg=20, r2=r * 0.86, coll=coll))
        out.append(K.cyl(name + "_rim", r * 1.03, 0.04, (x, y, zt + h - 0.01),
                         mat="plant_pot", seg=20, coll=coll))
        out.append(K.cyl(name + "_soil", r * 0.92, 0.03, (x, y, zt + h - 0.03),
                         mat="soil", seg=18, coll=coll))
        # a clipped topiary in a pot: squatter than a garden shrub, and with fewer, larger
        # cards so it does not read as a golf ball at 3 m
        sh = V.shrub(seed, 0.52 * scale, 0.52 * scale, coll=veg_coll, cards=420)
        sh.location = (x, y, zt + h - 0.02)
        gr = V.ornamental_grass(seed + 100, 0.42 * scale, 0.55 * scale, coll=veg_coll,
                                blades=70)
        gr.location = (x, y, zt + h - 0.02)
        return sh

    pot("pot_glaze1", 1.60, -0.95, 0.30, 0.62, 61, 0.95)
    pot("pot_glaze2", 6.10, -0.95, 0.26, 0.55, 62, 0.85)
    pot("pot_glaze3", 10.30, -0.95, 0.30, 0.62, 63, 0.95)
    pot("pot_entry1", W + 0.86, 3.92, 0.28, 0.58, 64, 0.9)
    pot("pot_entry2", W + 0.86, 6.44, 0.28, 0.58, 65, 0.9)

    # ---- entry fittings: a wall light and a house number, both tiny, both sell it
    out.append(K.box("entry_light", (0.09, 0.16, 0.30), (W + 0.05, 4.20, 1.95),
                     mat="black_steel", bevel=0.01, coll=coll))
    out.append(K.box("entry_light_face", (0.02, 0.13, 0.24), (W + 0.10, 4.20, 1.95),
                     mat="ceramic", coll=coll))
    out.append(K.box("entry_number", (0.02, 0.30, 0.16), (W + 0.03, 4.20, 2.30),
                     mat="alu_trim", bevel=0.004, coll=coll))
    # ---- wall-washer up-lights on the west garden wall
    for i, y in enumerate((-1.2, 3.4, 7.2)):
        out.append(K.box(f"wall_light{i}", (0.10, 0.10, 0.16), (-0.42, y, 0.52),
                         mat="black_steel", bevel=0.008, coll=coll))
    return out


# ----------------------------------------------------------------------- site
def site_v2(coll):
    """Terrace, pool, gravel margins, planting beds, driveway and garden walls."""
    out = []
    rnd = random.Random(7)

    # ---- terrace: large-format paving with a darker border course
    out.append(K.slab("terrace_v2", -0.15, -4.55, 13.45, 0.05, -0.16, 0.055,
                      "stone_paving", coll=coll))
    for name, x0, y0, x1, y1 in (
            ("terr_border_s", -0.15, -4.75, 13.45, -4.55),
            ("terr_border_w", -0.35, -4.75, -0.15, 0.05),
            ("terr_border_e", 13.45, -4.75, 13.65, 0.05)):
        out.append(K.slab(name, x0, y0, x1, y1, -0.16, 0.06, "lime_render", coll=coll))

    # ---- pool: shell, coping, water, and a slot on the terrace side
    px0, py0, px1, py1 = 14.40, -4.10, 18.90, -0.30
    out.append(K.slab("pool_coping", px0 - 0.35, py0 - 0.35, px1 + 0.35, py1 + 0.35,
                      -0.17, 0.05, "travertine_clad", bevel=0.012, coll=coll))
    out.append(K.slab("pool_basin", px0, py0, px1, py1, -1.75, -1.60, "pool_tile",
                      coll=coll))
    for name, x0, y0, x1, y1 in (("pw_n", px0, py1 - 0.12, px1, py1),
                                 ("pw_s", px0, py0, px1, py0 + 0.12),
                                 ("pw_w", px0, py0, px0 + 0.12, py1),
                                 ("pw_e", px1 - 0.12, py0, px1, py1)):
        out.append(K.slab(name, x0, y0, x1, y1, -1.60, 0.04, "pool_tile", coll=coll))
    out.append(K.slab("pool_water", px0 + 0.12, py0 + 0.12, px1 - 0.12, py1 - 0.12,
                      -0.06, 0.005, "water_ripple", coll=coll))

    # ---- gravel margin between terrace and lawn (breaks the green/stone seam)
    out.append(K.slab("gravel_margin", -0.35, -6.30, 19.3, -4.75, -0.17, 0.02, "gravel",
                      coll=coll))

    # ---- planting beds: raised edges + mulch
    beds = [(0.20, -6.25, 4.40, -5.05), (5.10, -6.25, 8.60, -5.05),
            (9.30, -6.25, 12.60, -5.05), (16.80, -6.25, 19.10, -5.05)]
    for i, (x0, y0, x1, y1) in enumerate(beds):
        out.append(K.slab(f"bed_soil{i}", x0, y0, x1, y1, -0.15, 0.02, "mulch", coll=coll))
        out.append(K.box(f"bed_edge{i}", (x1 - x0 + 0.12, 0.07, 0.12),
                         ((x0 + x1) / 2, y0 - 0.03, 0.0), mat="edging", coll=coll))
        out.append(K.box(f"bed_edge{i}b", (x1 - x0 + 0.12, 0.07, 0.12),
                         ((x0 + x1) / 2, y1 + 0.03, 0.0), mat="edging", coll=coll))

    # ---- driveway with a paving band and a gate pier pair on the east
    out.append(K.slab("drive_v2", 19.4, 3.30, 31.0, 8.10, -0.20, 0.02, "asphalt", coll=coll))
    out.append(K.slab("drive_pad", 19.4, 3.30, 23.6, 8.10, -0.20, 0.035, "stone_paving",
                      coll=coll))
    # gate piers stand clear of the door approach (the v1 pair straddled the entry path)
    for i, y in enumerate((2.60, 9.00)):
        out.append(K.box(f"gate_pier{i}", (0.55, 0.55, 1.55), (24.60, y, 0.72),
                         mat="board_concrete", bevel=0.01, coll=coll))
        # a dark stone cap, not polished metal: a metal top face mirrors the sky and
        # renders as a glowing white box, which is what killed the first entry shot
        out.append(K.box(f"gate_cap{i}", (0.60, 0.60, 0.07), (24.60, y, 1.52),
                         mat="roof_membrane", bevel=0.006, coll=coll))
    # forecourt paving in front of the entry, with a planting strip either side
    out.append(K.slab("forecourt", 19.55, 3.60, 24.30, 8.20, -0.19, 0.04, "stone_paving",
                      coll=coll))
    for i, (y0, y1) in enumerate(((2.20, 3.50), (8.30, 9.60))):
        out.append(K.slab(f"entry_bed{i}", 19.55, y0, 24.30, y1, -0.17, 0.02, "gravel",
                          coll=coll))

    # ---- low garden wall + hedge line to the west (frames the view)
    out.append(K.box("garden_wall_w", (0.24, 15.0, 0.62), (-0.35, 3.20, 0.28),
                     mat="board_concrete", bevel=0.008, coll=coll))
    # ---- stepping path from the terrace into the garden, off to the west so it does not
    #      cut across the hero view of the facade
    for i in range(7):
        out.append(K.box(f"stepstone{i}", (0.70, 0.40, 0.08),
                         (-1.10 - i * 0.05, -5.20 - i * 1.05, 0.005),
                         mat="stone_paving", bevel=0.008, coll=coll))

    # ---- distant hills: a low, deterministic ridge far beyond the plot, so the horizon
    #      reads as landscape instead of the edge of a plane. One mesh, no lighting cost.
    rnd_h = random.Random(11)
    for bi, (y_far, z_amp, dark) in enumerate(((-150.0, 11.0, 1.0), (-240.0, 17.0, 0.65))):
        seg = 96
        span = 700.0
        bm = bmesh.new()
        vb, vt = [], []
        for i in range(seg):
            u = i / (seg - 1)
            x = -span / 2 + u * span
            h = (z_amp * (0.55 + 0.45 * math.sin(u * 7.3 + bi * 2.0))
                 * (0.7 + 0.3 * math.sin(u * 21.0 + bi)) + 2.0)
            vb.append(bm.verts.new((x, y_far, -2.0)))
            vt.append(bm.verts.new((x, y_far + 14.0, h)))
        for i in range(seg - 1):
            try:
                bm.faces.new((vb[i], vb[i + 1], vt[i + 1], vt[i]))
            except ValueError:
                pass
        bm.normal_update()
        me = bpy.data.meshes.new(f"ridge{bi}")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f"ridge{bi}", me)
        (coll or bpy.context.scene.collection).objects.link(ob)
        me.materials.append(mats.build("ridge_dark" if dark < 1 else "ridge_far"))
        out.append(ob)

    # ---- boundary planting strip (dark soil under the tree line)
    # tree-line ground: keep it in the colour range of the lawn so it reads as shade
    # under planting, not as a tan band across the plot
    out.append(K.slab("boundary_bed", -34.0, -32.0, 58.0, -26.0, -0.17, 0.005, "planting_bed",
                      coll=coll))
    out.append(K.slab("boundary_bed_n", -28.0, 25.0, 54.0, 31.0, -0.17, 0.005, "planting_bed",
                      coll=coll))

    # ---- formal gravel apron with clipped box balls, in a rhythm off the terrace
    out.append(K.slab("apron", -0.35, -7.90, 19.30, -6.35, -0.18, 0.015, "gravel", coll=coll))
    for i, x in enumerate((0.4, 3.2, 6.0, 8.8, 11.6, 14.4, 17.2)):
        out.append(K.cyl(f"apron_paver{i}", 0.38, 0.02, (x, -7.10, 0.02), mat="stone_paving",
                         seg=28, coll=coll))
    return out


def garden(veg_coll, site_coll):
    """Planting plan: species, positions, and a legible composition.

    Rules used (these are the ones that make a garden read as designed rather than
    sprinkled): a tall canopy tree on each side of the main view, a mid layer of olives
    and cypresses to give depth, a low clipped hedge line to tie the bed edges
    together, textured grasses at the terrace edge, and nothing dead centre.
    """
    from . import vegetation as V
    objs = []

    def place(fn, x, y, scale=1.0, rotz=0.0):
        ob = fn()
        ob.location = (x, y, 0.0)
        ob.scale = (scale, scale, scale)
        ob.rotation_euler = (0, 0, rotz)
        objs.append(ob)
        return ob

    # ---- canopy trees: they frame the view from the sides, never in front of it.
    #      A tree between the camera and a glass facade reads as a "tree stuck on a
    #      wall" because you cannot see where it is planted.
    place(lambda: V.broadleaf(1, 9.6, 3.6, coll=veg_coll), -12.5, -12.4, 1.0, 0.4)
    place(lambda: V.broadleaf(11, 9.0, 4.1, coll=veg_coll), 28.0, -14.0, 1.0, 2.1)
    place(lambda: V.broadleaf(21, 8.2, 3.2, coll=veg_coll), 33.0, -7.4, 1.0, 1.2)
    place(lambda: V.broadleaf(51, 7.4, 2.6, coll=veg_coll), -16.0, -4.6, 1.0, 3.1)
    # north garden so bedroom windows have depth, and it never appears in the south shot
    place(lambda: V.broadleaf(31, 8.8, 3.2, coll=veg_coll), 3.2, 17.4, 1.0, 0.9)
    place(lambda: V.broadleaf(41, 7.4, 2.8, coll=veg_coll), 12.4, 18.6, 1.0, 2.6)

    # ---- mid layer: olives and cypress columns
    place(lambda: V.olive(2, 5.1, 2.6, coll=veg_coll), -6.4, -14.2, 1.0, 0.0)
    place(lambda: V.olive(12, 4.5, 2.3, coll=veg_coll), 16.8, -12.6, 1.0, 1.7)
    for i, (x, y) in enumerate(((13.2, -8.4), (18.4, -8.0), (-4.2, -15.4), (21.8, -14.0))):
        place(lambda i=i: V.cypress(3 + i, 7.6 + (i % 3) * 1.1, 0.78, coll=veg_coll), x, y,
              1.0, i * 0.7)
    # palms flank the pool, as a Mediterranean garden would
    # Palms sit behind the pool, not between a camera and the facade: a palm 4 m from a
    # 30 mm lens puts its trunk across the whole frame and (because the fronds are cards)
    # leaves them reading as detached paddles against the sky.
    place(lambda: V.palm(4, 9.4, coll=veg_coll), 25.4, 1.4, 1.0, 0.5)
    place(lambda: V.palm(14, 8.0, coll=veg_coll), 29.0, -6.2, 1.0, 2.2)

    # ---- clipped hedge line tying the beds together
    for i, (x0, x1) in enumerate(((0.2, 4.4), (5.1, 8.6), (9.3, 12.6), (16.8, 19.1))):
        place(lambda x0=x0, x1=x1, i=i: V.hedge(f"hedge_bed{i}", x0, -6.20, x1, -5.10, 0.72,
                                                coll=veg_coll, density=700.0, seed=70 + i),
              0.0, 0.0)
    # taller hedge running along the west garden wall
    place(lambda: V.hedge("hedge_west", -0.55, -4.6, -0.10, 10.6, 1.65, coll=veg_coll,
                          density=700.0, seed=91), 0.0, 0.0)

    # ---- textured low planting at the terrace edge
    for i, (x, y, r) in enumerate(((2.4, -5.55, 0.42), (3.6, -5.72, 0.36), (6.4, -5.60, 0.40),
                                   (10.6, -5.58, 0.42), (11.9, -5.72, 0.34),
                                   (17.6, -5.60, 0.40), (18.7, -5.74, 0.32))):
        place(lambda i=i, r=r: V.ornamental_grass(8 + i, r, 1.15, coll=veg_coll), x, y)
    for i, (x, y) in enumerate(((1.2, -5.5), (7.4, -5.6), (13.6, -5.4), (19.0, -5.6))):
        place(lambda i=i: V.agave(9 + i, 0.95, coll=veg_coll), x, y, 1.0, i)
    # clipped box balls on the gravel apron: formal counterpoint to the loose planting
    for i, x in enumerate((0.4, 3.2, 6.0, 8.8, 11.6, 14.4, 17.2)):
        place(lambda i=i: V.shrub(60 + i, 0.42, 0.48, coll=veg_coll,
                                  leaf_mat="spray_b", cards=700), x, -7.10, 1.0, i * 0.6)
    for i, (x, y, r) in enumerate(((0.9, -5.75, 0.62), (4.2, -5.85, 0.50), (8.8, -5.70, 0.68),
                                   (12.9, -5.78, 0.55), (15.4, -6.05, 0.72), (14.2, -5.6, 0.45))):
        place(lambda i=i, r=r: V.shrub(5 + i, r, coll=veg_coll), x, y)

    # ---- boundary tree line (cheap: cypress + broadleaf mix, far enough to read as depth)
    for i in range(16):
        x = -26 + i * 5.2 + (i % 3) * 1.1
        y = -27.0 - (i % 4) * 2.4
        if i % 3 == 0:
            place(lambda i=i: V.cypress(200 + i, 8.0 + (i % 4), 0.9, coll=veg_coll), x, y)
        else:
            place(lambda i=i: V.broadleaf(200 + i, 7.0 + (i % 4) * 1.3, 2.9, coll=veg_coll),
                  x, y)
    for i in range(10):
        x = -20 + i * 6.0
        place(lambda i=i: V.cypress(300 + i, 9.0 + (i % 3), 0.85, coll=veg_coll), x,
              25.0 + (i % 3) * 1.6)
    # east side: screen planting so the drive is not a void
    for i in range(5):
        place(lambda i=i: V.olive(400 + i, 4.2, 2.0, coll=veg_coll), 26.0 + i * 3.4,
              -2.0 + i * 3.2)
    return objs
