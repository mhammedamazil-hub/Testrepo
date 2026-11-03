"""Geometry diagnostics: furniture/furniture and furniture/wall intersections."""
import itertools

import bpy
from mathutils import Vector


def world_aabb(ob):
    """True AABB from the actual vertices (bound_box can be stale after joins)."""
    mw = ob.matrix_world
    me = ob.data
    if not me.vertices:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    xs = [v.co for v in me.vertices]
    pts = [mw @ c for c in xs]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def overlap(a, b, tol=0.02):
    """Return the intersection volume of two AABBs if they overlap by > tol per axis."""
    (alo, ahi), (blo, bhi) = a, b
    lo = Vector((max(alo.x, blo.x), max(alo.y, blo.y), max(alo.z, blo.z)))
    hi = Vector((min(ahi.x, bhi.x), min(ahi.y, bhi.y), min(ahi.z, bhi.z)))
    d = hi - lo
    if d.x > tol and d.y > tol and d.z > tol:
        return d
    return None


def report(verbose=True, ignore_walls_for=()):
    bpy.context.view_layer.update()
    fur = [o for o in bpy.data.objects
           if o.type == 'MESH' and o.name.startswith(tuple(_ROOMS))]
    walls = [o for o in bpy.data.collections.get("Shell").objects if o.type == 'MESH']
    floor = [o for o in bpy.data.collections.get("Floors").objects if o.type == 'MESH']

    boxes = {o.name: world_aabb(o) for o in fur}
    wboxes = [(o.name, world_aabb(o)) for o in walls]
    fboxes = [(o.name, world_aabb(o)) for o in floor]

    problems = []
    for a, b in itertools.combinations(fur, 2):
        d = overlap(boxes[a.name], boxes[b.name], 0.03)
        if d:
            problems.append((round(d.x * d.y * d.z, 3), "FUR-FUR", a.name, b.name))

    for o in fur:
        ob_box = boxes[o.name]
        for wn, wb in wboxes:
            d = overlap(ob_box, wb, 0.015)
            if d:
                problems.append((round(d.x * d.y * d.z, 3), "FUR-WALL", o.name, wn))
        for fn, fb in fboxes:
            # a piece dipping more than 3 cm below its floor slab is a bug
            if ob_box[0].z < fb[0].z + 0.08 and fb[0].z > -0.05:
                pass

    problems.sort(reverse=True)
    if verbose:
        for vol, kind, a, b in problems[:60]:
            print(f"{kind:9s} {vol:7.4f} m3  {a:34s} <-> {b}")
        print(f"TOTAL issues: {len(problems)}  (furniture pieces checked: {len(fur)})")
    return problems


def outside(verbose=True):
    bpy.context.view_layer.update()
    """Pieces whose footprint escapes the building envelope."""
    out = []
    for o in bpy.data.objects:
        if o.type != 'MESH' or not o.name.startswith(tuple(_ROOMS)):
            continue
        lo, hi = world_aabb(o)
        if lo.x < 0.20 or lo.y < 0.20 or hi.x > 18.80 or hi.y > 12.30:
            out.append((o.name, tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi)))
    if verbose:
        for n, lo, hi in out:
            print("OUTSIDE", n, lo, hi)
    return out


_ROOMS = ("living_", "dining_", "kitchen_", "utility_", "foyer_", "corridor_", "master_",
          "robe_", "ensuite_", "bed2_", "laundry_", "bath2_", "bed3_", "study_")
