#!/usr/bin/env python3
"""Assemble villa_v2 renders into one labelled contact sheet.

    python tools/villa_v2_contact_sheet.py [--dir villa_v2] [--cols 2] [--width 720]
"""
import argparse
import glob
import os

from PIL import Image, ImageDraw, ImageFont

ORDER = ["hero_garden", "hero_pool", "hero_entry", "hero_dusk", "hero_aerial",
         "detail_terrace", "living", "living_wide", "kitchen", "dining", "master",
         "corridor", "foyer", "bed2", "bath", "study"]


def label(draw, xy, text, size):
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        font = ImageFont.load_default()
    x, y = xy
    draw.rectangle([x, y, x + len(text) * size * 0.62 + 16, y + size * 1.5], fill=(12, 12, 14))
    draw.text((x + 8, y + size * 0.25), text, fill=(240, 240, 240), font=font)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="villa_v2")
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--width", type=int, default=760)
    ns = ap.parse_args()

    files = sorted(glob.glob(os.path.join(ns.dir, "*.png")))
    files = [f for f in files if not f.endswith("contact_sheet.png")]
    order = {n: i for i, n in enumerate(ORDER)}
    files.sort(key=lambda f: order.get(os.path.basename(f)[:-4], 99))

    tiles = []
    for f in files:
        im = Image.open(f).convert("RGB")
        h = int(im.height * ns.width / im.width)
        tiles.append((os.path.basename(f)[:-4], im.resize((ns.width, h), Image.LANCZOS)))
    if not tiles:
        raise SystemExit("no renders found")

    th = tiles[0][1].height
    rows = (len(tiles) + ns.cols - 1) // ns.cols
    pad = 10
    sheet = Image.new("RGB", (ns.cols * ns.width + pad * (ns.cols + 1),
                              rows * th + pad * (rows + 1)), (22, 22, 24))
    draw = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(tiles):
        c, r = i % ns.cols, i // ns.cols
        x = pad + c * (ns.width + pad)
        y = pad + r * (th + pad)
        sheet.paste(im, (x, y))
        label(draw, (x + 8, y + 8), name, max(14, ns.width // 42))
    out = os.path.join(ns.dir, "contact_sheet.png")
    sheet.save(out)
    print(f"wrote {out}  ({len(tiles)} shots, {sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
