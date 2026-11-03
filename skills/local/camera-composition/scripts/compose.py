"""Camera composition: framing, lens choice, DOF and review guides.

AI-generated shots usually fail on framing, not on shading: object dead-centre, wrong
lens, infinite depth of field, horizon through the middle. This does the boring parts
properly:

  * fit a bounding box with a chosen lens and margin, from any azimuth/elevation
  * lens presets by subject (product 85-100 mm, car 50-70 mm, interior 18-24 mm,
    architecture 24 mm shift-lens style)
  * physically plausible exposure: f-stop, shutter, ISO and DOF that matches the lens
  * orthographic views for technical/reference comparisons
  * optional rule-of-thirds guide burned into a rendered PNG for self-review

Usage:
  python tools/bpy_run.py <this> -- --target Car --preset car --az -35 --el 12 --render
  python tools/bpy_run.py <this> -- --target Car --ortho front --render
"""
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402

PRESETS = {
    #  name      lens  fstop  margin  elevation  distance multiplier
    "product":   (100.0, 8.0, 1.18, 12.0),
    "car":       (60.0, 5.6, 1.22, 10.0),
    "interior":  (20.0, 4.0, 1.05, 2.0),
    "architecture": (24.0, 8.0, 1.10, 3.0),
    "closeup":   (135.0, 2.8, 1.10, 8.0),
    "wide":      (35.0, 8.0, 1.35, 15.0),
}


IGNORE = {"ground", "floor", "backdrop", "cyclorama", "environment", "plane",
          "hdr_dome", "skydome"}


def _third_guides(path, out):
    from PIL import Image, ImageDraw
    im = Image.open(path).convert("RGB")
    w, h = im.size
    d = ImageDraw.Draw(im)
    for i in (1, 2):
        d.line([(w * i / 3, 0), (w * i / 3, h)], fill=(255, 90, 60), width=max(1, w // 400))
        d.line([(0, h * i / 3), (w, h * i / 3)], fill=(255, 90, 60), width=max(1, w // 400))
    im.save(out)
    return out


def run(target=None, preset="product", az=-35.0, el=None, margin=None, lens=None,
        fstop=None, ortho=None, render=False, out="/tmp/compose.png", res=800,
        samples=32, guide=False, **_):
    sc.object_mode()
    objs = sc.objects([target] if target else None)
    if not target:
        # framing "all meshes" in a real scene fits the ground plane and the car becomes
        # a speck: ignore studio furniture unless the caller asks for it explicitly
        keep = [o for o in objs if o.name.split(".")[0].lower() not in IGNORE]
        if keep:
            objs = keep
    if not objs:
        raise ValueError("no mesh objects to frame")
    lens_p, fstop_p, margin_p, el_p = PRESETS[preset]
    lens = lens or lens_p
    fstop = fstop or fstop_p
    margin = margin or margin_p
    el = el_p if el is None else el

    aspect = res / max(1, int(res * 0.5625))
    if ortho:
        view = {"front": 0.0, "rear": 180.0, "left": 90.0, "right": -90.0,
                "top": 90.0, "back": 180.0}.get(ortho, 0.0)
        cam = sc.frame_objects(objs, azimuth_deg=view, elevation_deg=90.0 if ortho == "top"
                              else 0.0, lens=lens, name=f"cam_ortho_{ortho}",
                              aspect=aspect)
        cam.data.type = "ORTHO"
        sc.fit_ortho(cam, objs, aspect=aspect, margin=margin)
        mode = f"ortho {ortho} scale {cam.data.ortho_scale:.3f}"
    else:
        cam = sc.frame_objects(objs, azimuth_deg=az, elevation_deg=el, lens=lens,
                               margin=margin, name="cam_compose", aspect=aspect)
        lo, hi = sc.bounds(objs)
        focus_point = (lo + hi) / 2
        cam.data.dof.use_dof = True
        cam.data.dof.aperture_fstop = fstop
        cam.data.dof.aperture_blades = 7
        cam.data.dof.focus_distance = (cam.location - focus_point).length
        mode = f"persp {lens:.0f}mm f/{fstop}"

    scene = bpy.context.scene
    scene.camera = cam
    result = {"ok": True, "camera": cam.name, "mode": mode, "preset": preset,
              "azimuth_deg": az, "elevation_deg": el,
              "sensor_mm": 36.0, "lens_mm": lens, "fstop": fstop,
              "advice": _advice(preset, lens, el)}
    if render:
        sc.look_transform(scene, "AgX - Medium High Contrast")
        sc.render(out, res=(res, int(res * 0.5625)), samples=samples, cam=cam)
        result["render"] = out
        result["focus_m"] = round(cam.data.dof.focus_distance / 1000.0, 4) if cam.data.dof.use_dof else None
        if guide:
            result["guided"] = _third_guides(out, os.path.splitext(out)[0] + "_thirds.png")
    return result


def _advice(preset, lens, el):
    tips = []
    if preset == "car" and el > 20:
        tips.append("car shots read best at 8-15 deg elevation; high angles make them "
                    "look like toys")
    if preset in ("product", "closeup") and el < 5:
        tips.append("very low elevation flattens the form; 10-20 deg shows the top plane")
    if lens > 85 and preset != "closeup":
        tips.append(f"{lens:.0f} mm compresses perspective a lot; good for products, "
                    "risky for interiors")
    if not tips:
        tips.append("keep the subject's optical centre on a thirds intersection, not the "
                    "frame centre, and leave more space in front than behind")
    return tips


if __name__ == "__main__":
    p = sc.add_common(sc.parser(__doc__), save=False)
    p.add_argument("--target", default=None)
    p.add_argument("--preset", default="product", choices=list(PRESETS))
    p.add_argument("--az", type=float, default=-35.0)
    p.add_argument("--el", type=float, default=None)
    p.add_argument("--margin", type=float, default=None)
    p.add_argument("--lens", type=float, default=None)
    p.add_argument("--fstop", type=float, default=None)
    p.add_argument("--ortho", default=None, choices=["front", "rear", "left", "right", "top"])
    p.add_argument("--render", action="store_true")
    p.add_argument("--guide", action="store_true")
    p.add_argument("--out", default="/tmp/compose.png")
    p.add_argument("--res", type=int, default=800)
    p.add_argument("--samples", type=int, default=32)
    sc.cli(run, p)
