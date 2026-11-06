#!/usr/bin/env python3
"""Compare a game frame with the Cycles reference frame, region by region.

The point of the Cycles pass is not only a pretty picture: it is a *target*. This script
samples the same three regions in both images - sky, lawn, built surfaces - and prints the
mean colour and the delta, so tuning the phone shader is a measurement instead of a guess.

    python tools/villa_match.py /tmp/beauty_1080.png /tmp/game.ppm [--json out.json]
"""
import argparse
import json
import sys

try:
    from PIL import Image
except ImportError:                      # pragma: no cover
    sys.exit("needs pillow")


def regions(im):
    """(name, box) in relative coordinates. Deliberately big, blurred regions: this is a
    calibration, not a pixel-diff (the two images do not share a tone curve or a sampler)."""
    w, h = im.size
    return [
        ("sky", (0.05, 0.02, 0.45, 0.18)),          # upper left, clear sky
        ("sky_horizon", (0.02, 0.26, 0.35, 0.31)),  # just above the roofline
        ("lawn_near", (0.25, 0.80, 0.75, 0.95)),    # foreground grass
        ("lawn_far", (0.05, 0.55, 0.30, 0.62)),     # grass at the treeline
        ("facade", (0.72, 0.30, 0.95, 0.48)),       # the lit wall
    ]


def stats(im, box):
    w, h = im.size
    x0, y0, x1, y1 = [int(round(v * (w if i % 2 == 0 else h))) for i, v in enumerate(box)]
    crop = im.crop((x0, y0, max(x1, x0 + 1), max(y1, y0 + 1))).convert("RGB")
    px = list(crop.getdata())
    n = max(len(px), 1)
    rgb = [sum(p[i] for p in px) / n for i in range(3)]
    lum = sum(0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2] for p in px) / n
    # mean saturation, to catch "neon emerald lawn" vs "olive lawn"
    sat = sum((max(p) - min(p)) / max(max(p), 1) for p in px) / n
    return {"rgb": [round(v, 1) for v in rgb], "lum": round(lum, 1), "sat": round(sat, 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference")
    ap.add_argument("game")
    ap.add_argument("--json", default=None)
    ns = ap.parse_args()
    a = Image.open(ns.reference)
    b = Image.open(ns.game)
    out = {}
    print(f"{'region':<12} {'reference rgb / lum / sat':<34} {'game rgb / lum / sat':<34} delta")
    worst = 0.0
    for (name, box) in regions(a):
        sa, sb = stats(a, box), stats(b, box)
        d = [round(sb["rgb"][i] - sa["rgb"][i], 1) for i in range(3)]
        dl = round(sb["lum"] - sa["lum"], 1)
        worst = max(worst, abs(dl))
        print(f"{name:<12} {str(sa['rgb']):>18} {sa['lum']:>6} {sa['sat']:>5}   "
              f"{str(sb['rgb']):>18} {sb['lum']:>6} {sb['sat']:>5}   "
              f"dRGB {d} dLum {dl:+}")
        out[name] = {"reference": sa, "game": sb, "delta_rgb": d, "delta_lum": dl}
    out["worst_lum_delta"] = round(worst, 1)
    print(f"\nworst luminance delta between the path trace and the phone renderer: {worst:.1f}/255")
    if ns.json:
        with open(ns.json, "w") as f:
            json.dump(out, f, indent=1)


main()
