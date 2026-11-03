"""Procedural PBR texture generation (numpy only, no downloads).

Every material in the villa is driven by real image textures generated here, so the
Cycles renders and the exported glTF look identical (glTF cannot carry Blender's
procedural shader nodes).

Output: villa/tex/<name>_alb.png, <name>_nrm.png, <name>_rough.png (all tileable).
"""
import os
import numpy as np
from PIL import Image

S = 1024
OUT = os.path.join(os.path.dirname(__file__), "..", "villa", "tex")


# ---------------------------------------------------------------- noise helpers
def _rng(seed):
    return np.random.default_rng(seed)


def value_noise(size, freq, seed, aspect=(1.0, 1.0)):
    """Tileable bilinear value noise on a freq_x x freq_y lattice."""
    fx = max(1, int(round(freq * aspect[0])))
    fy = max(1, int(round(freq * aspect[1])))
    g = _rng(seed).random((fy, fx))
    # tileable upscale
    yy = np.linspace(0, fy, size, endpoint=False)
    xx = np.linspace(0, fx, size, endpoint=False)
    y0 = np.floor(yy).astype(int) % fy
    x0 = np.floor(xx).astype(int) % fx
    y1 = (y0 + 1) % fy
    x1 = (x0 + 1) % fx
    fy_ = yy - np.floor(yy)
    fx_ = xx - np.floor(xx)
    # smoothstep
    fy_ = fy_ * fy_ * (3 - 2 * fy_)
    fx_ = fx_ * fx_ * (3 - 2 * fx_)
    a = g[np.ix_(y0, x0)]
    b = g[np.ix_(y0, x1)]
    c = g[np.ix_(y1, x0)]
    d = g[np.ix_(y1, x1)]
    wx = fx_[None, :]
    wy = fy_[:, None]
    top = a + (b - a) * wx
    bot = c + (d - c) * wx
    return top + (bot - top) * wy


def fbm(size, base_freq=4, octaves=5, seed=0, gain=0.5, aspect=(1.0, 1.0)):
    out = np.zeros((size, size))
    amp, tot, f = 1.0, 0.0, float(base_freq)
    for o in range(octaves):
        out += amp * value_noise(size, f, seed + o * 17, aspect=aspect)
        tot += amp
        amp *= gain
        f *= 2
    return out / tot


def _norm01(a):
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / max(1e-9, hi - lo)


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / max(1e-9, e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def normal_map(height, strength=2.0):
    """Height (0..1) -> tangent-space normal map RGB uint8."""
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5
    nx = -dx * strength * S / 256.0
    ny = -dy * strength * S / 256.0
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / ln * 0.5 + 0.5, ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5], -1)


def _tint(h, c0, c1):
    """Map a 0..1 height field between two RGB colours."""
    h = h[..., None]
    return np.clip(np.array(c0)[None, None, :] * (1 - h) + np.array(c1)[None, None, :] * h, 0, 1)


def _save(name, alb, nrm, rough=None, h=None, nstr=2.0):
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray((np.clip(alb, 0, 1) ** (1 / 1.0) * 255).astype(np.uint8)).save(
        os.path.join(OUT, f"{name}_alb.png"))
    if nrm is None:
        nrm = normal_map(_norm01(h) if h is not None else np.zeros((S, S)), nstr)
    Image.fromarray((np.clip(nrm, 0, 1) * 255).astype(np.uint8)).save(
        os.path.join(OUT, f"{name}_nrm.png"))
    if rough is not None:
        r = np.clip(rough, 0, 1)
        Image.fromarray((r * 255).astype(np.uint8)).convert("RGB").save(
            os.path.join(OUT, f"{name}_rough.png"))


