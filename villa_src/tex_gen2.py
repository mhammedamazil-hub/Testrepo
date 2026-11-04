"""Second-generation textures for the villa v2 upgrade (numpy + PIL, no downloads).

The v1 set covered interiors well but the exterior was left with three flat tints:
plaster, grass and "leaf". Close-up renders make that obvious - a wall with no
material variation reads as untextured CG, and a tree made of green spheres reads as
a placeholder.

This adds:

* **alpha leaf cards** - a real leaf silhouette with midrib, veins and edge erosion, so
  vegetation can be built from thousands of cards instead of spheres;
* **grass blade cards** - for tufts and ornamental grasses;
* **board-formed concrete**, **lime render**, **travertine cladding**, **asphalt**,
  **gravel**, **paving**, **timber slats** and **bark** for the architecture and site.

All maps are tileable and every colour is written as sRGB-ready albedo, with a tangent
normal map and a roughness map, exactly like `tex_gen.py`.

    python villa_src/tex_gen2.py            # writes villa/tex/*.png
"""
import math
import os

import numpy as np
from PIL import Image

from .tex_gen import S, OUT, _norm01, _smoothstep, _tint, fbm, normal_map, value_noise


# ------------------------------------------------------------------ save helpers
def _save_rgba(name, alb, alpha, nrm=None, rough=None, h=None, nstr=2.0):
    """Save albedo RGB + a separate alpha PNG + normal + roughness."""
    os.makedirs(OUT, exist_ok=True)
    a = np.clip(alb, 0, 1)
    al = np.clip(alpha, 0, 1)
    img = np.concatenate([a, al[..., None]], axis=-1)
    Image.fromarray((img * 255).astype(np.uint8), mode="RGBA").save(
        os.path.join(OUT, f"{name}_alb.png"))
    if nrm is None:
        nrm = normal_map(_norm01(h) if h is not None else np.zeros((S, S)), nstr)
    Image.fromarray((np.clip(nrm, 0, 1) * 255).astype(np.uint8)).save(
        os.path.join(OUT, f"{name}_nrm.png"))
    if rough is not None:
        Image.fromarray((np.clip(rough, 0, 1) * 255).astype(np.uint8)).convert("RGB").save(
            os.path.join(OUT, f"{name}_rough.png"))


