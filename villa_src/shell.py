"""Villa shell: floorplan, walls, glazing, doors, floors, ceiling, exterior.

Plan (metres, x=east, y=north, z=up):
    19.0 x 12.5 m single storey, flat roof, 3.0 m ceilings.
    South band : living (open to terrace), dining, kitchen
    East       : foyer + entry, utility
    Middle     : corridor
    North band : master suite (bed/robe/ensuite), bedroom 2, laundry+family bath,
                 bedroom 3, study
"""
import math

from . import kit, mats

H = 3.00           # ceiling height
EXT = 0.30         # exterior wall thickness
INT = 0.12         # interior wall thickness
W, D = 19.0, 12.5
IX0, IY0, IX1, IY1 = EXT, EXT, W - EXT, D - EXT

# room floor rectangles: name -> (x0, y0, x1, y1, material)
ROOMS = {
    "living":   (IX0, IY0, 7.10, 6.55, "oak_floor"),
    "dining":   (7.10, IY0, 10.70, 6.55, "oak_floor"),
    "kitchen":  (10.70, IY0, 15.20, 6.55, "limestone_tile"),
    "utility":  (15.20, IY0, 18.70, 3.40, "limestone_tile"),
    "foyer":    (15.20, 3.40, 18.70, 6.55, "limestone_tile"),
    "corridor": (IX0, 6.55, 18.70, 7.85, "oak_floor"),
    "master":   (IX0, 7.85, 5.40, 12.20, "oak_floor"),
    "robe":     (5.40, 7.85, 7.60, 9.60, "oak_floor"),
    "ensuite":  (5.40, 9.60, 7.60, 12.20, "bath_tile"),
    "bed2":     (7.60, 7.85, 11.60, 12.20, "oak_floor"),
    "laundry":  (11.60, 7.85, 13.60, 9.60, "limestone_tile"),
    "bath2":    (11.60, 9.60, 13.60, 12.20, "bath_tile"),
    "bed3":     (13.60, 7.85, 16.60, 12.20, "oak_floor"),
    "study":    (16.60, 7.85, 18.70, 12.20, "oak_floor"),
}


def opener(a, b, sill=0.0, head=2.10, kind="door"):
    return {"a": a, "b": b, "sill": sill, "head": head, "kind": kind}


def wall(name, x0, y0, x1, y1, axis, openings=(), mat="plaster_warm", height=H,
         coll=None, bevel=0.0):
    """Build a wall footprint with rectangular openings along `axis` ('x' or 'y')."""
    parts = []
    ops = sorted(openings, key=lambda o: o["a"])
    lo, hi = (x0, x1) if axis == "x" else (y0, y1)
    cur = lo

    def seg(a, b, zb, zt, tag):
        if b - a < 1e-4 or zt - zb < 1e-4:
            return
        if axis == "x":
            parts.append(kit.box(f"{name}_{tag}_{a:.2f}", (b - a, y1 - y0, zt - zb),
                                 ((a + b) / 2, (y0 + y1) / 2, (zb + zt) / 2),
                                 mat=mat, bevel=bevel, coll=coll))
        else:
            parts.append(kit.box(f"{name}_{tag}_{a:.2f}", (x1 - x0, b - a, zt - zb),
                                 ((x0 + x1) / 2, (a + b) / 2, (zb + zt) / 2),
                                 mat=mat, bevel=bevel, coll=coll))

    for o in ops:
        if o["a"] > cur:
            seg(cur, o["a"], 0.0, height, "p")
        if o["sill"] > 0:
            seg(o["a"], o["b"], 0.0, o["sill"], "sill")
        if o["head"] < height:
            seg(o["a"], o["b"], o["head"], height, "lintel")
        cur = o["b"]
    if cur < hi:
        seg(cur, hi, 0.0, height, "p")
    return parts


def glass_pane(name, x0, y0, x1, y1, z0, z1, mat="glass", coll=None):
    if x1 - x0 > y1 - y0:
        return kit.box(name, (x1 - x0, 0.012, z1 - z0),
                       ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), mat=mat, coll=coll)
    return kit.box(name, (0.012, y1 - y0, z1 - z0),
                   ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), mat=mat, coll=coll)


