"""Furnishing layout: places every piece in every room.

Each entry: (builder, name, x, y, rot_deg, kwargs). Rotation is about Z; a piece
faces -Y at rotation 0.
"""
import math

from . import furniture as F, kit

# room floor heights (tiled wet areas are 12 mm up)
Z_TILE = 0.012


def put(builder, name, x, y, rot=0.0, z=0.0, coll=None, **kw):
    """Place a piece. `z` is passed to the builder when it accepts one (pieces that
    are authored at an absolute height, e.g. wall cabinets or a range hood), and is
    otherwise used to lift the object (wall art, mirrors, objects on surfaces)."""
    import inspect
    if "z" in inspect.signature(builder).parameters:
        kw["z"] = z
        lift = 0.0
    else:
        lift = z
    ob = builder(coll=coll, **kw)
    ob.name = name
    ob.data.name = name
    ob.location = (x, y, lift)
    ob.rotation_euler = (0, 0, math.radians(rot))
    return ob


def furnish(colls):
    c = colls["furniture"]
    out = []

    def add(*a, **k):
        k.pop("coll", None)
        out.append(put(*a, coll=c, **k))

    # ------------------------------------------------------------- LIVING
    add(F.rug, "living_rug", 5.10, 4.20, 0, w=3.90, d=2.95, mat="rug_wool")
    add(F.tv_unit, "living_tv_unit", 5.35, 6.14, 0, w=1.95)
    add(F.sofa, "living_sofa", 5.10, 2.90, 180, w=2.55, d=0.98, mat="linen_sand")
    add(F.coffee_table, "living_coffee_table", 5.10, 4.35, 0, w=1.38, d=0.76)
    add(F.armchair, "living_armchair_a", 3.28, 4.55, 90, mat="boucle_cream")
    add(F.armchair, "living_armchair_b", 6.72, 4.55, -90, mat="boucle_cream")
    add(F.side_table, "living_side_table", 2.05, 3.15, 0, r=0.26, h=0.54)
    add(F.floor_lamp, "living_floor_lamp", 6.90, 5.95, 0, h=1.62)
    add(F.plant, "living_plant_a", 0.78, 1.25, 0, kind="fig", scale=1.05)
    add(F.plant, "living_plant_b", 1.05, 5.90, 0, kind="monstera", scale=0.95)
    add(F.armchair, "living_reading_chair", 1.35, 3.55, 90, mat="velvet_olive")
    add(F.art, "living_art_a", 4.05, 6.40, 0, w=1.10, h=1.40, style=1, z=1.58)
    add(F.books, "living_books", 4.90, 4.29, 0, count=4, z=0.401)
    add(F.bowl, "living_bowl", 5.45, 4.44, 0, r=0.15, h=0.07, z=0.401)
    add(F.vase, "living_vase", 2.05, 3.15, 0, h=0.28, r=0.08, mat="terracotta",
        stems=3, z=0.54)

    # ------------------------------------------------------------- DINING
    add(F.rug, "dining_rug", 8.90, 3.30, 0, w=3.20, d=2.60, mat="rug_ochre")
    add(F.dining_table, "dining_table", 8.90, 3.30, 0, w=2.30, d=1.02)
    for i, (dx, dy, r) in enumerate([(-0.70, -0.86, 180), (0.70, -0.86, 180),
                                     (-0.70, 0.86, 0), (0.70, 0.86, 0),
                                     (-1.45, 0.0, -90), (1.45, 0.0, 90)]):
        add(F.dining_chair, f"dining_chair_{i}", 8.90 + dx, 3.30 + dy, r)
    add(F.pendant, "dining_pendant", 8.90, 3.30, 0, r=0.19, drop=1.40, shade_h=0.30)
    add(F.sideboard, "dining_sideboard", 9.55, 6.22, 0, w=1.90, d=0.44, h=0.74)
    add(F.art, "dining_art", 9.55, 6.42, 0, w=1.25, h=0.85, style=3, z=1.62)
    add(F.vase, "dining_vase", 9.00, 6.22, 0, h=0.36, r=0.09, mat="ceramic", z=0.74)
    add(F.plant, "dining_plant", 10.35, 0.80, 0, kind="monstera", scale=0.95)

    # ------------------------------------------------------------ KITCHEN
    add(F.base_run, "kitchen_run_east", 14.79, 3.10, -90, length=3.90, depth=0.64,
        worktop="marble", splash_h=0.52, hob=True)
    add(F.base_run, "kitchen_run_south", 13.85, 0.63, 180, length=2.30, depth=0.64,
        worktop="marble", sink=True, doors=4, splash_h=0.52)
    add(F.tall_unit, "kitchen_fridge", 14.79, 5.98, -90, w=0.92, h=2.20, d=0.66,
        mat="oak_veneer", fridge=True)
    add(F.range_hood, "kitchen_hood", 14.86, 3.10, -90, w=0.92, z=1.62)
    add(F.wall_cabinets, "kitchen_wall_units", 14.96, 4.42, -90, length=1.15, h=0.72,
        z=1.50, depth=0.36)
    add(F.kitchen_island, "kitchen_island", 12.55, 3.45, 0, w=2.85, d=1.08, h=0.92,
        overhang=0.32)
    add(F.bar_stool, "kitchen_stool_a", 11.95, 2.62, 180, h=0.66)
    add(F.bar_stool, "kitchen_stool_b", 12.75, 2.62, 180, h=0.66)
    add(F.bar_stool, "kitchen_stool_c", 13.55, 2.62, 180, h=0.66)
    for i, x in enumerate((11.80, 12.55, 13.30)):
        add(F.pendant, f"kitchen_pendant_{i}", x, 3.45, 0, r=0.115, drop=1.48,
            shade_h=0.21)
    add(F.bowl, "kitchen_bowl", 12.10, 3.45, 0, r=0.19, h=0.08, mat="walnut",
        z=0.945)
    add(F.plant, "kitchen_plant", 10.95, 6.10, 0, kind="snake", scale=0.85)

    # ------------------------------------------------------------- UTILITY
    add(F.washer, "utility_washer", 16.05, 2.85, 0)
    add(F.washer, "utility_dryer", 16.70, 2.85, 0, dryer=True)
    add(F.shelving_unit, "utility_shelving", 18.30, 2.40, -90, w=1.10, h=1.60, d=0.34,
        coll=c)
    add(F.base_run, "utility_bench", 17.60, 0.62, 180, length=1.25, depth=0.60,
        worktop="microcement", doors=2)
    add(F.vase, "utility_vase", 17.50, 0.62, 0, h=0.24, r=0.07, z=0.945)

    # --------------------------------------------------------------- FOYER
    add(F.console, "foyer_console", 18.34, 3.98, -90, w=0.95, d=0.34, h=0.80)
    add(F.mirror, "foyer_mirror", 18.52, 3.98, -90, w=0.85, h=1.05, z=1.55)
    add(F.plant, "foyer_plant", 16.35, 4.20, 0, kind="fig", scale=0.90)
    add(F.bowl, "foyer_bowl", 18.34, 3.98, 0, r=0.13, h=0.06, mat="brass", z=0.80)
    add(F.vase, "foyer_vase", 18.34, 3.72, 0, h=0.30, r=0.075, stems=4, z=0.80)

    # ------------------------------------------------------------ CORRIDOR
    add(F.rug, "corridor_runner_a", 5.20, 7.20, 0, w=3.40, d=0.90, mat="rug_ochre")
    add(F.rug, "corridor_runner_b", 12.60, 7.20, 0, w=3.40, d=0.90, mat="rug_ochre")
    for i, x in enumerate((4.30, 5.45, 6.60)):
        add(F.art, f"corridor_art_{i}", x, 6.66, 180, w=0.62, h=0.82, style=1 + i % 3,
            z=1.60)
    add(F.plant, "corridor_plant", 3.05, 7.55, 0, kind="snake", scale=0.7)
    for i, x in enumerate((8.10, 9.55, 13.60, 14.80)):
        add(F.art, f"corridor_art_b{i}", x, 6.66, 180, w=0.52, h=0.70, style=1 + i % 4,
            z=1.62)
    add(F.console, "corridor_console", 10.10, 7.56, 0, w=1.05, d=0.30, h=0.78)
    add(F.bowl, "corridor_bowl", 10.10, 7.56, 0, r=0.13, h=0.06, mat="brass", z=0.78)
    add(F.plant, "corridor_plant_b", 15.30, 7.58, 0, kind="snake", scale=0.65)

    # ------------------------------------------------------------- MASTER
    zt = 0.0
    add(F.rug, "master_rug", 2.95, 10.05, 0, w=3.30, d=2.90, mat="rug_wool")
    add(F.bed, "master_bed", 1.60, 10.05, 90, w=1.92, l=2.12, mat="linen_sand",
        frame="walnut", head="boucle_cream")
    add(F.nightstand, "master_nightstand_a", 0.78, 8.68, 90)
    add(F.nightstand, "master_nightstand_b", 0.78, 11.42, 90)
    add(F.table_lamp, "master_lamp_a", 0.80, 8.68, 0, h=0.44, z=0.52)
    add(F.table_lamp, "master_lamp_b", 0.80, 11.42, 0, h=0.44, z=0.52)
    add(F.armchair, "master_armchair", 4.55, 11.35, 180, mat="velvet_olive")
    add(F.side_table, "master_side_table", 5.02, 10.15, 0, r=0.22, h=0.50)
    add(F.art, "master_art", 5.28, 10.05, -90, w=0.95, h=1.25, style=2, z=1.55)
    add(F.bed_bench, "master_bench", 3.15, 10.05, 90, w=1.45, d=0.42, h=0.44,
        mat="velvet_olive")
    add(F.curtain, "master_curtain_a", 1.10, 12.06, 0, w=1.25, h=2.86, mat="curtain_sheer")
    add(F.curtain, "master_curtain_b", 4.50, 12.06, 0, w=1.25, h=2.86, mat="curtain_sheer")
    add(F.art, "master_art_head", 0.36, 10.05, 90, w=1.80, h=0.72, style=4, z=1.66)
    add(F.plant, "master_plant", 4.85, 8.35, 0, kind="monstera", scale=0.85)
    

    # --------------------------------------------------------------- ROBE
    add(F.wardrobe, "robe_wardrobe", 7.18, 8.72, -90, w=1.48, h=2.35, d=0.62)
    add(F.shelving_unit, "robe_shelving", 5.68, 8.35, 90, w=0.90, h=1.90, d=0.34,
        coll=c)
    add(F.rug, "robe_rug", 6.40, 8.70, 0, w=1.30, d=1.10, mat="rug_wool")

    # ------------------------------------------------------------ ENSUITE
    add(F.vanity, "ensuite_vanity", 7.22, 10.95, -90, w=1.18, d=0.50, h=0.86)
    add(F.mirror, "ensuite_mirror", 7.44, 10.95, -90, w=1.05, h=0.95, z=1.52)
    add(F.shower, "ensuite_shower", 6.05, 11.55, 0, w=1.05, d=1.18, h=2.10)
    add(F.toilet, "ensuite_toilet", 7.16, 10.05, -90)
    add(F.towel_rail, "ensuite_towel", 6.60, 9.72, 0, w=0.62, z=1.25)

    # --------------------------------------------------------------- BED 2
    add(F.rug, "bed2_rug", 9.75, 9.60, 0, w=2.80, d=2.40, mat="rug_wool")
    add(F.bed, "bed2_bed", 8.78, 10.05, 90, w=1.62, l=2.02, mat="linen_graphite",
        frame="oak_veneer", head="linen_graphite")
    add(F.nightstand, "bed2_nightstand", 7.98, 8.90, 90)
    add(F.table_lamp, "bed2_lamp", 8.00, 8.90, 0, h=0.42, z=0.52)
    add(F.wardrobe, "bed2_wardrobe", 11.20, 9.30, -90, w=1.55, h=2.30, d=0.60)
    add(F.desk, "bed2_desk", 11.18, 11.28, -90, w=1.36, d=0.62, h=0.74)
    add(F.office_chair, "bed2_chair", 10.30, 11.28, 90)
    add(F.art, "bed2_art", 10.70, 8.02, 180, w=0.85, h=1.05, style=3, z=1.62)
    add(F.plant, "bed2_plant", 8.15, 11.78, 0, kind="fig", scale=0.85)

    # ------------------------------------------------------------- LAUNDRY
    add(F.washer, "laundry_washer", 13.18, 8.32, -90)
    add(F.washer, "laundry_dryer", 13.18, 9.02, -90, dryer=True)
    add(F.shelving_unit, "laundry_shelf", 11.92, 8.70, 90, w=1.20, h=1.70, d=0.32,
        coll=c)


    # --------------------------------------------------------------- BATH 2
    add(F.vanity, "bath2_vanity", 13.22, 10.42, -90, w=1.10, d=0.48, h=0.86)
    add(F.mirror, "bath2_mirror", 13.44, 10.42, -90, w=0.95, h=0.90, z=1.50)
    add(F.shower, "bath2_shower", 12.20, 11.55, 0, w=1.00, d=1.12, h=2.10)
    add(F.toilet, "bath2_toilet", 13.20, 11.62, -90)
    add(F.towel_rail, "bath2_towel", 12.40, 9.74, 0, w=0.55, z=1.25)

    # --------------------------------------------------------------- BED 3
    add(F.rug, "bed3_rug", 15.10, 9.45, 0, w=2.50, d=2.10, mat="rug_ochre")
    add(F.bed, "bed3_bed", 15.10, 11.05, 180, w=1.42, l=1.98, mat="boucle_cream",
        frame="oak_veneer", head="boucle_cream")
    add(F.nightstand, "bed3_nightstand", 16.15, 11.55, -90)
    add(F.table_lamp, "bed3_lamp", 16.15, 11.55, 0, h=0.40, z=0.52)
    add(F.wardrobe, "bed3_wardrobe", 13.98, 10.55, 90, w=1.45, h=2.25, d=0.58)
    add(F.desk, "bed3_desk", 14.00, 8.70, 90, w=1.20, d=0.58, h=0.74)
    add(F.office_chair, "bed3_chair", 14.72, 8.70, -90)
    add(F.art, "bed3_art", 15.80, 8.03, 180, w=0.68, h=0.90, style=1, z=1.60)

    # --------------------------------------------------------------- STUDY
    add(F.desk, "study_desk", 18.14, 10.40, -90, w=1.45, d=0.66, h=0.75)
    add(F.office_chair, "study_chair", 17.48, 10.40, 90)
    add(F.bookshelf, "study_bookshelf", 16.82, 9.30, 90, w=1.10, h=2.00, d=0.32)
    add(F.floor_lamp, "study_floor_lamp", 17.05, 11.85, 0, h=1.55)
    add(F.art, "study_art", 17.90, 8.06, 180, w=0.90, h=1.10, style=2, z=1.60)
    add(F.plant, "study_plant", 18.20, 8.40, 0, kind="snake", scale=0.8)
    add(F.books, "study_books", 18.14, 10.02, 0, count=3, z=0.75)
    add(F.bowl, "study_bowl", 18.14, 10.72, 0, r=0.10, h=0.05, z=0.75)

    return out
