"""Card-based vegetation: real leaf silhouettes instead of green spheres.

The v1 garden was built from UV spheres with a green texture. In a close render that
reads as a placeholder: no silhouette detail, no light coming through the canopy, no
variation between species.

This module builds plants the way a real-time/games artist would:

* **leaf cards** - hundreds of small alpha-cutout quads with a photographic-style leaf
  silhouette (see `tex_gen2.leaf_card`), scattered over an ellipsoid shell;
* a **dark inner core** so the canopy occludes the sky instead of looking transparent;
* **species that actually differ**: broadleaf, olive, cypress, palm, ornamental grass,
  clipped hedge and shrub masses;
* procedural but *stable* randomness (seeded), so a rebuild reproduces the same garden.

Everything is joined per plant into one object, so the scene stays navigable and the
export stays small.

    python villa_src/build_v2.py            # full rebuild (see that file)
"""
import math
import random

import bmesh
import bpy
from mathutils import Vector

from . import kit as K
from . import mats

UP = Vector((0.0, 0.0, 1.0))
CARD_SIZE = (0.55, 1.0)   # metres; tuned by rendering, not by guessing


# ------------------------------------------------------------------ card builder
def _frame(normal, roll):
    """Orthonormal card frame: (right, up) perpendicular to the facing normal."""
    n = Vector(normal).normalized()
    hint = UP if abs(n.z) < 0.94 else Vector((0.0, 1.0, 0.0))
    r = n.cross(hint)
    if r.length < 1e-6:
        r = n.cross(Vector((1.0, 0.0, 0.0)))
    r.normalize()
    u = r.cross(n).normalized()
    c, s = math.cos(roll), math.sin(roll)
    return r * c + u * s, u * c - r * s


def card_cloud(name, points, mat, coll=None, seed=0, uv_size=None):
    """Build one mesh from (centre, normal, width, length, roll) cards.

    One object per plant: hundreds of cards, one draw call, one material.
    """
    rnd = random.Random(seed)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    for (c, n, w, l) in points:
        r, u = _frame(n, rnd.uniform(0, math.pi * 2))
        # slight per-card bend: push the tip along the normal so canopies are not flat
        bend = rnd.uniform(0.04, 0.16) * l
        hw, hl = w * 0.5, l * 0.5
        c = Vector(c)
        v0 = bm.verts.new(c - r * hw - u * hl)
        v1 = bm.verts.new(c + r * hw - u * hl)
        v2 = bm.verts.new(c + r * hw + u * hl + Vector(n) * bend)
        v3 = bm.verts.new(c - r * hw + u * hl + Vector(n) * bend)
        try:
            f = bm.faces.new((v0, v1, v2, v3))
        except ValueError:
            continue
        for loop, (uu, vv) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[uv].uv = (uu, vv)
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    me.materials.append(mats.build(mat))
    return ob


def _clumps(rnd, n_clumps, rx, ry, rz, center, clump_r, cards_per_clump,
            size=(0.10, 0.20), inner=0.0, centers_only=False, push=1.0):
    """Scatter small leaf **clumps** over an ellipsoid.

    A single shell of cards reads as a powder puff, and a smooth sphere inside it reads
    as a green golf ball. Real canopies are clumps of foliage separated by gaps of sky
    and shadow - so canopies are built from clumps only, with a second, denser, dark
    clump cloud inside to occlude the light.
    """
    cx, cy, cz = center
    pts = []
    out_centres = []
    for _ in range(n_clumps):
        while True:
            v = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1)))
            if v.length > 1e-6:
                v.normalize()
                break
        rr = inner + (1.0 - inner) * (rnd.random() ** 0.45)
        c = Vector((cx + v.x * rx * rr, cy + v.y * ry * rr, cz + v.z * rz * rr))
        cr = clump_r * rnd.uniform(0.6, 1.35)
        nrm_c = Vector((v.x / max(rx, 1e-3), v.y / max(ry, 1e-3), v.z / max(rz, 1e-3)))
        out_centres.append((c, cr, nrm_c))
        if centers_only:
            continue
        for _ in range(cards_per_clump):
            d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
            p = c + d * cr * (0.55 + 0.45 * rnd.random())
            nrm = (nrm_c * 0.5 + d * 0.5).normalized()
            w = rnd.uniform(*size) * push
            pts.append((p, nrm, w, w * rnd.uniform(1.0, 1.45)))
    return out_centres if centers_only else pts


