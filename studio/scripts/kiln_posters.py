"""KILN — printed/social artwork.

Real Cycles plates + real type. Type is set with PIL against the same three faces the
site uses (Instrument Serif / Inter Tight / JetBrains Mono), so the print set and the
web set are optically identical: same tracking, same measures, same baseline rhythm.

Run:  python3 scripts/kiln_posters.py
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDERS = os.path.join(ROOT, "brand", "renders")
FONTS = os.path.join(ROOT, "fonts")

INK = (11, 12, 14)
PAPER = (242, 237, 228)
EMBER = (216, 84, 42)
EMBER_LIT = (238, 117, 65)
KILN = (138, 133, 120)
SMOKE = (85, 84, 79)

SERIF = os.path.join(FONTS, "instrument-serif.ttf")
SANS = os.path.join(FONTS, "inter-tight-400.ttf")
SANS_M = os.path.join(FONTS, "inter-tight-500.ttf")
MONO = os.path.join(FONTS, "jetbrains-mono.ttf")


def font(path, size):
    return ImageFont.truetype(path, size)


def tracked(draw, xy, text, f, fill, tracking=0.0):
    """Draw with letter-spacing in pixels (negative tightens). Returns advance width."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + tracking
    return x - xy[0]


def tracked_width(draw, text, f, tracking=0.0):
    return sum(draw.textlength(c, font=f) for c in text) + tracking * max(len(text) - 1, 0)


def right(draw, x_right, y, text, f, fill, tracking=0.0):
    """Right-align a tracked run to x_right."""
    w = tracked_width(draw, text, f, tracking)
    tracked(draw, (x_right - w, y), text, f, fill, tracking)


def para(draw, xy, text, f, fill, measure, leading, tracking=0.0):
    """Word-wrapped paragraph with explicit measure; returns bottom y."""
    x0, y = xy
    words = text.split()
    line, lines = "", []
    for w in words:
        probe = (line + " " + w).strip()
        if tracked_width(draw, probe, f, tracking) <= measure or not line:
            line = probe
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    for ln in lines:
        tracked(draw, (x0, y), ln, f, fill, tracking)
        y += leading
    return y


def scrim(img, box, color, stops):
    """Vertical/tapeless gradient scrim over `box` = (x0,y0,x1,y1)."""
    w = box[2] - box[0]
    h = box[3] - box[1]
    grad = Image.new("L", (1, 256))
    for i in range(256):
        t = i / 255
        v = 0
        for (p, a) in stops:
            v = v  # placeholder; replaced below
        # linear interpolation across stops
        prev_p, prev_a = stops[0]
        val = prev_a
        for p, a in stops:
            if t <= p:
                span = (p - prev_p) or 1
                val = prev_a + (a - prev_a) * ((t - prev_p) / span)
                break
            prev_p, prev_a = p, a
        else:
            val = stops[-1][1]
        grad.putpixel((0, i), int(val * 255))
    mask = grad.resize((w, h), Image.BILINEAR)
    layer = Image.new("RGB", (w, h), color)
    img.paste(layer, (box[0], box[1]), mask)


def crop(src, W, H, pos=(0.5, 0.5)):
    im = Image.open(os.path.join(RENDERS, src)).convert("RGB")
    sw, sh = im.size
    scale = max(W / sw, H / sh)
    im = im.resize((max(W, int(sw * scale + 0.5)), max(H, int(sh * scale + 0.5))), Image.LANCZOS)
    sw, sh = im.size
    left = int((sw - W) * pos[0])
    top = int((sh - H) * pos[1])
    return im.crop((left, top, left + W, top + H))


def grain(im, amount=5):
    """Subtle film grain so flat scrims never band."""
    import random
    random.seed(7)
    px = im.load()
    W, H = im.size
    for _ in range((W * H) // 26):
        x, y = random.randrange(W), random.randrange(H)
        r, g, b = px[x, y]
        d = random.randint(-amount, amount)
        px[x, y] = (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)))
    return im


def mark(img, x, y, size=44, color=PAPER):
    """The KILN mark, composited as a real alpha tile: solid block, door knocked out.

    Same geometry as brand/logo/kiln-mark.svg — radius = half the opening, springing
    380 units down a 1000-unit field, legs running past the foot.
    """
    s = int(size)
    tile = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rectangle([0, 0, s - 1, s - 1], fill=(*color, 255))

    door = Image.new("L", (s, s), 0)
    dd = ImageDraw.Draw(door)
    r = s * 0.15
    spring = s * 0.38
    cx = s / 2
    dd.rectangle([cx - r, spring, cx + r, s], fill=255)
    dd.ellipse([cx - r, spring - r, cx + r, spring + r], fill=255)

    a = tile.split()[3]
    tile.putalpha(Image.composite(Image.new("L", (s, s), 0), a, door))
    img.paste(tile, (int(x), int(y)), tile)