def _sstep(e0, e1, x):
    """Smoothstep that also accepts e0 > e1 (a falling edge).

    `tex_gen._smoothstep` clamps the denominator to a positive number, so a reversed
    edge silently returns 0 everywhere - which is exactly what hid every joint and
    plank seam in the first draft of these maps.
    """
    t = np.clip((x - e0) / (e1 - e0 if abs(e1 - e0) > 1e-9 else 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def _band(x, soft):
    """1 in the middle of a repeating 0..1 band, 0 at the seam, with `soft` feather."""
    return _sstep(0.0, soft, x) * _sstep(1.0, 1.0 - soft, x)


def _grid(n=S):
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    return (x + 0.5) / n, (y + 0.5) / n


# ------------------------------------------------------------------ vegetation
def leaf_card(name, seed, hue=(0.11, 0.19, 0.045), tip=(0.20, 0.30, 0.09),
              length=1.0, width=0.42, serrate=0.0, veins=7, dry=0.0):
    """A single leaf filling the card, with alpha.

    Shape: a pointed ellipse (u along the leaf, v across). The alpha edge is eroded
    with noise so silhouettes are not a clean vector outline - the single strongest
    cue that a card is a card and not a leaf.
    """
    u, v = _grid()
    # u runs along the leaf (0 = stem, 1 = tip), v across (-1..1)
    uu = u
    vv = (v - 0.5) * 2.0
    taper = np.sin(np.pi * np.clip(uu, 0, 1)) ** 0.55
    taper = taper * (0.55 + 0.45 * uu)                 # widest past the middle
    inside = np.abs(vv) <= (taper * width * 2.0)
    if serrate > 0:
        # serrated edge: small teeth along the outline
        teeth = np.sin(uu * 2 * np.pi * 26.0) * serrate * 0.06
        inside = np.abs(vv) <= (taper * width * 2.0 + teeth)
    edge = fbm(S, base_freq=90, octaves=3, seed=seed + 7)
    alpha = _smoothstep(0.0, 0.06, np.where(inside, 1.0, 0.0) - 0.35 * (edge - 0.5))
    alpha = np.where(inside, np.clip(0.85 + 0.35 * (edge - 0.5), 0, 1), 0.0)

    # colour: greener at the base, lighter/yellower at the tip, plus blotches
    blotch = fbm(S, base_freq=8, octaves=5, seed=seed + 3)
    fine = fbm(S, base_freq=120, octaves=2, seed=seed + 5)
    t = np.clip(0.55 * uu + 0.3 * _norm01(blotch) + 0.15 * fine, 0, 1)
    alb = _tint(t, np.array(hue), np.array(tip))

    # midrib + side veins darken slightly
    mid = np.exp(-((vv / 0.035) ** 2))
    alb = alb * (1.0 - 0.14 * mid[..., None])
    # side veins: short, angled towards the tip, low contrast (a hard crosshatch reads
    # as a texture swatch, not a leaf)
    for i in range(veins):
        u0 = 0.10 + 0.80 * i / max(1, veins - 1)
        d = np.abs((uu - u0) - np.abs(vv) * 0.13)
        reach = np.abs(vv) < (taper * width * 1.5) * (1.0 - 0.5 * np.abs(uu - u0))
        ve = np.exp(-((d / 0.006) ** 2)) * reach * 0.55
        alb = alb * (1.0 - 0.10 * ve[..., None])
    # dry/brown patches on older leaves
    if dry > 0:
        patch = _smoothstep(0.55, 0.85, fbm(S, base_freq=5, octaves=4, seed=seed + 11))
        alb = alb * (1 - dry * patch[..., None]) + np.array([0.26, 0.17, 0.06]) * (
            dry * patch[..., None])

    height = (0.5 + 0.5 * np.cos(vv * 1.1)) * 0.35 + 0.15 * mid
    _save_rgba(name, alb, alpha, rough=np.full((S, S), 0.52) + 0.1 * fine,
               h=np.where(inside, height, 0.0), nstr=1.2)


def _ellipse(px, py, cx, cy, ang, a, b):
    """Normalised distance to a rotated ellipse (1.0 = on the outline)."""
    c, s = math.cos(ang), math.sin(ang)
    dx, dy = px - cx, py - cy
    u = dx * c + dy * s
    v = -dx * s + dy * c
    return (u / max(a, 1e-6)) ** 2 + (v / max(b, 1e-6)) ** 2


def leaf_spray(name, seed, leaves=9, spread=52.0, leaf_len=0.17, leaf_w=0.045,
               hue=(0.055, 0.135, 0.028), tip=(0.115, 0.235, 0.055), droop=0.25,
               stem=True):
    """A **spray** of leaves on one stem, as a single alpha card.

    Production foliage is built this way: one card carries a whole twig, so a canopy
    needs a few hundred cards instead of a few thousand, and the silhouette has the
    irregular, airy breaks of real foliage instead of isolated dots.

    Geometry is stated in card units (0..1): the stem runs up the middle, leaves are
    rotated ellipses alternating left/right, and the whole spray occupies the full card
    so no texture area is wasted.
    """
    px, py = _grid()
    rng = np.random.default_rng(seed)
    alpha = np.zeros((S, S))
    shade = np.zeros((S, S))
    lean = 0.04 * np.sin(py * 3.1 + rng.uniform(0, 6))
    if stem:
        alpha = np.maximum(alpha, (np.abs(px - (0.5 + lean)) < 0.010).astype(float) * 0.9)
    n = leaves
    for i in range(n):
        # leaves distributed along the stem; the oldest (lowest) are the biggest
        t = 0.06 + 0.88 * i / max(1, n - 1)
        side = 1.0 if i % 2 == 0 else -1.0
        size = leaf_len * (1.06 - 0.55 * t) * rng.uniform(0.85, 1.15)
        wide = leaf_w * (1.0 - 0.40 * t) * rng.uniform(0.85, 1.15)
        ang = math.radians(spread * side * (0.55 + 0.85 * rng.random()))
        ox = 0.5 + float(lean[int(t * (S - 1)), 0]) + side * 0.008
        # leaf grows upward from its stem attachment point, opening sideways
        a_len = size * (0.55 + 0.45 * abs(math.sin(ang)))
        cx = ox + math.sin(ang) * size * 0.45
        cy = t + math.cos(ang) * size * 0.45
        # droop: bend the leaf tip downward as it gets further out
        e = _ellipse(px, py, cx, cy, ang, a_len, wide)
        m = e < 1.0
        alpha = np.maximum(alpha, m.astype(float))
        shade = np.maximum(shade, np.where(m, 0.55 + 0.45 * (1.0 - e), 0.0))
    edge = fbm(S, base_freq=110, octaves=2, seed=seed + 4)
    alpha = np.clip(alpha * (0.90 + 0.20 * (edge - 0.5)), 0, 1)
    blotch = fbm(S, base_freq=12, octaves=4, seed=seed + 2)
    t = np.clip(0.28 + 0.34 * _norm01(blotch) + 0.38 * shade, 0, 1)
    alb = _tint(t, np.array(hue), np.array(tip))
    # Real foliage albedo is low (a leaf reflects ~10-25 % of light). Anything brighter
    # renders as pale flowers once the sun hits it.
    alb = alb * (0.60 + 0.28 * shade[..., None])
    _save_rgba(name, alb, alpha, rough=np.full((S, S), 0.55) + 0.1 * edge,
               h=np.where(alpha > 0.2, shade, 0.0), nstr=1.0)


def grass_blade(name, seed):
    """A single tapered blade, tall in V, for tufts and meadow edges."""
    u, v = _grid()
    vv = (v - 0.5) * 2.0
    taper = (1.0 - u) ** 0.8 * 0.55 + 0.06
    inside = np.abs(vv) < taper
    edge = fbm(S, base_freq=70, octaves=3, seed=seed + 3)
    alpha = np.where(inside, np.clip(0.9 + 0.3 * (edge - 0.5), 0, 1), 0.0)
    t = np.clip(0.55 * u + 0.45 * _norm01(fbm(S, base_freq=20, octaves=4, seed=seed)), 0, 1)
    alb = _tint(t, np.array([0.045, 0.085, 0.022]), np.array([0.20, 0.26, 0.075]))
    _save_rgba(name, alb, alpha, rough=np.full((S, S), 0.6), h=taper, nstr=0.8)


def bark(name, seed):
    """Deep vertical fissures, grey-brown, for trunks and branches."""
    warp = fbm(S, base_freq=6, octaves=4, seed=seed, aspect=(1.0, 1.0))
    ridges = fbm(S, base_freq=22, octaves=5, seed=seed + 2, aspect=(1.0, 0.12))
    fiss = _norm01(0.65 * ridges + 0.35 * warp)
    h = np.clip(fiss ** 1.5, 0, 1)
    alb = _tint(h, np.array([0.055, 0.048, 0.040]), np.array([0.24, 0.215, 0.185]))
    moss = _smoothstep(0.62, 0.9, fbm(S, base_freq=9, octaves=4, seed=seed + 9))
    alb = alb * (1 - 0.5 * moss[..., None]) + np.array([0.12, 0.16, 0.07]) * (
        0.5 * moss[..., None])
    _save_rgba(name, alb, np.ones((S, S)), rough=np.full((S, S), 0.86), h=h, nstr=3.0)


# ------------------------------------------------------------------ architecture
def lime_render(name, seed, c=(0.80, 0.785, 0.745)):
    """Hand-applied lime render: near-flat colour with trowel clouds and fine grain."""
    cloud = fbm(S, base_freq=3, octaves=5, seed=seed)
    trowel = fbm(S, base_freq=7, octaves=3, seed=seed + 4, aspect=(1.6, 0.35))
    grain = fbm(S, base_freq=220, octaves=2, seed=seed + 8)
    h = 0.55 * grain + 0.25 * cloud + 0.20 * trowel
    v = 0.86 + 0.16 * _norm01(0.6 * cloud + 0.4 * trowel) - 0.05 * grain
    alb = np.array(c)[None, None, :] * v[..., None]
    # faint damp/weather streaks
    streak = fbm(S, base_freq=3, octaves=4, seed=seed + 12, aspect=(14.0, 0.6))
    dirt = _smoothstep(0.58, 0.92, streak)
    alb = alb * (1 - 0.10 * dirt[..., None])
    _save_rgba(name, alb, np.ones((S, S)), rough=0.80 + 0.12 * _norm01(grain), h=h, nstr=0.7)


def board_concrete(name, seed, c=(0.56, 0.545, 0.515)):
    """Board-formed concrete: horizontal plank marks + form-tie holes."""
    planks = 9
    u, v = _grid()
    band = (v * planks) % 1.0
    seam = _band(band, 0.045)
    wood = fbm(S, base_freq=40, octaves=3, seed=seed + 2, aspect=(1.0, 6.0))
    patch = fbm(S, base_freq=4, octaves=5, seed=seed)
    h = 0.55 * seam * (0.7 + 0.3 * wood) + 0.25 * patch + 0.20 * wood
    # tie holes: a sparse grid
    holes = np.zeros((S, S))
    rng = np.random.default_rng(seed)
    for cx in (0.25, 0.75):
        for cy in np.arange(0.06, 1.0, 0.22):
            d = np.sqrt((u - cx) ** 2 + (v - cy) ** 2)
            holes = np.maximum(holes, _smoothstep(0.019, 0.011, d))
    h = h - 0.6 * holes
    val = 0.92 + 0.12 * _norm01(patch) - 0.34 * (1 - seam) - 0.35 * holes
    alb = np.array(c)[None, None, :] * val[..., None]
    stain = _smoothstep(0.6, 0.95, fbm(S, base_freq=3, octaves=4, seed=seed + 6,
                                      aspect=(0.5, 8.0)))
    alb = alb * (1 - 0.16 * stain[..., None])
    _save_rgba(name, alb, np.ones((S, S)), rough=0.72 + 0.14 * _norm01(patch), h=h, nstr=1.6)


def travertine_clad(name, seed, strips=6):
    """Long stone strips with open joints - a common modern villa facade."""
    u, v = _grid()
    band = (v * strips) % 1.0
    joint = _band(band, 0.045)
    pit = fbm(S, base_freq=30, octaves=5, seed=seed, aspect=(2.5, 1.0))
    idx = np.clip((v[:, 0] * strips).astype(int), 0, strips - 1)
    band_tone = np.random.default_rng(seed).random(strips)
    tone = band_tone[idx]
    h = 0.6 * joint + 0.4 * pit
    val = (0.78 + 0.26 * tone)[:, None] * (0.88 + 0.22 * _norm01(pit)) * (0.35 + 0.65 * joint)
    base = np.array([0.79, 0.735, 0.655])
    alb = base[None, None, :] * val[..., None]
    _save_rgba(name, alb, np.ones((S, S)), rough=0.55 + 0.2 * _norm01(pit), h=h, nstr=2.2)


def paving(name, seed, nx=3, ny=3, c0=(0.60, 0.585, 0.545), c1=(0.72, 0.705, 0.665)):
    """Large-format external paving with fine joints and water staining."""
    u, v = _grid()
    gx = _band((u * nx) % 1.0, 0.022)
    gy = _band((v * ny) % 1.0, 0.022)
    joint = gx * gy
    stone = fbm(S, base_freq=18, octaves=5, seed=seed)
    speck = fbm(S, base_freq=260, octaves=2, seed=seed + 3)
    h = 0.5 * joint + 0.35 * stone + 0.15 * speck
    alb = _tint(_norm01(0.7 * stone + 0.3 * speck), np.array(c0), np.array(c1))
    alb = alb * (0.34 + 0.66 * joint[..., None])
    _save_rgba(name, alb, np.ones((S, S)), rough=0.68 + 0.12 * _norm01(speck), h=h, nstr=1.8)


def asphalt(name, seed, c=(0.115, 0.115, 0.12)):
    agg = fbm(S, base_freq=300, octaves=2, seed=seed)
    fine = fbm(S, base_freq=60, octaves=4, seed=seed + 2)
    h = 0.7 * agg + 0.3 * fine
    alb = np.array(c)[None, None, :] * (0.75 + 0.55 * _norm01(h))[..., None]
    _save_rgba(name, alb, np.ones((S, S)), rough=0.82 + 0.1 * _norm01(fine), h=h, nstr=1.4)


def lawn(name, seed, c0=(0.030, 0.068, 0.016), c1=(0.098, 0.185, 0.045)):
    """Mown lawn: fine blade streaks, clover patches, slight mowing-band variation.

    v1's grass map was brown-olive at a 2 m tile, which is why the garden read as a
    khaki carpet. Real lawn is *dark and saturated green* under an AgX view transform,
    because the transform desaturates highlights.
    """
    u, v = _grid()
    blades = fbm(S, base_freq=180, octaves=3, seed=seed, aspect=(1.0, 4.0))
    clump = fbm(S, base_freq=22, octaves=4, seed=seed + 2)
    patch = fbm(S, base_freq=4, octaves=4, seed=seed + 5)
    cut = 0.5 + 0.5 * np.sin(v * 2 * np.pi * 6.0)
    t = np.clip(0.34 * _norm01(blades) + 0.36 * _norm01(clump) + 0.24 * _norm01(patch)
                + 0.06 * cut, 0, 1)
    alb = _tint(t, np.array(c0), np.array(c1))
    dry = _smoothstep(0.72, 0.95, fbm(S, base_freq=7, octaves=3, seed=seed + 9))
    alb = alb * (1 - 0.35 * dry[..., None]) + np.array([0.14, 0.13, 0.055]) * (
        0.35 * dry[..., None])
    _save_rgba(name, alb, np.ones((S, S)), rough=np.full((S, S), 0.92),
               h=blades * 0.7 + clump * 0.3, nstr=1.1)


def gravel(name, seed, c0=(0.42, 0.40, 0.37), c1=(0.66, 0.63, 0.58)):
    """Loose gravel: rounded pebbles from a cellular-ish threshold of noise."""
    pts = fbm(S, base_freq=90, octaves=3, seed=seed)
    fine = fbm(S, base_freq=280, octaves=2, seed=seed + 5)
    h = np.clip(0.7 * pts + 0.3 * fine, 0, 1)
    alb = _tint(_norm01(h), np.array(c0), np.array(c1))
    _save_rgba(name, alb, np.ones((S, S)), rough=0.80 + 0.15 * _norm01(fine), h=h, nstr=2.6)


def timber_slat(name, seed, c0=(0.30, 0.19, 0.105), c1=(0.52, 0.36, 0.21)):
    """Warm timber with strong grain, used for pergola slats and soffits."""
    grain = fbm(S, base_freq=60, octaves=4, seed=seed, aspect=(1.0, 0.10))
    rings = fbm(S, base_freq=18, octaves=4, seed=seed + 4, aspect=(1.0, 0.06))
    h = 0.6 * rings + 0.4 * grain
    alb = _tint(_norm01(0.75 * rings + 0.25 * grain), np.array(c0), np.array(c1))
    _save_rgba(name, alb, np.ones((S, S)), rough=0.52 + 0.12 * _norm01(grain), h=h, nstr=1.5)


def water_ripple(name, seed):
    """Normal-only ripple map for the pool: overlapping circular wavelets."""
    u, v = _grid()
    h = np.zeros((S, S))
    rng = np.random.default_rng(seed)
    for _ in range(26):
        cx, cy = rng.random(2)
        f = rng.uniform(9, 26)
        ph = rng.uniform(0, 6.28)
        amp = rng.uniform(0.3, 1.0)
        h += amp * np.sin(2 * np.pi * f * np.hypot(u - cx, v - cy) + ph) / (1 + 30 * np.hypot(
            u - cx, v - cy))
    h += 0.6 * fbm(S, base_freq=10, octaves=4, seed=seed + 2)
    alb = np.tile(np.array([0.035, 0.075, 0.085])[None, None, :], (S, S, 1))
    _save_rgba(name, alb, np.ones((S, S)), rough=np.full((S, S), 0.045), h=_norm01(h), nstr=1.1)


def main():
    os.makedirs(OUT, exist_ok=True)
    print("tex_gen2 ->", os.path.abspath(OUT), flush=True)
    # vegetation: spray cards (canopies) + single-leaf cards (palms, agave, grass)
    leaf_spray("spray_a", 2001, leaves=9, spread=58, leaf_len=0.21, leaf_w=0.055,
               hue=(0.050, 0.120, 0.025), tip=(0.10, 0.210, 0.048), droop=0.30)
    leaf_spray("spray_b", 2013, leaves=11, spread=48, leaf_len=0.17, leaf_w=0.042,
               hue=(0.042, 0.105, 0.023), tip=(0.085, 0.190, 0.042), droop=0.20)
    leaf_spray("spray_c", 2027, leaves=7, spread=64, leaf_len=0.24, leaf_w=0.062,
               hue=(0.070, 0.145, 0.035), tip=(0.130, 0.240, 0.060), droop=0.40)
    leaf_spray("spray_dark", 2051, leaves=10, spread=52, leaf_len=0.19, leaf_w=0.048,
               hue=(0.012, 0.030, 0.008), tip=(0.030, 0.065, 0.016), droop=0.25)
    leaf_spray("spray_olive", 2039, leaves=13, spread=40, leaf_len=0.15, leaf_w=0.022,
               hue=(0.100, 0.130, 0.070), tip=(0.170, 0.190, 0.110), droop=0.15)
    leaf_card("leaf_card_a", 1001, hue=(0.10, 0.235, 0.045), tip=(0.24, 0.44, 0.11),
              width=0.40, veins=7, dry=0.10)
    leaf_card("leaf_card_b", 1013, hue=(0.075, 0.185, 0.038), tip=(0.20, 0.36, 0.085),
              width=0.34, serrate=1.0, veins=6)
    leaf_card("leaf_card_c", 1027, hue=(0.13, 0.265, 0.06), tip=(0.32, 0.46, 0.15),
              width=0.46, veins=8, dry=0.18)
    leaf_card("leaf_card_olive", 1031, hue=(0.17, 0.21, 0.095), tip=(0.30, 0.34, 0.165),
              width=0.22, veins=5)
    grass_blade("grass_blade", 1103)
    bark("bark", 1201)
    # architecture + site
    lime_render("lime_render", 1301)
    lime_render("lime_warm", 1311, c=(0.775, 0.735, 0.665))
    board_concrete("board_concrete", 1321)
    travertine_clad("travertine_clad", 1331)
    paving("stone_paving", 1341)
    asphalt("asphalt", 1351)
    gravel("gravel", 1361, c0=(0.30, 0.285, 0.26), c1=(0.48, 0.46, 0.42))
    lawn("lawn_v2", 1391, c0=(0.012, 0.048, 0.004), c1=(0.055, 0.150, 0.018))
    timber_slat("timber_slat", 1371)
    water_ripple("water_ripple", 1381)
    print("done:", len([f for f in os.listdir(OUT) if f.endswith(".png")]), "maps", flush=True)


if __name__ == "__main__":
    main()