# ------------------------------------------------------------------- materials
def wood(name, c0, c1, rows, cols, seed, rough=0.45, gap=0.0016, shade_var=0.10,
         rings=13.0, fibre=150.0, joints=True):
    """Realistic wood: staggered planks, ring grain, longitudinal pores, dark seams.

    rows x cols = plank grid per texture tile. Grain runs along X.
    """
    r = _rng(seed)
    v = np.linspace(0, 1, S, endpoint=False)
    X, Y = np.meshgrid(v, v)

    warp = fbm(S, base_freq=4, octaves=5, seed=seed)              # isotropic, no lattice bands
    fine = fbm(S, base_freq=22, octaves=4, seed=seed + 5)

    rowf = Y * rows
    row_id = np.floor(rowf).astype(int) % rows
    row_frac = rowf - np.floor(rowf)                            # 0..1 across the plank

    # ---- ring grain: near-parallel bands, gently wandering along the plank length
    along = X * cols
    ph = row_frac * rings + 0.16 * np.sin(along * 6.283 + 2.0 * warp) \
         + 0.10 * (fine - 0.5) + 0.25 * (warp - 0.5)
    band = 0.5 + 0.5 * np.sin(ph * 2 * np.pi)
    band = band ** 3.0
    # ---- longitudinal pores: high frequency across, near-zero along X
    pore = 0.5 + 0.5 * np.sin((row_frac * fibre + (warp - 0.5) * 26.0) * 2 * np.pi)
    pore = _smoothstep(0.55, 1.0, pore)
    slow = fbm(S, base_freq=2, octaves=3, seed=seed + 9)         # long-scale colour drift

    # ---- per plank tone
    pj = r.random(rows * max(cols, 1) + 64) * 2 - 1
    pid = (row_id * 13 + (np.floor(X * cols).astype(int) % max(cols, 1)) * 7)
    shade = pj[pid % len(pj)] * shade_var

    h = 0.20 * band + 0.12 * pore + 0.40 * fine + 0.28 * slow
    base = _tint(_norm01(h), c0, c1) * (1 + shade[..., None])

    # ---- seams: row gaps + staggered end joints
    seam = np.zeros((S, S))
    drow = np.minimum(rowf % 1.0, 1 - rowf % 1.0) / rows
    seam = np.maximum(seam, 1 - _smoothstep(gap * 0.5, gap, drow))
    if joints and cols > 1:
        for i in range(rows):
            m = row_id == i
            for j in range(int(r.integers(1, cols + 1))):
                jx = (r.random() + j / cols) % 1.0
                dx = np.abs(((X - jx + 0.5) % 1.0) - 0.5)
                seam = np.maximum(seam, m * (1 - _smoothstep(gap * 0.5, gap, dx)))

    base *= (1 - 0.62 * seam)[..., None]
    hh = h - 1.4 * seam
    rough_m = np.clip(rough + 0.14 * seam + 0.06 * (fine - 0.5), 0.05, 0.95)
    _save(name, base, None, rough_m, hh, nstr=2.4)


def stone(name, c0, c1, seed, vein=0.0, rough=0.5, speck=0.0):
    g = fbm(S, base_freq=3, octaves=6, seed=seed)
    a = _tint(_norm01(g), c0, c1)
    h = g.copy()
    if vein > 0:
        # thin veins: iso-lines of a smooth noise field (classic marble construction)
        n1 = fbm(S, base_freq=3, octaves=6, seed=seed + 7)
        n2 = fbm(S, base_freq=7, octaves=5, seed=seed + 8)
        n3 = fbm(S, base_freq=2, octaves=4, seed=seed + 9)
        warp = (n3 - 0.5) * 0.05
        v1 = 1 - _smoothstep(0.0, 0.016, np.abs(n1 + warp - 0.5))
        v2 = 1 - _smoothstep(0.0, 0.009, np.abs(n2 + warp - 0.5))
        m = np.clip(v1 + 0.6 * v2, 0, 1)
        a = a * (1 - vein * m[..., None]) + vein * m[..., None] * np.array([0.33, 0.34, 0.36])
        h = h - 0.25 * m
    if speck > 0:
        sp = _rng(seed + 9).random((S, S))
        m = (sp > 0.995).astype(float) * speck
        a = a * (1 - m[..., None]) + m[..., None] * np.array([0.18, 0.17, 0.16])
    _save(name, a, None, np.clip(rough + 0.05 * (g - 0.5), 0.05, 0.9), h, nstr=1.0)


