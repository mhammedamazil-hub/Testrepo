"""Parametric geometry kit for the villa.

Everything is built with bmesh, beveled for realistic edge highlights, and given
box-projected UVs in metres so one texture tile == a fixed physical size.
"""
import math
import bmesh
import bpy
from mathutils import Vector, Matrix, Euler

from . import mats


# ------------------------------------------------------------------ primitives
def _finish(name, bm, mat, collection=None, bevel=0.0, bevel_seg=2, smooth=False,
            uv=True, uv_off=(0.0, 0.0)):
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges), offset=bevel,
                        offset_type='OFFSET', segments=bevel_seg, profile=0.5,
                        affect='EDGES', clamp_overlap=True, loop_slide=True)
    bm.normal_update()
    if uv:
        scale = 1.0 / mats.tile_m(mat) if isinstance(mat, str) and mat in mats.SPEC else 1.0
        lay = bm.loops.layers.uv.verify()
        for f in bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                c = l.vert.co
                if ax == 0:
                    u, v = c.y, c.z
                elif ax == 1:
                    u, v = c.x, c.z
                else:
                    u, v = c.x, c.y
                if n[ax] < 0:
                    u = -u
                l[lay].uv = (u * scale + uv_off[0], v * scale + uv_off[1])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if mat:
        me.materials.append(mats.build(mat) if isinstance(mat, str) else mat)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def box(name, size, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, bevel=0.0, bevel_seg=2,
        smooth=False, coll=None):
    """Axis-aligned box centred on `loc` (before rotation about loc)."""
    sx, sy, sz = (s * 0.5 for s in size)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    ob = _finish(name, bm, mat, coll, bevel, bevel_seg, smooth)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def rbox(name, size, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, radius=0.03, seg=3,
         coll=None, smooth=True):
    """Box with rounded edges (radius clamp to 45% of the smallest dimension)."""
    r = min(radius, 0.45 * min(size))
    return box(name, size, loc, rot, mat, bevel=r, bevel_seg=seg, smooth=smooth,
               coll=coll)


def cyl(name, r, h, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, seg=32, r2=None,
        bevel=0.0, coll=None, smooth=True, cap=True):
    """Cylinder/cone along +Z, centred on loc."""
    bm = bmesh.new()
    r2 = r if r2 is None else r2
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=seg,
                          radius1=r, radius2=r2, depth=h)
    ob = _finish(name, bm, mat, coll, bevel, 2, smooth)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def sphere(name, r, loc=(0, 0, 0), mat=None, seg=24, rings=14, coll=None, scale=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    if scale:
        bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    ob = _finish(name, bm, mat, coll, 0, 2, True)
    ob.location = loc
    return ob


def lathe(name, profile, loc=(0, 0, 0), mat=None, seg=48, coll=None, smooth=True,
          close=True):
    """Revolve a (radius, z) profile around Z. First point should have r>=0."""
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            try:
                bm.faces.new((a[i], a[j], b[j], b[i]))
            except ValueError:
                pass
    if close:
        for ring, rev in ((rings[0], True), (rings[-1], False)):
            if max(v.co.length for v in ring) > 1e-6:
                try:
                    f = bm.faces.new(ring[::-1] if rev else ring)
                    f.normal_update()
                except ValueError:
                    pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = _finish(name, bm, mat, coll, 0, 2, smooth)
    ob.location = loc
    return ob


def tube(name, r_out, r_in, h, loc=(0, 0, 0), mat=None, seg=32, coll=None):
    return lathe(name, [(r_in, -h / 2), (r_out, -h / 2), (r_out, h / 2), (r_in, h / 2),
                        (r_in, -h / 2)], loc, mat, seg, coll)


def extrude(name, pts, depth, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, bevel=0.0,
            coll=None, smooth=False, axis='Z'):
    """Extrude a 2D polygon (list of (x,y)) by `depth` along `axis`, centred."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, -depth / 2)) for (x, y) in pts]
    try:
        bm.faces.new(vs)
    except ValueError:
        pass
    ret = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    for el in ret["geom"]:
        if isinstance(el, bmesh.types.BMVert):
            el.co.z += depth
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if axis == 'Y':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=Matrix.Rotation(math.radians(-90), 3, 'X'))
    elif axis == 'X':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=Matrix.Rotation(math.radians(90), 3, 'Y'))
    ob = _finish(name, bm, mat, coll, bevel, 3, smooth)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def rod(name, p0, p1, r, mat=None, seg=16, coll=None, caps=True):
    """Cylinder spanning two points (world coords)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    ob = cyl(name, r, L, (0, 0, 0), (0, 0, 0), mat, seg, coll=coll, cap=caps)
    ob.location = (p0 + p1) / 2
    up = Vector((0, 0, 1))
    if d.length > 1e-9:
        q = up.rotation_difference(d.normalized())
        ob.rotation_mode = 'QUATERNION'
        ob.rotation_quaternion = q
    return ob


def slab(name, x0, y0, x1, y1, z0, z1, mat, bevel=0.0, coll=None):
    """Box from bounds (not centre/size)."""
    return box(name, (x1 - x0, y1 - y0, z1 - z0),
               ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), mat=mat,
               bevel=bevel, coll=coll)