def _cloud(rnd, centres, cards_per, size, jitter=1.0):
    """Turn clump centres into card poses."""
    pts = []
    for (c, cr, nrm_c) in centres:
        for _ in range(cards_per):
            d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
            p = c + d * cr * (0.5 + 0.5 * rnd.random()) * jitter
            nrm = (nrm_c * 0.5 + d * 0.5).normalized()
            w = rnd.uniform(*size)
            pts.append((p, nrm, w, w * rnd.uniform(1.0, 1.45)))
    return pts


def _shell_points(rnd, n, rx, ry, rz, center, leaf, size=(0.30, 0.55), inner=0.55,
                  up_bias=0.0, flat=0.0):
    """Scatter card poses over an ellipsoid shell (and a few inside, for depth)."""
    cx, cy, cz = center
    out = []
    for i in range(n):
        # cosine-ish distribution over the sphere, biased to the outside
        while True:
            v = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1)))
            if v.length > 1e-6:
                v.normalize()
                break
        rr = inner + (1.0 - inner) * math.sqrt(rnd.random())
        p = Vector((cx + v.x * rx * rr, cy + v.y * ry * rr,
                    cz + v.z * rz * rr + up_bias * rz * (1 - rr)))
        nrm = Vector((v.x / max(rx, 1e-3), v.y / max(ry, 1e-3), v.z / max(rz, 1e-3)))
        nrm = (nrm * (1.0 - flat) + UP * flat).normalized()
        w = rnd.uniform(*size) * leaf
        out.append((p, nrm, w, w * rnd.uniform(0.85, 1.25)))
    return out