# ─────────────────────────────────────────────────────────── manifesto
def manifesto():
    W, H = 1200, 1600
    im = crop("hero-2400x1600.png", W, H, pos=(0.62, 0.5))
    scrim(im, (0, 0, W, H), INK, [(0.0, 0.86), (0.42, 0.55), (0.72, 0.90), (1.0, 1.0)])
    d = ImageDraw.Draw(im)

    m = 84
    mark(im, m, m, 30)
    tracked(d, (m + 52, m + 2), "KILN", font(SERIF, 30), PAPER, 9)
    right(d, W - m, m + 10, "STUDIO NOTE 001", font(MONO, 15), KILN, 3.2)

    y = H * 0.545
    d.text((m, y), "Rooms,", font=font(SERIF, 168), fill=PAPER)
    d.text((m, y + 158), "not pages.", font=font(SERIF, 168), fill=EMBER_LIT)

    d.rectangle([m, y + 350, m + 96, y + 352], fill=EMBER)

    body = ("Every KILN build begins as a real room in Blender: camera, scale and light "
            "settled before a single line of interface exists. The site is then rendered, "
            "not illustrated — under two megabytes, sixty frames, on a phone.")
    para(d, (m, y + 392), body, font(SANS, 27), (222, 216, 205), 610, 42, 0.1)

    tracked(d, (m, H - 96), "KILN.STUDIO", font(MONO, 16), PAPER, 3.4)
    right(d, W - m, H - 96, "BLENDER · BPY · REACT", font(MONO, 16), SMOKE, 2.4)

    grain(im, 4)
    out = os.path.join(ROOT, "ads", "posters", "kiln-manifesto-1200x1600.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out, optimize=True)
    print("  ", out)


# ─────────────────────────────────────────────────────────── hiring
def hiring():
    W, H = 1200, 1600
    im = crop("keyart-1600x2000.png", W, H, pos=(0.5, 0.46))
    scrim(im, (0, 0, W, H), INK, [(0.0, 0.72), (0.30, 0.12), (0.62, 0.72), (1.0, 0.98)])
    d = ImageDraw.Draw(im)
    m = 84

    mark(im, m, m, 26)
    tracked(d, (m + 44, m + 2), "KILN", font(SERIF, 26), PAPER, 8)

    y = H * 0.60
    tracked(d, (m, y - 44), "WE ARE HIRING", font(MONO, 17), EMBER_LIT, 3.6)
    d.text((m, y), "Two hands,", font=font(SERIF, 132), fill=PAPER)
    d.text((m, y + 124), "one furnace.", font=font(SERIF, 132), fill=PAPER)

    roles = [
        ("01", "Blender / bpy asset engineer", "Geometry, lighting, exports. You think in scripts."),
        ("02", "Creative developer, WebGL", "R3F, shaders, sixty frames on a cheap phone."),
    ]
    yy = y + 300
    d.rectangle([m, yy - 34, W - m, yy - 32], fill=(58, 57, 54))
    for num, title, sub in roles:
        tracked(d, (m, yy), num, font(MONO, 15), EMBER, 2.4)
        d.text((m + 52, yy - 8), title, font=font(SANS_M, 27), fill=PAPER)
        d.text((m + 52, yy + 30), sub, font=font(SANS, 21), fill=(168, 162, 150))
        yy += 108

    tracked(d, (m, H - 96), "JOBS@KILN.STUDIO", font(MONO, 16), PAPER, 3.4)
    right(d, W - m, H - 96, "LONDON · REMOTE · CONTRACT", font(MONO, 16), SMOKE, 2.2)

    grain(im, 4)
    out = os.path.join(ROOT, "ads", "posters", "kiln-hiring-1200x1600.png")
    im.save(out, optimize=True)
    print("  ", out)


# ─────────────────────────────────────────────────────────── social set
def social():
    """Square + story crops of the hero plate, with the wordmark set once."""
    for tag, W, H, src, pos in [
        ("square", 1080, 1080, "square-1600x1600.png", (0.5, 0.5)),
        ("story", 1080, 1920, "keyart-1600x2000.png", (0.5, 0.42)),
        ("wide", 1920, 1080, "hero-2400x1600.png", (0.55, 0.5)),
    ]:
        im = crop(src, W, H, pos=pos)
        scrim(im, (0, 0, W, H), INK, [(0.0, 0.0), (0.55, 0.0), (1.0, 0.82)])
        d = ImageDraw.Draw(im)
        m = int(W * 0.07)
        mark(im, m, m, int(W * 0.026), PAPER)
        tracked(d, (m + int(W * 0.042), m + 2), "KILN", font(SERIF, int(W * 0.026)), PAPER, int(W * 0.008))
        size = int(W * 0.085)
        d.text((m, H - m - size * 2.1), "Rooms,", font=font(SERIF, size), fill=PAPER)
        d.text((m, H - m - size * 1.05), "not pages.", font=font(SERIF, size), fill=EMBER_LIT)
        grain(im, 4)
        out = os.path.join(ROOT, "ads", "set", f"kiln-{tag}-{W}x{H}.png")
        im.save(out, optimize=True)
        print("  ", out)


def avatars():
    """Profile avatar and cover banner — the mark, at the size each platform crops to."""
    for tag, W, H in [("avatar-1024", 1024, 1024), ("avatar-512", 512, 512), ("cover-1500x500", 1500, 500)]:
        im = Image.new("RGB", (W, H), INK)
        d = ImageDraw.Draw(im)
        if tag.startswith("avatar"):
            # the mark alone, optically centred: at avatar size any wordmark is illegible
            size = int(W * 0.46)
            mark(im, (W - size) / 2, (H - size) / 2, size, PAPER)
        else:
            size = int(H * 0.40)
            m = 78
            mark(im, m, (H - size) / 2 - 10, size, PAPER)
            tracked(d, (m + size + 34, H * 0.5 - size * 0.52 + size * 0.14), "KILN", font(SERIF, int(size * 0.92)), PAPER, 10)
            tracked(d, (m + size + 36, H * 0.5 + size * 0.62 + size * 0.14), "INTERACTIVE ARCHITECTURE", font(MONO, 19), KILN, 3.4)
            right(d, W - m, H * 0.5 + size * 0.62 + size * 0.14, "KILN.STUDIO", font(MONO, 19), SMOKE, 3.0)
        grain(im, 3)
        out = os.path.join(ROOT, "ads", "avatars", f"{tag}.png")
        im.save(out, optimize=True)
        print("  ", out)


if __name__ == "__main__":
    print("kiln print set")
    manifesto()
    hiring()
    social()
    avatars()