def plaster(name, c0, seed, rough=0.85, bump=1.0):
    g = fbm(S, base_freq=3, octaves=6, seed=seed)
    fine = fbm(S, base_freq=48, octaves=3, seed=seed + 2)
    h = 0.6 * g + 0.4 * fine
    a = _tint(0.35 + 0.65 * h * bump, np.array(c0) * 0.93, np.array(c0) * 1.04)
    _save(name, a, None, np.clip(rough + 0.08 * (fine - 0.5), 0.05, 1.0), h, nstr=0.9)


def concrete(name, c0, seed, rough=0.72):
    g = fbm(S, base_freq=2, octaves=5, seed=seed)
    mott = fbm(S, base_freq=5, octaves=4, seed=seed + 4)
    pits = fbm(S, base_freq=40, octaves=2, seed=seed + 7)
    h = 0.45 * g + 0.35 * mott + 0.20 * (1 - _smoothstep(0.4, 0.55, pits))
    a = _tint(_norm01(h), np.array(c0) * 0.95, np.array(c0) * 1.05)
    _save(name, a, None, np.clip(rough + 0.07 * (mott - 0.5), 0.05, 1.0), h, nstr=1.1)


def fabric(name, c0, seed, weave=180, rough=0.92, slub=0.5):
    v = np.linspace(0, 1, S, endpoint=False)
    X, Y = np.meshgrid(v, v)
    warp = 0.5 + 0.5 * np.sin(X * weave * 2 * np.pi)
    weft = 0.5 + 0.5 * np.sin(Y * weave * 2 * np.pi)
    twill = 0.5 + 0.5 * np.sin((X + Y) * weave * np.pi)
    w = 0.45 * warp + 0.45 * weft + 0.25 * twill
    sl = fbm(S, base_freq=10, octaves=5, seed=seed, aspect=(1.0, 3.0))
    h = 0.55 * w + slub * sl
    a = _tint(_norm01(h), np.array(c0) * 0.82, np.array(c0) * 1.10)
    _save(name, a, None, np.clip(rough + 0.05 * (sl - 0.5), 0.2, 1.0), h, nstr=1.5)


def leather(name, c0, seed, rough=0.42):
    cell = fbm(S, base_freq=180, octaves=2, seed=seed)
    pebble = fbm(S, base_freq=60, octaves=3, seed=seed + 1)
    broad = fbm(S, base_freq=4, octaves=4, seed=seed + 3)
    h = 0.45 * _smoothstep(0.42, 0.62, cell) + 0.30 * pebble + 0.25 * broad
    a = _tint(0.35 + 0.65 * _norm01(h), np.array(c0) * 0.88, np.array(c0) * 1.10)
    _save(name, a, None, np.clip(rough + 0.10 * (broad - 0.5), 0.1, 0.9), h, nstr=1.1)


def tiles(name, c0, grout, nx, ny, seed, rough=0.28, depth=0.004):
    v = np.linspace(0, 1, S, endpoint=False)
    X, Y = np.meshgrid(v, v)
    fx, fy = X * nx, Y * ny
    dxs = np.minimum(fx % 1.0, 1 - fx % 1.0) / nx
    dys = np.minimum(fy % 1.0, 1 - fy % 1.0) / ny
    d = np.minimum(dxs, dys)
    g = 1 - _smoothstep(depth * 0.4, depth * 0.75, d)
    var = fbm(S, base_freq=nx * 0.7, octaves=3, seed=seed)
    a = _tint(var, np.array(c0) * 0.97, np.array(c0) * 1.03)
    a = a * (1 - g[..., None]) + g[..., None] * np.array(grout)
    h = 1.0 - 0.9 * g
    _save(name, a, None, np.clip(rough + 0.35 * g, 0.05, 1.0), h, nstr=3.0)


