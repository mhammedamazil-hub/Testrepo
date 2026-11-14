"""KILN — motion sting.

A six-second identity animation, built frame by frame from the real Cycles plate and
the identity's own geometry. No stock footage, no template transitions, no JS ray-tracer.

Beats
  0.00–1.10  ink; an ember hairline draws across the optical centre
  1.10–2.30  the kiln door opens: the plate is revealed *through* the arch, not on top of it
  2.30–3.60  slow push inside the arch; KILN tracks up beneath it (+0.20em → +0.06em)
  3.60–4.90  the arch contracts to lockup position; descriptor wipes in
  4.90–6.00  hold; the ember rule fades back to a single pixel

Everything is composited at 2× and downsampled, so edges are clean.

Usage:  python3 scripts/kiln_motion.py
Out:    ads/video/kiln-sting-1080.mp4   H.264, 1080×1080, 24 fps, silent
        ads/video/kiln-sting-1080.webm  VP9 (web embed)
        ads/video/kiln-loop-720.gif     4 s loop for email/Slack
        ads/video/kiln-sting-poster.png 1:1 still, used as <video poster>
"""
import math
import os

import av
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VID = os.path.join(ROOT, "ads", "video")
RN = os.path.join(ROOT, "brand", "renders")
FONTS = os.path.join(ROOT, "fonts")

OUT = 1080
SS = 2                     # supersample factor
W = H = OUT * SS
FPS = 24
DUR = 6.0

INK = (11, 12, 14)
PAPER = (242, 237, 228)
EMBER = (216, 84, 42)
EMBER_LIT = (238, 117, 65)
KILN = (138, 133, 120)

SERIF = os.path.join(FONTS, "instrument-serif.ttf")
MONO = os.path.join(FONTS, "jetbrains-mono.ttf")


# ───────────────────────────────────────────── geometry (mirrors wordmark.js)
class Door:
    """The mark's arch, in a 1000-unit box, expressed in screen units."""
    R = 150.0          # radius
    SPRING = 380.0     # y of the springing line inside the box
    BOX = 1000.0

    @staticmethod
    def path(cx, base, size, open_frac=0.62):
        """Arch outline sitting on `base`, `size` tall. open_frac widens the mouth."""
        s = size / Door.BOX
        r = size * open_frac / 2
        spring = base - (Door.BOX - Door.SPRING) * s
        return r, spring


def arch_mask(W, H, cx, base, height, half=None):
    """Full-frame L mask: a kiln door with feet on `base`, crown `height` above it."""
    half = half if half is not None else height * 0.31
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    r = half
    spring = base - height + r
    d.rectangle([cx - r, spring, cx + r, base], fill=255)
    # draw the semicircular head into a separate layer and union it, otherwise
    # PIL's ellipse is clipped by the rectangle it is drawn over
    head = Image.new("L", (W, H), 0)
    ImageDraw.Draw(head).ellipse([cx - r, spring - r, cx + r, spring + r], fill=255)
    # anything below the feet is not the door — clip the head at the threshold
    np = __import__("numpy")
    h = np.array(head)
    h[int(base):, :] = 0
    return Image.fromarray(np.maximum(np.array(m), h))


# ───────────────────────────────────────────── easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(t):
    """cubic-bezier(0.16, 1, 0.3, 1) approximated by a quintic ease-out."""
    t = clamp(t)
    return 1 - (1 - t) ** 5