# ------------------------------------------------------------------- species
def broadleaf(seed=1, h=8.0, crown=3.0, coll=None, leaf_mat="spray_a", cards=7000,
              trunk_mat="bark"):
    """Trunk + forked limbs + a card canopy with a dark occlusion core.

    Card *size* is the whole game: leaves much above ~0.25 m read as a shrub made of
    paddles, and below ~0.08 m the silhouette is fine but the cost explodes. Small
    leaves + many of them + several overlapping canopy lobes is what reads as a tree.
    """
    rnd = random.Random(seed)
    parts = []
    parts.append(K.cyl(f"t{seed}_trunk", 0.055 * crown + 0.05, h * 0.58,
                       (0, 0, h * 0.29), mat=trunk_mat, seg=14,
                       r2=0.035 * crown + 0.03, coll=coll))
    limb_ends = []
    n_limb = rnd.randint(5, 7)
    for i in range(n_limb):
        a = 2 * math.pi * i / n_limb + rnd.uniform(-0.35, 0.35)
        z0 = h * rnd.uniform(0.38, 0.60)
        reach = crown * rnd.uniform(0.30, 0.58)
        end = (reach * math.cos(a), reach * math.sin(a), z0 + crown * rnd.uniform(0.25, 0.50))
        parts.append(K.rod(f"t{seed}_limb{i}", (0, 0, z0), end, 0.030 * crown, trunk_mat,
                           seg=8, coll=coll))
        # secondary limbs
        for j in range(2):
            a2 = a + rnd.uniform(-0.7, 0.7)
            reach2 = crown * rnd.uniform(0.45, 0.80)
            end2 = (reach2 * math.cos(a2), reach2 * math.sin(a2),
                    end[2] + crown * rnd.uniform(0.05, 0.30))
            parts.append(K.rod(f"t{seed}_limb{i}{j}", end, end2, 0.016 * crown, trunk_mat,
                               seg=6, coll=coll))
            limb_ends.append(end2)
    # canopy lobes at several heights and radii: a crown is never one sphere. Some
    # hang below the widest point, which is what makes the silhouette irregular.
    lobes = []
    for i in range(rnd.randint(12, 16)):
        a = rnd.uniform(0, 2 * math.pi)
        rr = crown * rnd.uniform(0.05, 0.80)
        cz = h * rnd.uniform(0.46, 0.80)
        lobes.append((rr * math.cos(a), rr * math.sin(a), cz,
                      crown * rnd.uniform(0.18, 0.36)))
    pts, shadow_pts = [], []
    per = max(8, cards // max(1, len(lobes))) // 5      # clumps per lobe
    for i, (x, y, z, r) in enumerate(lobes):
        # inner shadow cloud: dark cards, dense enough to block the sky
        inner_c = _clumps(rnd, max(4, per // 3), r * 0.45, r * 0.45, r * 0.40,
                          (x, y, z), clump_r=0.16 * (r / max(crown * 0.5, 0.2)),
                          cards_per_clump=0, centers_only=True, inner=0.0)
        inner_pts = _cloud(rnd, inner_c, 2, (0.16, 0.30), jitter=0.8)
        outer_c = _clumps(rnd, per, r * 1.05, r * 1.05, r * 0.92, (x, y, z),
                          clump_r=0.26 * (r / max(crown * 0.5, 0.2)),
                          cards_per_clump=0, centers_only=True, inner=0.0)
        outer_pts = _cloud(rnd, outer_c, 6, CARD_SIZE, jitter=1.0)
        shadow_pts += inner_pts
        pts += outer_pts
    parts.append(card_cloud(f"t{seed}_core", shadow_pts, "spray_dark", coll,
                            seed=seed * 3 + 5))
    parts.append(card_cloud(f"t{seed}_leaves", pts, leaf_mat, coll, seed=seed * 7 + 1))
    return K.join(parts, f"tree_{seed}")


def olive(seed=2, h=4.6, crown=2.4, coll=None):
    """Gnarly multi-stem olive: silvery narrow leaves, sparse open crown."""
    rnd = random.Random(seed)
    parts = []
    for i in range(3):
        a = rnd.uniform(0, 6.28)
        lean = crown * rnd.uniform(0.10, 0.28)
        top = (lean * math.cos(a), lean * math.sin(a), h * rnd.uniform(0.5, 0.72))
        parts.append(K.rod(f"o{seed}_stem{i}", (rnd.uniform(-.1, .1), rnd.uniform(-.1, .1), 0),
                           top, 0.075, "bark", seg=9, coll=coll))
    inner = _clumps(rnd, 60, crown * 0.55, crown * 0.55, crown * 0.42, (0, 0, h * 0.72),
                    clump_r=0.22, cards_per_clump=0, centers_only=True)
    parts.append(card_cloud(f"o{seed}_core", _cloud(rnd, inner, 3, (0.24, 0.44)),
                            "spray_dark", coll, seed=seed * 11))
    pts = _clumps(rnd, 220, crown, crown * 0.95, crown * 0.70, (0, 0, h * 0.74),
                  clump_r=0.24, cards_per_clump=4, size=(0.22, 0.38), inner=0.10)
    parts.append(card_cloud(f"o{seed}_leaves", pts, "spray_olive", coll, seed=seed * 13))
    return K.join(parts, f"olive_{seed}")


def cypress(seed=3, h=7.0, r=0.75, coll=None):
    """Italian cypress: a tall, tight, slightly irregular column. Very recognisable."""
    rnd = random.Random(seed)
    parts = []
    pts = []
    for i in range(260):
        t = rnd.random() ** 0.7
        z = h * (0.04 + 0.94 * t)
        taper = max(0.06, math.sin(math.pi * min(1.0, 0.12 + 0.9 * t)) ** 0.5)
        a = rnd.uniform(0, 6.28)
        rr = r * taper * (0.55 + 0.45 * rnd.random())
        c = Vector((rr * math.cos(a), rr * math.sin(a), z))
        nrm_c = Vector((math.cos(a), math.sin(a), 0.25))
        for _ in range(6):
            d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
            p = c + d * 0.20 * rnd.random()
            w = rnd.uniform(0.24, 0.42)
            pts.append((p, (nrm_c * 0.6 + d * 0.4).normalized(), w, w * 1.2))
    # inner column of dark cards so the column is solid at the top, hollow at the base
    shadow = []
    for i in range(300):
        t = rnd.random() ** 0.8
        z = h * (0.10 + 0.86 * t)
        taper = max(0.05, math.sin(math.pi * min(1.0, 0.10 + 0.90 * t)) ** 0.5)
        a = rnd.uniform(0, 6.28)
        rr = r * taper * 0.55 * rnd.random()
        w = rnd.uniform(0.18, 0.30)
        shadow.append((Vector((rr * math.cos(a), rr * math.sin(a), z)),
                       Vector((math.cos(a), math.sin(a), 0.2)), w, w * 1.2))
    parts.append(card_cloud(f"c{seed}_core", shadow, "spray_dark", coll, seed=seed * 2))
    parts.append(card_cloud(f"c{seed}_leaves", pts, "spray_b", coll, seed=seed * 5))
    return K.join(parts, f"cypress_{seed}")


def palm(seed=4, h=8.5, coll=None):
    """Palm: curved ringed trunk, arching fronds made of leaflets, a few dead fronds."""
    rnd = random.Random(seed)
    parts = []
    seg = 14
    # trunk: stacked tapered segments along a gentle curve
    for i in range(seg):
        t0, t1 = i / seg, (i + 1) / seg
        z0, z1 = h * 0.62 * t0, h * 0.62 * t1
        x0 = 0.55 * (t0 ** 2) * (h / 8.5)
        x1 = 0.55 * (t1 ** 2) * (h / 8.5)
        r0 = 0.17 - 0.06 * t0
        parts.append(K.rod(f"p{seed}_trunk{i}", (x0, 0, z0), (x1, 0, z1), r0,
                           "bark", seg=10, coll=coll))
        parts.append(K.cyl(f"p{seed}_ring{i}", r0 * 1.06, 0.05, (x1, 0, z1), mat="bark",
                           seg=10, coll=coll))
    top = Vector((0.55 * (h / 8.5), 0.0, h * 0.62))
    n_frond = 13
    pts = []
    for i in range(n_frond):
        a = 2 * math.pi * i / n_frond + rnd.uniform(-0.12, 0.12)
        dead = i >= n_frond - 3
        droop = rnd.uniform(0.55, 1.15) + (0.55 if dead else 0)
        L = rnd.uniform(2.0, 2.9) * (h / 8.5) * (0.72 if dead else 1.0)
        # rachis as a curve of points; leaflets as cards along it
        n_leaf = 26
        for j in range(n_leaf):
            u = (j + 1) / n_leaf
            rad = L * u
            zz = -droop * L * (u ** 1.7) + 0.35 * L * u
            p = top + Vector((rad * math.cos(a), rad * math.sin(a), zz))
            leaflet_len = 0.42 * L * (1.0 - u) ** 0.65 + 0.05
            for side in (-1, 1):
                side_a = a + side * math.pi / 2.0
                perp = Vector((math.cos(side_a), math.sin(side_a), 0.35))
                nrm = Vector((math.cos(a + side * 0.6), math.sin(a + side * 0.6),
                              -0.35 - 0.3 * u))
                pts.append((p + perp * 0.02, nrm, leaflet_len * 0.55, leaflet_len))
        if not dead:
            # frond rib
            parts.append(K.rod(f"p{seed}_rib{i}",
                               top, top + Vector((L * math.cos(a), L * math.sin(a),
                                                  -droop * L * 0.72)),
                               0.022, "plant_leaf_lo", seg=5, coll=coll))
    parts.append(card_cloud(f"p{seed}_fronds", pts, "leaf_card_c", coll, seed=seed * 3))
    return K.join(parts, f"palm_{seed}")


def shrub(seed=5, r=0.9, h=None, coll=None, leaf_mat="spray_b", cards=900):
    """Rounded shrub: card shell over a dark core, small leaves."""
    rnd = random.Random(seed)
    h = h or r * 0.95
    inner = _clumps(rnd, 40, r * 0.85, r * 0.85, h * 0.50, (0, 0, h * 0.52),
                    clump_r=r * 0.22, cards_per_clump=0, centers_only=True)
    parts = [card_cloud(f"s{seed}_core", _cloud(rnd, inner, 3, (0.16, 0.30)),
                        "spray_dark", coll, seed=seed * 6)]
    pts = _clumps(rnd, cards // 5, r, r, h * 0.62, (0, 0, h * 0.55), clump_r=r * 0.26,
                  cards_per_clump=5, size=(0.20, 0.34), inner=0.08)
    parts.append(card_cloud(f"s{seed}_leaves", pts, leaf_mat, coll, seed=seed * 9))
    return K.join(parts, f"shrub_{seed}")


def hedge(name, x0, y0, x1, y1, h=1.1, coll=None, leaf_mat="spray_b", density=1600.0,
          seed=7):
    """Clipped hedge block with a card skin so its edge is not a razor-straight box."""
    rnd = random.Random(seed)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    sx, sy = max(x1 - x0, 0.3), max(y1 - y0, 0.3)
    # dark card core (a box read as a green slab through the leaves)
    core = []
    rnd_c = random.Random(seed + 1)
    for i in range(int(max(120, sx * sy * h * 260))):
        p = Vector((rnd_c.uniform(x0 - 0.04, x1 + 0.04),
                    rnd_c.uniform(y0 - 0.04, y1 + 0.04), rnd_c.uniform(0.05, h * 0.98)))
        w = rnd_c.uniform(0.34, 0.55)
        core.append((p, Vector((rnd_c.uniform(-1, 1), rnd_c.uniform(-1, 1),
                                rnd_c.uniform(-0.4, 1))).normalized(), w, w * 1.2))
    parts = [card_cloud(f"{name}_core", core, "spray_dark", coll, seed=seed + 3)]
    n = int(max(220, (sx + sy) * h * density / 3.0))
    pts = []
    for i in range(n):
        side = rnd.random()
        z = rnd.uniform(0.10, 0.99) * h
        if side < 0.45:                      # long faces
            if rnd.random() < 0.5:
                p = Vector((rnd.uniform(x0, x1), y0 + rnd.uniform(-0.05, 0.05), z))
                nrm = Vector((0, -1, rnd.uniform(0.1, 0.5)))
            else:
                p = Vector((rnd.uniform(x0, x1), y1 + rnd.uniform(-0.05, 0.05), z))
                nrm = Vector((0, 1, rnd.uniform(0.1, 0.5)))
        elif side < 0.80:                    # ends
            if rnd.random() < 0.5:
                p = Vector((x0 + rnd.uniform(-0.05, 0.05), rnd.uniform(y0, y1), z))
                nrm = Vector((-1, 0, rnd.uniform(0.1, 0.5)))
            else:
                p = Vector((x1 + rnd.uniform(-0.05, 0.05), rnd.uniform(y0, y1), z))
                nrm = Vector((1, 0, rnd.uniform(0.1, 0.5)))
        else:                                # clipped top
            p = Vector((rnd.uniform(x0, x1), rnd.uniform(y0, y1), h + rnd.uniform(-0.03, 0.07)))
            nrm = Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 1.0))
        w = rnd.uniform(0.16, 0.30)
        pts.append((p, nrm, w, w * 1.25))
    parts.append(card_cloud(f"{name}_leaves", pts, leaf_mat, coll, seed=seed))
    return K.join(parts, name)