# --------------------------------------------------------------------- helpers
def join(objs, name):
    """Join a list of objects into one mesh object, keeping material slots."""
    objs = [o for o in objs if o is not None]
    if not objs:
        raise ValueError("nothing to join")
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    # the join inherits the active object's transform: bake it in so the piece's
    # local coordinates are exactly what the builder produced (origin at 0,0,0)
    mw = ob.matrix_world.copy()
    ob.data.transform(mw)
    ob.matrix_world = Matrix.Identity(4)
    ob.data.update()
    ob.name = name
    ob.data.name = name
    return ob


def set_origin(ob, point):
    """Move the object origin to `point` (world), keeping the geometry in place."""
    apply_transforms(ob)
    p = Vector(point)
    ob.data.transform(Matrix.Translation(-p))
    ob.data.update()
    ob.location = p


def set_uv_01(ob):
    """Normalise box-projected UVs to 0..1 across the object's bounding box."""
    me = ob.data
    lay = me.uv_layers.active or me.uv_layers.new(name="UVMap")
    vs = [v.co for v in me.vertices]
    lo = [min(v[i] for v in vs) for i in range(3)]
    hi = [max(v[i] for v in vs) for i in range(3)]
    me.update()
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        a, b = [(1, 2), (0, 2), (0, 1)][ax]
        span_a = max(1e-6, hi[a] - lo[a])
        span_b = max(1e-6, hi[b] - lo[b])
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            u = (co[a] - lo[a]) / span_a
            v = (co[b] - lo[b]) / span_b
            lay.data[li].uv = (u if n[ax] >= 0 else 1 - u, v)
    me.update()


def leaf(name, L=0.30, W=0.16, mat="leaf", curl=0.18, fold=0.16, coll=None, seg=10,
         width_pts=5):
    """A single curved leaf blade in the XZ plane, base at origin, tip at +Z."""
    bm = bmesh.new()
    rows = []
    for i in range(seg + 1):
        t = i / seg
        # pointed at both ends, widest at 40 %
        w = W * 0.5 * (math.sin(math.pi * min(1.0, t ** 0.75)) ** 0.85)
        z = t * L
        y_bend = curl * L * (t ** 2) * 0.5
        row = []
        for j in range(width_pts + 1):
            u = j / width_pts * 2 - 1
            row.append(bm.verts.new((u * w, y_bend + fold * w * abs(u), z)))
        rows.append(row)
    for i in range(seg):
        for j in range(width_pts):
            try:
                bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1],
                              rows[i + 1][j]))
            except ValueError:
                pass
    bm.normal_update()
    ob = _finish(name, bm, mat, coll, 0, 2, True)
    return ob


def smooth_by_angle(ob, angle=math.radians(35)):
    me = ob.data
    for p in me.polygons:
        p.use_smooth = True
    me.update()
    import bmesh as _bm
    bm = _bm.new()
    bm.from_mesh(me)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            e.smooth = e.calc_face_angle(0.0) < angle
    bm.to_mesh(me)
    bm.free()
    me.update()


def collection(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c
