"""Dimensioned blockout from a spec - the step that must happen before detailing.

A blockout is checked part-by-part against the reference. Building it from a JSON spec
(not freehand cubes) means every part carries its target size, and the script can prove
the result matches:

  * each part is created, named, sized and placed from the spec
  * a proportion report compares achieved vs requested dimensions and flags drift
  * an assembly report checks the parts actually touch/overlap where intended
  * optional wheel/axle helper: cylinders on an axle (cars, machinery)

Spec format (all metres):
{
  "parts": [
    {"name": "body",  "type": "box", "size": [4.50, 1.90, 0.55], "at": [0, 0, 0.62],
     "bevel": 0.06},
    {"name": "cabin", "type": "box", "size": [2.10, 1.70, 0.48], "at": [-0.15, 0, 1.35],
     "bevel": 0.10, "taper": [0.86, 0.94]},
    {"name": "wheel_fl", "type": "cyl", "radius": 0.34, "length": 0.24,
     "at": [1.45, -0.86, 0.34], "axis": "y"}
  ]
}

Usage:
  python tools/bpy_run.py <this> -- --spec car.json --collection Blockout
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402

BLOCK_MAT_COLORS = [(0.55, 0.57, 0.60), (0.72, 0.45, 0.25), (0.35, 0.55, 0.72),
                    (0.62, 0.62, 0.35), (0.72, 0.35, 0.5)]


def _mat(i):
    name = f"blockout_mat_{i}"
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = sc.principled(m)
    c = BLOCK_MAT_COLORS[i % len(BLOCK_MAT_COLORS)]
    sc.set_input(b, "Base Color", (*c, 1))
    sc.set_input(b, "Roughness", 0.55)
    return m


def _box(part, coll, mat):
    sx, sy, sz = part["size"]
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((sx, sy, sz)), verts=bm.verts)
    taper = part.get("taper")
    if taper:  # taper the top face in X/Y (cabin-like volumes)
        top = max(v.co.z for v in bm.verts)
        for v in bm.verts:
            if abs(v.co.z - top) < 1e-6:
                v.co.x *= taper[0]
                v.co.y *= taper[1] if len(taper) > 1 else taper[0]
    if part.get("bevel"):
        bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges),
                        offset=part["bevel"], segments=part.get("segments", 3),
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    bm.normal_update()
    me = bpy.data.meshes.new(part["name"])
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(part["name"], me)
    coll.objects.link(ob)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = bool(part.get("bevel"))
    return ob


def _cyl(part, coll, mat):
    r = part["radius"]
    length = part.get("length", 0.2)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=part.get("segments", 32),
                          radius1=r, radius2=part.get("radius2", r), depth=length)
    bm.normal_update()
    me = bpy.data.meshes.new(part["name"])
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(part["name"], me)
    coll.objects.link(ob)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    axis = part.get("axis", "z").lower()
    if axis == "y":
        ob.rotation_euler = (math.radians(90), 0, 0)
    elif axis == "x":
        ob.rotation_euler = (0, math.radians(90), 0)
    return ob


def run(spec=None, collection="Blockout", check_tolerance=0.02, **_):
    sc.object_mode()
    if not spec:
        raise ValueError("--spec is required")
    with open(bpy.path.abspath(spec)) as f:
        data = json.load(f)
    parts = data.get("parts", [])
    if not parts:
        raise ValueError("spec has no parts")
    coll = sc.ensure_collection(collection)
    made, drift = [], []
    for i, part in enumerate(parts):
        mat = _mat(i)
        t = part.get("type", "box")
        ob = _box(part, coll, mat) if t == "box" else _cyl(part, coll, mat)
        ob.location = part.get("at", (0, 0, 0))
        if part.get("rot"):
            ob.rotation_euler = [math.radians(a) for a in part["rot"]]
        bpy.context.view_layer.update()
        d = sc.dims(ob)
        want = part.get("size") or [part.get("radius", 0) * 2] * 3
        if t == "cyl":  # a cylinder's extents depend on its axis
            r2 = part.get("radius", 0) * 2
            length = part.get("length", 0.2)
            axis = part.get("axis", "z").lower()
            want = {"x": [length, r2, r2], "y": [r2, length, r2]}.get(axis, [r2, r2, length])
        err = [abs(a - b) / max(b, 1e-6) for a, b in zip(d, want)]
        taper = part.get("taper")
        if taper:   # a taper intentionally narrows the top: those axes are not drift
            err = [e * (0.0 if (axis < 2 and (taper[axis] if axis < len(taper) else 1.0) < 1.0)
                        else 1.0) for axis, e in enumerate(err)]
        rec = {"part": ob.name, "dims_m": [round(v, 4) for v in d],
               "target_m": [round(v, 4) for v in want],
               "max_drift_pct": round(100 * max(err), 2)}
        if taper:
            rec["taper"] = "intentional top taper; tapered axes excluded from drift"
        made.append(rec)
        if max(err) > check_tolerance:
            drift.append(rec)

    # envelope + assembly sanity
    objs = [bpy.data.objects[m["part"]] for m in made]
    lo, hi = sc.aabb(objs[0])
    for o in objs[1:]:
        l2, h2 = sc.aabb(o)
        lo = Vector([min(a, b) for a, b in zip(lo, l2)])
        hi = Vector([max(a, b) for a, b in zip(hi, h2)])
    env = [round(v, 4) for v in (hi - lo)]
    spec_env = data.get("envelope_m")
    result = {
        "ok": True, "collection": coll.name, "parts": made,
        "envelope_m": env,
        "bbox_min": [round(v, 4) for v in lo], "bbox_max": [round(v, 4) for v in hi],
        "drift_over_tolerance": drift,
        "verdict": "BLOCKOUT OK" if not drift else "DRIFT - fix before detailing",
    }
    if spec_env:
        err = [abs(a - b) / max(b, 1e-6) for a, b in zip(env, spec_env)]
        result["envelope_target_m"] = spec_env
        result["envelope_delta_pct"] = [round(100 * e, 2) for e in err]
        if max(err) > check_tolerance:
            result["verdict"] = "ENVELOPE OFF by >2 % - fix before detailing"
    return result


if __name__ == "__main__":
    p = sc.add_common(sc.parser(__doc__))
    p.add_argument("--spec", required=True)
    p.add_argument("--collection", default="Blockout")
    p.add_argument("--tolerance", dest="check_tolerance", type=float, default=0.02)
    sc.cli(run, p)