def window(name, axis, a0, a1, wall0, wall1, z0, z1, panes=3, mat="glass",
           frame="black_steel", coll=None, rail=False):
    """Frame + glazing filling a wall opening. a0..a1 along `axis`, wall0..wall1 the
    wall thickness span on the other axis."""
    out = []
    w = 0.055
    c = (wall0 + wall1) / 2
    fw = 0.075
    if axis == "x":
        def bar(x0, x1, z0_, z1_):
            out.append(kit.box(f"{name}_f", (x1 - x0, fw, z1_ - z0_),
                               ((x0 + x1) / 2, c, (z0_ + z1_) / 2), mat=frame, coll=coll))
        out.append(glass_pane(f"{name}_g", a0 + w, wall1 - 0.09, a1 - w, wall1 - 0.07, z0 + w, z1 - w,
                              mat, coll))
    else:
        def bar(x0, x1, z0_, z1_):
            out.append(kit.box(f"{name}_f", (fw, x1 - x0, z1_ - z0_),
                               (c, (x0 + x1) / 2, (z0_ + z1_) / 2), mat=frame, coll=coll))
        out.append(glass_pane(f"{name}_g", wall1 - 0.09, a0 + w, wall1 - 0.07, a1 - w, z0 + w, z1 - w,
                              mat, coll))
    lo, hi = a0 + w / 2, a1 - w / 2
    bar(lo, hi, z0, z0 + w)          # bottom
    bar(lo, hi, z1 - w, z1)          # top
    n = max(1, panes)
    for i in range(n + 1):
        p = lo + (hi - lo) * i / n
        bar(p - w / 2, p + w / 2, z0, z1)
    if rail and z1 - z0 > 1.6:
        bar(lo, hi, z1 - 1.05, z1 - 1.05 + w * 0.7)
    return out


def door_leaf(name, axis, a0, a1, wall_c, z1=2.10, mat="oak_veneer", coll=None,
              swing=95.0):
    """Open door leaf hinged at a0. `swing` is degrees about Z from the closed pose."""
    from mathutils import Matrix
    w = a1 - a0 - 0.012
    t = 0.045
    leaf = kit.box(name, (w, t, z1 - 0.012), (0, 0, 0), mat=mat, bevel=0.004, coll=coll)
    leaf.data.transform(Matrix.Translation((w / 2, 0, (z1 - 0.012) / 2)))
    leaf.data.update()
    if axis == "x":
        leaf.location = (a0, wall_c, 0.0)
        base = 0.0
    else:
        leaf.location = (wall_c, a0, 0.0)
        base = math.pi / 2
    leaf.rotation_euler = (0, 0, base + math.radians(swing))
    return leaf


