#!/usr/bin/env python3
"""Analytic basketball surface: seam layout, UV mapping, leather sampling.

Everything here is defined on the *unit sphere direction* rather than on a mesh,
so the same function drives the geometry, the texture bake and the ray tracer.
That is what keeps the seams exactly aligned with the grooves and the pebble
grain continuous across the whole ball.

Layout: a real 8-panel basketball is four great circles that all pass through
two antipodal "pinch" points. With the pinch axis along Y, the four seam planes
have normals in the X-Z plane (0deg, 45deg, 90deg, 135deg).
"""
from __future__ import annotations

import numpy as np

# Size 7 ball: 24.2 cm diameter, 620 g.
RADIUS = 0.1210
CIRCUMFERENCE = 2 * np.pi * RADIUS

# half-width of the seam channel (metres of chord), and its depth
SEAM_HALF_WIDTH = 0.0026
SEAM_SHOULDER = 1.15          # profile reaches zero at this multiple of the half-width
SEAM_DEPTH = 0.0019

_C = np.cos(np.radians(45.0))
SEAM_NORMALS = np.array([
    [0.0, 0.0, 1.0],
    [1.0, 0.0, 0.0],
    [_C, 0.0, _C],
    [-_C, 0.0, _C],
], dtype=np.float64)


def seam_chord(d: np.ndarray) -> np.ndarray:
    """Distance (metres) from a surface point to its nearest seam plane.

    `d` is a unit direction; the plane containing a great circle with normal n
    is the set d.n = 0, so |d.n| * R is the perpendicular distance to it.
    """
    return np.abs(d @ SEAM_NORMALS.T).min(axis=-1) * RADIUS


def groove_fraction(chord: np.ndarray) -> np.ndarray:
    """1 in the bottom of a seam channel, 0 on the panel surface (smooth)."""
    t = chord / SEAM_HALF_WIDTH
    lo, hi = 0.45, SEAM_SHOULDER
    s = np.clip((t - lo) / (hi - lo), 0.0, 1.0)
    smooth = s * s * (3.0 - 2.0 * s)     # smoothstep
    return 1.0 - smooth


def displacement(d: np.ndarray) -> np.ndarray:
    """Radial displacement from the ideal sphere, in metres (negative = groove)."""
    return -SEAM_DEPTH * groove_fraction(seam_chord(d))


# ------------------------------------------------------------------ UV map ---
def uv_from_dir(d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Equirectangular: u around the Y (pinch) axis, v from -Z pole to +Z pole."""
    x, y, z = d[..., 0], d[..., 1], d[..., 2]
    u = (np.arctan2(y, x) / (2 * np.pi)) % 1.0
    v = 0.5 - np.arcsin(np.clip(z, -1, 1)) / np.pi
    return u, v


def dir_from_uv(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    theta = u * 2 * np.pi
    phi = (0.5 - v) * np.pi           # latitude
    cp = np.cos(phi)
    return np.stack([cp * np.cos(theta), cp * np.sin(theta), np.sin(phi)], axis=-1)


def tangent_frame(d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Unit tangents matching uv_from_dir.

    Tu follows increasing u (around the pinch axis), Tv follows increasing v
    (downwards in the image). The mesh exporter, the baker and the renderer all
    use this, so a normal map baked in this frame is valid everywhere.
    """
    x, y, z = d[..., 0], d[..., 1], d[..., 2]
    r = np.maximum(np.hypot(x, y), 1e-9)
    tu = np.stack([-y / r, x / r, np.zeros_like(z)], axis=-1)
    lat = np.sqrt(np.maximum(1.0 - z * z, 1e-12))
    tv = np.stack([x * z / (r * lat), y * z / (r * lat), -lat], axis=-1)
    tu = tu / np.maximum(np.linalg.norm(tu, axis=-1, keepdims=True), 1e-12)
    tv = tv / np.maximum(np.linalg.norm(tv, axis=-1, keepdims=True), 1e-12)
    return tu, tv


def surface_normal(d: np.ndarray, u: np.ndarray, v: np.ndarray,
                   texture, detail: float = 1.0) -> np.ndarray:
    """Perturbed normal: sphere normal + baked normal map, in world space."""
    tu, tv = tangent_frame(d)
    n_tex = texture.normal_at(u, v) * detail
    n = (tu * n_tex[..., 0:1] + tv * n_tex[..., 1:2] + d * n_tex[..., 2:3])
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)


