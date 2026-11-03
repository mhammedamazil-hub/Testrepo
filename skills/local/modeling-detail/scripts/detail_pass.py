"""Hard-surface detail pass: panel grooves, bevel/weighted-normal stack, mesh audit.

The gap between "modelled shape" and "finished part" is almost never more modelling. It
is detail discipline:

  * **panel grooves** cut as shallow boolean slots (door shut lines, hood cuts) instead of
    drawn-on decals, so they catch real light and survive any camera angle;
  * a **bevel -> weighted normal** stack that makes edges catch a highlight instead of
    reading as a hard CG crease;
  * an **audit** that measures what actually went wrong: non-manifold edges, flipped
    normals, zero-area faces, loose verts, n-gons on curved surfaces, sharp shading
    islands.

Every run returns the audit before and after, so "it ran" and "the mesh is sound" are two
separate statements.

Usage:
  # inspect only
  python tools/bpy_run.py <this> -- --objects CarBody --audit-only
  # door shut lines + a consistent bevel, applied to a copy
  python tools/bpy_run.py <this> --blend car.blend -- --objects CarBody \
      --grooves 1.2 -1.2 --gap 6 --bevel 3 --weighted-normal --apply
"""
import math
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402


def audit_mesh(ob):
    """Measure mesh health. Returns a dict; `problems` lists only real failures."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    non_manifold = [e for e in bm.edges if not e.is_manifold]
    loose_verts = [v for v in bm.verts if not v.link_edges]
    loose_edges = [e for e in bm.edges if not e.link_faces]
    zero_area = [f for f in bm.faces if f.calc_area() < 1e-12]
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    curved_ngons = []
    for f in ngons:
        # an n-gon is only a risk when its own normal disagrees with its neighbours
        for e in f.edges:
            for nf in e.link_faces:
                if nf is f:
                    continue
                if f.normal.angle(nf.normal, 0.0) > math.radians(12):
                    curved_ngons.append(f)
                    break
            else:
                continue
            break
    interior = [e for e in bm.edges if len(e.link_faces) == 2]
    sharp = [e for e in interior if e.calc_face_angle(0.0) > math.radians(50)]
    flipped = sum(1 for f in bm.faces if f.normal.length < 1e-9)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    vol = bm.calc_volume(signed=True) if bm.faces else 0.0
    bm.free()

    problems = []
    if non_manifold:
        problems.append(f"{len(non_manifold)} non-manifold edge(s)")
    if loose_verts or loose_edges:
        problems.append(f"{len(loose_verts)} loose vert(s), {len(loose_edges)} loose edge(s)")
    if zero_area:
        problems.append(f"{len(zero_area)} zero-area face(s)")
    if curved_ngons:
        problems.append(f"{len(curved_ngons)} n-gon(s) on curved surfaces")
    if vol < 0:
        problems.append("normals point inward (negative volume)")
    return {
        "object": ob.name, "verts": len(me.vertices), "faces": len(me.polygons),
        "tris": tris, "non_manifold_edges": len(non_manifold),
        "loose_verts": len(loose_verts), "zero_area_faces": len(zero_area),
        "ngons": len(ngons), "curved_ngons": len(curved_ngons),
        "sharp_edges": len(sharp), "volume": round(vol, 3),
        "problems": problems, "ok": not problems,
    }


def repair_mesh(ob, merge=1e-5, fix_ngons=True):
    """Merge doubles, drop degenerate geometry, re-orient normals, triangulate n-gons
    that sit on curved surfaces (boolean output is the usual source of those)."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    before = {"verts": len(bm.verts), "faces": len(bm.faces)}
    changed = []
    if merge:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
        changed.append(f"merge {merge}")
    degenerate = [f for f in bm.faces if f.calc_area() < 1e-12]
    if degenerate:
        bmesh.ops.delete(bm, geom=degenerate, context="FACES_ONLY")
        changed.append(f"deleted {len(degenerate)} zero-area face(s)")
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=merge)
    bad = []
    if fix_ngons:
        for f in bm.faces:
            if len(f.verts) <= 4:
                continue
            for e in f.edges:
                if any(nf is not f and f.normal.angle(nf.normal, 0.0) > math.radians(12)
                       for nf in e.link_faces):
                    bad.append(f)
                    break
        if bad:
            bmesh.ops.triangulate(bm, faces=bad, quad_method="BEAUTY",
                                  ngon_method="BEAUTY")
            changed.append(f"triangulated {len(bad)} curved n-gon(s)")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return {"before": before, "changed": changed}