def ease_in_out(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def lerp(a, b, k):
    return a + (b - a) * k


# ───────────────────────────────────────────── assets
def load_plate(scale=1.25):
    """The hero plate, cropped square, pre-scaled for the push-in."""
    im = Image.open(os.path.join(RN, "hero-2400x1600.png")).convert("RGB")
    sw, sh = im.size
    side = min(sw, sh // 0.999)
    im = im.crop(((sw - side) // 2, (sh - side) // 2, (sw + side) // 2, (sh + side) // 2))
    big = int(W * scale)
    return im.resize((big, big), Image.LANCZOS)


def tracked_text(draw, xy, text, font, fill, tracking):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return x


def tracked_width(draw, text, font, tracking):
    return sum(draw.textlength(c, font=font) for c in text) + tracking * max(len(text) - 1, 0)


def grain(im, amount=3, seed=0):
    """Deterministic fine grain — keeps the flat ink from banding in H.264."""
    import random
    rnd = random.Random(seed)
    px = im.load()
    for _ in range((W * H) // 240):
        x, y = rnd.randrange(W), rnd.randrange(H)
        r, g, b = px[x, y]
        d = rnd.randint(-amount, amount)
        px[x, y] = (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)))
    return im


# ───────────────────────────────────────────── frame
PLATE = load_plate(1.30)


def frame(t):
    base = Image.new("RGB", (W, H), INK)

    # the door opens out of the lockup, becomes the room, then closes again
    opening = ease_in_out(seg(t, 0.95, 2.55))
    closing = ease_in_out(seg(t, 3.75, 4.55))
    grow = opening * (1 - closing)
    push = 1.0 + 0.10 * ease_out(seg(t, 1.4, 4.2))

    arch_h = lerp(H * 0.400, H * 0.660, grow)
    base_y = lerp(H * 0.700, H * 0.690, closing)   # feet settle a hair as the lockup forms
    half = lerp(H * 0.400 * 0.31, H * 0.245, grow)
    # the room pulls back to show the arch it lives in, then pushes in again
    zoom = lerp(1.34, 1.02, grow)

    crop = int(W / (push * zoom))
    off = int((PLATE.width - crop) / 2 + crop * (0.055 + 0.145 * grow))   # centre the vessel
    top = max(0, int((PLATE.height - crop) / 2 + crop * 0.02))
    plate = PLATE.crop((off, top, off + crop, top + crop)).resize((W, H), Image.LANCZOS)
    # the room reads a stop brighter than the plate does at full frame
    plate = Image.blend(plate, Image.new("RGB", plate.size, (255, 244, 232)), 0.05 + 0.05 * grow)

    mask = arch_mask(W, H, W // 2, base_y, arch_h, half)
    mask = mask.filter(ImageFilter.GaussianBlur(SS * 0.8))

    base.paste(plate, (0, 0), mask)

    # inner shadow: darken the blurred rim of the mask so the render sits *inside*
    # the opening rather than floating on top of it
    if grow > 0.02:
        inset = mask.point(lambda v: 255 if 14 < v < 241 else 0)
        inset = inset.filter(ImageFilter.GaussianBlur(arch_h * 0.05))
        base = Image.composite(Image.new("RGB", (W, H), (6, 6, 7)), base,
                               inset.point(lambda v: int(v * 0.6 * grow)))

    # as the door closes it stops being a photograph and becomes the mark: solid paper.
    solid = clamp(ease_out(seg(t, 4.25, 5.00)) * 1.15)
    if solid > 0.002:
        paper = Image.new("RGB", (W, H), PAPER)
        base.paste(paper, (0, 0), mask.point(lambda v: int(v * solid)))

    # ember edge where the render meets the block — the lit lip of the door
    edge = mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(SS * 1.4))
    ember = Image.new("RGB", (W, H), EMBER)
    base = Image.composite(ember, base, edge.point(lambda v: int(v * 0.30)))

    d = ImageDraw.Draw(base, "RGBA")

    # ── ember hairline: draws in, then retires as the door opens
    hair = ease_out(seg(t, 0.10, 0.95)) * (1 - ease_in_out(seg(t, 1.05, 1.75)))
    hair = max(hair, ease_out(seg(t, 4.55, 5.10)) * 0.9)
    if hair > 0.005:
        y = base_y
        half = W * 0.135 * hair
        d.rectangle([W // 2 - half, y - SS * 1.5, W // 2 + half, y + SS * 1.5], fill=(*EMBER, 255))

    # ── wordmark: present in the lockup, gone while the room is open
    wm = 1 - ease_in_out(seg(t, 0.95, 1.55))
    wm = max(wm, ease_out(seg(t, 4.05, 4.70)))
    if wm > 0.004:
        size = int(H * 0.115)
        f = ImageFont.truetype(SERIF, size)
        track = size * lerp(0.16, 0.06, clamp((t - 4.0) / 0.7))
        text = "KILN"
        w = tracked_width(d, text, f, track)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        tracked_text(ld, (W / 2 - w / 2, base_y + H * 0.055), text, f, (*PAPER, int(255 * wm)), track)
        base = Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")
        d = ImageDraw.Draw(base, "RGBA")

    # ── descriptor returns with the lockup
    dk = ease_out(seg(t, 4.35, 5.15))
    if dk > 0.004:
        f = ImageFont.truetype(MONO, int(H * 0.0155))
        track = f.size * 0.19
        label = "INTERACTIVE ARCHITECTURE"
        w = tracked_width(d, label, f, track)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        tracked_text(ld, (W / 2 - w / 2, base_y + H * 0.215), label, f, (*KILN, int(255 * dk)), track)
        base = Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")
        d = ImageDraw.Draw(base, "RGBA")

    # footer
    fa = int(150 * ease_out(seg(t, 4.45, 5.10)))
    if fa > 4:
        f = ImageFont.truetype(MONO, int(H * 0.0125))
        tracked_text(d, (W * 0.055, H * 0.938), "KILN.STUDIO", f, (*PAPER, fa), f.size * 0.22)
        lbl = "BLENDER · BPY · REACT"
        w = tracked_width(d, lbl, f, f.size * 0.16)
        tracked_text(d, (W * 0.945 - w, H * 0.938), lbl, f, (*KILN, int(fa * 0.85)), f.size * 0.16)

    # vignette
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-W * 0.16, -H * 0.16, W * 1.16, H * 1.16], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(W * 0.07))
    base = Image.composite(base, Image.new("RGB", (W, H), (0, 0, 0)), vig.point(lambda v: int(92 + v * 0.64)))

    base = grain(base, 3, seed=int(t * 100))
    return base.resize((OUT, OUT), Image.LANCZOS)


def main():
    os.makedirs(VID, exist_ok=True)
    n = int(FPS * DUR)
    frames = [frame(i / FPS) for i in range(n)]
    print(f"{n} frames")

    poster = os.path.join(VID, "kiln-sting-poster.png")
    frames[int(FPS * 5.2)].save(poster, optimize=True)
    print(" ", poster)

    for name, codec, opts in [
        ("kiln-sting-1080.mp4", "libx264", {"crf": "18", "preset": "slow", "pix_fmt": "yuv420p"}),
        ("kiln-sting-1080.webm", "libvpx-vp9", {"crf": "32", "b:v": "0"}),
    ]:
        out = av.open(os.path.join(VID, name), "w")
        st = out.add_stream(codec, rate=FPS)
        st.width, st.height = OUT, OUT
        st.pix_fmt = "yuv420p"
        for k, opt in opts.items():
            st.options[k] = opt
        for im in frames:
            for pkt in st.encode(av.VideoFrame.from_image(im)):
                out.mux(pkt)
        for pkt in st.encode():
            out.mux(pkt)
        out.close()
        p = os.path.join(VID, name)
        print(f"  {name}  {os.path.getsize(p) / 1024:.0f} KB")

    # 4 s loop for email — the reveal, forever. 720 px, 12 fps, 96-colour palette so it
    # stays under a few hundred KB; GIF is for Slack and email, not for the site.
    loop = [frame(0.55 + (i / 12.0)).resize((720, 720), Image.LANCZOS).convert(
        "P", palette=Image.ADAPTIVE, colors=96) for i in range(48)]
    gif = os.path.join(VID, "kiln-loop-720.gif")
    loop[0].save(
        gif, save_all=True, append_images=loop[1:], duration=83,
        loop=0, optimize=True, disposal=2,
    )
    print(f"  kiln-loop-720.gif  {os.path.getsize(gif) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