# ------------------------------------------------------------------ leather ---
def _mirror(t: np.ndarray) -> np.ndarray:
    """Triangular wave: seamless, mirror-repeat tiling with period 2."""
    t = np.mod(t, 2.0)
    return np.where(t > 1.0, 2.0 - t, t)


class LeatherTexture:
    """The generated pebble-leather photograph, sampled seamlessly.

    The tile is applied with mirror-repeat (a triangular wave) so no seam can
    appear at the tile border, and it is sampled in UV space so the grain follows
    the ball exactly like a printed/laminated basketball cover.
    """

    def __init__(self, image_path, u_repeat: float = 7.0, v_repeat: float = 6.2):
        from PIL import Image
        rgb = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.float32) / 255.0
        self.image = rgb
        self.height = rgb.max(axis=2) ** 1.4      # pebbles are the bright bumps
        self.h = rgb.shape[0]
        self.w = rgb.shape[1]
        self.u_repeat = u_repeat
        self.v_repeat = v_repeat

    def _bilinear(self, field: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        h, w = field.shape[0], field.shape[1]
        x = np.clip(x * (w - 1), 0, w - 1.001)
        y = np.clip(y * (h - 1), 0, h - 1.001)
        x0 = x.astype(np.int32)
        y0 = y.astype(np.int32)
        x1 = np.minimum(x0 + 1, w - 1)
        y1 = np.minimum(y0 + 1, h - 1)
        fx = (x - x0)[..., None] if field.ndim == 3 else (x - x0)
        fy = (y - y0)[..., None] if field.ndim == 3 else (y - y0)
        c00 = field[y0, x0]
        c10 = field[y0, x1]
        c01 = field[y1, x0]
        c11 = field[y1, x1]
        return (c00 * (1 - fx) + c10 * fx) * (1 - fy) + (c01 * (1 - fx) + c11 * fx) * fy

    def coords(self, u, v):
        x = _mirror(u * self.u_repeat)
        y = _mirror(v * self.v_repeat)
        return x, y

    def colour(self, u, v) -> np.ndarray:
        x, y = self.coords(u, v)
        return self._bilinear(self.image, x, y)

    def height_at(self, u, v) -> np.ndarray:
        x, y = self.coords(u, v)
        return self._bilinear(self.height, x, y)


class MaterialMaps:
    """Baked PBR maps in the ball's UV space, ready for sampling."""

    def __init__(self, base: np.ndarray, normal: np.ndarray, orm: np.ndarray):
        self.base = base
        self.normal = normal
        self.orm = orm

    @staticmethod
    def _sample(field, u, v):
        h, w = field.shape[:2]
        x = np.clip(u * (w - 1), 0, w - 1.001)
        y = np.clip(v * (h - 1), 0, h - 1.001)
        x0, y0 = x.astype(np.int32), y.astype(np.int32)
        x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
        fx = (x - x0)[..., None] if field.ndim == 3 else (x - x0)
        fy = (y - y0)[..., None] if field.ndim == 3 else (y - y0)
        c00, c10 = field[y0, x0], field[y0, x1]
        c01, c11 = field[y1, x0], field[y1, x1]
        return (c00 * (1 - fx) + c10 * fx) * (1 - fy) + (c01 * (1 - fx) + c11 * fx) * fy

    def color_at(self, u, v) -> np.ndarray:
        return self._sample(self.base, u, v)

    def normal_at(self, u, v) -> np.ndarray:
        n = self._sample(self.normal, u, v) * 2.0 - 1.0
        return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)

    def rough_at(self, u, v) -> np.ndarray:
        return self._sample(self.orm[..., 1], u, v)

    def ao_at(self, u, v) -> np.ndarray:
        return self._sample(self.orm[..., 0], u, v)
