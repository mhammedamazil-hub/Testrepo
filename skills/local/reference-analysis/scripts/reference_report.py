"""Reference-image analysis: silhouette, proportions and palette - before modelling.

Solve the #1 failure mode in AI 3D: jumping to geometry without measuring. This reads
reference image(s), extracts the subject silhouette, and reports:

  * silhouette bbox and aspect ratio (width/height)
  * optional real-world scale: give one known dimension in the image and get mm-per-px
  * measured extents in those units, for the axes the reference can actually show
  * dominant palette (k-means, in linear-ish sRGB) for material authoring
  * per-row silhouette width profile -> gives you the shoulder/waist/hip curve to match
  * a saved silhouette overlay PNG so a human (or the agent) can sanity-check the mask

Works headless with numpy + PIL (both ship in this environment). No network.

Usage:
  python tools/bpy_run.py <this> -- --image side.png --known-mm 4976 --known-axis x
  python tools/bpy_run.py <this> -- --image a.png b.png --compare-model Car
"""
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402


def _load(path):
    from PIL import Image
    im = Image.open(bpy.path.abspath(path)).convert("RGB")
    return np.asarray(im).astype(np.float32) / 255.0, im.size


def silhouette(rgb, bg_tol=0.09, min_frac=0.002):
    """Foreground mask: pixels that differ from the estimated background colour.

    Background = the median colour of the image border (robust for studio shots,
    white sweeps, and plain backdrops). For busy backgrounds this under-segments -
    the report says so, and returns `mask_quality`.
    """
    h, w, _ = rgb.shape
    border = np.concatenate([rgb[0:2].reshape(-1, 3), rgb[-2:].reshape(-1, 3),
                             rgb[:, 0:2].reshape(-1, 3), rgb[:, -2:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    diff = np.abs(rgb - bg).max(axis=2)
    mask = diff > bg_tol
    frac = mask.mean()
    quality = "good" if 0.02 < frac < 0.85 else "poor"
    return mask, bg, quality


def bbox(mask):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def width_profile(mask, bands=16):
    """Normalised silhouette width per horizontal band, bottom->top."""
    x0, y0, x1, y1 = bbox(mask)
    out = []
    for i in range(bands):
        ya = y0 + int((y1 - y0) * i / bands)
        yb = y0 + int((y1 - y0) * (i + 1) / bands)
        band = mask[ya:max(yb, ya + 1)]
        cols = np.nonzero(band.any(axis=0))[0]
        out.append(0.0 if len(cols) == 0 else float((cols.max() - cols.min() + 1)
                                                    / (x1 - x0 + 1)))
    return out


def palette(rgb, mask, k=6, iters=12, seed=0):
    px = rgb[mask]
    if len(px) == 0:
        return []
    rng = np.random.default_rng(seed)
    c = px[rng.choice(len(px), size=min(k, len(px)), replace=False)]
    for _ in range(iters):
        d = ((px[:, None, :] - c[None, :, :]) ** 2).sum(axis=2)
        lab = d.argmin(axis=1)
        for j in range(len(c)):
            sel = px[lab == j]
            if len(sel):
                c[j] = sel.mean(axis=0)
    counts = np.bincount(lab, minlength=len(c)) / len(px)
    order = np.argsort(-counts)
    return [{"rgb": [round(float(v), 3) for v in c[j]],
             "share": round(float(counts[j]), 3)} for j in order]


def run(image, known_mm=None, known_axis="x", compare_model=None, bands=16,
        save_overlay=None, **_):
    sc.object_mode()
    images = image if isinstance(image, (list, tuple)) else [image]
    model = bpy.data.objects[compare_model] if compare_model else None
    mdims = sc.dims(model) if model else None

    report = {"ok": True, "images": [], "model": None}
    if mdims is not None:
        report["model"] = {"name": compare_model,
                           "dims_m": [round(v, 4) for v in mdims],
                           "rollout_m": float(2 * (mdims.x + mdims.y))}

    for idx, path in enumerate(images):
        rgb, size = _load(path)
        mask, bg, quality = silhouette(rgb)
        bb = bbox(mask)
        entry = {"file": path, "size_px": list(size), "background_rgb": [round(float(v), 3)
                                                                        for v in bg],
                 "mask_quality": quality}
        if bb:
            x0, y0, x1, y1 = bb
            wpx, hpx = x1 - x0 + 1, y1 - y0 + 1
            entry.update({"silhouette_bbox_px": [x0, y0, x1, y1],
                          "silhouette_aspect_w_over_h": round(wpx / hpx, 4),
                          "silhouette_fill_frac": round(wpx * hpx
                                                        / (size[0] * size[1]), 4),
                          "width_profile_bottom_to_top": [round(v, 3) for v in
                                                          width_profile(mask, bands)]})
            kmm = known_mm[idx] if isinstance(known_mm, (list, tuple)) else known_mm
            if kmm:
                mmp = float(kmm) / (wpx if known_axis == "x" else hpx)
                entry["mm_per_px"] = round(mmp, 4)
                entry["measured"] = {
                    "known_axis": known_axis,
                    "extent_x_mm": round(wpx * mmp, 1),
                    "extent_y_mm": round(hpx * mmp, 1),
                    "note": "only the two screen axes are measurable from one view; "
                            "the third needs a side/top reference",
                }
                if mdims is not None:
                    model_ratio = mdims.x / mdims.y if mdims.y else 0
                    entry["compare"] = {
                        "reference_aspect": round(wpx / hpx, 4),
                        "model_aspect_xy": round(model_ratio, 4),
                        "delta_pct": round(100 * (model_ratio - wpx / hpx)
                                           / (wpx / hpx), 2),
                    }
        entry["palette"] = palette(rgb, mask)
        report["images"].append(entry)

        if save_overlay:
            from PIL import Image
            if len(images) > 1:   # one overlay per input image
                root, ext = os.path.splitext(save_overlay)
                save_overlay = f"{root}_{idx}{ext or '.png'}"
            out = (rgb * 255).astype(np.uint8).copy()
            out[mask] = (out[mask] * 0.45 + np.array([255, 40, 40]) * 0.55).astype(np.uint8)
            Image.fromarray(out).save(bpy.path.abspath(save_overlay))
            report.setdefault("overlays", []).append(save_overlay)

    # the workflow gate: a proportion check must pass before detailing starts
    deltas = [im["compare"]["delta_pct"] for im in report["images"] if "compare" in im]
    if deltas:
        report["proportion_gate"] = {
            "max_delta_pct": max(abs(d) for d in deltas),
            "pass": max(abs(d) for d in deltas) <= 5.0,
            "rule": "blockout aspect must be within 5 % of the reference before detailing",
        }
    return report


if __name__ == "__main__":
    p = sc.add_common(sc.parser(__doc__), save=False)
    p.add_argument("--image", nargs="+", required=True)
    p.add_argument("--known-mm", type=float, nargs="+", default=None,
                   help="real length of the silhouette's width (or height)")
    p.add_argument("--known-axis", default="x", choices=["x", "y"])
    p.add_argument("--compare-model", default=None)
    p.add_argument("--bands", type=int, default=16)
    p.add_argument("--overlay", dest="save_overlay", default=None)
    sc.cli(run, p)
