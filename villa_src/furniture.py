"""Furniture library. Every builder returns one joined object whose origin is at the
centre of its footprint on the floor (z=0), with the piece facing -Y.

That convention makes placement trivial and gives every exported per-piece GLB a
sensible pivot.
"""
import math

from . import kit, mats

K = kit


def _fur(piece, parts, coll=None):
    ob = K.join(parts, piece)
    ob["piece"] = piece
    return ob


def puff(name, size, loc, mat, r=0.30, coll=None, rot=(0, 0, 0), seg=4):
    rad = min(size) * r
    return K.box(name, size, loc, rot, mat, bevel=rad, bevel_seg=seg, smooth=True, coll=coll)


def legs(prefix, w, d, h, r=0.024, mat="black_steel", inset=0.08, coll=None, taper=True):
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x = sx * (w / 2 - inset)
            y = sy * (d / 2 - inset)
            out.append(K.cyl(f"{prefix}_leg", r, h, (x, y, h / 2), mat=mat,
                             seg=14, r2=r * 0.72 if taper else r, coll=coll))
    return out


def handles(prefix, w, n=2, z=0.0, x0=0.0, y=0.0, mat="brass", coll=None, vertical=False,
            length=0.16, depth=0.02):
    out = []
    for i in range(n):
        xx = x0 + (i - (n - 1) / 2) * w if n > 1 else x0
        out.append(K.box(f"{prefix}_h", (0.012, depth, length) if vertical else (length, depth, 0.012),
                         (xx, y, z), mat=mat, bevel=0.004, coll=coll))
    return out


# ------------------------------------------------------------------ seating
def sofa(w=2.40, d=0.95, mat="linen_sand", leg_mat="black_steel", pillows=True, coll=None):
    p = []
    leg_h = 0.13
    seat_z = 0.36
    arm_w = 0.17
    back_t = 0.18
    p += legs("sofa", w, d, leg_h, 0.026, leg_mat, 0.10, coll)
    p.append(K.box("sofa_deck", (w - 0.02, d - 0.02, seat_z - leg_h),
                   (0, 0, (leg_h + seat_z) / 2), mat=mat, bevel=0.02, coll=coll))
    # seat cushions
    n = 3
    cw = (w - 2 * arm_w - 0.04) / n
    for i in range(n):
        x = -w / 2 + arm_w + 0.02 + cw * (i + 0.5)
        p.append(puff("sofa_seat", (cw - 0.012, d - back_t - 0.06, 0.15),
                      (x, -back_t / 2 + 0.01, seat_z + 0.075), mat, 0.42, coll))
    # back cushions, tilted
    for i in range(n):
        x = -w / 2 + arm_w + 0.02 + cw * (i + 0.5)
        p.append(puff("sofa_back", (cw - 0.02, 0.17, 0.40),
                      (x, d / 2 - back_t / 2 - 0.05, seat_z + 0.28), mat, 0.40, coll,
                      rot=(math.radians(-11), 0, 0)))
    # arms
    for sx in (-1, 1):
        p.append(K.rbox("sofa_arm", (arm_w, d - 0.02, 0.30),
                        (sx * (w / 2 - arm_w / 2), 0, seat_z + 0.15), mat=mat,
                        radius=0.055, seg=4, coll=coll))
    if pillows:
        p.append(puff("sofa_pillow_a", (0.42, 0.13, 0.40), (-w / 2 + 0.42, d / 2 - 0.30,
                      seat_z + 0.30), "velvet_olive", 0.34, coll,
                      rot=(math.radians(-14), 0, math.radians(7))))
        p.append(puff("sofa_pillow_b", (0.36, 0.12, 0.34), (w / 2 - 0.40, d / 2 - 0.28,
                      seat_z + 0.28), "leather_cognac", 0.34, coll,
                      rot=(math.radians(-16), 0, math.radians(-9))))
    return _fur("sofa", p, coll)


def armchair(mat="boucle_cream", coll=None):
    w, d = 0.86, 0.88
    p = []
    leg_h = 0.16
    seat_z = 0.40
    p += legs("chair", w, d, leg_h, 0.022, "walnut", 0.09, coll)
    p.append(K.rbox("arm_seat", (w, d, 0.16), (0, 0, seat_z - 0.08), mat=mat,
                    radius=0.055, seg=4, coll=coll))
    p.append(puff("arm_back", (w - 0.02, 0.16, 0.44), (0, d / 2 - 0.10, seat_z + 0.24),
                  mat, 0.42, coll, rot=(math.radians(-10), 0, 0)))
    for sx in (-1, 1):
        p.append(K.rbox("arm_side", (0.10, d - 0.06, 0.26),
                        (sx * (w / 2 - 0.05), -0.02, seat_z + 0.05), mat=mat,
                        radius=0.045, seg=3, coll=coll))
    p.append(puff("arm_cushion", (0.44, 0.13, 0.36), (0.06, d / 2 - 0.24, seat_z + 0.24),
                  "velvet_olive", 0.34, coll, rot=(math.radians(-13), 0, math.radians(6))))
    return _fur("armchair", p, coll)


def dining_chair(mat="walnut", upholstery="leather_cognac", coll=None):
    w, d = 0.47, 0.50
    seat_z = 0.45
    p = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(K.cyl("dc_leg", 0.021, seat_z, (sx * (w / 2 - 0.055), sy * (d / 2 - 0.055),
                                                     seat_z / 2), mat=mat, seg=12,
                           r2=0.014, coll=coll))
    p.append(K.rbox("dc_seatframe", (w, d, 0.032), (0, 0, seat_z - 0.016), mat=mat,
                    radius=0.012, seg=3, coll=coll))
    p.append(puff("dc_seatpad", (w - 0.028, d - 0.028, 0.065), (0, 0, seat_z + 0.030),
                  upholstery, 0.34, coll))
    # back: two posts + a curved upholstered panel
    for sx in (-1, 1):
        p.append(K.cyl("dc_post", 0.017, 0.50, (sx * (w / 2 - 0.06), d / 2 - 0.06,
                                                seat_z + 0.25), mat=mat, seg=12,
                       r2=0.015, coll=coll))
    p.append(puff("dc_back", (w - 0.02, 0.075, 0.34), (0, d / 2 - 0.045, seat_z + 0.30),
                  upholstery, 0.34, coll, rot=(math.radians(-8), 0, 0)))
    p.append(K.rbox("dc_rail", (w - 0.02, 0.055, 0.045), (0, d / 2 - 0.028, seat_z + 0.50),
                    mat=mat, radius=0.018, seg=3, coll=coll,
                    rot=(math.radians(-8), 0, 0)))
    return _fur("dining_chair", p, coll)


