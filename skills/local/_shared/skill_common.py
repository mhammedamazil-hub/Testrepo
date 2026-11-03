"""Shared helpers for this repo's own Blender skills.

Same contract as the vendored skill pack, so an agent only has to learn one thing:
    every script exposes run(**kwargs) -> dict
    every script prints its result after a literal `@@JSON@@` marker
    CLI args arrive after `--`
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

MARK = "@@JSON@@"


# --------------------------------------------------------------------- CLI glue
def argv():
    """Arguments after '--' (Blender's own args are ignored)."""
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def parser(doc=""):
    return argparse.ArgumentParser(description=(doc or "").strip().splitlines()[0])


def add_common(p, save=True):
    p.add_argument("--objects", nargs="*", default=None,
                   help="object names (default: selected, else all meshes)")
    if save:
        p.add_argument("--save", default=None, help="save .blend here after the run")
    return p


def emit(obj):
    print(MARK, json.dumps(_default(obj), sort_keys=True))


def _default(o):
    if isinstance(o, (Vector, tuple, list)):
        return [_default(x) for x in o]
    if isinstance(o, dict):
        return {k: _default(v) for k, v in o.items()}
    if hasattr(o, "__len__") and not isinstance(o, str):
        return [_default(x) for x in o]
    if isinstance(o, float):
        return round(o, 5)
    if isinstance(o, bpy.types.ID):
        return o.name
    return o


def cli(run, p):
    args = p.parse_args(argv())
    try:
        result = run(**vars(args))
        save = getattr(args, "save", None)
        if save:
            bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(save))
            result["saved"] = save
        emit(result)
    except Exception as e:  # report, never dump a traceback into agent context
        emit({"ok": False, "error": f"{type(e).__name__}: {e}"})
        raise SystemExit(1)


# ------------------------------------------------------------------- scene lookups
def objects(names=None, types=("MESH",)):
    if names:
        missing = [n for n in names if n not in bpy.data.objects]
        if missing:
            raise KeyError(f"objects not found: {missing}")
        return [bpy.data.objects[n] for n in names]
    # No names given -> every visible mesh. Deliberately ignores the current selection:
    # falling back to "whatever happens to be selected" made callers silently frame
    # (or export, or audit) one unrelated object left selected in the .blend.
    return [o for o in bpy.context.scene.objects
            if (not types or o.type in types) and o.visible_get()]


def active_mesh():
    ob = bpy.context.view_layer.objects.active
    return ob if ob and ob.type == "MESH" else None


def object_mode():
    ob = bpy.context.view_layer.objects.active
    if ob and ob.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def select_only(objs, active=None):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or (objs[0] if objs else None)


def aabb(ob, world=True):
    """True bounding box from vertices (bound_box goes stale after joins)."""
    objs = ob if isinstance(ob, (list, tuple)) else [ob]
    lo = Vector((1e18, 1e18, 1e18))
    hi = Vector((-1e18, -1e18, -1e18))
    for o in objs:
        mw = o.matrix_world if world else __import__("mathutils").Matrix.Identity(4)
        for v in o.data.vertices:
            p = mw @ v.co
            lo = Vector((min(lo.x, p.x), min(lo.y, p.y), min(lo.z, p.z)))
            hi = Vector((max(hi.x, p.x), max(hi.y, p.y), max(hi.z, p.z)))
    return lo, hi


def dims(ob):
    lo, hi = aabb(ob)
    return hi - lo


