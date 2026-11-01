#!/usr/bin/env python3
"""Photo silhouette carving: build a real car mesh from the 9-view turnaround sheet.

Why this exists
---------------
Generative image-to-3D (InstantMesh) invents geometry that no photograph
supports. A visual hull cannot invent anything: every voxel it keeps is
consistent with every view, so what it produces is defensible. The price is
that it can only recover what silhouettes determine.

Pipeline
--------
1. **Segment** each view of the studio turnaround sheet. The studio background
   is modelled per column as a linear ramp between the top and bottom
   background strips; pixels that are meaningfully darker, brighter or more
   detailed than that model belong to the car.
2. **Calibrate** the four axis-aligned views from the car's real dimensions
   (BMW M5 F90: 4.976 m long, 1.903 m wide, 1.473 m tall, 2.126 m
   mirror-to-mirror). One axis of each view is measured cleanly by its
   bounding box. The render is close to orthographic (front-view aspect 1.442
   vs. the physical 1.443), so the vertical scale equals the horizontal one,
   which places the ground row analytically and drops the floor reflection.
   The sheet is not internally consistent - the "Right Side View" has the nose
   on the right while the "Top View" has it on the left - so the side view is
   mirrored on load. X is defined as nose-at-zero.
3. **Pose-estimate** the five three-quarter views: yaw and elevation are
   searched against the four-view hull, with scale and translation solved in
   closed form by matching projected and photographed bounding boxes. Only
   poses that reconstruct their photograph well are kept.
4. **Carve** in signed-distance space. Each view extrudes its own 2-D signed
   distance field (in metres) along its viewing axis, and the intersection is
   the pointwise max. Distances rather than a binary AND keep the surface free
   of pixel stair-stepping.
5. **Validate** by re-projecting the finished solid into every view and
   reporting silhouette IoU against the photograph.

Usage:
    python tools/carve_car.py --pitch 0.008 --out carved
    python tools/carve_car.py --pitch 0.008 --no-3q      # orthographic views only
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import color, measure, morphology

# ---------------------------------------------------------------- real car ---
LENGTH, WIDTH, HEIGHT, MIRROR_SPAN = 4.976, 1.903, 1.473, 2.126

# name: (file stem, horizontal axis, vertical axis, flip horizontally?)
#   horizontal/vertical axis: which physical axis that image axis measures.
ORTHO_VIEWS = {
    "front": ("0_0_front", "Y", "Z", False),
    "rear": ("0_1_rear", "Y", "Z", False),
    "side": ("2_0_side_right", "X", "Z", True),
    "top": ("1_1_top", "X", "Y", False),
}

THREE_QUARTER_VIEWS = [
    "0_2_side_left_3q",
    "1_0_rear_left_3q",
    "1_2_front_right_3q",
    "2_1_front_left_3q",
    "2_2_rear_right_3q",
]

AXIS_SPAN = {"X": LENGTH, "Y": MIRROR_SPAN, "Z": HEIGHT}


# ------------------------------------------------------------ segmentation ---
def background_model(lum: np.ndarray, xmax: float = 0.95) -> np.ndarray:
    """Per-column linear ramp between the top and bottom background strips."""
    h, w = lum.shape
    xcut = int(w * xmax)
    top = np.median(lum[0:16, :xcut], axis=0)
    bot = np.median(lum[-14:, :xcut], axis=0)
    ramp = np.linspace(0.0, 1.0, h)[:, None]
    bg = np.empty_like(lum)
    bg[:, :xcut] = top[None, :] * (1 - ramp) + bot[None, :] * ramp
    bg[:, xcut:] = bg[:, xcut - 1: xcut]
    return bg


def segment_view(path: Path, dark: float = 0.10, bright: float = 0.12,
                 detail_thr: float = 0.055, xmargin: float = 0.05,
                 bottom: float = 0.885, erode: int = 2) -> tuple[np.ndarray, np.ndarray]:
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    h, w, _ = rgb.shape
    lum = color.rgb2gray(rgb)
    bg = background_model(lum, 1.0 - xmargin)

    mean = ndimage.uniform_filter(lum, 7)
    var = np.clip(ndimage.uniform_filter(lum * lum, 7) - mean * mean, 0, None)
    detail = np.sqrt(var)

    mask = ((bg - lum) > dark) | ((lum - bg) > bright) | (detail > detail_thr)
    mask[:, int(w * (1 - xmargin)):] = False   # neighbour-view sliver
    mask[int(h * bottom):] = False             # caption pill
    mask = ndimage.binary_closing(mask, np.ones((7, 7)))
    mask = ndimage.binary_fill_holes(mask)
    mask = morphology.remove_small_objects(mask, int(h * w * 0.004))  # keep the car, drop specks

    lab = measure.label(mask)
    if lab.max() == 0:
        raise RuntimeError(f"segmentation found nothing in {path}")
    mask = lab == max(measure.regionprops(lab), key=lambda p: p.area).label
    if erode:
        # the studio floor's contact shadow is within a couple of pixels of the
        # tyre/valance edge; stripping that fringe keeps a thin shadow flap out
        # of the visual hull
        mask = ndimage.binary_erosion(mask, np.ones((2 * erode + 1, 2 * erode + 1)))
    return rgb, mask


def mask_sdf(mask: np.ndarray, u_per_m: float) -> np.ndarray:
    """Signed distance in metres: negative inside the silhouette."""
    inside = ndimage.distance_transform_edt(mask)
    outside = ndimage.distance_transform_edt(~mask)
    return ((outside - inside) / u_per_m).astype(np.float32)


def bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    cols = np.where(mask.any(axis=0))[0]
    rows = np.where(mask.any(axis=1))[0]
    return int(cols.min()), int(rows.min()), int(cols.max()) + 1, int(rows.max()) + 1


class View:
    """One photograph: a mask plus the affine map from car space to its pixels."""

    def __init__(self, name, stem, mask, sdf, u_axis, v_axis, u_aff, v_aff,
                 source="ortho", pose=None, rgb=None):
        self.name, self.stem, self.mask, self.sdf = name, stem, mask, sdf
        self.rgb = None if rgb is None else np.asarray(rgb, dtype=np.float32)
        self.u_axis = np.asarray(u_axis, float)      # metre-projection direction
        self.v_axis = np.asarray(v_axis, float)
        self.u_aff = u_aff                            # (scale, offset) metres -> px
        self.v_aff = v_aff
        self.source, self.pose = source, pose or {}

    def project(self, pts: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        u_m = pts @ self.u_axis
        v_m = pts @ self.v_axis
        u = self.u_aff[0] * u_m + self.u_aff[1]
        v = self.v_aff[0] * v_m + self.v_aff[1]
        return u, v, np.full(len(pts), 1.0)

    def lookup(self, u, v) -> np.ndarray:
        return affine_lookup(self.sdf, u, v)

    def sample_colour(self, u, v) -> np.ndarray:
        """Bilinear RGB sample (0..1) at pixel coordinates."""
        if self.rgb is None:
            return np.full((len(u), 3), 0.5, dtype=np.float64)
        h, w, _ = self.rgb.shape
        x = np.clip(u - 0.5, 0, w - 1.001)
        y = np.clip(v - 0.5, 0, h - 1.001)
        x0, y0 = x.astype(np.int32), y.astype(np.int32)
        x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
        fx, fy = (x - x0)[:, None], (y - y0)[:, None]
        c00 = self.rgb[y0, x0]; c10 = self.rgb[y0, x1]
        c01 = self.rgb[y1, x0]; c11 = self.rgb[y1, x1]
        top = c00 * (1 - fx) + c10 * fx
        bot = c01 * (1 - fx) + c11 * fx
        return (top * (1 - fy) + bot * fy).astype(np.float64)

    def to_json(self) -> dict:
        return {"source": self.source, "stem": self.stem,
                "u_axis": np.round(self.u_axis, 5).tolist(),
                "v_axis": np.round(self.v_axis, 5).tolist(),
                "u_affine": [round(float(a), 4) for a in self.u_aff],
                "v_affine": [round(float(a), 4) for a in self.v_aff],
                "pose": self.pose}


def affine_lookup(field: np.ndarray, u, v) -> np.ndarray:
    ui = np.clip(np.rint(u).astype(np.int32), 0, field.shape[1] - 1)
    vi = np.clip(np.rint(v).astype(np.int32), 0, field.shape[0] - 1)
    return field[vi, ui]


# --------------------------------------------------- axis-aligned calibration --
def symmetry_axis(rgb: np.ndarray, r0: int, r1: int) -> int:
    """Column of the car's mirror plane, from image self-similarity.

    A front or rear render is symmetric about the car's centre line, so the
    column that best maps onto its own reflection is that centre line. This
    survives a cropped framing (the rear cell of the sheet cuts 44 px off the
    car's left flank), which a bounding box does not.
    """
    lum = color.rgb2gray(rgb)
    h, w = lum.shape
    rows = slice(int(r0 + 0.12 * (r1 - r0)), int(r0 + 0.80 * (r1 - r0)))
    band = lum[rows]
    best, best_err = w // 2, np.inf
    for a in range(int(0.25 * w), int(0.95 * w)):
        d = int(min(a, w - 1 - a, 0.34 * w))
        if d < 30:
            continue
        left = band[:, a - d:a]
        right = band[:, a:a + d][:, ::-1]
        err = float(np.mean((left - right) ** 2))
        if err < best_err:
            best, best_err = a, err
    return best


def mirror_complete(mask: np.ndarray, axis: int) -> np.ndarray:
    """Fill in a clipped flank by mirroring the complete one about `axis`."""
    cols = np.arange(mask.shape[1])
    mirror_cols = np.clip(2 * axis - cols, 0, mask.shape[1] - 1)
    mirrored = mask[:, mirror_cols]
    # only trust the mirrored copy where the original is background *and* the
    # source pixel was mirrored from inside the frame
    inside = (2 * axis - cols >= 0) & (2 * axis - cols <= mask.shape[1] - 1)
    return mask | (mirrored & inside[None, :])


def axis_affine(c0: int, c1: int, lo: float, hi: float, invert: bool = False):
    """(scale, offset) mapping a physical interval [lo, hi] onto [c0, c1] pixels."""
    scale = (c1 - c0) / (hi - lo)
    if invert:
        scale = -scale
    return (scale, c0 - scale * (lo if not invert else hi))


def make_ortho_view(name: str, stem: str, haxis: str, vaxis: str, flip: bool,
                    src: Path, out: Path) -> View:
    rgb, mask = segment_view(src / f"{stem}.png")
    if flip:
        rgb, mask = rgb[:, ::-1], mask[:, ::-1]
    c0, r0, c1, r1 = bbox(mask)

    if haxis == "X":
        px_per_m = (c1 - c0) / LENGTH
        u_aff = axis_affine(c0, c1, 0.0, LENGTH)
    else:
        # symmetric view: calibrate from the mirror plane, not the (possibly
        # clipped) bounding box, then mirror the incomplete flank back in
        axis = symmetry_axis(rgb, r0, r1)
        half_px = float(np.abs(np.arange(mask.shape[1]) - axis).max() * 0
                         + (mask * np.abs(np.arange(mask.shape[1])[None, :] - axis)).max())
        px_per_m = half_px / (MIRROR_SPAN / 2)
        u_aff = (px_per_m, float(axis))
        mask = mirror_complete(mask, axis)
        c0, r0, c1, r1 = bbox(mask)
        print(f"    symmetry axis {axis} ({half_px:.0f} px half-span, cropped by "
              f"{max(0, int(axis - (axis - c0)))} px on the near side)")

    if vaxis == "Z":                       # height: anchored on the analytic ground row
        ground = r0 + HEIGHT * px_per_m
        v_aff = (px_per_m * -1.0, ground)  # image rows grow downward
        pose = {"ground_row": round(ground, 2),
                "reflection_px": round(r1 - ground, 1)}
        # a car cannot be below the ground plane: everything under that row is
        # shadow, and left in it extrudes into a thin sheet under the hull
        below = int(np.ceil(ground))
        mask = mask.copy()
        mask[below:] = False
        rgb = rgb.copy()
    else:                                  # plan view: its vertical axis is width
        v_aff = axis_affine(r0, r1, -MIRROR_SPAN / 2, MIRROR_SPAN / 2)
        pose = {}

    u_axis = {"X": (1, 0, 0), "Y": (0, 1, 0)}[haxis]
    v_axis = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[vaxis]

    sdf = mask_sdf(mask, px_per_m)
    Image.fromarray((mask * 255).astype(np.uint8)).save(out / "masks" / f"{name}.png")
    ov = (rgb * 255).astype(np.uint8)
    ov[mask ^ ndimage.binary_erosion(mask, np.ones((3, 3)))] = [0, 255, 0]
    if vaxis == "Z":
        ov[int(round(pose["ground_row"])), :] = [255, 0, 0]
    Image.fromarray(ov).save(out / "masks" / f"{name}_overlay.png")

    pose.update(px_per_m=round(px_per_m, 2), bbox=[c0, r0, c1, r1])
    rgb_out = rgb
    print(f"  {name:16s} bbox {c0},{r0}..{c1},{r1} | {px_per_m:6.1f} px/m"
          + (f" | ground {pose['ground_row']:.0f} ({pose['reflection_px']:.0f} px"
             f" reflection trimmed)" if vaxis == "Z" else " | bbox-affine"))
    return View(name, stem, mask, sdf, u_axis, v_axis, u_aff, v_aff, "ortho", pose, rgb_out)


# ---------------------------------------------------------- pose estimation ---
def screen_axes(yaw_deg: float, elev_deg: float):
    """Camera basis for a view seen from yaw/elevation (degrees).

    `u_axis` is screen-right, `v_axis` screen-up, both in car coordinates.
    """
    th, el = math.radians(yaw_deg), math.radians(elev_deg)
    u = np.array([-math.sin(th), math.cos(th), 0.0])
    v = np.array([-math.cos(th) * math.sin(el), -math.sin(th) * math.sin(el), math.cos(el)])
    return u, v


def fit_projection(points: np.ndarray, u_axis, v_axis, mask: np.ndarray,
                   zoom: float = 1.0):
    """Orthographic fit of a point cloud onto a photograph.

    A single scale is shared by both image axes - that is the whole point. An
    earlier version normalised each axis separately, which erased the aspect
    ratio and made every azimuth score alike.
    """
    u = points @ u_axis
    v = points @ v_axis
    c0, r0, c1, r1 = bbox(mask)
    s = zoom * (r1 - r0) / max(1e-9, v.max() - v.min())     # px per metre
    tu = 0.5 * (c0 + c1) - 0.5 * s * (u.max() + u.min())
    tv = 0.5 * (r0 + r1) + 0.5 * s * (v.max() + v.min())    # v up -> rows down
    return s, tu, tv


def project_to_grid(points, u_axis, v_axis, s, tu, tv, shape):
    u = points @ u_axis * s + tu
    v = -points @ v_axis * s + tv
    out = np.zeros(shape, bool)
    xi = np.clip(u.astype(int), 0, shape[1] - 1)
    yi = np.clip(v.astype(int), 0, shape[0] - 1)
    out[yi, xi] = True
    # a sparse point set cannot fill the silhouette: thicken, then close and fill
    out = ndimage.binary_dilation(out, np.ones((3, 3)))
    out = ndimage.binary_closing(out, np.ones((5, 5)))
    return ndimage.binary_fill_holes(out)


def iou(a: np.ndarray, b: np.ndarray) -> float:
    union = (a | b).sum()
    return float((a & b).sum() / union) if union else 0.0


ZOOMS = (0.90, 0.95, 1.0, 1.05, 1.10)


def estimate_pose(points: np.ndarray, mask: np.ndarray, name: str) -> tuple[dict, float]:
    """Search yaw / elevation / zoom; scale+translation are solved in closed form."""
    c0, r0, c1, r1 = bbox(mask)
    sub = mask[r0:r1, c0:c1]
    sub_pad = np.pad(sub, 3)
    best, best_s = None, -1.0
    for elev in range(0, 41, 4):
        for yaw in range(0, 360, 5):
            u_axis, v_axis = screen_axes(yaw, elev)
            for zoom in ZOOMS:
                s_, tu, tv = fit_projection(points, u_axis, v_axis, mask, zoom)
                sil = project_to_grid(points, u_axis, v_axis, s_, tu, tv, mask.shape)
                crop = sil[r0:r1, c0:c1]
                sc = iou(crop, sub)
                if sc > best_s:
                    best, best_s = (float(yaw), float(elev), float(zoom)), sc
    by, be, bz = best
    for elev in np.arange(max(0, be - 4), be + 4.01, 1.0):
        for yaw in np.arange(by - 5, by + 5.01, 1.0):
            u_axis, v_axis = screen_axes(yaw, elev)
            for zoom in np.arange(bz - 0.05, bz + 0.051, 0.025):
                s_, tu, tv = fit_projection(points, u_axis, v_axis, mask, zoom)
                sil = project_to_grid(points, u_axis, v_axis, s_, tu, tv, mask.shape)
                sc = iou(sil[r0:r1, c0:c1], sub)
                if sc > best_s:
                    best, best_s = (float(yaw), float(elev), float(zoom)), sc
    pose = {"yaw_deg": round(best[0] % 360, 1), "elev_deg": round(best[1], 1),
            "zoom": round(best[2], 3), "hull_iou": round(best_s, 4)}
    print(f"  {name:18s} yaw {pose['yaw_deg']:6.1f}  elev {pose['elev_deg']:4.1f}"
          f"  zoom {pose['zoom']:.2f}  -> hull/photo IoU {best_s:.3f}")
    return pose, best_s


def make_3q_view(name: str, mask: np.ndarray, sdf: np.ndarray, pose: dict) -> View:
    return View(name, name, mask, sdf, pose["u_axis"], pose["v_axis"],
                (pose["s"], pose["tu"]), (-pose["s"], pose["tv"]),
                "three_quarter", pose)


# --------------------------------------------------------------- hull build ---
def carve(views: list[View], xs, ys, zs, chunk: int = 40) -> np.ndarray:
    """Intersection of the extruded silhouette half-spaces, in metres."""
    dist = np.full((xs.size, ys.size, zs.size), -np.inf, dtype=np.float32)
    YY, ZZ = np.meshgrid(ys, zs, indexing="ij")
    for start in range(0, xs.size, chunk):
        stop = min(xs.size, start + chunk)
        n = stop - start
        block = np.empty((n * ys.size * zs.size, 3), dtype=np.float32)
        block[:, 0] = np.repeat(xs[start:stop], ys.size * zs.size)
        block[:, 1] = np.tile(YY.ravel(), n)
        block[:, 2] = np.tile(ZZ.ravel(), n)
        view = np.empty(block.shape[0], dtype=np.float32)
        acc = np.full(block.shape[0], -np.inf, dtype=np.float32)
        for v in views:
            u, vv, _ = v.project(block)
            view[:] = v.lookup(u, vv)
            np.maximum(acc, view + v.pose.get("margin_m", 0.0), out=acc)
        dist[start:stop] = acc.reshape(stop - start, ys.size, zs.size)
    for v in views:
        print(f"    {v.name:20s} {v.source:14s} -> final inside {100*(dist < 0).mean():5.1f}%")
    return dist


def surface_points(mesh, count: int = 60_000) -> np.ndarray:
    pts, _ = _sample_surface(mesh, count)
    return pts


def _sample_surface(mesh, count: int):
    import trimesh
    pts, fidx = trimesh.sample.sample_surface_even(mesh, count)
    return np.asarray(pts, dtype=np.float64), fidx


def marching(dist, xs, ys, zs, pitch, level, blur):
    if blur:
        dist = ndimage.gaussian_filter(dist, blur, mode="nearest")
    # pad with "outside" (not edge) so the iso-surface always closes at the
    # domain boundary; padding with edge values can leave the surface open
    pad = float(np.nanmax(dist)) + 1.0
    verts, faces, _, _ = measure.marching_cubes(
        np.pad(dist, 1, mode="constant", constant_values=pad), level=level,
        spacing=(pitch, pitch, pitch))
    verts -= pitch
    verts += np.array([xs[0] - pitch / 2, ys[0] - pitch / 2, zs[0] - pitch / 2])
    import trimesh
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
    mesh.fix_normals()
    return mesh, dist


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="carve_src")
    ap.add_argument("--out", default="carved")
    ap.add_argument("--pitch", type=float, default=0.008, help="voxel size, metres")
    ap.add_argument("--blur", type=float, default=1.0, help="field blur, voxels")
    ap.add_argument("--level", type=float, default=-0.004, help="iso level, metres")
    ap.add_argument("--pose-points", type=int, default=30000)
    ap.add_argument("--min-pose-iou", type=float, default=0.88)
    ap.add_argument("--margin-3q", type=float, default=-0.025,
                    help="trust radius for pose-estimated views, metres. Negative: a "
                         "point must be clearly outside the photographed silhouette "
                         "before that view is allowed to carve it, because yaw is only "
                         "identifiable to roughly +-30 deg from a silhouette alone.")
    ap.add_argument("--no-3q", action="store_true", help="orthographic views only")
    args = ap.parse_args()

    t0 = time.time()
    src, out = Path(args.src), Path(args.out)
    (out / "masks").mkdir(parents=True, exist_ok=True)

    print("[1] segment + calibrate axis-aligned views")
    ortho = [make_ortho_view(n, *spec, src, out) for n, spec in ORTHO_VIEWS.items()]

    p = args.pitch
    xs = np.arange(p / 2, LENGTH, p)
    ys = np.arange(-MIRROR_SPAN / 2 + p / 2, MIRROR_SPAN / 2, p)
    zs = np.arange(p / 2, HEIGHT, p)
    print(f"    grid {xs.size}x{ys.size}x{zs.size} = {xs.size*ys.size*zs.size/1e6:.1f}M"
          f" voxels @ {p*1000:.1f} mm")

    print("[2] carve 4-view hull (seed for pose estimation)")
    dist = carve(ortho, xs, ys, zs)
    seed_mesh, _ = marching(dist, xs, ys, zs, p, args.level, args.blur)
    pc = surface_points(seed_mesh, args.pose_points)
    print(f"    seed hull {len(seed_mesh.faces)} faces, extents {np.round(seed_mesh.extents, 3)}")

    views = list(ortho)
    poses = {}
    if not args.no_3q:
        print("[3] estimate poses of the five three-quarter views")
        for stem in THREE_QUARTER_VIEWS:
            rgb, mask = segment_view(src / f"{stem}.png")
            pose, iou_val = estimate_pose(pc, mask, stem)
            if iou_val < args.min_pose_iou:
                print(f"    rejected {stem}: hull/photo IoU {iou_val:.3f} < {args.min_pose_iou}")
                continue
            u_axis, v_axis = screen_axes(pose["yaw_deg"], pose["elev_deg"])
            s_, tu, tv = fit_projection(pc, u_axis, v_axis, mask, pose["zoom"])
            pose.update(u_axis=u_axis, v_axis=v_axis, s=s_, tu=tu, tv=tv,
                        px_per_m=round(s_, 2), margin_m=args.margin_3q)
            sdf = mask_sdf(mask, s_)
            views.append(make_3q_view(stem, mask, sdf, pose))
            poses[stem] = pose
            Image.fromarray((mask * 255).astype(np.uint8)).save(out / "masks" / f"{stem}.png")

        print(f"[4] carve {len(views)}-view hull")
        dist = carve(views, xs, ys, zs)

    mesh, dist = marching(dist, xs, ys, zs, p, args.level, args.blur)
    print(f"  mesh: {len(mesh.vertices)} verts / {len(mesh.faces)} faces"
          f" | extents {np.round(mesh.extents, 3)} | watertight {mesh.is_watertight}")

    print("[5] validate: re-project the solid into every view")
    solid = dist < args.level
    (out / "validate").mkdir(exist_ok=True)
    iou_out, cover_out = {}, {}
    for v in views:
        grid = reproject_solid(solid, xs, ys, zs, v)
        iou_out[v.name] = round(iou(grid, v.mask), 4)
        cover_out[v.name] = round(float((grid & v.mask).sum() / max(1, v.mask.sum())), 4)
        vis = np.zeros(v.mask.shape + (3,), np.uint8)
        vis[v.mask & grid] = [70, 110, 70]
        vis[v.mask & ~grid] = [220, 60, 60]     # photo says car, hull misses it
        vis[~v.mask & grid] = [60, 90, 220]     # hull spills outside the photo
        Image.fromarray(vis).save(out / "validate" / f"{v.name}.png")
    print("    silhouette IoU vs photos:", iou_out)
    print("    photo coverage (hull in photo):", cover_out)

    mesh.export(out / "carve_raw.glb")
    (out / "carve_report.json").write_text(json.dumps({
        "pitch_m": p, "iso_level_m": args.level, "blur_voxels": args.blur,
        "views_used": [v.name for v in views],
        "three_quarter_poses": {k: {kk: (vv.tolist() if isinstance(vv, np.ndarray) else vv)
                                    for kk, vv in val.items()} for k, val in poses.items()},
        "ortho_calibration": {v.name: v.to_json() for v in ortho},
        "silhouette_iou": iou_out, "photo_coverage": cover_out,
        "extents_m": np.round(mesh.extents, 4).tolist(),
        "vertices": int(len(mesh.vertices)), "faces": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "seconds": round(time.time() - t0, 1),
        "reference_dimensions_m": {"length": LENGTH, "width": WIDTH,
                                   "height": HEIGHT, "mirror_span": MIRROR_SPAN},
    }, indent=2))
    print(f"done in {time.time() - t0:.1f}s -> {out}/carve_raw.glb")
    return 0


def reproject_solid(solid, xs, ys, zs, view: View) -> np.ndarray:
    """Project the voxel solid onto a view's image plane; returns an occupancy map."""
    idx = np.nonzero(solid)
    if len(idx[0]) == 0:
        return np.zeros_like(view.mask)
    # subsample to keep this cheap
    step = max(1, len(idx[0]) // 400_000)
    pts = np.stack([xs[idx[0][::step]], ys[idx[1][::step]], zs[idx[2][::step]]], axis=1)
    u, v, _ = view.project(pts)
    out = np.zeros_like(view.mask, dtype=bool)
    ui = np.clip(u.astype(int), 0, out.shape[1] - 1)
    vi = np.clip(v.astype(int), 0, out.shape[0] - 1)
    out[vi, ui] = True
    out = ndimage.binary_closing(out, np.ones((5, 5)))
    return ndimage.binary_fill_holes(out)


if __name__ == "__main__":
    raise SystemExit(main())