def rug(name, c0, c1, seed):
    """Wool rug: fine pile, framed by a woven border (border sits at the UV edge)."""
    v = np.linspace(0, 1, S, endpoint=False)
    X, Y = np.meshgrid(v, v)
    pile = fbm(S, base_freq=120, octaves=3, seed=seed)
    warp = fbm(S, base_freq=30, octaves=4, seed=seed + 4, aspect=(1.0, 12.0))
    pat = 0.5 + 0.5 * np.sin(X * 22 * np.pi) * np.sin(Y * 22 * np.pi)
    t = np.clip(0.55 * _norm01(pile) + 0.30 * pat + 0.15 * _norm01(warp), 0, 1)
    a = _tint(t, c0, c1)
    # border: a 5 % frame in a darker tone
    edge = np.minimum(np.minimum(X, 1 - X), np.minimum(Y, 1 - Y))
    border = _smoothstep(0.030, 0.046, edge) * (1 - _smoothstep(0.056, 0.070, edge))
    inner = 1 - _smoothstep(0.070, 0.085, edge)
    a = a * (1 - 0.55 * inner[..., None]) + 0.55 * inner[..., None] * np.array(c0) * 1.35
    a = a * (1 - border[..., None]) + border[..., None] * np.array(c1) * 0.62
    _save(name, a, None, np.full((S, S), 0.95), pile - 0.06 * border, nstr=2.2)


def foliage(name, seed):
    """Plant leaf texture: mottled greens."""
    g = fbm(S, base_freq=14, octaves=6, seed=seed)
    g2 = fbm(S, base_freq=60, octaves=3, seed=seed + 2)
    t = _norm01(0.7 * g + 0.3 * g2)
    a = _tint(t, np.array([0.035, 0.075, 0.022]), np.array([0.115, 0.20, 0.055]))
    if name.endswith("dark"):
        a = a * 0.55
    _save(name, a, None, np.full((S, S), 0.55), g, nstr=1.8)


def grass(name, seed):
    """Lawn: mottled greens with fine blade streaks."""
    g = fbm(S, base_freq=8, octaves=5, seed=seed)
    blades = fbm(S, base_freq=150, octaves=3, seed=seed + 2, aspect=(1.0, 3.0))
    patch = fbm(S, base_freq=2, octaves=4, seed=seed + 5)
    t = np.clip(0.40 * _norm01(g) + 0.34 * blades + 0.26 * _norm01(patch), 0, 1)
    a = _tint(t, np.array([0.030, 0.055, 0.016]), np.array([0.10, 0.165, 0.038]))
    _save(name, a, None, np.full((S, S), 0.95), blades * 0.7 + g * 0.3, nstr=1.4)


def metal(name, c0, seed, rough=0.32):
    brushed = fbm(S, base_freq=6, octaves=4, seed=seed, aspect=(1.0, 90.0))
    fine = fbm(S, base_freq=200, octaves=2, seed=seed + 1, aspect=(1.0, 40.0))
    h = 0.5 * brushed + 0.5 * fine
    a = _tint(_norm01(h), np.array(c0) * 0.82, np.array(c0) * 1.14)
    _save(name, a, None, np.clip(rough + 0.15 * (h - 0.5), 0.05, 0.8), h, nstr=1.0)


def painting(name, palette, seed, kind="fields"):
    """Abstract wall art: soft colour fields / arcs, canvas-like."""
    r = _rng(seed)
    v = np.linspace(0, 1, S, endpoint=False)
    X, Y = np.meshgrid(v, v)
    canvas = fbm(S, base_freq=60, octaves=3, seed=seed + 3)
    img = np.ones((S, S, 3)) * np.array(palette[0])
    if kind == "fields":
        for i in range(1, len(palette)):
            cx, cy = r.uniform(0.15, 0.85), r.uniform(0.15, 0.85)
            rad = r.uniform(0.18, 0.46)
            wob = fbm(S, base_freq=4, octaves=4, seed=seed + i * 7)
            d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) + 0.06 * (wob - 0.5)
            m = 1 - _smoothstep(rad - 0.012, rad + 0.012, d)
            img = img * (1 - m[..., None]) + m[..., None] * np.array(palette[i])
    else:  # arcy line composition
        img = np.ones((S, S, 3)) * np.array(palette[0])
        for i in range(1, len(palette)):
            cx, cy = r.uniform(0.1, 0.9), r.uniform(0.1, 0.9)
            rad = r.uniform(0.15, 0.40)
            d = np.abs(np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) - rad)
            m = 1 - _smoothstep(r.uniform(0.006, 0.018), r.uniform(0.020, 0.032), d)
            img = img * (1 - m[..., None]) + m[..., None] * np.array(palette[i])
    img = img * (0.94 + 0.10 * canvas[..., None])
    _save(name, img, None, None, canvas, nstr=0.5)


