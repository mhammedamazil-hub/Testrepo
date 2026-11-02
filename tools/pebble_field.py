#!/usr/bin/env python3
"""Synthesise the pebble grain of a basketball cover on the unit sphere.

A photographed macro tile cannot be tiled convincingly over a sphere: the
repeats meet at mirror seams and, minified into a 2k map, the grain collapses
into a fabric-like moire. So the pebble field is generated instead - jittered
sites on the sphere, one rounded bump per site - which keeps every pebble
isotropic however the equirectangular map stretches it near the poles, and wraps
seamlessly because it is defined in 3D.

The generated leather photograph is still used, but only for slow colour
variation, where nothing needs to line up.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

# A size-7 ball is ~0.184 m^2 of surface. Pebbles are ~2.4 mm across, so about
# ~24k of them cover the ball at a 2.1 mm pitch (a real size-7 cover).
PEBBLE_SITES = 24_000
PEBBLE_RELIEF = 0.00034      # metres from crease to crown (0.34 mm)


def pebble_sites(n: int = PEBBLE_SITES, jitter: float = 0.36, seed: int = 7) -> np.ndarray:
    """Fibonacci sphere with tangent jitter: even, but not machine-regular."""
    rng = np.random.default_rng(seed)
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)
    theta = np.pi * (1.0 + 5 ** 0.5) * i
    p = np.stack([np.cos(theta) * np.sin(phi),
                  np.sin(theta) * np.sin(phi),
                  np.cos(phi)], axis=1)

    # tangent basis per site, then a random offset inside jitter * spacing
    up = np.where(np.abs(p[:, 2:3]) < 0.9, np.array([[0.0, 0.0, 1.0]]),
                  np.array([[1.0, 0.0, 0.0]]))
    t1 = np.cross(p, up)
    t1 /= np.linalg.norm(t1, axis=1, keepdims=True)
    t2 = np.cross(p, t1)
    spacing = np.sqrt(4 * np.pi / n)
    a = rng.uniform(0, 2 * np.pi, n)
    r = jitter * spacing * np.sqrt(rng.uniform(0, 1, n))
    p = p + (np.cos(a) * r)[:, None] * t1 + (np.sin(a) * r)[:, None] * t2
    return p / np.linalg.norm(p, axis=1, keepdims=True)


class PebbleField:
    """Nearest-site distance field, queried at unit directions."""

    def __init__(self, n: int = PEBBLE_SITES, seed: int = 7):
        self.sites = pebble_sites(n, seed=seed)
        self.tree = cKDTree(self.sites)
        # per-pebble variation: real grain is not a lattice of identical domes
        rng = np.random.default_rng(seed + 1)
        self.scale = np.clip(rng.normal(1.0, 0.085, n), 0.75, 1.30)
        self.depth = np.clip(rng.normal(1.0, 0.10, n), 0.70, 1.35)
        self.flat = np.clip(rng.normal(1.0, 0.14, n), 0.60, 1.55)
        # spacing between neighbouring pebbles, in metres of arc
        d, _ = self.tree.query(self.sites, k=2, workers=-1)
        self.spacing_m = float(np.median(d[:, 1])) * 0.1210

    def query(self, dirs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Returns (height 0..1, crease 0..1) for each direction."""
        dist, idx = self.tree.query(dirs, k=2, workers=-1)
        r1, r2 = dist[..., 0], dist[..., 1]
        near = idx[..., 0]
        # chord distance -> arc distance, for points on the unit sphere
        arc1 = 2.0 * np.arcsin(np.clip(r1 * 0.5, 0, 1))
        cell = np.maximum(r2, 1e-6)
        t = np.clip(arc1 / cell, 0, 1)          # 0 at the site, 1 at the midpoint
        # bigger pebbles reach further across their cell, so t is stretched by
        # their size and the dome profile exponent varies their flatness
        t = np.clip(t / self.scale[near], 0, 1)
        expo = np.sqrt(self.flat[near])
        dome = np.power(np.clip(1.0 - t * t, 0.0, 1.0), 0.40 * expo)
        dome = dome * self.depth[near] ** 0.5
        # the last 18 % of each cell is the crease between pebbles
        crease = np.clip((t - 0.58) / 0.42, 0.0, 1.0)
        crease = crease * crease * (3.0 - 2.0 * crease)
        return dome, crease
