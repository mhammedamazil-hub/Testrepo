#!/usr/bin/env python3
"""Physically-plausible ray-traced preview of the basketball.

The repository's splat/triangle rasterisers are fine for checking geometry, but
they cannot show whether a material looks real: they have no specular response,
no Fresnel, no environment. This renderer is a small path-agnostic ray tracer
aimed at one object:

* rays are intersected with the **displaced** surface (radius + seam profile),
* shading = Lambert diffuse + GGX specular from two area lights + a three-band
  studio environment with Fresnel weighting,
* occlusion and roughness come from the baked ORM map, the pebble relief from
  the baked normal map, so what you see is what the GLB contains,
* the backdrop is a studio sweep: vertical gradient, floor bounce, soft contact
  shadow and vignette.

Usage:
    python tools/ball_render.py --mesh basketball/model.glb --out basketball/renders
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import ball_material as bm


# ------------------------------------------------------------------ helpers ---
def normalize(v, axis=-1):
    return v / np.maximum(np.linalg.norm(v, axis=axis, keepdims=True), 1e-12)


def load_maps(paths: dict) -> bm.MaterialMaps:
    def read(p):
        return np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0
    return bm.MaterialMaps(read(paths["base"]), read(paths["normal"]), read(paths["orm"]))


def ggx_specular(n_dot_h, n_dot_l, n_dot_v, v_dot_h, roughness):
    """Cook-Torrance specular, single-scatter, no Fresnel (added separately)."""
    a = np.maximum(roughness, 0.03) ** 2
    a2 = a * a
    denom = n_dot_h * n_dot_h * (a2 - 1.0) + 1.0
    D = a2 / (np.pi * np.maximum(denom, 1e-9) ** 2)
    k = a * 0.5
    G = (n_dot_l / (n_dot_l * (1 - k) + k)) * (n_dot_v / (n_dot_v * (1 - k) + k))
    return D * G / np.maximum(4.0 * n_dot_l * n_dot_v, 1e-6)


def fresnel(cos_theta, f0=0.028):
    return f0 + (1.0 - f0) * (1.0 - np.clip(cos_theta, 0, 1)) ** 5


# --------------------------------------------------------------- ray tracing ---
class Ball:
    """Analytic sphere displaced by the analytic seam profile."""

    def __init__(self, maps: bm.MaterialMaps, radius=bm.RADIUS):
        self.maps = maps
        self.radius = radius

    def hit(self, origins: np.ndarray, dirs: np.ndarray):
        """Returns (t, point, dir_at_surface, t_far) for rays that hit."""
        R = self.radius
        # grooves are < 1 % of the radius, so two fixed-point refinements of a
        # plain sphere intersection land on the displaced surface to microns
        b = np.einsum("ij,ij->i", origins, dirs)
        c = np.einsum("ij,ij->i", origins, origins) - R * R
        disc = b * b - c
        ok = disc > 0
        t = -b - np.sqrt(np.maximum(disc, 0))
        t_near = t.copy()
        for _ in range(2):
            p = origins + dirs * t[:, None]
            d = normalize(p)
            r_eff = R + bm.displacement(d)
            b2 = np.einsum("ij,ij->i", origins, dirs)
            c2 = np.einsum("ij,ij->i", origins, origins) - r_eff ** 2
            disc2 = b2 * b2 - c2
            t = -b2 - np.sqrt(np.maximum(disc2, 0))
        return np.where(ok, t, np.inf), t_near, ok


def _camera_basis(eye_dir, roll_deg=0.0):
    fwd = normalize(-eye_dir)
    up0 = np.array([0.0, 0.0, 1.0])
    right = normalize(np.cross(fwd, up0))
    up = normalize(np.cross(right, fwd))
    th = math.radians(roll_deg)
    r2 = np.array([[math.cos(th), -math.sin(th), 0.0],
                   [math.sin(th), math.cos(th), 0.0], [0.0, 0.0, 1.0]])
    return r2 @ right, r2 @ up, fwd


def _rot_y(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), 0.0, math.sin(a)],
                     [0.0, 1.0, 0.0],
                     [-math.sin(a), 0.0, math.cos(a)]])


def _rot_z(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), -math.sin(a), 0.0],
                     [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])


def render_ball(maps: bm.MaterialMaps, size: int, ss: int = 3,
                cam=(0.93, -0.24, 0.28), fov_deg=30.0, spin=(0.0, 0.0),
                exposure: float = 1.0):
    """Ray-traced ball.

    `spin` = (yaw about Z, pitch about Y) applied to the *ball's* seam layout,
    so successive frames show genuinely different panels while the lighting and
    camera stay put - the way a product turntable is shot.
    """
    W = H = size
    Wp, Hp = W * ss, H * ss
    ys, xs = np.mgrid[0:Hp, 0:Wp]
    px = (xs + 0.5) / Wp * 2 - 1
    py = 1 - (ys + 0.5) / Hp * 2
    half = math.tan(math.radians(fov_deg) / 2)
    dx = px * half
    dy = py * half

    eye_dir = normalize(np.array(cam, float))
    eye = -eye_dir * (6.0 * bm.RADIUS)
    right, up, fwd = _camera_basis(eye_dir)

    dirs = normalize(fwd[None, None, :] + dx[..., None] * right + dy[..., None] * up)
    origins = np.broadcast_to(eye, dirs.shape).reshape(-1, 3)
    dirs = dirs.reshape(-1, 3)

    ball = Ball(maps)
    t, _, ok = ball.hit(origins, dirs)
    hit = ok & np.isfinite(t)
    out = np.zeros((dirs.shape[0], 3), np.float32)
    alpha = hit.astype(np.float32)

    p = origins[hit] + dirs[hit] * t[hit, None]
    d_local = normalize(p)

    # spin the seam layout without moving anything else
    R = _rot_z(spin[0]) @ _rot_y(spin[1])
    d = d_local @ R            # world -> ball-local (R is orthonormal)

    u, v = bm.uv_from_dir(d)
    base = maps.color_at(u, v)
    n_local = bm.surface_normal(d, u, v, maps)
    nrm = normalize(n_local @ R.T)     # back to world space
    rough = np.clip(maps.rough_at(u, v), 0.05, 1.0)
    ao = np.clip(maps.ao_at(u, v), 0.0, 1.0)
    view = normalize(-dirs[hit])

    # ---------------------------------------------------------------- lights
    key_dir = normalize(np.array([-0.55, -0.62, 0.56]))
    fill_dir = normalize(np.array([0.78, -0.30, 0.18]))
    rim_dir = normalize(np.array([0.30, 0.85, 0.35]))

    def lambert(ldir):
        return np.clip(nrm @ ldir, 0, 1)

    # ambient dome: dim floor bounce, brighter sky
    sky = 0.5 + 0.5 * nrm[:, 2]
    ambient = (0.055 + 0.085 * sky)[:, None] * np.array([0.98, 0.94, 0.92])

    col = base * (ambient * ao[:, None] * 2.4)

    for ldir, lcol, power in (
        (key_dir, np.array([1.00, 0.93, 0.82]), 3.20),
        (fill_dir, np.array([0.70, 0.78, 0.92]), 0.38),
        (rim_dir, np.array([1.00, 0.98, 0.95]), 0.75),
    ):
        n_dot_l = lambert(ldir)[:, None]
        col = col + base * lcol * power * n_dot_l * ao[:, None]
        half_v = normalize(ldir + view)
        n_dot_h = np.clip(np.einsum("ij,ij->i", nrm, half_v), 0, 1)
        n_dot_v = np.clip(np.einsum("ij,ij->i", nrm, view), 0, 1)
        v_dot_h = np.clip(np.einsum("ij,ij->i", view, half_v), 0, 1)
        spec = ggx_specular(n_dot_h, np.clip(n_dot_l[:, 0], 1e-4, 1), np.maximum(n_dot_v, 1e-4),
                            v_dot_h, rough)
        col = col + (spec * fresnel(v_dot_h))[:, None] * lcol * power * 1.35 * (n_dot_l > 0.02)

    # environment reflection: soft studio gradient, Fresnel-weighted
    refl = normalize(view - 2.0 * np.einsum("ij,ij->i", view, nrm)[:, None] * nrm)
    # a real studio is bright all round the horizon, which is what separates a
    # dark ball from the backdrop instead of leaving a dead black rim
    horizon = np.exp(-(refl[:, 2] ** 2) / 0.10)
    env = (0.42
           + 0.55 * np.clip(refl[:, 2], 0, 1)[:, None]
           + 1.10 * horizon[:, None]
           + 0.55 * np.clip(refl @ key_dir, 0, 1)[:, None] ** 3)
    env = env * np.array([0.95, 0.96, 1.0])
    n_dot_v = np.clip(np.einsum("ij,ij->i", nrm, view), 0, 1)
    col = col + env * fresnel(n_dot_v, f0=0.05)[:, None] * (0.55 + 0.45 * ao[:, None])

    # the floor is close under the ball: darken the underside and warm it with
    # bounced light, otherwise the ball looks like it is floating
    down = np.clip(-nrm[:, 2], 0, 1)
    col = col * (1.0 - 0.55 * down ** 2)[:, None]
    col = col + (0.030 * down ** 3)[:, None] * np.array([1.0, 0.86, 0.70])

    out[hit] = np.clip(col * exposure, 0, 8.0)
    img = out.reshape(Hp, Wp, 3).reshape(H, ss, W, ss, 3).mean(axis=(1, 3))
    a = alpha.reshape(Hp, Wp).reshape(H, ss, W, ss).mean(axis=(1, 3))
    return img, a


# ------------------------------------------------------------------ backdrop ---
def studio_backdrop(size: int, shadow=None, horizon: float = 0.80) -> np.ndarray:
    """Seamless studio sweep: lit wall, soft floor, contact shadow, vignette.

    The wall/floor transition is a wide smoothstep rather than a line - a hard
    step here reads as a grey bar across the frame, which is exactly what a
    cheap backdrop looks like.
    """
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size

    # wall: bright near the key light, falling off downward and outward
    wall_tone = 0.62 - 0.30 * np.clip(ys / max(horizon, 1e-3), 0, 1)
    key = np.exp(-((xs - 0.30) ** 2 + (ys - 0.10) ** 2) / 0.30)
    wall = (wall_tone + 0.20 * key)[..., None] * np.array([1.00, 0.995, 0.985])

    # floor: darker, slightly warmer, darkening toward the camera
    floor_t = np.clip((ys - horizon * 0.75) / (1.0 - horizon * 0.75), 0, 1)
    floor = (0.46 - 0.24 * floor_t)[..., None] * np.array([1.0, 0.985, 0.97])

    blend = np.clip((ys - horizon + 0.10) / 0.20, 0, 1)[..., None]
    blend = blend * blend * (3.0 - 2.0 * blend)
    bg = wall * (1 - blend) + floor * blend

    if shadow is not None:
        cx, cy = shadow
        # contact core + wide penumbra, both fully soft-edged
        core = np.clip(1.0 - np.sqrt(((xs - cx) / 0.215) ** 2 + ((ys - cy) / 0.062) ** 2), 0, 1) ** 1.5
        soft = np.clip(1.0 - np.sqrt(((xs - cx) / 0.36) ** 2 + ((ys - cy) / 0.10) ** 2), 0, 1) ** 1.7
        dark = np.clip(0.52 * core + 0.30 * soft, 0, 0.72)
        bg = bg * (1.0 - dark[..., None])

    vig = 1.0 - 0.26 * (((xs - 0.5) ** 2 + (ys - 0.5) ** 2) / 0.5) ** 1.1
    return np.clip(bg * vig[..., None], 0, 1)


def composite(ball_rgb, alpha, bg):
    a = alpha[..., None]
    return np.clip(ball_rgb * a + bg * (1 - a), 0, 1)


# ---------------------------------------------------------------------- main ---
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="basketball/renders")
    ap.add_argument("--maps", default="basketball")
    ap.add_argument("--size", type=int, default=900)
    ap.add_argument("--ss", type=int, default=3)
    ap.add_argument("--views", type=int, default=4)
    ap.add_argument("--exposure", type=float, default=0.88)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    md = Path(args.maps)
    def pick(stem):
        for ext in (".jpg", ".png"):
            if (md / f"{stem}{ext}").exists():
                return md / f"{stem}{ext}"
        raise SystemExit(f"missing {stem}.jpg/png in {md}")
    maps = load_maps({"base": pick("basecolor"), "normal": pick("normal"),
                      "orm": pick("orm")})
    print(f"maps {maps.base.shape[0]}px")

    bg = studio_backdrop(args.size)
    for i in range(args.views):
        spin = (360.0 * i / args.views, 12.0 + 7.0 * i)
        rgb, a = render_ball(maps, args.size, ss=args.ss, spin=spin,
                             exposure=args.exposure)
        # contact shadow anchored on the ball's own silhouette
        rows = np.where(a.max(axis=1) > 0.02)[0]
        cols = np.where(a.max(axis=0) > 0.02)[0]
        cy = rows.max() / args.size if rows.size else 0.80
        cx = 0.5 * (cols.min() + cols.max()) / args.size if cols.size else 0.5
        bg_ball = studio_backdrop(args.size, shadow=(cx, cy - 0.02))
        img = composite(rgb, a, bg_ball)
        img = img / (1.0 + 0.42 * img)          # gentle highlight roll-off
        img = np.clip(img, 0, 1) ** (1 / 2.2)   # sRGB encode
        Image.fromarray((img * 255).astype(np.uint8)).save(out / f"ball_{i:02d}.png")
        print(f"  view {i}  spin {spin[0]:.0f}/{spin[1]:.0f} deg -> ball_{i:02d}.png")

    print(f"wrote {args.views} renders -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
