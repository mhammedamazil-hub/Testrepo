#!/usr/bin/env python3
"""Segment a car from a studio/turnaround photo — try several methods, keep the best.

Dark car on a dark gradient background defeats a global threshold, so this
compares three approaches and scores them by plausibility (area, fill ratio,
touching the frame border, aspect ratio) before picking one.

Usage:
    python tools/segment_car.py                 # debug: writes masks + overlays + report
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import color, filters, measure, morphology, segmentation

SRC = Path("carve_src")


def load(name: str, work: int = 420):
    im = Image.open(SRC / f"{name}.png").convert("RGB")
    scale = work / im.width
    if scale < 1:
        im = im.resize((work, max(1, int(im.height * scale))), Image.LANCZOS)
    return np.asarray(im, dtype=np.float32) / 255.0, im


def _clean(mask: np.ndarray, min_frac: float = 0.02) -> np.ndarray:
    mask = morphology.remove_small_objects(mask.astype(bool), min_size=int(mask.size * min_frac))
    mask = ndimage.binary_closing(mask, np.ones((7, 7)))
    mask = ndimage.binary_fill_holes(mask)
    return mask


def _largest_not_bottom(mask: np.ndarray) -> np.ndarray:
    """Keep the biggest component that does not live in the bottom label strip."""
    lab = measure.label(mask)
    if lab.max() == 0:
        return mask
    h = mask.shape[0]
    props = measure.regionprops(lab)
    cands = [p for p in props if p.bbox[2] < h * 0.93] or props
    best = max(cands, key=lambda p: p.area)
    return lab == best.label


def method_flood(rgb: np.ndarray) -> np.ndarray:
    """Flood from all four corners across the smooth background."""
    lum = color.rgb2gray(rgb)
    blur = filters.gaussian(lum, 2)
    seeds = [(0, 0), (0, blur.shape[1] - 1), (blur.shape[0] - 1, 0), (blur.shape[0] - 1, blur.shape[1] - 1)]
    bg = np.zeros(blur.shape, bool)
    for s in seeds:
        try:
            bg |= segmentation.flood(blur, s, tolerance=0.10)
        except Exception:
            pass
    return _largest_not_bottom(_clean(~bg))


def method_chanvese(rgb: np.ndarray) -> np.ndarray:
    """Region-based active contour: robust to smooth background gradients."""
    lum = filters.gaussian(color.rgb2gray(rgb), 1.5)
    init = np.zeros_like(lum, bool)
    h, w = lum.shape
    init[int(h * 0.12):int(h * 0.9), int(w * 0.06):int(w * 0.94)] = True
    try:
        cv = segmentation.chan_vese(lum, mu=0.2, lambda1=1.0, lambda2=1.0, tol=1e-3,
                                    max_num_iter=250, init_level_set=init)
    except Exception:
        return np.zeros_like(lum, bool)
    return _largest_not_bottom(_clean(cv))


def method_localvar(rgb: np.ndarray) -> np.ndarray:
    """The car has texture/edges; the studio background is smooth."""
    lum = color.rgb2gray(rgb)
    mean = ndimage.uniform_filter(lum, 15)
    sq = ndimage.uniform_filter(lum * lum, 15)
    var = np.clip(sq - mean * mean, 0, None)
    detail = np.sqrt(var)
    thr = filters.threshold_otsu(detail)
    m = detail > thr
    m = ndimage.binary_closing(m, np.ones((15, 15)))
    m = ndimage.binary_fill_holes(m)
    return _largest_not_bottom(_clean(m))


def score(mask: np.ndarray) -> dict:
    h, w = mask.shape
    area = float(mask.mean())
    lbl = measure.label(mask)
    touch = int(mask[0].any()) + int(mask[-1].any()) + int(mask[:, 0].any()) + int(mask[:, -1].any())
    props = measure.regionprops(lbl)
    fill = 0.0
    bbox = None
    if props:
        p = max(props, key=lambda r: r.area)
        minr, minc, maxr, maxc = p.bbox
        bbox = [int(minc), int(minr), int(maxc), int(maxr)]
        fill = p.area / max(1, (maxr - minr) * (maxc - minc))
    plausible = 0.03 <= area <= 0.55 and touch == 0 and fill > 0.45
    return {"area_frac": round(area, 4), "border_touch": touch,
            "bbox_fill": round(fill, 3), "bbox": bbox, "plausible": bool(plausible),
            "score": round(fill - 0.1 * touch + (0.3 if plausible else 0), 3)}


def segment(name: str):
    rgb, im = load(name)
    out = {}
    for mname, fn in (("flood", method_flood), ("chanvese", method_chanvese), ("localvar", method_localvar)):
        try:
            m = fn(rgb)
        except Exception as exc:  # noqa: BLE001
            m = np.zeros(rgb.shape[:2], bool)
            out[mname] = {"error": str(exc)}
        else:
            out[mname] = score(m)
        out[mname]["mask"] = m
    best = max((k for k in out if "mask" in out[k]), key=lambda k: out[k]["score"], default=None)
    return im, rgb, out, best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--views", nargs="*", default=["0_0_front", "0_1_rear", "2_0_side_right", "1_1_top"])
    ap.add_argument("--debug-dir", default="carve_debug")
    args = ap.parse_args()

    dbg = Path(args.debug_dir)
    dbg.mkdir(exist_ok=True)
    report = {}
    for name in args.views:
        im, rgb, out, best = segment(name)
        report[name] = {k: {kk: vv for kk, vv in v.items() if kk != "mask"} for k, v in out.items()}
        report[name]["chosen"] = best
        for k, v in out.items():
            if "mask" not in v:
                continue
            m = v["mask"]
            Image.fromarray((m * 255).astype(np.uint8)).save(dbg / f"{name}__{k}.png")
            ov = np.asarray(im).copy()
            if m.any():
                edge = m ^ ndimage.binary_erosion(m, np.ones((3, 3)))
                ov[edge] = [0, 255, 0]
            Image.fromarray(ov).save(dbg / f"{name}__{k}_overlay.png")
        print(f"{name:14s} chosen={best}")
        for k, v in out.items():
            print(f"   {k:9s} {json.dumps({a: b for a, b in v.items() if a != 'mask'})}")
    (dbg / "report.json").write_text(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