def main():
    os.makedirs(OUT, exist_ok=True)
    print("generating textures ->", os.path.abspath(OUT))
    wood("oak_floor", [0.42, 0.315, 0.225], [0.60, 0.475, 0.355], 10, 2, 11, rough=0.40,
         rings=11.0, fibre=130.0)
    wood("oak_veneer", [0.415, 0.295, 0.185], [0.625, 0.475, 0.325], 1, 1, 21, rough=0.44,
         rings=9.0, fibre=95.0, joints=False)
    wood("walnut", [0.175, 0.105, 0.062], [0.325, 0.205, 0.125], 1, 1, 31, rough=0.36,
         rings=8.0, fibre=110.0, joints=False)
    plaster("plaster_warm", [0.845, 0.826, 0.795], 41, 0.86)
    plaster("plaster_white", [0.94, 0.94, 0.93], 43, 0.88)
    concrete("microcement", [0.62, 0.61, 0.59], 51, 0.70)
    stone("marble", [0.93, 0.93, 0.92], [0.86, 0.87, 0.88], 61, vein=0.55, rough=0.16)
    tiles("limestone_tile", [0.615, 0.585, 0.525], [0.47, 0.445, 0.40], 2, 2, 71, 0.32, 0.006)
    tiles("bath_tile", [0.80, 0.80, 0.78], [0.62, 0.62, 0.60], 4, 4, 81, 0.22)
    fabric("linen_sand", [0.72, 0.66, 0.56], 91, 200, 0.94, 0.6)
    fabric("linen_graphite", [0.26, 0.26, 0.27], 93, 200, 0.93, 0.5)
    fabric("boucle_cream", [0.88, 0.85, 0.79], 95, 260, 0.95, 0.9)
    fabric("velvet_olive", [0.20, 0.24, 0.15], 97, 300, 0.75, 0.35)
    leather("leather_cognac", [0.33, 0.16, 0.075], 101)
    rug("rug_wool", [0.46, 0.435, 0.395], [0.60, 0.575, 0.525], 111)
    rug("rug_ochre", [0.50, 0.36, 0.19], [0.64, 0.49, 0.28], 113)
    foliage("leaf", 121)
    foliage("leaf_dark", 123)
    grass("grass", 125)
    painting("paint_1", [[0.90, 0.87, 0.80], [0.62, 0.33, 0.18], [0.24, 0.27, 0.22],
                         [0.86, 0.68, 0.42]], 201, "fields")
    painting("paint_2", [[0.16, 0.20, 0.18], [0.86, 0.83, 0.74], [0.55, 0.62, 0.50]],
             203, "fields")
    painting("paint_3", [[0.93, 0.91, 0.86], [0.12, 0.12, 0.13], [0.70, 0.44, 0.24]],
             205, "arcs")
    painting("paint_4", [[0.80, 0.76, 0.68], [0.30, 0.42, 0.44], [0.88, 0.86, 0.80],
                         [0.35, 0.25, 0.18]], 207, "fields")
    metal("steel", [0.78, 0.78, 0.80], 131, 0.30)
    metal("brass", [0.80, 0.63, 0.34], 141, 0.34)
    metal("black_steel", [0.10, 0.10, 0.11], 151, 0.38)
    print("done:", len([f for f in os.listdir(OUT) if f.endswith('.png')]), "maps")


if __name__ == "__main__":
    main()