def cut_grooves(ob, ys, gap, z_top=None):
    """Cut vertical panel slots through the shell at the given world Y values.

    Two things that measurably do not work, both found by re-measuring the mesh instead of
    trusting the operator's return value:

    * a shallow boolean box parked at the silhouette - the flank wanders in X with height,
      so a fixed offset sits outside the surface at some heights and misses entirely;
    * one boolean per cutter - the second pass can leave bridging faces across the first
      gap (44 of them in the test car).

    So: all slots are built as one cutter and cut with a single boolean.
    """
    lo, hi = sc.aabb(ob)
    z0 = lo.z - 1.0
    z1 = (hi.z + 1.0) if z_top is None else z_top
    coll = bpy.data.collections.get("GrooveCutters") or bpy.data.collections.new("GrooveCutters")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    for y in ys:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        cutter = bpy.context.object
        cutter.name = f"Groove_{int(round(y * 1000))}"
        cutter.scale = (hi.x - lo.x + 40.0, gap / 2.0, (z1 - z0) / 2.0)
        cutter.location = (0.0, y, (z0 + z1) / 2.0)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        for c in list(cutter.users_collection):
            c.objects.unlink(cutter)
        coll.objects.link(cutter)
    boo = ob.modifiers.new("Grooves", "BOOLEAN")
    boo.operation = "DIFFERENCE"
    boo.solver = "EXACT"
    boo.operand_type = "COLLECTION"
    boo.collection = coll
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    ok = True
    try:
        bpy.ops.object.modifier_apply(modifier=boo.name)
    except RuntimeError as exc:
        ob.modifiers.remove(boo)
        ok = False
        sc.emit({"warn": f"groove boolean failed: {exc}"})
    for o in list(coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(coll)
    return [{"y": y, "gap": gap} for y in ys] if ok else []


def add_detail_stack(ob, bevel=0.0, segments=2, subsurf=0, weighted_normal=True,
                     smooth_angle=40.0):
    """Bevel + shade-smooth-by-angle + weighted normal, in the artist's order."""
    added = []
    if bevel > 0:
        b = ob.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = segments
        b.limit_method = "ANGLE"
        b.angle_limit = math.radians(30)
        b.use_clamp_overlap = True
        b.harden_normals = True
        b.miter_outer = "MITER_ARC"
        added.append("Bevel")
    if subsurf > 0:
        s = ob.modifiers.new("Subdivision", "SUBSURF")
        s.levels = subsurf
        s.render_levels = subsurf
        added.append("Subdivision")
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(smooth_angle))
        added.append(f"shade_auto_smooth({smooth_angle:.0f})")
    except Exception as exc:  # pragma: no cover - version specific
        sc.emit({"warn": f"shade_auto_smooth unavailable: {exc}"})
    if weighted_normal:
        w = ob.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
        w.mode = "FACE_AREA"
        w.keep_sharp = True
        w.weight = 50
        added.append("WeightedNormal")
    return added


def run(objects=None, audit_only=False, grooves=None, gap=6.0, bevel=3.0,
        segments=2, subsurf=0, weighted_normal=True, smooth_angle=40.0, apply=False,
        fix=False, save=None, **_):
    sc.object_mode()
    objs = sc.objects(objects)
    if not objs:
        raise ValueError("no mesh objects (--objects Name)")
    rows, grooves_made, stacks, repairs = [], {}, {}, {}
    for ob in objs:
        before = audit_mesh(ob)
        if not audit_only:
            made = []
            repairs[ob.name] = repair_mesh(ob) if fix else None
            if grooves:
                made = cut_grooves(ob, grooves, gap)
            stacks[ob.name] = add_detail_stack(ob, bevel=bevel, segments=segments,
                                              subsurf=subsurf,
                                              weighted_normal=weighted_normal,
                                              smooth_angle=smooth_angle)
            if apply:
                bpy.context.view_layer.objects.active = ob
                bpy.ops.object.select_all(action="DESELECT")
                ob.select_set(True)
                for name in list(stacks[ob.name])[::-1]:
                    m = ob.modifiers.get(name)
                    if m:
                        try:
                            bpy.ops.object.modifier_apply(modifier=m.name)
                        except RuntimeError as exc:
                            sc.emit({"warn": f"{name}: {exc}"})
            grooves_made[ob.name] = made
        rows.append({"before": before,
                     "after": audit_mesh(ob) if not audit_only else before})
        stacks.setdefault(ob.name, [])
    ok = all(r["after"]["ok"] for r in rows)
    result = {
        "ok": ok, "audit_only": audit_only, "objects": [o.name for o in objs],
        "audit": rows, "grooves": grooves_made, "stack": stacks, "repairs": repairs,
        "verdict": "MESH SOUND" if ok else "MESH HAS PROBLEMS",
    }
    if save:
        bpy.ops.wm.save_as_mainfile(filepath=save)
        result["saved"] = save
    return result


if __name__ == "__main__":
    ap = sc.parser(__doc__)
    sc.add_common(ap, save=True)
    ap.add_argument("--audit-only", dest="audit_only", action="store_true")
    ap.add_argument("--grooves", nargs="*", type=float, default=None,
                    help="world-space Y positions for panel slots")
    ap.add_argument("--gap", type=float, default=6.0)
    ap.add_argument("--bevel", type=float, default=3.0)
    ap.add_argument("--segments", type=int, default=2)
    ap.add_argument("--subsurf", type=int, default=0)
    ap.add_argument("--no-weighted-normal", dest="weighted_normal", action="store_false")
    ap.add_argument("--smooth-angle", dest="smooth_angle", type=float, default=40.0)
    ap.add_argument("--fix", action="store_true",
                    help="merge doubles, drop degenerates, triangulate curved n-gons")
    ap.add_argument("--apply", action="store_true")
    sc.cli(run, ap)
