"""Parametric automotive body builder: lower body, greenhouse, arches, wheels, proportions.

A car is not a stack of primitives and it is not one lofted blob either. Production
shapes are built in two parts:

  * **lower body** - slab sides with a shoulder, a crowned hood/deck that is flat in
    profile. Everything below the beltline.
  * **greenhouse** - a second loft sitting on that deck, with tumblehome (the roof is
    narrower than the beltline). Glass on the sides, paint on the roof.

Building them separately is what makes the silhouette read as a car instead of a loaf,
and it makes the glass/paint split fall out for free.

Sections run along +Y (nose forward), width along X, height along Z. Only half a section
is described; the other half is mirrored in the vertex table, so the mesh is closed and
there is no mirror-modifier seam down the nose.

This is a *package-accurate blockout*: measured proportions, correct stance, real
wheelbase/overhang relationships. Surface language, panel breaks and lighting detail come
from ``modeling-detail`` afterwards. Do not present it as a finished car.

Usage:
  python tools/bpy_run.py <this> -- --preset sedan --render --out /tmp/car.png
  python tools/bpy_run.py <this> -- --preset suv --length 4800 --save /tmp/car.blend
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402

# Real package figures, millimetres. Ranges a designer would use as reference data.
PRESETS = {
    "sedan": dict(length=4900, width=1860, height=1445, wheelbase=2870, track=1580,
                  tyre_d=680, roof=0.30, nose_drop=0.14),
    "suv":   dict(length=4800, width=1930, height=1760, wheelbase=2820, track=1640,
                  tyre_d=760, roof=0.34, nose_drop=0.08),
    "coupe": dict(length=4550, width=1880, height=1360, wheelbase=2700, track=1600,
                  tyre_d=700, roof=0.26, nose_drop=0.18),
    "hatch": dict(length=4050, width=1770, height=1460, wheelbase=2580, track=1540,
                  tyre_d=640, roof=0.32, nose_drop=0.12),
}

# t = 0 tail, t = 1 nose.
#   half-width of the body as a fraction of W/2
#   deck height (hood / boot / belt plane) as a fraction of H
_STATIONS = [
    (0.000, 0.86, 0.610),
    (0.020, 0.90, 0.630),
    (0.070, 0.96, 0.660),
    (0.150, 1.000, 0.675),
    (0.240, 1.000, 0.685),
    (0.330, 1.000, 0.695),
    (0.420, 1.000, 0.705),
    (0.500, 1.000, 0.710),
    (0.580, 1.000, 0.710),
    (0.660, 1.000, 0.705),
    (0.740, 0.995, 0.695),
    (0.840, 0.965, 0.680),
    (0.930, 0.905, 0.640),
    (0.980, 0.880, 0.600),
    (1.000, 0.820, 0.585),
]


def _interp(t, col):
    for i in range(len(_STATIONS) - 1):
        t0, t1 = _STATIONS[i][0], _STATIONS[i + 1][0]
        if t0 <= t <= t1:
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return _STATIONS[i][col] + (_STATIONS[i + 1][col] - _STATIONS[i][col]) * f
    return _STATIONS[-1][col]


def _drop(t, nose_drop, H):
    """Smooth, monotone droop of the whole section at the extreme nose/tail."""
    if t > 0.78:
        e = (t - 0.78) / 0.22
    elif t < 0.16:
        e = (0.16 - t) / 0.16
    else:
        return 0.0
    return nose_drop * H * e * e


def _lower_section(t, H, W, nose_drop):
    """Half section of the lower body: floor -> shoulder -> crowned deck."""
    deck_raw = _interp(t, 2) * H
    deck = deck_raw - _drop(t, nose_drop, H)
    hw = _interp(t, 1) * (W / 2.0)
    # The rocker sits at a fixed ride height: only the deck droops at the ends. Letting
    # the sill follow the deck makes the bumpers dive under the wheels.
    sill = max(0.185 * H, deck_raw - 0.44 * H)
    deck = max(deck, sill + 0.20 * H)
    return [
        (0.00 * hw, sill),                   # floor centre
        (0.60 * hw, sill),
        (0.90 * hw, sill + 0.22 * (deck - sill)),
        (1.00 * hw, sill + 0.62 * (deck - sill)),   # widest, low shoulder
        (0.995 * hw, deck - 0.055 * (deck - sill)),  # beltline
        (0.93 * hw, deck),
        (0.62 * hw, deck + 0.022 * H),       # crown
        (0.00, deck + 0.030 * H),
    ]


def _greenhouse_section(t, t0, t1, H, W, nose_drop):
    """Half section of the cabin: beltline -> tumblehome -> roof centre."""
    s = (t - t0) / max(t1 - t0, 1e-6)
    deck = _interp(t, 2) * H - _drop(t, nose_drop, H)
    eyebrow = (H * 0.985) - deck
    shape = min(1.0, math.sin(math.pi * min(max(s, 0.0), 1.0)) ** 0.42)
    rh = max(eyebrow * shape, 0.004 * H)
    hw = _interp(t, 1) * (W / 2.0)
    return [
        (0.965 * hw, deck),
        (0.930 * hw, deck + 0.30 * rh),
        (0.845 * hw, deck + 0.68 * rh),
        (0.700 * hw, deck + 0.94 * rh),
        (0.380 * hw, deck + rh),
        (0.00, deck + rh),
    ]


def _loft(name, sections, ts, cap_ends=True):
    """Build a closed half-lofted shell from per-station half sections."""
    bm = bmesh.new()
    rings = []
    for t, half in zip(ts, sections):
        y = (t - 0.5) * 1.0
        right = [bm.verts.new((x, y, z)) for x, z in half]
        left = [bm.verts.new((-x, y, z)) for x, z in reversed(half[:-1])]
        rings.append(right + left)
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for j in range(n):
            k = (j + 1) % n
            try:
                bm.faces.new((a[j], a[k], b[k], b[j]))
            except ValueError:
                pass
    if cap_ends:
        for ring in (rings[0], rings[-1]):
            try:
                bm.faces.new(ring)
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    sc.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def _stations_for(t0, t1, extra=()):
    ts = sorted({round(t0 + (t1 - t0) * i / 24.0, 4) for i in range(25)} | {round(t, 4) for t in extra})
    return [t for t in ts if t0 - 1e-9 <= t <= t1 + 1e-9]


def build_body(L, W, H, nose_drop, name="CarBody"):
    """Lower body: slab sides, crowned hood and deck, wheel arches cut later."""
    ts = [t for t, _, _ in _STATIONS]
    ts += [round(t0 + (1.0 - t0) * 0.5, 4) for t0 in ()]
    ts = sorted(set(ts) | {0.045, 0.11, 0.20, 0.285, 0.375, 0.455, 0.54, 0.62, 0.70,
                           0.79, 0.885, 0.955})
    secs = []
    for t, _, _ in [(t, 0, 0) for t in ts]:
        half = _lower_section(t, H, W, nose_drop)
        secs.append([(x, (t - 0.5) * L, z) for x, z in half])
    return _loft_y(name, secs)


def _loft_y(name, sections):
    bm = bmesh.new()
    rings = []
    for sec in sections:
        right = [bm.verts.new((x, y, z)) for x, y, z in sec]
        left = [bm.verts.new((-x, y, z)) for x, y, z in reversed(sec[1:-1])]
        rings.append(right + left)
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for j in range(n):
            k = (j + 1) % n
            try:
                bm.faces.new((a[j], a[k], b[k], b[j]))
            except ValueError:
                pass
    for ring in (rings[0], rings[-1]):
        try:
            bm.faces.new(ring)
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    sc.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def build_greenhouse(L, W, H, nose_drop, cabin=(0.315, 0.715), name="Greenhouse"):
    """Cabin loft with tumblehome, spanning ``cabin`` in normalised length."""
    t0, t1 = cabin
    ts = _stations_for(t0, t1)
    secs = []
    for t in ts:
        half = _greenhouse_section(t, t0, t1, H, W, nose_drop)
        secs.append([(x, (t - 0.5) * L, z) for x, z in half])
    return _loft_y(name, secs)


def cut_wheel_arches(body, W, wheelbase, tyre_d):
    """Boolean the wheel arches into the flanks (the shell must already be subdivided)."""
    r = tyre_d / 2.0 * 1.12
    for xs in (-1, 1):
        for y in (-wheelbase / 2.0, wheelbase / 2.0):
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=40, radius=r, depth=W * 0.46,
                location=(xs * (W * 0.30), y, tyre_d / 2.0),
                rotation=(0.0, math.pi / 2.0, 0.0))
            cutter = bpy.context.object
            cutter.name = f"ArchCut_{xs}_{int(y)}"
            boo = body.modifiers.new(cutter.name, "BOOLEAN")
            boo.operation = "DIFFERENCE"
            boo.solver = "EXACT"
            boo.object = cutter
            bpy.context.view_layer.objects.active = body
            bpy.ops.object.select_all(action="DESELECT")
            body.select_set(True)
            try:
                bpy.ops.object.modifier_apply(modifier=boo.name)
            except RuntimeError:
                body.modifiers.remove(boo)
            bpy.data.objects.remove(cutter, do_unlink=True)
    for p in body.data.polygons:
        p.use_smooth = True
    return body


def _simple_mat(name, color, metallic=0.0, rough=0.5, transmission=0.0):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = sc.principled(mat)
    sc.set_input(b, "Base Color", (*color, 1.0))
    sc.set_input(b, "Metallic", metallic)
    sc.set_input(b, "Roughness", rough)
    if transmission:
        sc.set_input(b, "Transmission Weight", transmission)
        sc.set_input(b, "IOR", 1.45)
    return mat


def glass_paint_split(greenhouse, glass, paint):
    """Glass on the flanks and screens, paint on the roof - judged from face normals."""
    me = greenhouse.data
    me.materials.clear()
    me.materials.append(paint)   # index 0
    me.materials.append(glass)   # index 1
    for p in me.polygons:
        p.material_index = 0 if p.normal.z > 0.55 else 1
    return greenhouse


def build_wheels(W, wheelbase, track, tyre_d, tyre_w=None):
    """Four wheels: tyre + rim, axis along X, sitting on z = 0."""
    r = tyre_d / 2.0
    w = tyre_w or tyre_d * 0.34
    tyre_mat = _simple_mat("Tyre", (0.030, 0.030, 0.033), 0.0, 0.78)
    rim_mat = _simple_mat("Rim", (0.62, 0.63, 0.65), 1.0, 0.22)
    wheels = []
    for i, x in enumerate((-track / 2.0, track / 2.0)):
        for j, y in enumerate((-wheelbase / 2.0, wheelbase / 2.0)):
            for name, rad, dep, mat in ((f"Tyre_{i}{j}", r, w, tyre_mat),
                                        (f"Rim_{i}{j}", r * 0.64, w * 1.02, rim_mat)):
                bpy.ops.mesh.primitive_cylinder_add(
                    vertices=48, radius=rad, depth=dep, location=(x, y, r),
                    rotation=(0.0, math.pi / 2.0, 0.0))
                ob = bpy.context.object
                ob.name = name
                ob.data.materials.append(mat)
                # a smooth-shaded cylinder cap reads as a sphere: hold the caps flat
                bpy.context.view_layer.objects.active = ob
                ob.select_set(True)
                try:
                    bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
                except Exception:
                    for p in ob.data.polygons:
                        p.use_smooth = True
                ob.select_set(False)
                wheels.append(ob)
    return wheels


def proportion_check(L, W, H, wheelbase, tyre_d, roof):
    """Package ratios, with the ranges production cars actually sit in."""
    checks = [
        ("wheelbase/length", wheelbase / L, 0.55, 0.63,
         "short wheelbases give a toy-like stance, long ones read as a barge"),
        ("wheel_diameter/height", tyre_d / H, 0.40, 0.60,
         "under 0.40 looks like the body is dragging, over 0.60 is an off-roader"),
        ("height/width", H / W, 0.70, 0.95,
         "sets the stance: below 0.70 is a supercar, above 0.95 an MPV"),
        ("greenhouse/height", roof, 0.22, 0.40,
         "a modern car spends 22-40 % of its height on the glasshouse"),
        ("front overhang/length", (L - wheelbase) / 2.0 / L, 0.13, 0.22,
         "overhangs beyond 22 % per side look like a limo"),
    ]
    rows, ok = [], True
    for name, val, lo, hi, note in checks:
        good = lo <= val <= hi
        ok = ok and good
        rows.append({"check": name, "value": round(val, 3), "range": [lo, hi],
                     "ok": good, "note": None if good else note})
    return ok, rows


def _three_point(center, radius):
    """Key/fill/rim scaled to the subject (mm-scale scenes need real wattage)."""
    specs = [((-1.0, -1.2, 0.9), 1.0, 1.0), ((1.1, -0.7, 0.45), 0.40, 1.0),
             ((0.2, 1.3, 0.85), 0.65, 0.8)]
    for i, (d, power, size) in enumerate(specs):
        data = bpy.data.lights.new(f"CarKey{i}", "AREA")
        data.energy = power * 260.0 * max(radius, 0.5) ** 2
        data.size = radius * size
        ob = bpy.data.objects.new(f"CarKey{i}", data)
        sc.link(ob)
        pos = Vector(center) + Vector(d) * radius * 2.6
        ob.location = pos
        ob.rotation_euler = (Vector(center) - pos).to_track_quat("-Z", "Y").to_euler()
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.22, 0.24, 0.28, 1.0)
        bg.inputs[1].default_value = 0.65


def run(preset="sedan", length=None, width=None, height=None, wheelbase=None, track=None,
        tyre=None, roof=None, nose_drop=None, subsurf=2, apply=False, wheels=True,
        save=None, render=False, out="/tmp/car.png", res=640, samples=24, **_):
    sc.object_mode()
    p = dict(PRESETS[preset])
    L = length or p["length"]
    W = width or p["width"]
    H = height or p["height"]
    WB = wheelbase or p["wheelbase"]
    TR = track or p["track"]
    TD = tyre or p["tyre_d"]
    RH = p["roof"] if roof is None else roof
    ND = p["nose_drop"] if nose_drop is None else nose_drop

    paint = _simple_mat("CarPaint", (0.42, 0.035, 0.03), 0.7, 0.25)
    glass = _simple_mat("CarGlass", (0.02, 0.025, 0.03), 0.0, 0.04, transmission=1.0)

    body = build_body(L, W, H, ND)
    body.data.materials.append(paint)
    sub = body.modifiers.new("Subdivision", "SUBSURF")
    sub.levels = subsurf
    sub.render_levels = subsurf
    if wheels:
        bpy.context.view_layer.objects.active = body
        bpy.ops.object.select_all(action="DESELECT")
        body.select_set(True)
        bpy.ops.object.modifier_apply(modifier=sub.name)
        cut_wheel_arches(body, W, WB, TD)
    elif apply:
        bpy.context.view_layer.objects.active = body
        bpy.ops.object.select_all(action="DESELECT")
        body.select_set(True)
        bpy.ops.object.modifier_apply(modifier=sub.name)

    cabin = build_greenhouse(L, W, H, ND)
    glass_paint_split(cabin, glass, paint)
    gsub = cabin.modifiers.new("Subdivision", "SUBSURF")
    gsub.levels = subsurf
    gsub.render_levels = subsurf

    wl = build_wheels(W, WB, TR, TD) if wheels else []

    ok, rows = proportion_check(L, W, H, WB, TD, RH)
    dims = sc.dims(body)
    tris = sc.tri_count(body) + sc.tri_count(cabin) + sum(sc.tri_count(w) for w in wl)
    result = {
        "ok": True, "preset": preset, "body": body.name, "greenhouse": cabin.name,
        "spec_mm": {"length": L, "width": W, "height": H, "wheelbase": WB, "track": TR,
                    "tyre_d": TD},
        "body_dims_mm": [round(d, 1) for d in dims],
        "tris": tris, "objects": len(wl) + 2, "subsurf": subsurf,
        "proportion_ok": ok, "proportions": rows,
    }
    if save:
        bpy.ops.wm.save_as_mainfile(filepath=save)
        result["saved"] = save
    if render:
        lo, hi = sc.bounds([body] + wl)
        _three_point((lo + hi) / 2, max((hi - lo).length / 2, 1.0))
        ground = _simple_mat("Asphalt", (0.13, 0.13, 0.14), 0.0, 0.6)
        bpy.ops.mesh.primitive_plane_add(size=max(L, W) * 6, location=(0, 0, 0))
        bpy.context.object.name = "Ground"
        bpy.context.object.data.materials.append(ground)
        cam = sc.frame_objects([body] + wl, azimuth_deg=-58.0, elevation_deg=9.0,
                               lens=62.0, margin=1.18, name="cam_car",
                               aspect=res / (res * 0.5625))
        sc.look_transform(bpy.context.scene)
        sc.render(out, res=(res, int(res * 0.5625)), samples=samples, cam=cam)
        result["render"] = out
    return result


if __name__ == "__main__":
    ap = sc.parser(__doc__)
    sc.add_common(ap, save=True)
    ap.add_argument("--preset", default="sedan", choices=list(PRESETS))
    ap.add_argument("--length", type=float, default=None)
    ap.add_argument("--width", type=float, default=None)
    ap.add_argument("--height", type=float, default=None)
    ap.add_argument("--wheelbase", type=float, default=None)
    ap.add_argument("--track", type=float, default=None)
    ap.add_argument("--tyre", type=float, default=None)
    ap.add_argument("--roof", type=float, default=None)
    ap.add_argument("--nose-drop", dest="nose_drop", type=float, default=None)
    ap.add_argument("--subsurf", type=int, default=2)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--no-wheels", dest="wheels", action="store_false")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--out", default="/tmp/car.png")
    ap.add_argument("--res", type=int, default=640)
    ap.add_argument("--samples", type=int, default=24)
    sc.cli(run, ap)
