#!/usr/bin/env python3
"""Dependency-free triangle rasteriser with per-pixel texturing.

Why not the verifier's renderer: `verify_mesh.py` rasterises triangles but only
ever samples the texture at a triangle's centroid, and silently subsamples the
face list of big meshes, so it cannot show what a textured asset really looks
like. This one interpolates UVs and vertex normals per pixel through a real
z-buffer, and never drops geometry.

Usage:
    python tools/render_mesh.py MESH --out DIR --frames 6 --size 800x600
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image


def load_mesh(path: Path):
    import trimesh
    obj = trimesh.load(path, force="mesh")
    if isinstance(obj, trimesh.Scene):
        obj = obj.to_geometry()
    return obj


def mesh_arrays(mesh):
    """Vertices, faces, per-vertex normals, per-vertex UVs and an optional texture."""
    v = np.array(mesh.vertices, dtype=np.float64)
    f = np.array(mesh.faces, dtype=np.int64)
    try:
        n = np.array(mesh.vertex_normals, dtype=np.float64)
    except Exception:  # noqa: BLE001
        n = None
    uv = None
    tex = None
    try:
        visual = mesh.visual
        if isinstance(visual, __import__("trimesh").visual.TextureVisuals):
            uv = np.asarray(visual.uv, dtype=np.float64)
            mat = visual.material
            img = getattr(mat, "image", None)
            if img is None:
                # glTF keeps the diffuse map in baseColorTexture; PIL.Image has
                # no `.image` so check for that before trusting it
                img = getattr(mat, "baseColorTexture", None)
            if img is not None and not hasattr(img, "convert"):
                img = None
            if img is not None:
                tex = np.asarray(img.convert("RGB"), dtype=np.float64) / 255.0
        elif visual is not None:
            cols = np.asarray(visual.vertex_colors, dtype=np.float64)[:, :3] / 255.0
            if len(cols) == len(v) and cols.std() > 1e-3:
                tex = ("vcol", cols)
    except Exception:  # noqa: BLE001
        pass
    return v, f, n, uv, tex


def sample_texture(tex, uv):
    """Bilinear texture lookup, uv in [0,1]."""
    if tex is None:
        return np.full((uv.shape[0], 3), 0.62)
    if isinstance(tex, tuple):
        cols = tex[1]
        return cols[np.clip((uv[:, 1] * (len(cols) - 1)).astype(int), 0, len(cols) - 1)]
    h, w, _ = tex.shape
    x = np.clip(uv[:, 0] * (w - 1), 0, w - 1.001)
    y = np.clip(uv[:, 1] * (h - 1), 0, h - 1.001)  # glTF: UV origin is top-left
    x0, y0 = x.astype(np.int32), y.astype(np.int32)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    c00, c10 = tex[y0, x0], tex[y0, x1]
    c01, c11 = tex[y1, x0], tex[y1, x1]
    return (c00 * (1 - fx) + c10 * fx) * (1 - fy) + (c01 * (1 - fx) + c11 * fx) * fy


def render(mesh, angle_deg: float, elev_deg: float, size=(800, 600), fov=28.0,
           bg=(0.055, 0.062, 0.075), light=(0.35, 0.45, 0.82), ambient=0.42,
           supersample=1, flip_up=None):
    W, H = size[0] * supersample, size[1] * supersample
    v, f, n, uv, tex = mesh_arrays(mesh)

    centre = 0.5 * (v.min(0) + v.max(0))
    radius = float(np.linalg.norm(v - centre, axis=1).max())
    dist = radius / math.tan(math.radians(fov) / 2) * 1.06

    th, el = math.radians(angle_deg), math.radians(elev_deg)
    Rz = np.array([[math.cos(th), -math.sin(th), 0], [math.sin(th), math.cos(th), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, math.cos(el), -math.sin(el)], [0, math.sin(el), math.cos(el)]])
    R = Rx @ Rz
    p = (v - centre) @ R.T
    # car axes: X length, Y width, Z up. Put Z up on screen: view along +Y is
    # "front", so rotate so screen axes are (X, Z); depth along Y.
    screen = np.stack([p[:, 0], p[:, 2], p[:, 1]], axis=1)
    if flip_up:
        screen[:, 1] *= -1
    screen[:, 2] += dist

    focal = 0.5 * min(W, H) / math.tan(math.radians(fov) / 2)
    sx = W / 2 + focal * screen[:, 0] / screen[:, 2]
    sy = H / 2 - focal * screen[:, 1] / screen[:, 2]
    sz = screen[:, 2]

    if n is not None:
        nn = n @ R.T
        nrm = np.stack([nn[:, 0], nn[:, 2], nn[:, 1]], axis=1)
    else:
        nrm = None

    zbuf = np.full((H, W), np.inf)
    img = np.zeros((H, W, 3))
    img[:] = bg

    lv = np.array(light, float)
    lv /= np.linalg.norm(lv)

    order = np.argsort(-((v[f].mean(1) - centre) @ np.array([0.0, 0.0, 1.0])))  # stable-ish
    for fi in order:
        idx = f[fi]
        if (sz[idx] <= 0.05).any():
            continue
        ax, ay = sx[idx[0]], sy[idx[0]]
        bx, by = sx[idx[1]], sy[idx[1]]
        cx, cy = sx[idx[2]], sy[idx[2]]
        area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
        if abs(area) < 1e-9:
            continue
        x0 = max(0, int(min(ax, bx, cx)))
        x1 = min(W - 1, int(max(ax, bx, cx)) + 1)
        y0 = max(0, int(min(ay, by, cy)))
        y1 = min(H - 1, int(max(ay, by, cy)) + 1)
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((bx - ax) * (gy - ay) - (gx - ax) * (by - ay)) / area
        w1 = ((gx - ax) * (cy - ay) - (cx - ax) * (gy - ay)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        z = w0 * sz[idx[0]] + w1 * sz[idx[1]] + w2 * sz[idx[2]]
        sub_z = zbuf[y0:y1 + 1, x0:x1 + 1]
        closer = inside & (z < sub_z)
        if not closer.any():
            continue
        sub_z[closer] = z[closer]

        if nrm is not None:
            nn_ = (w0[..., None] * nrm[idx[0]] + w1[..., None] * nrm[idx[1]]
                   + w2[..., None] * nrm[idx[2]])
            nn_ /= np.maximum(np.linalg.norm(nn_, axis=2, keepdims=True), 1e-9)
            lam = np.clip(np.abs(nn_[..., 0] * lv[0] + nn_[..., 1] * lv[1]
                                 + nn_[..., 2] * lv[2]), 0, 1)
            shade = ambient + (1 - ambient) * lam
        else:
            shade = np.full_like(w0, 0.75)

        if uv is not None and tex is not None:
            uu = (w0 * uv[idx[0], 0] + w1 * uv[idx[1], 0] + w2 * uv[idx[2], 0]).ravel()
            vv = (w0 * uv[idx[0], 1] + w1 * uv[idx[1], 1] + w2 * uv[idx[2], 1]).ravel()
            sel = closer.ravel()
            col = np.empty((uniq(sel), 3))
            col = sample_texture(tex, np.stack([uu[sel], vv[sel]], axis=1))
            rgb = np.zeros((*shade.shape, 3))
            rgb[closer] = col
        else:
            base = np.array([0.70, 0.72, 0.76])
            rgb = np.broadcast_to(base, (*shade.shape, 3)).copy()

        sub_img = img[y0:y1 + 1, x0:x1 + 1]
        sub_img[closer] = rgb[closer] * shade[closer][:, None]

    if supersample > 1:
        img = img.reshape(H // supersample, supersample, W // supersample, supersample, 3).mean(axis=(1, 3))
    return np.clip(img * 255.0, 0, 255).astype(np.uint8)


def uniq(mask):
    return int(mask.sum())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh")
    ap.add_argument("--out", default="renders")
    ap.add_argument("--frames", type=int, default=6)
    ap.add_argument("--size", default="800x600")
    ap.add_argument("--elev", type=float, default=16.0)
    ap.add_argument("--start", type=float, default=30.0)
    ap.add_argument("--fov", type=float, default=30.0)
    ap.add_argument("--ss", type=int, default=2, help="supersampling factor")
    args = ap.parse_args()

    W, H = (int(x) for x in args.size.lower().split("x"))
    mesh = load_mesh(Path(args.mesh))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for i in range(args.frames):
        ang = args.start + 360.0 * i / args.frames
        arr = render(mesh, ang, args.elev, (W, H), fov=args.fov, supersample=args.ss)
        Image.fromarray(arr).save(out / f"render_{i:02d}.png")
    print(f"wrote {args.frames} frames -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