def bar_stool(h=0.66, mat="black_steel", coll=None):
    p = []
    p.append(K.cyl("st_base", 0.19, 0.02, (0, 0, 0.01), mat=mat, seg=28, coll=coll))
    p.append(K.cyl("st_post", 0.026, h - 0.06, (0, 0, (h - 0.06) / 2 + 0.02), mat=mat,
                   seg=16, coll=coll))
    p.append(K.cyl("st_ring", 0.13, 0.014, (0, 0, 0.22), mat=mat, seg=24, coll=coll))
    p.append(K.lathe("st_seat", [(0.0, 0.0), (0.175, 0.0), (0.185, 0.035), (0.17, 0.055),
                                 (0.0, 0.052)], (0, 0, h), mat="leather_cognac", seg=32,
                     coll=coll))
    return _fur("bar_stool", p, coll)


def office_chair(coll=None):
    p = []
    for i in range(5):
        a = 2 * math.pi * i / 5
        p.append(K.box("oc_leg", (0.30, 0.045, 0.022),
                       (0.15 * math.cos(a), 0.15 * math.sin(a), 0.035), mat="black_steel",
                       bevel=0.008, coll=coll, rot=(0, 0, a)))
    p.append(K.cyl("oc_post", 0.028, 0.30, (0, 0, 0.19), mat="chrome", seg=14, coll=coll))
    p.append(K.rbox("oc_seat", (0.50, 0.48, 0.07), (0, 0, 0.38), mat="linen_graphite",
                    radius=0.03, seg=3, coll=coll))
    p.append(K.rbox("oc_back", (0.44, 0.07, 0.46), (0, 0.22, 0.66), mat="linen_graphite",
                    radius=0.03, seg=3, coll=coll, rot=(math.radians(-9), 0, 0)))
    p.append(K.cyl("oc_spine", 0.022, 0.30, (0, 0.22, 0.44), mat="chrome", seg=12, coll=coll))
    return _fur("office_chair", p, coll)


# -------------------------------------------------------------------- tables
def coffee_table(w=1.35, d=0.72, h=0.38, mat="oak_veneer", leg_mat="black_steel", coll=None):
    p = []
    p.append(K.rbox("ct_top", (w, d, 0.035), (0, 0, h - 0.018), mat=mat, radius=0.018,
                    seg=4, coll=coll))
    p.append(K.rbox("ct_shelf", (w - 0.22, d - 0.18, 0.022), (0, 0, 0.10), mat=mat,
                    radius=0.01, seg=3, coll=coll))
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(K.box("ct_leg", (0.030, 0.030, h - 0.03),
                           (sx * (w / 2 - 0.07), sy * (d / 2 - 0.07), (h - 0.03) / 2),
                           mat=leg_mat, bevel=0.006, coll=coll))
    return _fur("coffee_table", p, coll)


def side_table(r=0.24, h=0.52, mat="walnut", coll=None):
    p = [K.lathe("st_top", [(0, 0), (r, 0), (r, 0.035), (0, 0.035)], (0, 0, h - 0.035),
                 mat=mat, seg=40, coll=coll),
         K.cyl("st_col", 0.028, h - 0.035, (0, 0, (h - 0.035) / 2), mat=mat, seg=16,
               coll=coll),
         K.cyl("st_foot", r * 0.62, 0.022, (0, 0, 0.011), mat=mat, seg=28, coll=coll)]
    return _fur("side_table", p, coll)


def dining_table(w=2.20, d=0.98, h=0.75, mat="oak_veneer", coll=None):
    p = []
    top = K.rbox("dt_top", (w, d, 0.042), (0, 0, h - 0.021), mat=mat, radius=0.02, seg=4,
                 coll=coll)
    p.append(top)
    # twin trestle legs in dark steel
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.28)
        p.append(K.box("dt_trestle", (0.055, d - 0.26, h - 0.055), (x, 0, (h - 0.055) / 2),
                       mat="black_steel", bevel=0.01, coll=coll))
        p.append(K.box("dt_foot", (0.10, d - 0.20, 0.022), (x, 0, 0.011), mat="black_steel",
                       bevel=0.006, coll=coll))
    p.append(K.box("dt_stretcher", (w - 0.56, 0.05, 0.05), (0, 0, h * 0.42),
                   mat="black_steel", bevel=0.008, coll=coll))
    return _fur("dining_table", p, coll)


def desk(w=1.45, d=0.68, h=0.74, mat="walnut", coll=None):
    p = [K.rbox("dk_top", (w, d, 0.038), (0, 0, h - 0.019), mat=mat, radius=0.014, seg=3,
                coll=coll)]
    for sx in (-1, 1):
        p.append(K.box("dk_side", (0.035, d - 0.08, h - 0.05),
                       (sx * (w / 2 - 0.09), 0, (h - 0.05) / 2), mat="black_steel",
                       bevel=0.006, coll=coll))
    p.append(K.box("dk_rail", (w - 0.22, 0.03, 0.06), (0, -d / 2 + 0.10, h - 0.09),
                   mat="black_steel", bevel=0.005, coll=coll))
    return _fur("desk", p, coll)


# ------------------------------------------------------------------- storage
def sideboard(w=1.90, d=0.45, h=0.72, mat="walnut", coll=None, doors=3):
    p = []
    leg_h = 0.14
    body_h = h - leg_h
    p.append(K.rbox("sb_body", (w, d, body_h), (0, 0, leg_h + body_h / 2), mat=mat,
                    radius=0.008, seg=2, coll=coll))
    for sx in (-1, 1):
        p.append(K.cyl("sb_leg", 0.018, leg_h, (sx * (w / 2 - 0.10), d / 2 - 0.09, leg_h / 2),
                       mat="black_steel", seg=12, r2=0.012, coll=coll))
        p.append(K.cyl("sb_leg", 0.018, leg_h, (sx * (w / 2 - 0.10), -d / 2 + 0.09, leg_h / 2),
                       mat="black_steel", seg=12, r2=0.012, coll=coll))
    # door shadow gaps
    dw = w / doors
    for i in range(doors):
        x = -w / 2 + dw * (i + 0.5)
        p.append(K.box("sb_front", (dw - 0.008, 0.012, body_h - 0.012),
                       (x, -d / 2 - 0.002, leg_h + body_h / 2), mat=mat, bevel=0.003,
                       coll=coll))
    p += handles("sb", w * 0.55, 1, leg_h + body_h - 0.06, 0.0, -d / 2 - 0.012, coll=coll,
                 length=0.10)
    return _fur("sideboard", p, coll)