def build_shell(colls):
    """Walls, glazing, doors, floor slabs, ceiling, roof, exterior."""
    ext = colls["shell"]
    glass = colls["glazing"]
    H_ = H

    # ---------------- exterior walls, with openings
    # south (y 0..0.30) : big glazing to the terrace
    kit_wall = []
    kit_wall += wall("S", IX0 - EXT, 0.0, 12.60, EXT, "x",
                     [opener(0.60, 6.30, 0.05, 2.88, "glass"),
                      opener(7.00, 12.10, 0.05, 2.88, "glass")],
                     "plaster_warm", H_, ext)
    kit_wall += wall("S2", 12.60, 0.0, IX1 + EXT, EXT, "x",
                     [opener(13.10, 15.60, 1.05, 2.40, "glass")], "plaster_warm", H_, ext)
    # north
    kit_wall += wall("N", IX0 - EXT, IY1, IX1 + EXT, D, "x",
                     [opener(1.40, 4.20, 0.45, 2.40, "glass"),
                      opener(8.40, 11.00, 0.45, 2.40, "glass"),
                      opener(12.15, 13.05, 1.95, 2.55, "glass"),
                      opener(14.20, 16.20, 0.45, 2.40, "glass"),
                      opener(17.10, 18.20, 0.45, 2.40, "glass")],
                     "plaster_warm", H_, ext)
    # west
    kit_wall += wall("W", 0.0, IY0 - EXT, EXT, IY1 + EXT, "y",
                     [opener(1.30, 4.40, 0.30, 2.80, "glass")], "plaster_warm", H_, ext)
    # east
    kit_wall += wall("E", IX1, IY0 - EXT, IX1 + EXT, IY1 + EXT, "y",
                     [opener(4.45, 5.95, 0.0, 2.35, "door"),
                      opener(8.60, 10.60, 1.90, 2.55, "glass")],
                     "plaster_warm", H_, ext)

    # ---------------- interior walls
    iw = [
        # y=6.55 spine (living/kitchen | corridor)
        (IX0, 6.49, IX1, 6.61, "x",
         [opener(1.60, 3.40, 0.0, 2.40, "open"),
          opener(11.15, 12.75, 0.0, 2.40, "open"),
          opener(15.60, 17.30, 0.0, 2.40, "open")]),
        # y=7.85 (corridor | bedrooms)
        (IX0, 7.79, IX1, 7.91, "x",
         [opener(4.15, 5.05, 0.0, 2.10, "door"),
          opener(8.05, 8.95, 0.0, 2.10, "door"),
          opener(11.85, 12.60, 0.0, 2.10, "door"),
          opener(14.10, 15.00, 0.0, 2.10, "door"),
          opener(17.05, 17.95, 0.0, 2.10, "door")]),
        # x=5.40 master | robe/ensuite
        (5.34, 7.91, 5.46, 12.20, "y", [opener(8.20, 9.10, 0.0, 2.10, "door")]),
        # x=7.60 robe/ensuite | bed2
        (7.54, 7.91, 7.66, 12.20, "y", []),
        # x=11.60 bed2 | laundry/bath2
        (11.54, 7.91, 11.66, 12.20, "y", []),
        # x=13.60 laundry/bath2 | bed3
        (13.54, 7.91, 13.66, 12.20, "y", []),
        # x=16.60 bed3 | study
        (16.54, 7.91, 16.66, 12.20, "y", []),
        # y=9.60 robe|ensuite and laundry|bath2
        (5.46, 9.54, 7.54, 9.66, "x", [opener(6.10, 6.95, 0.0, 2.10, "door")]),
        (11.66, 9.54, 13.54, 9.66, "x", [opener(12.20, 13.05, 0.0, 2.10, "door")]),
        # x=15.20 kitchen | utility/foyer
        (15.14, IY0, 15.26, 6.49, "y", [opener(4.30, 5.20, 0.0, 2.10, "door")]),
        # y=3.40 utility | foyer
        (15.26, 3.34, 18.70, 3.46, "x", [opener(16.30, 17.20, 0.0, 2.10, "door")]),
    ]
    for i, (x0, y0, x1, y1, ax, ops) in enumerate(iw):
        kit_wall += wall(f"IW{i}", x0, y0, x1, y1, ax, ops, "plaster_white", H_, ext)

    # ---------------- glazing + doors in the openings
    gl = []
    gl += window("glassS1", "x", 0.60, 6.30, 0.02, EXT, 0.05, 2.88, panes=4, rail=True,
                 coll=glass)
    gl += window("glassS2", "x", 7.00, 12.10, 0.02, EXT, 0.05, 2.88, panes=4, rail=True,
                 coll=glass)
    gl += window("glassS3", "x", 13.10, 15.60, 0.02, EXT, 1.05, 2.40, panes=2, coll=glass)
    gl += window("glassN1", "x", 1.40, 4.20, IY1, D - 0.02, 0.45, 2.40, panes=3, coll=glass)
    gl += window("glassN2", "x", 8.40, 11.00, IY1, D - 0.02, 0.45, 2.40, panes=3, coll=glass)
    gl += window("glassN3", "x", 12.15, 13.05, IY1, D - 0.02, 1.95, 2.55, panes=1, coll=glass)
    gl += window("glassN4", "x", 14.20, 16.20, IY1, D - 0.02, 0.45, 2.40, panes=2, coll=glass)
    gl += window("glassN5", "x", 17.10, 18.20, IY1, D - 0.02, 0.45, 2.40, panes=1, coll=glass)
    gl += window("glassW1", "y", 1.30, 4.40, EXT - 0.02, 0.0, 0.30, 2.80, panes=3, coll=glass)
    gl += window("glassE1", "y", 8.60, 10.60, IX1, IX1 + EXT - 0.02, 1.90, 2.55, panes=2,
                 coll=glass)

    doors = []
    D_ = colls["doors"]
    doors.append(door_leaf("door_front", "y", 4.45, 5.95, IX1 + 0.15, 2.35, "walnut",
                           D_, swing=26))
    doors.append(door_leaf("door_master", "x", 4.15, 5.05, 7.85, 2.10, coll=D_, swing=100))
    doors.append(door_leaf("door_bed2", "x", 8.05, 8.95, 7.85, 2.10, coll=D_, swing=96))
    doors.append(door_leaf("door_laundry", "x", 11.85, 12.60, 7.85, 2.10, coll=D_, swing=98))
    doors.append(door_leaf("door_bed3", "x", 14.10, 15.00, 7.85, 2.10, coll=D_, swing=100))
    doors.append(door_leaf("door_study", "x", 17.05, 17.95, 7.85, 2.10, coll=D_, swing=95))
    doors.append(door_leaf("door_robe", "y", 8.20, 9.10, 5.40, 2.10, coll=D_, swing=-92))
    doors.append(door_leaf("door_ensuite", "x", 6.10, 6.95, 9.60, 2.10, coll=D_, swing=95))
    doors.append(door_leaf("door_bath2", "x", 12.20, 13.05, 9.60, 2.10, coll=D_, swing=95))
    doors.append(door_leaf("door_utility", "y", 4.30, 5.20, 15.20, 2.10, coll=D_, swing=90))

    # ---------------- floor slabs per room
    floors = []
    for name, (x0, y0, x1, y1, mat) in ROOMS.items():
        if name in ("utility", "foyer", "laundry", "ensuite", "bath2"):
            z0, z1 = -0.10, 0.012
        else:
            z0, z1 = -0.10, 0.0
        floors.append(kit.box(f"floor_{name}", (x1 - x0, y1 - y0, z1 - z0),
                              ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                              mat=mat, coll=colls["floors"]))
    # subfloor for everything (so no gaps between room slabs)
    floors.append(kit.box("subfloor", (W - 2 * EXT + 0.1, D - 2 * EXT + 0.1, 0.24),
                          (W / 2, D / 2, -0.24), mat="microcement", coll=colls["floors"]))

    # ---------------- ceiling + roof
    ceil = kit.box("ceiling", (IX1 - IX0 + 0.2, IY1 - IY0 + 0.2, 0.06),
                   ((IX0 + IX1) / 2, (IY0 + IY1) / 2, H_ + 0.03), mat="plaster_white",
                   coll=colls["ceiling"])
    roof = kit.box("roof_slab", (W + 1.8, D + 1.2, 0.28),
                   (W / 2 + 0.5, D / 2 - 0.55, H_ + 0.20), mat="microcement",
                   coll=colls["ceiling"])
    fascia = []
    fascia.append(kit.box("fascia_s", (W + 1.8, 0.06, 0.34), (W / 2 + 0.5, -0.62, H_ + 0.19),
                          mat="black_steel", coll=colls["ceiling"]))
    fascia.append(kit.box("fascia_n", (W + 1.8, 0.06, 0.34), (W / 2 + 0.5, D + 0.05, H_ + 0.19),
                          mat="black_steel", coll=colls["ceiling"]))
    for sx in (-0.4, W + 1.4):
        fascia.append(kit.box("fascia_e", (0.06, D + 0.7, 0.34), (sx, D / 2 - 0.55, H_ + 0.19),
                              mat="black_steel", coll=colls["ceiling"]))

    return kit_wall + gl + floors + [ceil, roof] + fascia


