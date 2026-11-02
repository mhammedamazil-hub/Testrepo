#!/usr/bin/env python3
"""Build a photoreal basketball: grooved mesh + baked PBR maps.

Geometry, texture and shading all come from one analytic surface description
(`tools/ball_material.py`), so the seam grooves in the mesh, the black rubber in
the albedo and the channel shading in the normal map are the same curves.

Outputs (per tier)
------------------
model.glb            texture-embedded GLB: baseColor + normal + ORM
model.obj/.mtl/.png  engine-friendly OBJ with external maps
print_mm.stl         true-size solid for printing

Usage
-----
    python tools/basketball.py --out basketball          # web tier
    python tools/basketball.py --out basketball_high --tier high
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

import ball_material as bm
from pebble_field import PebbleField, PEBBLE_RELIEF

# Face counts are deliberately modest: a sphere needs far fewer triangles than
# it looks like it does, and every one of them costs more than a texel.
TIERS = {
    "web": {"subdiv": 5, "base": 2048, "jpeg_q": 92},
    "high": {"subdiv": 6, "base": 4096, "jpeg_q": 95},
}

# The cover, not the photo: the generated leather tile is a lit macro shot, so
# its mean is brighter and cooler than a basketball's actual albedo.
LEATHER_TINT = np.array([1.12, 0.66, 0.30], dtype=np.float32)
RUBBER = np.array([0.030, 0.026, 0.024], dtype=np.float32)
LEATHER_ROUGH = 0.62
SEAM_ROUGH = 0.34


# ------------------------------------------------------------------ leather ---
def prefiltered_leather(path: Path, u_repeat: float, tex_size: int) -> bm.LeatherTexture:
    """The tile, blurred hard.

    Its pebble grain is far too coarse to wrap a 24 cm ball (tiled it reads as
    fabric), so the grain itself is synthesised separately; the photograph is
    kept only as slow tonal variation, which means it can be blurred heavily and
    still do its job without aliasing.
    """
    tex = bm.LeatherTexture(path, u_repeat=u_repeat)
    img = Image.fromarray((tex.image * 255).astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(18.0))
    tex.image = np.asarray(img, dtype=np.float32) / 255.0
    tex.height = tex.image.max(axis=2) ** 1.4
    return tex, 18.0


def mottling(d: np.ndarray) -> np.ndarray:
    """Low-frequency variation so the cover is not a uniform colour."""
    x, y, z = d[..., 0], d[..., 1], d[..., 2]
    a = np.sin(2.7 * x + 1.3) * np.sin(3.1 * y + 0.4) * np.sin(2.2 * z + 2.1)
    b = np.sin(6.3 * x - 0.7) * np.sin(5.1 * z + 1.9)
    c = np.sin(11.0 * y + 2.4) * np.sin(9.0 * x + 0.2)
    return 0.030 * a + 0.018 * b + 0.010 * c


# --------------------------------------------------------------------- bake ---
def bake_maps(tex: bm.LeatherTexture, size: int, pebbles: PebbleField,
              rows: int = 512, log=print) -> bm.MaterialMaps:
    """Bake base colour, tangent-space normal and ORM over the whole UV square.

    Baked in horizontal strips: a 4096 map is 16.7 M texels and the pebble
    lookup plus its normal gradients would need several gigabytes at once (this
    sandbox has 3.8 GB), which silently killed the high tier.
    """
    base = np.zeros((size, size, 3), np.float32)
    normal = np.zeros((size, size, 3), np.float32)
    orm = np.zeros((size, size, 3), np.float32)
    vs_all = (np.arange(size, dtype=np.float32) + 0.5) / size
    us = (np.arange(size, dtype=np.float32) + 0.5) / size

    log(f"    {size}x{size} in {int(np.ceil(size / rows))} strips")
    dh_du = np.zeros((rows + 2, size), np.float32)
    for r0 in range(0, size, rows):
        r1 = min(size, r0 + rows)
        n = r1 - r0
        # one extra row either side for the vertical gradient
        lo = max(0, r0 - 1)
        hi = min(size, r1 + 1)
        V = vs_all[lo:hi][:, None] * np.ones((1, size), np.float32)
        U = np.ones((hi - lo, 1), np.float32) * us[None, :]
        d = bm.dir_from_uv(U, V)
        chord = bm.seam_chord(d)
        groove = bm.groove_fraction(chord)

        dome, crease = pebbles.query(d.reshape(-1, 3))
        dome = dome.reshape(U.shape)
        crease = crease.reshape(U.shape)

        albedo = np.clip(tex.colour(U, V) * LEATHER_TINT * (1.0 + mottling(d)[..., None]), 0, 1)
        albedo *= (0.90 + 0.15 * dome)[..., None]
        albedo = albedo * (1.0 - 0.30 * crease[..., None])
        lip = np.exp(-((chord - bm.SEAM_HALF_WIDTH * 1.35) / (bm.SEAM_HALF_WIDTH * 0.55)) ** 2) * 0.35
        albedo = albedo * (1.0 - lip[..., None])
        blend = np.clip(groove, 0, 1)[..., None] ** 0.75
        albedo = albedo * (1 - blend) + RUBBER * blend

        h = (PEBBLE_RELIEF * (dome - 0.5) - 0.70 * PEBBLE_RELIEF * crease
             - bm.SEAM_DEPTH * groove)
        cos_lat = np.maximum(np.sqrt(np.maximum(1.0 - d[..., 2] ** 2, 0.0)), 0.06)
        du = 1.0 / size
        dsu = 2 * np.pi * bm.RADIUS * cos_lat * du
        dsv = np.pi * bm.RADIUS * du
        grad_u = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) / (2 * dsu)
        grad_v = np.gradient(h, axis=0) / dsv
        nn = np.stack([-grad_u, -grad_v, np.ones_like(grad_u)], axis=-1)
        nn /= np.linalg.norm(nn, axis=-1, keepdims=True)

        ao = 1.0 - 0.28 * crease - 0.60 * groove - 0.18 * lip
        rough = 0.56 + 0.16 * (1.0 - dome) + 0.10 * crease
        rough = rough * (1 - blend[..., 0]) + SEAM_ROUGH * blend[..., 0]

        sl = slice(r0 - lo, r0 - lo + n)
        base[r0:r1] = albedo[sl]
        normal[r0:r1] = nn[sl] * 0.5 + 0.5
        orm[r0:r1, :, 0] = np.clip(ao[sl], 0, 1)
        orm[r0:r1, :, 1] = np.clip(rough[sl], 0.05, 1)

    to8 = lambda a: (np.clip(a, 0, 1) * 255.0 + 0.5).astype(np.uint8)
    return bm.MaterialMaps(to8(base), to8(normal), to8(orm))


# ------------------------------------------------------------------- geometry ---
def build_mesh(subdiv: int):
    """Icosphere displaced by the seam profile, with a UV seam split."""
    import trimesh
    base = trimesh.creation.icosphere(subdivisions=subdiv)
    d = np.asarray(base.vertices, dtype=np.float64)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    radius = bm.RADIUS + bm.displacement(d)
    verts = d * radius[:, None]
    faces = np.asarray(base.faces, dtype=np.int64)

    welded = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    normals = np.asarray(welded.vertex_normals, dtype=np.float64)

    u, v = bm.uv_from_dir(d)
    fac_u = u[faces].copy()
    # any triangle straddling the u wrap gets its low corners lifted so the
    # texture is interpolated forwards, never backwards across the whole map
    straddle = (fac_u.min(axis=1) < 0.5) & (fac_u.max(axis=1) > 0.5)
    fac_u[straddle[:, None] & (fac_u < 0.5)] += 1.0

    key = np.stack([np.ravel(faces), (np.ravel(fac_u) >= 1.0).astype(np.int64)], axis=1)
    uniq, inverse = np.unique(key, axis=0, return_inverse=True)
    src = uniq[:, 0]
    # process=True welds the duplicated seam vertices back into a closed shell
    # *without* dropping the split UVs, because they are attached per-vertex
    # afterwards. process=False leaves 320 boundary edges and a non-watertight
    # mesh - measured, not assumed.
    split = trimesh.Trimesh(
        vertices=verts[src],
        faces=inverse.reshape(-1, 3),
        process=True,
    )
    # process=True may also merge vertices by rounding their positions, so the
    # UVs must be rebuilt against the *final* vertex list, not carried over by
    # index (carrying them over silently leaves UVs past 1.0 and misaligns the
    # seam). UV is a function of direction, so just re-evaluate it.
    d_final = np.asarray(split.vertices, dtype=np.float64)
    d_final = d_final / np.linalg.norm(d_final, axis=1, keepdims=True)
    uf, vf = bm.uv_from_dir(d_final)
    # any triangle straddling the u wrap gets its low corners lifted
    faces_arr = np.asarray(split.faces)
    fu = uf[faces_arr].copy()
    straddle = (fu.min(axis=1) < 0.5) & (fu.max(axis=1) > 0.5)
    fu[straddle[:, None] & (fu < 0.5)] += 1.0
    # per-vertex UV: average the (wrapped) u of the triangles touching it
    acc = np.zeros(len(split.vertices))
    cnt = np.zeros(len(split.vertices))
    for k in range(3):
        np.add.at(acc, faces_arr[:, k], fu[:, k])
        np.add.at(cnt, faces_arr[:, k], 1.0)
    uv = np.zeros((len(split.vertices), 2))
    uv[:, 0] = acc / np.maximum(cnt, 1)
    uv[:, 1] = vf
    split.vertex_normals = attached_normals(d_final)
    return welded, split, uv


def attached_normals(d: np.ndarray) -> np.ndarray:
    """Sphere normal, tilted where the seam profile tilts the surface."""
    eps = 2e-4
    n = np.zeros_like(d)
    tangents = [np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])]
    grad = np.zeros_like(d)
    for t in tangents:
        t = t - d * np.einsum("ij,j->i", d, t)[:, None]
        nt = np.linalg.norm(t, axis=1, keepdims=True)
        t = t / np.maximum(nt, 1e-9)
        p_plus = d + eps * t
        p_plus /= np.linalg.norm(p_plus, axis=1, keepdims=True)
        p_minus = d - eps * t
        p_minus /= np.linalg.norm(p_minus, axis=1, keepdims=True)
        r_plus = bm.RADIUS + bm.displacement(p_plus)
        r_minus = bm.RADIUS + bm.displacement(p_minus)
        grad += ((r_plus - r_minus) / (2 * eps))[:, None] * t
    n = d - grad
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)


# ---------------------------------------------------------------------- main ---
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="basketball")
    ap.add_argument("--tier", choices=sorted(TIERS), default="web")
    ap.add_argument("--leather", default="basketball_src/leather_tile.png")
    ap.add_argument("--u-repeat", type=float, default=17.2)
    ap.add_argument("--v-repeat", type=float, default=8.7)
    ap.add_argument("--maps", default="", help="reuse an existing maps .npz")
    args = ap.parse_args()

    t0 = time.time()
    cfg = TIERS[args.tier]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[1] leather tile ({args.u_repeat}x{args.v_repeat} around the ball)")
    tex, sigma = prefiltered_leather(Path(args.leather), args.u_repeat, cfg["base"])
    print(f"    prefilter sigma {sigma:.2f} px (anti-aliasing mip)")

    print(f"[2] bake {cfg['base']}px PBR maps")
    pebbles = PebbleField()
    maps = bake_maps(tex, cfg["base"], pebbles)
    # Lossy encoding on purpose: three uncompressed 2k PNGs are 19 MB of a
    # 20 MB GLB, and at q92/q95 the difference is invisible on a leather cover
    # while the file becomes small enough to actually ship.
    q = cfg["jpeg_q"]
    enc = {}
    for name, arr, quality in (("basecolor", maps.base, q),
                               ("normal", maps.normal, max(q, 95)),
                               ("orm", maps.orm, max(q, 92))):
        path = out / f"{name}.jpg"
        Image.fromarray(arr).save(path, quality=quality, subsampling=0, optimize=True)
        enc[name] = path
    keep_maps = args.tier == "web"     # the high tier's maps live inside its GLB

    print(f"[3] mesh (icosphere subdiv {cfg['subdiv']}, {bm.SEAM_DEPTH*1000:.1f}mm grooves)")
    welded, mesh, uv = build_mesh(cfg["subdiv"])
    print(f"    {len(mesh.faces)} faces / {len(mesh.vertices)} verts"
          f" (seam split adds {len(mesh.vertices) - len(welded.vertices)})")
    print(f"    diameter {2*np.max(np.abs(welded.vertices)):.1f} mm |"
          f" watertight(welded) {welded.is_watertight}")

    print("[4] material + export")
    import trimesh
    def load(path):
        # `.convert()` drops the format hint, and trimesh's glTF exporter picks
        # the embedded MIME type from it - without this every map is re-encoded
        # as PNG and the GLB triples in size.
        img = Image.open(path).convert("RGB")
        img.format = "JPEG"
        return img

    material = trimesh.visual.material.PBRMaterial(
        name="basketball_leather",
        baseColorTexture=load(enc["basecolor"]),
        normalTexture=load(enc["normal"]),
        metallicRoughnessTexture=load(enc["orm"]),
        occlusionTexture=load(enc["orm"]),
        metallicFactor=0.0,
        roughnessFactor=1.0,
    )
    mesh.visual = trimesh.visual.TextureVisuals(uv=uv, material=material)
    glb = out / "model.glb"
    mesh.export(glb)

    if args.tier == "web":
        obj = out / "model.obj"
        mesh.export(obj)
        (out / "model.mtl").write_text(
            "newmtl basketball_leather\nKa 1 1 1\nKd 1 1 1\nKs 0.15 0.15 0.15\n"
            "Ns 42\nd 1\nillum 2\nmap_Kd basecolor.jpg\nmap_Bump normal.jpg\n"
            "map_Ks orm.jpg\n")

    if args.tier == "web":
        # the high tier's print file is the same solid at 4x the density; one
        # printable STL in the repo is enough
        stl = out / "print_mm.stl"
        w = welded.copy()
        w.apply_scale(1000.0)
        w.export(stl)

    if keep_maps is False:
        for path in enc.values():
            path.unlink(missing_ok=True)

    ext = welded.extents * 1000.0
    metrics = {
        "tier": args.tier,
        "diameter_mm": round(float(2 * np.max(np.abs(welded.vertices)) * 1000), 2),
        "extents_mm": [round(float(x), 2) for x in ext],
        "circumference_mm": round(float(bm.CIRCUMFERENCE * 1000), 2),
        "seam_depth_mm": round(bm.SEAM_DEPTH * 1000, 2),
        "seam_width_mm": round(2 * bm.SEAM_HALF_WIDTH * 1000, 2),
        "faces": int(len(mesh.faces)),
        "vertices": int(len(mesh.vertices)),
        "watertight": bool(welded.is_watertight),
        "volume_cm3": round(float(welded.volume * 1e6), 1),
        "leather_repeat": [args.u_repeat, args.v_repeat],
        "pebble_relief_mm": round(PEBBLE_RELIEF * 1000, 3),
        "pebbles": int(len(pebbles.sites)),
        "pebble_spacing_mm": round(pebbles.spacing_m * 1000, 2),
        "maps": {"size": cfg["base"], "encoding": f"JPEG q{cfg['jpeg_q']} (normal q95)"},
        "files": {},
        "seconds": round(time.time() - t0, 1),
    }
    for f in sorted(out.iterdir()):
        if f.is_file():
            metrics["files"][f.name] = f.stat().st_size
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps({k: metrics[k] for k in
                      ("diameter_mm", "faces", "watertight", "watertight")}, indent=1))
    print(f"done in {time.time() - t0:.1f}s -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
