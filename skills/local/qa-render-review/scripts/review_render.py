"""Render the QA review set and *measure* it, instead of trusting that it rendered.

Every delivered model must survive a look at it from several angles. This renders
front / rear / left / right / top / three-quarter + a contact sheet, then computes
per-view image statistics that catch the usual silent failures:

  * black or blank frames            -> mean luma, coverage (fraction of pixels that
                                        differ from the background)
  * blown-out highlights             -> clipped fraction above 0.99
  * crushed shadows                  -> clipped fraction below 0.01
  * empty background / missing model -> coverage below threshold
  * silhouette out of frame          -> subject bbox touching an image edge

It also reports real geometry numbers per object (tris, dims, materials, UVs) so a
"looks fine" claim is backed by data.

Usage:
  python tools/bpy_run.py <this> -- --objects Car --out /tmp/review \
      --views front three_quarter left --res 512 --samples 24
"""
import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402

VIEWS = {
    "front":       (0.0, 0.0),
    "rear":        (180.0, 0.0),
    "left":        (90.0, 0.0),
    "right":       (-90.0, 0.0),
    "top":         (0.0, 78.0),
    "bottom":      (0.0, -78.0),
    "three_quarter": (-35.0, 18.0),
    "hero":        (-55.0, 12.0),
}


def _studio(scene):
    if scene.world is None:
        scene.world = bpy.data.worlds.new("QAWorld")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.45, 0.47, 0.5, 1)
        bg.inputs[1].default_value = 0.6
    for name, loc, energy, size in (("qa_key", (3.0, -3.2, 4.0), 700, 3.0),
                                    ("qa_rim", (-3.4, 2.6, 3.0), 400, 2.5)):
        if name in bpy.data.objects:
            continue
        lg = bpy.data.lights.new(name, "AREA")
        lg.energy, lg.size = energy, size
        ob = bpy.data.objects.new(name, lg)
        scene.collection.objects.link(ob)
        ob.location = loc
        from mathutils import Vector
        ob.rotation_euler = (Vector((0, 0, 0.3)) - Vector(loc)).to_track_quat(
            "-Z", "Y").to_euler()


def _stats(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255.0
    luma = a @ np.array([0.2126, 0.7152, 0.0722])
    h, w = luma.shape
    border = np.concatenate([luma[0:2].ravel(), luma[-2:].ravel(),
                             luma[:, 0:2].ravel(), luma[:, -2:].ravel()])
    bg = float(np.median(border))
    mask = np.abs(luma - bg) > 0.06
    cov = float(mask.mean())
    out = {"mean_luma": round(float(luma.mean()), 4),
           "clipped_high": round(float((luma > 0.99).mean()), 4),
           "clipped_low": round(float((luma < 0.01).mean()), 4),
           "coverage": round(cov, 4)}
    if mask.any():
        ys, xs = np.nonzero(mask)
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        out["subject_bbox_px"] = [int(x0), int(y0), int(x1), int(y1)]
        out["touching_edge"] = bool(x0 <= 1 or y0 <= 1 or x1 >= w - 2 or y1 >= h - 2)
        out["subject_aspect"] = round((x1 - x0 + 1) / max(1, (y1 - y0 + 1)), 4)
    problems = []
    if out["mean_luma"] < 0.02:
        problems.append("frame is black (lighting or camera inside geometry)")
    if out["coverage"] < 0.01:
        problems.append("subject not visible (coverage < 1 %)")
    if out["coverage"] > 0.9:
        problems.append("camera too close / subject fills frame")
    if out["clipped_high"] > 0.15:
        problems.append("highlights blown (>15 % pixels clipped)")
    if out.get("touching_edge"):
        problems.append("subject touches the frame edge (cropped)")
    out["problems"] = problems
    return out


def _sheet(paths, out, cols=4):
    from PIL import Image
    ims = [Image.open(p) for p in paths]
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h), (18, 18, 18))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((w, h)), ((i % cols) * w, (i // cols) * h))
    sheet.save(out)
    return out


def run(objects=None, out="/tmp/review", views=None, res=512, samples=24,
        engine="CYCLES", **_):
    sc.object_mode()
    objs = sc.objects(objects)
    if not objs:
        raise ValueError("no mesh objects")
    views = views or ["front", "rear", "left", "right", "top", "three_quarter"]
    os.makedirs(out, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = engine
    _studio(scene)
    sc.look_transform(scene, "AgX - Medium High Contrast")

    geo = []
    for ob in objs:
        d = sc.dims(ob)
        geo.append({"object": ob.name, "tris": sc.tri_count(ob),
                    "dims_m": [round(v, 4) for v in d],
                    "materials": [s.material.name for s in ob.material_slots
                                  if s.material],
                    "uv_layers": len(ob.data.uv_layers),
                    "verts": len(ob.data.vertices)})

    shots = []
    for v in views:
        if v not in VIEWS:
            raise ValueError(f"view must be one of {sorted(VIEWS)}")
        az, el = VIEWS[v]
        cam = sc.frame_objects(objs, azimuth_deg=az, elevation_deg=el,
                              name=f"qa_cam_{v}")
        path = os.path.join(out, f"{v}.png")
        sc.render(path, res=(res, res), samples=samples, cam=cam)
        st = _stats(path)
        st["view"], st["path"] = v, path
        shots.append(st)
        # the camera is scaffolding, not part of the asset
        bpy.data.objects.remove(cam, do_unlink=True)

    sheet = _sheet([s["path"] for s in shots], os.path.join(out, "contact_sheet.png"))
    bad = [s for s in shots if s["problems"]]
    return {"ok": True, "contact_sheet": sheet, "views": shots, "geometry": geo,
            "verdict": "PASS" if not bad else "FAIL",
            "problems": {s["view"]: s["problems"] for s in bad},
            "note": "verdict=PASS means no silent render failures; it does NOT mean "
                    "the art direction is good - look at the contact sheet"}


if __name__ == "__main__":
    p = sc.add_common(sc.parser(__doc__), save=False)
    p.add_argument("--out", default="/tmp/review")
    p.add_argument("--views", nargs="*", default=None)
    p.add_argument("--res", type=int, default=512)
    p.add_argument("--samples", type=int, default=24)
    p.add_argument("--engine", default="CYCLES")
    sc.cli(run, p)