def build_site(colls):
    """Terrace, lawn, pool, planting -- what you see through the glazing."""
    ex = colls["site"]
    out = []
    from . import kit as K
    # terrace slab running the length of the south glazing
    out.append(K.box("terrace", (13.6, 4.2, 0.16), (6.6, -2.1, -0.02), mat="limestone_tile",
                     coll=ex))
    # lawn
    out.append(K.box("lawn", (150.0, 74.0, 0.10), (9.5, -38.0, -0.14), mat="grass",
                     coll=ex))
    out.append(K.box("lawn_n", (150.0, 60.0, 0.10), (9.5, 42.0, -0.14), mat="grass",
                     coll=ex))
    out.append(K.box("lawn_w", (60.0, 150.0, 0.10), (-35.0, 0.0, -0.14), mat="grass",
                     coll=ex))
    out.append(K.box("lawn_e", (60.0, 150.0, 0.10), (55.0, 0.0, -0.14), mat="grass",
                     coll=ex))
    out.append(K.box("drive", (7.0, 6.5, 0.12), (22.5, 5.2, -0.10), mat="microcement",
                     coll=ex))
    # pool
    out.append(K.box("pool_shell", (5.4, 4.0, 0.30), (15.9, -2.4, -0.10), mat="pool_tile",
                     coll=ex))
    out.append(K.box("pool_water", (5.1, 3.7, 0.06), (15.9, -2.4, 0.03), mat="water",
                     coll=ex))
    return out


def build_all():
    colls = {
        "shell": kit.collection("Shell"),
        "glazing": kit.collection("Glazing"),
        "doors": kit.collection("Doors"),
        "floors": kit.collection("Floors"),
        "ceiling": kit.collection("Ceiling"),
        "site": kit.collection("Site"),
    }
    build_shell(colls)
    build_site(colls)
    return colls