def console(w=1.30, d=0.36, h=0.80, mat="oak_veneer", coll=None):
    p = [K.rbox("cn_top", (w, d, 0.032), (0, 0, h - 0.016), mat=mat, radius=0.012, seg=3,
                coll=coll),
         K.rbox("cn_shelf", (w - 0.10, d - 0.05, 0.026), (0, 0, 0.16), mat=mat,
                radius=0.01, seg=2, coll=coll)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(K.box("cn_leg", (0.026, 0.026, h - 0.02),
                           (sx * (w / 2 - 0.03), sy * (d / 2 - 0.03), (h - 0.02) / 2),
                           mat="black_steel", bevel=0.004, coll=coll))
    return _fur("console", p, coll)


def tv_unit(w=1.85, d=0.42, h=0.42, mat="walnut", coll=None, screen_w=1.42):
    p = [K.rbox("tv_cab", (w, d, h - 0.10), (0, 0, 0.10 + (h - 0.10) / 2), mat=mat,
                radius=0.008, seg=2, coll=coll),
         K.box("tv_plinth", (w - 0.20, d - 0.10, 0.10), (0, 0.02, 0.05), mat="black_paint",
               bevel=0.006, coll=coll)]
    for i in range(2):
        p.append(K.box("tv_door", (w / 2 - 0.02, 0.012, h - 0.12),
                       (-w / 4 + i * w / 2 + (0.01 if i else -0.01), -d / 2 - 0.002,
                        h / 2 + 0.02), mat=mat, bevel=0.003, coll=coll))
    p += handles("tv", w * 0.5, 1, h - 0.08, 0, -d / 2 - 0.012, coll=coll, length=0.12)
    # television on top
    sw, sh = screen_w, screen_w * 0.5625
    zt = h + 0.02 + 0.05
    p.append(K.box("tv_stand", (0.30, 0.19, 0.018), (0, 0.02, h + 0.03), mat="black_paint",
                   bevel=0.004, coll=coll))
    p.append(K.box("tv_neck", (0.06, 0.03, 0.10), (0, 0.02, h + 0.08), mat="black_paint",
                   coll=coll))
    p.append(K.box("tv_screen", (sw, 0.035, sh), (0, 0.0, h + 0.13 + sh / 2),
                   mat="tv_screen", bevel=0.004, coll=coll))
    p.append(K.box("tv_bezel", (sw + 0.012, 0.028, sh + 0.012), (0, 0.006, h + 0.13 + sh / 2),
                   mat="black_paint", bevel=0.003, coll=coll))
    return _fur("tv_unit", p, coll)


def bookshelf(w=1.10, h=2.05, d=0.32, shelves=5, mat="oak_veneer", coll=None, books=True):
    p = []
    t = 0.028
    for sx in (-1, 1):
        p.append(K.box("bs_side", (t, d, h), (sx * (w / 2 - t / 2), 0, h / 2), mat=mat,
                       bevel=0.004, coll=coll))
    p.append(K.box("bs_back", (w, 0.014, h), (0, d / 2 - 0.007, h / 2), mat=mat,
                   bevel=0.003, coll=coll))
    for i in range(shelves):
        z = h * (i + 0.06) / (shelves + 0.12) + 0.03
        p.append(K.box("bs_shelf", (w - 2 * t, d - 0.02, 0.022), (0, 0, z), mat=mat,
                       bevel=0.003, coll=coll))
    if books:
        import random
        rnd = random.Random(7)
        cols = ["book_red", "book_blue", "book_cream", "paper", "walnut", "black_paint"]
        for i in range(shelves):
            z = h * (i + 0.06) / (shelves + 0.12) + 0.03 + 0.011
            x = -w / 2 + t + 0.02
            while x < w / 2 - t - 0.12:
                bw = rnd.uniform(0.022, 0.045)
                bh = rnd.uniform(0.18, 0.27)
                p.append(K.box("bs_book", (bw, rnd.uniform(0.14, 0.21), bh),
                               (x + bw / 2, -0.02, z + bh / 2), mat=rnd.choice(cols),
                               bevel=0.002, coll=coll))
                x += bw + 0.004
                if rnd.random() < 0.12:
                    x += rnd.uniform(0.04, 0.12)
    return _fur("bookshelf", p, coll)


def wardrobe(w=1.60, h=2.35, d=0.62, mat="oak_veneer", coll=None, doors=3):
    p = [K.box("wd_body", (w, d, h), (0, 0, h / 2), mat=mat, bevel=0.005, coll=coll)]
    dw = w / doors
    for i in range(doors):
        x = -w / 2 + dw * (i + 0.5)
        p.append(K.box("wd_door", (dw - 0.006, 0.016, h - 0.01), (x, -d / 2 - 0.008, h / 2),
                       mat=mat, bevel=0.003, coll=coll))
        p.append(K.box("wd_handle", (0.012, 0.02, 0.26),
                       (x + (dw / 2 - 0.05) if i % 2 == 0 else x - (dw / 2 - 0.05),
                        -d / 2 - 0.026, 1.15), mat="black_steel", bevel=0.004, coll=coll))
    return _fur("wardrobe", p, coll)


def shelving_unit(w=1.20, h=1.80, d=0.34, coll=None, mat="black_steel", wood="walnut"):
    p = []
    for sx in (-1, 1):
        p.append(K.box("sh_side", (0.025, d, h), (sx * (w / 2 - 0.012), 0, h / 2), mat=mat,
                       bevel=0.003, coll=coll))
    for i in range(4):
        z = h * (i + 0.5) / 4
        p.append(K.box("sh_shelf", (w - 0.05, d - 0.02, 0.028), (0, 0, z), mat=wood,
                       bevel=0.003, coll=coll))
    return _fur("shelving_unit", p, coll)


# ---------------------------------------------------------------------- beds
def bed(w=1.85, l=2.10, mat="linen_sand", frame="walnut", head="boucle_cream",
        head_h=1.12, coll=None, throw=True, pillows=2):
    """Headboard at +Y; the bed extends towards -Y. Origin at the floor centre."""
    p = []
    leg_h = 0.11
    plat_h = 0.22
    p += legs("bed", w + 0.02, l - 0.10, leg_h, 0.032, "black_steel", 0.13, coll)
    # platform base, inset from the mattress edge
    p.append(K.rbox("bed_frame", (w + 0.09, l - 0.02, plat_h),
                    (0, 0, leg_h + plat_h / 2), mat=frame, radius=0.012, seg=3,
                    coll=coll))
    p.append(K.rbox("bed_mattress", (w, l - 0.06, 0.26),
                    (0, -0.02, leg_h + plat_h + 0.13), mat="mattress", radius=0.045,
                    seg=4, coll=coll))
    ztop = leg_h + plat_h + 0.26
    # duvet: covers from the foot to two thirds up, draping over the sides
    duv_y0 = -l / 2 + 0.02          # foot end
    duv_y1 = l / 2 - 0.46           # leaves the pillows clear
    p.append(K.rbox("bed_duvet", (w + 0.075, duv_y1 - duv_y0, 0.12),
                    (0, (duv_y0 + duv_y1) / 2, ztop + 0.03), mat=mat,
                    radius=0.05, seg=4, coll=coll))
    p.append(K.rbox("bed_duvet_drop", (w + 0.075, 0.10, 0.26),
                    (0, duv_y0 + 0.03, ztop - 0.10), mat=mat, radius=0.03, seg=3,
                    coll=coll))
    # turned-down top edge
    p.append(K.rbox("bed_turn", (w + 0.08, 0.22, 0.09),
                    (0, duv_y1 - 0.10, ztop + 0.055), mat="linen_throw",
                    radius=0.038, seg=3, coll=coll))
    # pillows: upright against the headboard, then a smaller pair in front
    for i in range(pillows):
        x = (i - (pillows - 1) / 2) * (w * 0.50)
        p.append(puff("bed_pillow_big", (w * 0.46, 0.20, 0.42),
                      (x, l / 2 - 0.20, ztop + 0.20), "pillow", 0.30, coll,
                      rot=(math.radians(-14), 0, 0)))
        p.append(puff("bed_pillow_small", (w * 0.40, 0.16, 0.30),
                      (x, l / 2 - 0.38, ztop + 0.14), "pillow", 0.32, coll,
                      rot=(math.radians(-20), 0, 0)))
    if throw:
        p.append(puff("bed_throw", (w + 0.075, 0.58, 0.05),
                      (0, -l / 2 + 0.62, ztop + 0.075), "linen_throw", 0.32, coll))
    # upholstered headboard, wider than the bed
    p.append(K.rbox("bed_head", (w + 0.22, 0.085, head_h), (0, l / 2 + 0.02, head_h / 2),
                    mat=head, radius=0.030, seg=3, coll=coll))
    return _fur("bed", p, coll)


def bed_bench(w=1.40, d=0.42, h=0.44, mat="linen_graphite", leg_mat="black_steel",
              coll=None):
    p = [puff("bb_top", (w, d, 0.14), (0, 0, h - 0.07), mat, 0.34, coll)]
    for sx in (-1, 1):
        p.append(K.box("bb_leg", (0.035, d - 0.10, h - 0.14),
                       (sx * (w / 2 - 0.10), 0, (h - 0.14) / 2), mat=leg_mat,
                       bevel=0.006, coll=coll))
    p.append(K.box("bb_rail", (w - 0.24, 0.03, 0.05), (0, 0, 0.16), mat=leg_mat,
                   bevel=0.004, coll=coll))
    return _fur("bed_bench", p, coll)


def curtain(w=1.60, h=2.85, folds=9, amp=0.055, mat="curtain_sheer", coll=None,
            top=3.0):
    """A gently pleated curtain panel hanging from `top` down to the floor."""
    import bmesh
    bm = bmesh.new()
    nx = max(4, folds * 4)
    rows = []
    for i in range(nx + 1):
        t = i / nx
        x = (t - 0.5) * w
        y = amp * math.sin(t * folds * 2 * math.pi)
        rows.append([bm.verts.new((x, y, z)) for z in (0.01, top - 0.03)])
    for i in range(nx):
        try:
            bm.faces.new((rows[i][0], rows[i + 1][0], rows[i + 1][1], rows[i][1]))
        except ValueError:
            pass
    bm.normal_update()
    ob = K._finish("curtain", bm, mat, coll, 0, 2, True)
    return _fur("curtain", [ob], coll)


def nightstand(w=0.50, d=0.42, h=0.52, mat="walnut", coll=None):
    p = [K.rbox("ns_body", (w, d, h - 0.14), (0, 0, 0.14 + (h - 0.14) / 2), mat=mat,
                radius=0.008, seg=2, coll=coll),
         K.box("ns_plinth", (w - 0.06, d - 0.05, 0.14), (0, 0, 0.07), mat="black_paint",
               bevel=0.004, coll=coll)]
    for i in range(2):
        z = 0.14 + (h - 0.14) * (0.28 + 0.42 * i)
        p.append(K.box("ns_drawer", (w - 0.02, 0.012, (h - 0.14) * 0.40 - 0.008),
                       (0, -d / 2 - 0.002, z), mat=mat, bevel=0.003, coll=coll))
        p.append(K.box("ns_pull", (w * 0.45, 0.018, 0.012), (0, -d / 2 - 0.014, z),
                       mat="brass", bevel=0.003, coll=coll))
    return _fur("nightstand", p, coll)


# ------------------------------------------------------------------ kitchen
def base_run(length, depth=0.62, h=0.90, mat="oak_veneer", worktop="marble", coll=None,
             doors=None, sink=False, hob=False, plinth_h=0.10, splash_h=0.0):
    p = [K.box("kb_carcass", (length, depth, h - plinth_h), (0, 0, plinth_h + (h - plinth_h) / 2),
               mat=mat, bevel=0.004, coll=coll),
         K.box("kb_plinth", (length - 0.06, depth - 0.09, plinth_h), (0, -0.04, plinth_h / 2),
               mat="black_paint", bevel=0.003, coll=coll),
         K.rbox("kb_top", (length + 0.02, depth + 0.03, 0.04), (0, -0.012, h + 0.02),
                mat=worktop, radius=0.006, seg=2, coll=coll),
         K.box("kb_splash", (length, 0.024, max(0.10, splash_h)), (0, depth / 2 - 0.012,
               h + 0.04 + max(0.10, splash_h) / 2), mat=worktop, bevel=0.003, coll=coll)]
    n = doors or max(2, int(round(length / 0.60)))
    dw = length / n
    for i in range(n):
        x = -length / 2 + dw * (i + 0.5)
        p.append(K.box("kb_door", (dw - 0.008, 0.016, h - plinth_h - 0.02),
                       (x, -depth / 2 - 0.008, plinth_h + (h - plinth_h) / 2), mat=mat,
                       bevel=0.003, coll=coll))
        p.append(K.box("kb_pull", (0.012, 0.02, 0.14) if i % 2 else (0.14, 0.02, 0.012),
                       (x, -depth / 2 - 0.026, h - 0.09), mat="brass", bevel=0.003,
                       coll=coll))
    if sink:
        p.append(K.box("kb_sink_rim", (0.62, 0.44, 0.012), (0, -0.02, h + 0.045),
                       mat="steel", bevel=0.004, coll=coll))
        p.append(K.box("kb_sink_bowl", (0.56, 0.38, 0.20), (0, -0.02, h + 0.02 - 0.10),
                       mat="steel", bevel=0.006, coll=coll))
        p.append(K.cyl("kb_tap", 0.014, 0.32, (0, depth / 2 - 0.16, h + 0.16), mat="brass",
                       seg=14, coll=coll))
        p.append(K.rod("kb_tap_arm", (0, depth / 2 - 0.16, h + 0.32),
                       (0, depth / 2 - 0.30, h + 0.30), 0.013, "brass", coll=coll))
    if hob:
        p.append(K.box("kb_hob", (0.60, 0.50, 0.012), (0, -0.01, h + 0.046), mat="tv_screen",
                       bevel=0.004, coll=coll))
        for i in range(4):
            p.append(K.lathe("kb_burner", [(0.02, 0), (0.075, 0), (0.075, 0.006), (0.02, 0.006)],
                             (-0.15 + 0.30 * (i % 2), -0.12 + 0.24 * (i // 2), h + 0.052),
                             mat="black_steel", seg=20, coll=coll))
    return _fur("kitchen_base_run", p, coll)


def wall_cabinets(length, h=0.72, depth=0.35, z=1.50, mat="oak_veneer", coll=None, doors=None):
    p = [K.box("wc_body", (length, depth, h), (0, 0, z + h / 2), mat=mat, bevel=0.004,
               coll=coll)]
    n = doors or max(2, int(round(length / 0.60)))
    dw = length / n
    for i in range(n):
        x = -length / 2 + dw * (i + 0.5)
        p.append(K.box("wc_door", (dw - 0.008, 0.016, h - 0.012), (x, -depth / 2 - 0.008,
                       z + h / 2), mat=mat, bevel=0.003, coll=coll))
        p.append(K.box("wc_pull", (0.012, 0.02, 0.12), (x, -depth / 2 - 0.026, z + 0.10),
                       mat="brass", bevel=0.003, coll=coll))
    return _fur("wall_cabinets", p, coll)


def tall_unit(w=0.90, h=2.30, d=0.62, mat="oak_veneer", coll=None, fridge=False):
    p = [K.box("tu_body", (w, d, h), (0, 0, h / 2), mat=mat, bevel=0.004, coll=coll)]
    if fridge:
        for i in range(2):
            hh = h * (0.62 if i == 0 else 0.38)
            z = 0.0 if i == 0 else h * 0.62
            p.append(K.box("tu_door", (w - 0.012, 0.02, hh - 0.012), (0, -d / 2 - 0.010,
                           z + hh / 2), mat="steel" if i == 0 else "steel", bevel=0.004,
                           coll=coll))
            p.append(K.box("tu_bar", (0.014, 0.05, 0.60), (w / 2 - 0.06, -d / 2 - 0.055,
                           z + hh * 0.55), mat="black_steel", bevel=0.004, coll=coll))
    else:
        p.append(K.box("tu_door", (w - 0.012, 0.018, h - 0.012), (0, -d / 2 - 0.009, h / 2),
                       mat=mat, bevel=0.003, coll=coll))
        p.append(K.box("tu_bar", (0.014, 0.02, 0.30), (w / 2 - 0.05, -d / 2 - 0.028, 1.20),
                       mat="brass", bevel=0.003, coll=coll))
    return _fur("tall_unit", p, coll)


def range_hood(w=0.90, h=0.70, d=0.50, z=1.65, coll=None):
    p = [K.box("rh_body", (w, d, h * 0.42), (0, 0, z + h * 0.42 / 2), mat="steel_soft",
               bevel=0.008, coll=coll),
         K.box("rh_chimney", (w * 0.46, d * 0.62, h * 0.58), (0, 0.04, z + h * 0.71),
               mat="steel_soft", bevel=0.004, coll=coll),
         K.box("rh_lip", (w + 0.012, d + 0.012, 0.016), (0, 0, z + h * 0.42),
               mat="black_paint", bevel=0.003, coll=coll)]
    return _fur("range_hood", p, coll)


def kitchen_island(w=2.80, d=1.05, h=0.92, mat="oak_veneer", worktop="marble", coll=None,
                   overhang=0.30):
    p = [K.box("ki_body", (w, d - overhang, h - 0.10), (0, overhang / 2, 0.10 + (h - 0.10) / 2),
               mat=mat, bevel=0.004, coll=coll),
         K.box("ki_plinth", (w - 0.05, d - overhang - 0.05, 0.10), (0, overhang / 2, 0.05),
               mat="black_paint", bevel=0.003, coll=coll),
         K.rbox("ki_top", (w + 0.04, d + 0.04, 0.05), (0, 0, h + 0.025), mat=worktop,
                radius=0.008, seg=2, coll=coll)]
    n = max(2, int(round(w / 0.65)))
    dw = w / n
    for i in range(n):
        x = -w / 2 + dw * (i + 0.5)
        p.append(K.box("ki_panel", (dw - 0.01, 0.016, h - 0.14),
                       (x, -d / 2 + overhang - 0.008, 0.12 + (h - 0.14) / 2), mat=mat,
                       bevel=0.003, coll=coll))
    return _fur("kitchen_island", p, coll)


def pendant(r=0.16, drop=1.10, mat="black_steel", shade_h=0.20, coll=None, bulb=True,
           ceiling=3.0):
    """Hangs from `ceiling`: cord of length `drop`, then a spun-metal shade."""
    z_top = ceiling - drop                    # bottom rim of the shade
    z_shade_hi = z_top + shade_h
    p = [K.cyl("pd_cord", 0.005, drop - shade_h, (0, 0, ceiling - (drop - shade_h) / 2),
               mat="black_steel", seg=8, coll=coll),
         K.cyl("pd_canopy", 0.045, 0.02, (0, 0, ceiling - 0.012), mat="black_steel",
               seg=20, coll=coll)]
    # shade: outer cone + inner reflector, closed at the top
    p.append(K.lathe("pd_shade", [(r * 0.20, 0.0), (r * 0.98, shade_h * 0.86),
                                  (r, shade_h), (r * 0.10, shade_h),
                                  (r * 0.12, shade_h * 0.94), (r * 0.90, shade_h * 0.80)],
                     (0, 0, z_top), mat=mat, seg=48, coll=coll))
    if bulb:
        p.append(K.sphere("pd_bulb", min(0.032, r * 0.32),
                          (0, 0, z_top + shade_h * 0.55),
                          mats.warm((1.0, 0.80, 0.55), 4.5, "pendant_bulb"), seg=14, rings=8, coll=coll))
    return _fur("pendant", p, coll)


def floor_lamp(h=1.62, coll=None, shade_mat="linen_throw"):
    p = [K.lathe("fl_base", [(0, 0), (0.16, 0), (0.16, 0.02), (0.05, 0.035), (0.05, 0.04),
                             (0, 0.04)], (0, 0, 0), mat="black_steel", seg=32, coll=coll),
         K.cyl("fl_pole", 0.011, h - 0.35, (0, 0, (h - 0.35) / 2 + 0.03), mat="brass",
               seg=12, coll=coll),
         K.lathe("fl_shade", [(0.16, 0), (0.20, 0.26), (0.19, 0.27), (0.15, 0.01)],
                 (0, 0, h - 0.35), mat=shade_mat, seg=40, coll=coll),
         K.sphere("fl_bulb", 0.028, (0, 0, h - 0.22), mats.warm((1.0, 0.80, 0.55), 5.0, "floorlamp_bulb"),
                  seg=12, coll=coll)]
    return _fur("floor_lamp", p, coll)


def table_lamp(h=0.46, coll=None):
    p = [K.lathe("tl_base", [(0, 0), (0.075, 0), (0.09, 0.03), (0.05, 0.14), (0.03, 0.16),
                             (0, 0.16)], (0, 0, 0), mat="ceramic", seg=32, coll=coll),
         K.cyl("tl_neck", 0.008, h - 0.34, (0, 0, 0.16 + (h - 0.34) / 2), mat="brass",
               seg=10, coll=coll),
         K.lathe("tl_shade", [(0.13, 0), (0.16, 0.20), (0.15, 0.21), (0.12, 0.01)],
                 (0, 0, h - 0.21), mat="linen_throw", seg=36, coll=coll),
         K.sphere("tl_bulb", 0.022, (0, 0, h - 0.13), mats.warm((1.0, 0.80, 0.55), 3.5, "tablelamp_bulb"),
                  seg=12, coll=coll)]
    return _fur("table_lamp", p, coll)


# ------------------------------------------------------------------ bathroom
def vanity(w=1.20, d=0.50, h=0.86, coll=None, basins=1):
    p = [K.box("vn_body", (w, d, h - 0.16), (0, 0, 0.16 + (h - 0.16) / 2), mat="walnut",
               bevel=0.004, coll=coll),
         K.box("vn_plinth", (w - 0.08, d - 0.06, 0.16), (0, 0.02, 0.08), mat="black_paint",
               bevel=0.003, coll=coll),
         K.rbox("vn_top", (w + 0.02, d + 0.02, 0.04), (0, 0, h + 0.02), mat="marble",
                radius=0.006, seg=2, coll=coll)]
    for i in range(basins):
        x = (i - (basins - 1) / 2) * (w / max(basins, 1) * 0.92)
        p.append(K.lathe("vn_basin", [(0.0, 0.0), (0.17, 0.0), (0.19, 0.055), (0.185, 0.13),
                                      (0.16, 0.125), (0.165, 0.045), (0.0, 0.035)],
                         (x, -0.02, h + 0.045), mat="ceramic", seg=36, coll=coll))
        p.append(K.cyl("vn_tap", 0.012, 0.22, (x, d / 2 - 0.11, h + 0.14), mat="brass",
                       seg=12, coll=coll))
        p.append(K.rod("vn_spout", (x, d / 2 - 0.11, h + 0.25), (x, d / 2 - 0.20, h + 0.23),
                       0.011, "brass", coll=coll))
    ob = _fur("vanity", p, coll)
    ob["basins"] = basins
    return ob


def toilet(coll=None):
    p = [K.box("wc_tank", (0.38, 0.16, 0.36), (0, 0.22, 0.58), mat="ceramic", bevel=0.02,
               coll=coll),
         K.lathe("wc_bowl", [(0.0, 0.0), (0.17, 0.0), (0.19, 0.10), (0.20, 0.24),
                             (0.21, 0.34), (0.0, 0.34)], (0, -0.03, 0.16), mat="ceramic",
                 seg=36, coll=coll),
         K.rbox("wc_seat", (0.40, 0.46, 0.035), (0, -0.03, 0.51), mat="ceramic",
                radius=0.05, seg=4, coll=coll)]
    return _fur("toilet", p, coll)


def shower(w=1.05, d=1.20, h=2.10, coll=None):
    p = [K.box("sh_tray", (w, d, 0.05), (0, 0, 0.025), mat="ceramic", bevel=0.01, coll=coll),
         K.box("sh_drain", (0.14, 0.14, 0.012), (0, 0, 0.052), mat="steel", bevel=0.003,
               coll=coll)]
    # glass walls on the two open sides, in 10 mm glass
    p.append(K.box("sh_glass_a", (0.012, d, h - 0.05), (-w / 2 + 0.006, 0, h / 2),
                   mat="glass", coll=coll))
    p.append(K.box("sh_glass_b", (w * 0.55, 0.012, h - 0.05), (w / 2 - w * 0.275, -d / 2 + 0.006,
                   h / 2), mat="glass", coll=coll))
    p.append(K.box("sh_frame", (0.02, 0.02, h - 0.05), (-w / 2 + 0.01, -d / 2 + 0.01, h / 2),
                   mat="black_steel", bevel=0.003, coll=coll))
    p.append(K.cyl("sh_head_pipe", 0.012, 0.35, (0, d / 2 - 0.14, h - 0.20), mat="black_steel",
                   seg=12, coll=coll))
    p.append(K.lathe("sh_head", [(0, 0), (0.13, 0.025), (0.135, 0.03), (0, 0.032)],
                     (0, d / 2 - 0.30, h - 0.06), mat="black_steel", seg=32, coll=coll))
    p.append(K.box("sh_control", (0.14, 0.02, 0.10), (0.22, d / 2 - 0.01, 1.05),
                   mat="black_steel", bevel=0.004, coll=coll))
    return _fur("shower", p, coll)


def bathtub(w=1.70, d=0.78, h=0.58, coll=None):
    p = [K.rbox("bt_body", (w, d, h), (0, 0, h / 2), mat="ceramic", radius=0.075, seg=5,
                coll=coll),
         K.rbox("bt_water", (w - 0.16, d - 0.16, 0.005), (0, 0, h - 0.015), mat="white_paint",
                radius=0.05, seg=4, coll=coll),
         K.cyl("bt_tap", 0.014, 0.24, (-w / 2 + 0.14, 0, h + 0.10), mat="brass", seg=12,
               coll=coll),
         K.rod("bt_spout", (-w / 2 + 0.14, 0, h + 0.21), (-w / 2 + 0.26, 0, h + 0.19), 0.012,
               "brass", coll=coll)]
    return _fur("bathtub", p, coll)


def mirror(w=1.10, h=0.90, mat="mirror", coll=None):
    p = [K.box("mi_glass", (w, 0.012, h), (0, 0, 0), mat=mat, bevel=0.003, coll=coll),
         K.box("mi_frame", (w + 0.03, 0.02, h + 0.03), (0, 0.012, 0), mat="black_steel",
               bevel=0.004, coll=coll)]
    return _fur("mirror", p, coll)


def towel_rail(w=0.60, coll=None):
    p = [K.cyl("tr_bar", 0.011, w, (0, 0, 0), mat="brass", seg=14, coll=coll),
         K.box("tr_towel_a", (w * 0.9, 0.16, 0.30), (0, 0.08, -0.13), mat="towel",
               bevel=0.02, coll=coll)]
    p[0].rotation_euler = (0, math.radians(90), 0)
    return _fur("towel_rail", p, coll)


def washer(coll=None, dryer=False):
    p = [K.box("wa_body", (0.60, 0.60, 0.85), (0, 0, 0.425), mat="white_paint", bevel=0.008,
               coll=coll),
         K.cyl("wa_drum", 0.20, 0.03, (0, -0.305, 0.50), mat="black_steel", seg=32,
               coll=coll, rot=(math.radians(90), 0, 0)),
         K.cyl("wa_glass", 0.155, 0.012, (0, -0.325, 0.50), mat="glass", seg=32,
               coll=coll, rot=(math.radians(90), 0, 0)),
         K.box("wa_panel", (0.56, 0.012, 0.14), (0, -0.306, 0.74), mat="black_steel",
               bevel=0.004, coll=coll)]
    return _fur("dryer" if dryer else "washer", p, coll)


# -------------------------------------------------------------------- decor
def rug(w=3.0, d=2.2, mat="rug_wool", coll=None, thick=0.014):
    return _fur("rug", [K.box("rug", (w, d, thick), (0, 0, thick / 2), mat=mat,
                              bevel=0.005, bevel_seg=2, coll=coll)], coll)


def art(w=0.9, h=1.15, style=1, frame="black_paint", coll=None, canvas="paint"):
    """Framed print: 4 cm painted frame, 3 mm mount, printed canvas."""
    p = [K.box("art_frame", (w, 0.040, h), (0, 0, 0), mat=frame, bevel=0.003, coll=coll)]
    p.append(K.box("art_mount", (w - 0.055, 0.016, h - 0.055), (0, -0.016, 0),
                   mat="paper", bevel=0.001, coll=coll))
    c = K.box("art_canvas", (w - 0.13, 0.008, h - 0.13), (0, -0.026, 0),
              mat=f"{canvas}_{style}" if canvas == "paint" else canvas, coll=coll)
    K.set_uv_01(c)
    p.append(c)
    return _fur("art", p, coll)


def vase(h=0.34, r=0.09, mat="ceramic", coll=None, stems=0, neck=0.55):
    prof = [(0, 0), (r * 0.72, 0), (r * 0.95, h * 0.25), (r, h * 0.55), (r * neck, h),
            (r * neck * 1.12, h), (r * neck * 0.86, h - 0.012), (r * 0.86, h * 0.52),
            (r * 0.7, h * 0.06), (0, h * 0.04)]
    p = [K.lathe("va_body", prof, (0, 0, 0), mat=mat, seg=36, coll=coll)]
    for i in range(stems):
        a = 2 * math.pi * i / max(stems, 1)
        tip = (0.10 * math.cos(a), 0.10 * math.sin(a), h + 0.42)
        p.append(K.rod("va_stem", (0, 0, h - 0.02), tip, 0.004, "bark", seg=6, coll=coll))
        p.append(K.sphere("va_bloom", 0.045, tip, "leaf", seg=10, rings=6, coll=coll,
                          scale=(1.0, 1.0, 0.6)))
    return _fur("vase", p, coll)


def bowl(r=0.16, h=0.075, mat="ceramic", coll=None):
    return _fur("bowl", [K.lathe("bw", [(0, 0), (r * 0.55, 0), (r * 0.9, h * 0.5),
                                        (r, h), (r * 0.92, h), (r * 0.84, h * 0.55),
                                        (r * 0.5, 0.012), (0, 0.012)], (0, 0, 0), mat=mat,
                          seg=36, coll=coll)], coll)


def books(count=4, coll=None):
    import random
    rnd = random.Random(3)
    p = []
    z = 0.0
    for i in range(count):
        w = rnd.uniform(0.20, 0.30)
        d = rnd.uniform(0.16, 0.22)
        t = rnd.uniform(0.025, 0.045)
        p.append(K.box("bk", (w, d, t), (rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02),
                       z + t / 2), mat=rnd.choice(["book_red", "book_blue", "book_cream"]),
                       bevel=0.002, coll=coll))
        z += t
    return _fur("books", p, coll)


def candle(h=0.12, r=0.05, coll=None):
    p = [K.cyl("cd_wax", r, h, (0, 0, h / 2), mat="candle_wax", seg=24, coll=coll),
         K.cyl("cd_wick", 0.003, 0.012, (0, 0, h + 0.006), mat="black_paint", seg=6,
               coll=coll)]
    return _fur("candle", p, coll)


def plant(kind="fig", scale=1.0, coll=None):
    """Fiddle-leaf fig / snake plant / monstera in a terracotta pot."""
    import random
    p = []
    ph = 0.40 * scale
    pr = 0.19 * scale
    p.append(K.lathe("pl_pot", [(0, 0), (pr * 0.78, 0), (pr, ph * 0.92), (pr * 1.03, ph),
                                (pr * 0.92, ph), (pr * 0.88, ph - 0.025),
                                (pr * 0.64, 0.03), (0, 0.03)], (0, 0, 0),
                     mat="terracotta", seg=32, coll=coll))
    p.append(K.cyl("pl_soil", pr * 0.86, 0.02, (0, 0, ph - 0.012), mat="soil", seg=28,
                   coll=coll))
    rnd = random.Random(hash(kind) % 9999 + int(scale * 100))

    if kind == "snake":
        for i in range(11):
            a = 2 * math.pi * i / 11 + rnd.uniform(-0.2, 0.2)
            hgt = rnd.uniform(0.55, 1.05) * scale
            lf = K.leaf(f"sn_leaf", L=hgt, W=0.075 * scale, mat="leaf", curl=0.06,
                        fold=0.25, coll=coll, seg=8, width_pts=3)
            lf.location = (0.055 * math.cos(a), 0.055 * math.sin(a), ph - 0.02)
            lf.rotation_euler = (rnd.uniform(-0.16, 0.16), rnd.uniform(-0.16, 0.16), a)
            p.append(lf)
    else:
        big = kind == "monstera"
        trunk_h = (0.95 if big else 1.15) * scale
        lw = (0.34 if big else 0.26) * scale
        ll = (0.42 if big else 0.36) * scale
        # two or three stems fanning out
        stems = 3
        for si in range(stems):
            a0 = 2 * math.pi * si / stems + rnd.uniform(-0.3, 0.3)
            lean = rnd.uniform(0.10, 0.26) * scale
            top = (lean * math.cos(a0), lean * math.sin(a0), ph + trunk_h)
            p.append(K.rod(f"pl_stem{si}", (0, 0, ph - 0.04), top,
                           0.020 * scale, "bark", seg=8, coll=coll))
            nl = 9 if not big else 8
            for i in range(nl):
                t = i / max(nl - 1, 1)
                z = ph + trunk_h * (0.22 + 0.78 * t)
                frac = t
                x = lean * frac * math.cos(a0)
                y = lean * frac * math.sin(a0)
                a = a0 + (i * 2.39996)
                lf = K.leaf(f"pl_leaf{si}_{i}", L=ll * rnd.uniform(0.75, 1.15),
                            W=lw * rnd.uniform(0.8, 1.1), mat="leaf",
                            curl=rnd.uniform(0.12, 0.30), fold=0.22, coll=coll)
                lf.location = (x, y, z - 0.02)
                lf.rotation_euler = (math.radians(rnd.uniform(55, 78)),
                                     rnd.uniform(-0.2, 0.2), a)
                p.append(lf)
    return _fur("plant", p, coll)


def tree(h=6.0, r=2.2, coll=None, seed=1):
    """Simple broadleaf tree: tapered trunk, forked branches, dense crown."""
    import random
    rnd = random.Random(seed)
    p = [K.cyl("tr_trunk", 0.10 * r, h * 0.62, (0, 0, h * 0.31), mat="bark",
               seg=12, r2=0.05 * r, coll=coll)]
    for i in range(5):
        a = 2 * math.pi * i / 5 + rnd.uniform(-0.3, 0.3)
        z0 = h * rnd.uniform(0.42, 0.60)
        rad = r * rnd.uniform(0.35, 0.58)
        tip = (rad * math.cos(a), rad * math.sin(a), z0 + r * rnd.uniform(0.35, 0.6))
        p.append(K.rod("tr_branch", (0, 0, z0), tip, 0.025 * r, "bark", seg=6, coll=coll))
    n = 16
    for i in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        rr = r * rnd.uniform(0.0, 0.95)
        zz = h * 0.62 + rnd.uniform(-0.5, 0.55) * r
        p.append(K.sphere(f"tr_leaf{i}", r * rnd.uniform(0.30, 0.46),
                          (rr * math.cos(a), rr * math.sin(a), zz),
                          "leaf_dark" if i % 3 else "leaf", seg=12, rings=8, coll=coll,
                          scale=(1.0, 1.0, rnd.uniform(0.75, 1.0))))
    return _fur(f"tree_{seed}", p, coll)


def wall_light(coll=None):
    p = [K.box("wl_body", (0.10, 0.10, 0.26), (0, 0, 0), mat="brass", bevel=0.01, coll=coll),
         K.box("wl_glow", (0.035, 0.035, 0.20), (0, -0.05, 0), mat=warm((1.0, 0.87, 0.68), 6.0),
               bevel=0.006, coll=coll)]
    return _fur("wall_light", p, coll)


def warm(rgb, strength):  # re-export for convenience
    return mats.warm(rgb, strength)
