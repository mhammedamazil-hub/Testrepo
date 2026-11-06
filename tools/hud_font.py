#!/usr/bin/env python3
"""Bake the HUD font atlas the native renderer draws text with.

The game used to put its HUD on top of the GL surface with Android's Canvas, which needs Java.
The whole app is native now (NativeActivity), so the HUD is drawn in GL from this atlas.

Output, both committed because CI must not depend on a font being installed:

  android/game/app/src/main/assets/hud_font.png   white glyphs, alpha = coverage
  android/game/app/src/main/assets/hud_font.txt   "<cols> <rows> <cell_w> <cell_h> <first> <count>"

Every glyph is rendered into a fixed cell so the C++ side needs no per-glyph metrics: it
indexes by ASCII code. DejaVu Sans Bold at 34 px reads cleanly on a phone at 1080p; the HUD
scales it down by picking a quad size in pixels.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PNG = os.path.join(ROOT, "android/game/app/src/main/assets/hud_font.png")
OUT_TXT = os.path.join(ROOT, "android/game/app/src/main/assets/hud_font.txt")

CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]

FIRST, LAST = 32, 126          # printable ASCII
CELL_W, CELL_H = 30, 44        # one cell per glyph, 4 px of slack all round
COLS = 16


def main():
    path = next((p for p in CANDIDATES if os.path.exists(p)), None)
    if not path:
        print("FAIL: no TrueType font found; the atlas would be unreadable", file=sys.stderr)
        return 1
    size = 34
    font = ImageFont.truetype(path, size)
    count = LAST - FIRST + 1
    rows = (count + COLS - 1) // COLS
    atlas = Image.new("RGBA", (COLS * CELL_W, rows * CELL_H), (255, 255, 255, 0))
    draw = ImageDraw.Draw(atlas)
    for i in range(count):
        ch = chr(FIRST + i)
        cx = (i % COLS) * CELL_W
        cy = (i // COLS) * CELL_H
        bbox = draw.textbbox((0, 0), ch, font=font)
        gw = bbox[2] - bbox[0]
        gh = bbox[3] - bbox[1]
        ox = cx + (CELL_W - gw) // 2 - bbox[0]
        oy = cy + (CELL_H - gh) // 2 - bbox[1]
        draw.text((ox, oy), ch, font=font, fill=(255, 255, 255, 255))
    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
    atlas.save(OUT_PNG, optimize=True)
    with open(OUT_TXT, "w", encoding="ascii") as f:
        f.write(f"{COLS} {rows} {CELL_W} {CELL_H} {FIRST} {count}\n")
    print(f"hud font: {count} glyphs in {COLS}x{rows} cells of {CELL_W}x{CELL_H} "
          f"-> {os.path.relpath(OUT_PNG, ROOT)} ({os.path.getsize(OUT_PNG)} B) "
          f"from {os.path.basename(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