def ornamental_grass(seed=8, r=0.55, h=1.0, coll=None, blades=90):
    """Mounded ornamental grass - motion and soft edges next to hard architecture."""
    rnd = random.Random(seed)
    pts = []
    for i in range(blades):
        a = rnd.uniform(0, 6.28)
        rr = r * math.sqrt(rnd.random())
        p = Vector((rr * math.cos(a), rr * math.sin(a), 0.02))
        lean = rnd.uniform(0.15, 0.55)
        nrm = Vector((math.cos(a) * lean, math.sin(a) * lean, 1.0))
        w = h * rnd.uniform(0.75, 1.15)
        pts.append((p + Vector((0, 0, w * 0.45)), nrm, w * 0.16, w))
    parts = [card_cloud(f"ogr{seed}_blades", pts, "grass_blade", coll, seed=seed * 4)]
    parts.append(K.sphere(f"ogr{seed}_base", r * 0.5, (0, 0, 0.10), "mulch", seg=10,
                          rings=6, coll=coll, scale=(1.0, 1.0, 0.4)))
    return K.join(parts, f"ograss_{seed}")


def agave(seed=9, r=0.9, coll=None):
    """Spiky succulent - a Mediterranean garden staple, eight fat leaves."""
    rnd = random.Random(seed)
    parts = []
    for i in range(9):
        a = 2 * math.pi * i / 9 + rnd.uniform(-0.2, 0.2)
        tilt = rnd.uniform(0.55, 1.15)
        lf = K.leaf(f"ag{seed}_leaf{i}", L=r * rnd.uniform(0.8, 1.2), W=r * 0.20,
                    mat="plant_leaf", curl=-0.35, fold=0.35, coll=coll, seg=8,
                    width_pts=3)
        lf.rotation_euler = (tilt, 0, a)
        lf.location = (0, 0, 0.05)
        parts.append(lf)
    return K.join(parts, f"agave_{seed}")