def ensure_collection(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def link(ob, coll=None):
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def new_mesh_object(name, verts, faces, mat=None, coll=None, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    link(ob, coll)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if mat is not None:
        me.materials.append(mat if isinstance(mat, bpy.types.Material) else material(mat))
    return ob


# ------------------------------------------------------------------ node helpers
def node(nt, kind, loc=(0, 0), label=None):
    n = nt.nodes.new(kind)
    n.location = loc
    if label:
        n.label = label
    return n


def principled(mat):
    for n in mat.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    raise ValueError(f"{mat.name}: no Principled BSDF")


def set_input(node_, name, value):
    """Set a socket by English name if it exists (socket sets differ between builds)."""
    for s in node_.inputs:
        if s.name == name or s.identifier == name:
            s.default_value = value
            return True
    return False


def material(name, nodes_builder=None):
    """Get/create a node material; `nodes_builder(mat, nt, bsdf)` fills it in once."""
    mat = bpy.data.materials.get(name)
    if mat and mat.get("_built"):
        return mat
    if not mat:
        mat = bpy.data.materials.new(name)
    if not mat.use_nodes:
        mat.use_nodes = True
    if nodes_builder:
        nt = mat.node_tree
        nodes_builder(mat, nt, principled(mat))
        mat["_built"] = True
    return mat


def image_save(path, rgba, width, height, colorspace_gamma=True):
    """Write a flat float buffer (len = w*h*4) to a PNG."""
    img = bpy.data.images.new(os.path.basename(path), width, height)
    img.pixels.foreach_set(rgba)
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return path


def camera(name, loc, target, lens=50.0, sensor=36.0, fstop=None, focus=None,
           ortho_scale=None):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.sensor_width = sensor
    if ortho_scale:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho_scale
    if fstop:
        cam_data.dof.use_dof = True
        cam_data.dof.aperture_fstop = fstop
        cam_data.dof.focus_distance = focus if focus is not None else (Vector(target)
                                                                     - Vector(loc)).length
    ob = bpy.data.objects.new(name, cam_data)
    link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    # Blender's default 0.1 / 1000 clip range silently swallows whole scenes that are
    # modelled in millimetres (a car 19 m from the camera renders empty grey).
    dist = (Vector(loc) - Vector(target)).length
    if dist > 0:
        cam_data.clip_start = max(dist / 1000.0, 0.001)
        cam_data.clip_end = dist * 8.0 + 100.0
    return ob


def bounds(objs):
    """World-space AABB of a list of objects -> (Vector lo, Vector hi)."""
    lo, hi = aabb(objs[0], world=True)
    for o in objs[1:]:
        l2, h2 = aabb(o, world=True)
        lo = Vector((min(lo.x, l2.x), min(lo.y, l2.y), min(lo.z, l2.z)))
        hi = Vector((max(hi.x, h2.x), max(hi.y, h2.y), max(hi.z, h2.z)))
    return lo, hi


def frame_objects(objs, azimuth_deg=-35.0, elevation_deg=18.0, lens=50.0, margin=1.35,
                  name="cam_frame", aspect=1.0, shift_to_center=True):
    """Place a camera that frames the given objects from a given direction.

    ``aspect`` is render width / height: a 36 mm sensor is fitted to the *wider*
    dimension, so a 16:9 frame is much tighter vertically than horizontally. Ignoring
    that crops product shots at the top and bottom - the most common framing mistake.
    """
    lo, hi = bounds(objs)
    center = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 1e-3)
    # fit a sphere of `radius`: use the tighter of the horizontal / vertical half-FOV
    tan_h = 18.0 / lens
    tan_v = (18.0 / max(aspect, 1e-6)) / lens
    dist = radius * margin / min(tan_h, tan_v)
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    off = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam = camera(name, center + off * dist, center, lens=lens)
    if shift_to_center:
        cam.data.shift_x = 0.0
        cam.data.shift_y = 0.0
    return cam


def fit_ortho(cam, objs, aspect=1.0, margin=1.15):
    """Set ORTHO scale so the objects' projected bounds fit the frame on both axes.

    Blender sizes ``ortho_scale`` along the larger render dimension, so the vertical
    extent available is ``ortho_scale / aspect`` for a landscape frame.
    """
    lo, hi = bounds(objs)
    cam.data.type = "ORTHO"
    # matrix_world is lazily evaluated: without an update the inverse is identity and
    # the ortho scale comes out several times too large.
    bpy.context.view_layer.update()
    inv = cam.matrix_world.to_3x3().inverted()
    ux = uy = 0.0
    for i in range(8):
        corner = Vector((hi.x if i & 1 else lo.x, hi.y if i & 2 else lo.y,
                         hi.z if i & 4 else lo.z))
        local = inv @ (corner - cam.location)
        ux = max(ux, abs(local.x))
        uy = max(uy, abs(local.y))
    # ortho_scale spans the wider dimension (x when aspect >= 1)
    needed = max(2 * ux, 2 * uy * max(aspect, 1e-6)) * margin
    cam.data.ortho_scale = needed
    return needed


def render(path, res=(800, 800), samples=64, cam=None, engine="CYCLES", denoise=True,
           transparent=False):
    sc = bpy.context.scene
    sc.render.engine = engine
    if engine == "CYCLES":
        sc.cycles.device = "CPU"
        sc.cycles.samples = samples
        sc.cycles.use_denoising = denoise
        sc.cycles.adaptive_threshold = 0.02
        sc.cycles.max_bounces = 8 if samples > 32 else 4
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    if cam:
        sc.camera = cam
    if sc.camera is None:
        raise ValueError("scene has no camera")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def look_transform(scene, look="AgX - Medium High Contrast", exposure=0.0):
    vs = scene.view_settings
    try:
        vs.view_transform = "AgX"
    except TypeError:
        pass
    try:
        vs.look = look
    except TypeError:
        pass
    vs.exposure = exposure


def tri_count(ob, evaluated=True):
    dg = bpy.context.evaluated_depsgraph_get()
    if evaluated:
        eo = ob.evaluated_get(dg)
        me = eo.to_mesh()
        try:
            me.calc_loop_triangles()
            return len(me.loop_triangles)
        finally:
            eo.to_mesh_clear()
    me = ob.data
    me.calc_loop_triangles()
    return len(me.loop_triangles)


def human(n):
    return f"{n/1e6:.2f}M" if n >= 1e6 else f"{n/1e3:.1f}k" if n >= 1e3 else str(n)
