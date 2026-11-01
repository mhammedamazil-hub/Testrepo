#!/usr/bin/env python3
"""Finish a carved hull: smooth it, project the photographs onto it, export.

The texture is baked **per texel**, not per vertex. For every texel the UV
atlas locates a 3-D point on the surface; that point is projected into the
photographs that face it, using the same calibration the carve used, and the
samples are blended by how squarely each camera sees the surface and by how
deep inside each silhouette the point sits (so silhouette edges, where the
background bleeds in, contribute almost nothing). The result keeps the
photograph's resolution instead of the mesh's.

The car is mirror-symmetric, so the right-flank photograph textures both
flanks; the underside, which no photograph shows, is given a dark neutral tone
rather than invented detail.

Usage:
    python tools/carve_finish.py carved/carve_raw.glb --out refined_carve --tier web
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import carve_car as cc  # noqa: E402
import refine_mesh as rm  # noqa: E402
import trimesh  # noqa: E402

TIERS = {
    "web": {"faces": 45_000, "texture": 2048},
    "high": {"faces": 160_000, "texture": 4096},
}


def taubin(mesh, iterations: int, lamb: float = 0.5, nu: float = -0.53):
    """Shrink-free smoothing: alternate a positive and a slightly larger negative step."""
    if iterations <= 0:
        return mesh
    v = np.asarray(mesh.vertices, dtype=np.float64)
    f = np.asarray(mesh.faces)
    edges = np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    n = len(v)
    for _ in range(iterations):
        for factor in (lamb, nu):
            acc = np.zeros_like(v)
            cnt = np.zeros(n)
            np.add.at(acc, edges[:, 0], v[edges[:, 1]])
            np.add.at(acc, edges[:, 1], v[edges[:, 0]])
            np.add.at(cnt, edges[:, 0], 1)
            np.add.at(cnt, edges[:, 1], 1)
            lap = acc / np.maximum(cnt, 1)[:, None] - v
            v = v + factor * lap
    out = trimesh.Trimesh(vertices=v, faces=f, process=False)
    return out


def build_views(src: Path, mask_dir: Path) -> list[cc.View]:
    (mask_dir / "masks").mkdir(parents=True, exist_ok=True)
    views = []
    for name, spec in cc.ORTHO_VIEWS.items():
        views.append(cc.make_ortho_view(name, *spec, src, mask_dir))
    return views


def blend_photo_colour(pos: np.ndarray, nrm: np.ndarray, views: list[cc.View],
                       deep_bias: float = 0.035, power: float = 2.0,
                       chunk: int = 400_000):
    """Normal- and depth-weighted blend of the photographs at every surface point."""
    n = len(pos)
    acc = np.zeros((n, 3), np.float64)
    wsum = np.zeros(n, np.float64)
    for v in views:
        axis = {"front": (-1, 0, 0), "rear": (1, 0, 0), "side": (0, 0, 0),
                "top": (0, 0, 1)}.get(v.name, (0, 0, 0))
        if v.name == "side":
            facing = np.abs(nrm[:, 1])                  # both flanks, one photo
        elif v.name == "top":
            facing = np.maximum(nrm[:, 2], 0.0)
        else:
            facing = np.maximum(nrm @ np.array(axis, float), 0.0)
        if not np.any(facing > 1e-3):
            continue
        rgb = v.image_rgb if hasattr(v, "image_rgb") else None
        for start in range(0, n, chunk):
            stop = min(n, start + chunk)
            u, vv, _ = v.project(pos[start:stop])
            inside = -v.lookup(u, vv)                   # metres inside the silhouette
            w = facing[start:stop] ** power * np.clip(inside / deep_bias, 0.0, 1.0)
            if not np.any(w > 1e-4):
                continue
            acc[start:stop] += v.sample_colour(u, vv) * w[:, None]
            wsum[start:stop] += w
    return acc, wsum


def bake_photo_texture(mesh, uv, size: int, views: list[cc.View], safe_margin: float = 0.012,
                       blend_ratio: float = 0.6):
    """Per-texel photo projection.

    Each texel is mapped through the UV atlas to a 3-D point and normal, and
    that point samples the photographs directly. Interpolating per-vertex
    colours instead (the obvious approach) smears detail across whole UV
    triangles and turns the body into stripes - measured, not guessed.
    """
    from scipy import ndimage

    v = np.array(mesh.vertices, dtype=np.float64)
    n = np.array(mesh.vertex_normals, dtype=np.float64)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    faces = np.asarray(mesh.faces)

    pix = uv * (size - 1)
    pos_tex = np.zeros((size * size, 3), np.float32)
    nrm_tex = np.zeros((size * size, 3), np.float32)
    hit = np.zeros(size * size, bool)

    p = pix[faces]
    lo = np.floor(p.min(axis=1)).astype(int)
    hi = np.ceil(p.max(axis=1)).astype(int)
    for i in range(len(faces)):
        x0, y0 = max(0, lo[i, 0]), max(0, lo[i, 1])
        x1, y1 = min(size - 1, hi[i, 0]), min(size - 1, hi[i, 1])
        if x1 < x0 or y1 < y0:
            continue
        ax, ay = p[i, 0]
        bx, by = p[i, 1]
        cx, cy = p[i, 2]
        area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
        if abs(area) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((bx - ax) * (gy - ay) - (gx - ax) * (by - ay)) / area
        w1 = ((gx - ax) * (cy - ay) - (cx - ax) * (gy - ay)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
        if not inside.any():
            continue
        idx = faces[i]
        pos = (w0[..., None] * v[idx[0]] + w1[..., None] * v[idx[1]] + w2[..., None] * v[idx[2]])
        nr = (w0[..., None] * n[idx[0]] + w1[..., None] * n[idx[1]] + w2[..., None] * n[idx[2]])
        flat = (np.arange(y0, y1 + 1)[:, None] * size + np.arange(x0, x1 + 1)[None, :])
        sel = flat[inside]
        pos_tex[sel] = pos[inside]
        nrm_tex[sel] = nr[inside]
        hit[sel] = True

    coverage = float(hit.mean())
    tex = np.zeros((size * size, 3), np.float32)
    tex[:] = np.array([0.10, 0.10, 0.11], np.float32)   # unshot regions: dark neutral

    sel = np.nonzero(hit)[0]
    pos_s = pos_tex[sel].astype(np.float64)
    nrm_s = nrm_tex[sel].astype(np.float64)

    # The four renders do not share an exposure: the same bumper reads 17, 75
    # and 62 out of 255 in the front, rear and side photographs. Blending them
    # raw makes the body a patchwork of exposure zones, so each view is first
    # normalised to a common median brightness over the surface it can see.
    axes = {"front": (-1, 0, 0), "rear": (1, 0, 0)}
    step = 300_000

    def view_weight_facing(view):
        if view.name == "side":
            return np.abs(nrm_s[:, 1])
        if view.name == "top":
            return np.maximum(nrm_s[:, 2], 0.0)
        return np.maximum(nrm_s @ np.array(axes[view.name], float), 0.0)

    sub = np.arange(0, len(sel), max(1, len(sel) // 400_000))
    medians = {}
    for view in views:
        facing = view_weight_facing(view)[sub]
        u, vv, _ = view.project(pos_s[sub])
        inside = -view.lookup(u, vv)
        w = facing ** 3 * np.clip(inside / safe_margin, 0, 1)
        ok = w > 0.5
        if ok.sum() < 50:
            continue
        c = view.sample_colour(u[ok], vv[ok])
        lum = 0.2126 * c[:, 0] + 0.7152 * c[:, 1] + 0.0722 * c[:, 2]
        medians[view.name] = float(np.median(lum))
    target = float(np.exp(np.mean([np.log(max(m, 1e-3)) for m in medians.values()]))) if medians else 1.0
    gains = {k: (target / max(v, 1e-3)) for k, v in medians.items()}
    print("    exposure medians " + ", ".join(f"{k}={v:.3f}" for k, v in medians.items())
          + " | gains " + ", ".join(f"{k}={v:.2f}x" for k, v in gains.items()))

    # blend among the cameras that are comparably good for each texel
    mixed = np.zeros((len(sel), 3), dtype=np.float32)
    got = np.zeros(len(sel), dtype=bool)
    SS = 2   # 2x2 supersampling per texel: the photographs are ~100 px/m, a 2k
             # atlas is ~400 texels/m, so point sampling aliases badly
    for s0 in range(0, len(sel), step):
        s1 = min(len(sel), s0 + step)
        W = np.zeros((s1 - s0, len(views)), np.float32)
        C = np.zeros((s1 - s0, len(views), 3), np.float32)
        for vi, view in enumerate(views):
            facing = view_weight_facing(view)[s0:s1]
            u, vv, _ = view.project(pos_s[s0:s1])
            inside = -view.lookup(u, vv)
            w = facing ** 3 * np.clip(inside / safe_margin, 0, 1)
            ok = w > 1e-3
            if not ok.any():
                continue
            W[:, vi] = np.where(ok, w, 0.0)
            cols = np.zeros((s1 - s0, 3), np.float32)
            for oy in (0.25, 0.75):
                for ox in (0.25, 0.75):
                    cols[ok] += (view.sample_colour(u[ok] + ox, vv[ok] + oy)
                                 * gains.get(view.name, 1.0)) / (SS * SS)
            C[:, vi] = cols
        best = W.max(axis=1)
        # A *binary* keep threshold draws a hard line where two cameras tie,
        # which shows up as a vertical seam down the whole car. Ramp instead:
        # cameras below `blend_ratio` of the best contribute nothing, cameras at
        # the best contribute fully, and the transition is smooth.
        ref = np.maximum(blend_ratio * best, 1e-6)[:, None]
        keep = np.clip((W - ref) / np.maximum(best[:, None] - ref, 1e-6), 0.0, 1.0)
        keep[W <= 1e-3] = 0.0
        W = W * keep
        denom = np.maximum(W.sum(axis=1), 1e-9)
        chunk_col = (C * W[..., None]).sum(axis=1) / denom[:, None]
        mixed[s0:s1] = chunk_col
        got[s0:s1] = best > 1e-3

    tex[sel[got]] = np.clip(mixed[got], 0, 1)
    del sel, mixed, pos_tex, nrm_tex

    img = tex.reshape(size, size, 3)
    if got.sum() > 1000:
        # kill salt-and-pepper from atlas seams and switching cameras on a 3x3
        # median, which leaves real edges (panel lines, lights) intact
        img = ndimage.median_filter(img, size=3)
    hole = ~hit.reshape(size, size)
    if hole.any():
        idx = ndimage.distance_transform_edt(hole, return_distances=False, return_indices=True)
        img = img[tuple(idx)]
    out = Image.fromarray(np.clip(img * 255.0, 0, 255).astype(np.uint8), mode="RGB")
    print(f"    texels with photo colour: {100*(hit.mean()*float(got.mean()) if got.size else 0):.1f}%"
          f" | atlas coverage {100*coverage:.1f}%")
    return out, {"texture_size": size, "atlas_coverage": round(coverage, 4),
                 "texels_photo_coloured": int(got.sum()), "texels_total": int(hit.sum())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", default="refined_carve")
    ap.add_argument("--tier", choices=sorted(TIERS), default="web")
    ap.add_argument("--src", default="carve_src")
    ap.add_argument("--smooth", type=int, default=18)
    ap.add_argument("--faces", type=int, default=0, help="override tier face count")
    ap.add_argument("--texture-size", type=int, default=0)
    ap.add_argument("--no-texture", action="store_true")
    ap.add_argument("--fit-exact", action="store_true",
                    help="scale to the published 4.976 x 2.126 x 1.473 m")
    ap.add_argument("--blend-ratio", type=float, default=0.35,
                    help="cameras within this fraction of the best one for a texel are "
                         "averaged; 1.0 means winner-take-all")
    args = ap.parse_args()

    t0 = time.time()
    cfg = TIERS[args.tier]
    faces_target = args.faces or cfg["faces"]
    tex_size = args.texture_size or cfg["texture"]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("[1] load carved hull")
    mesh = trimesh.load(args.input, force="mesh")
    print(f"    {len(mesh.faces)} faces | extents {np.round(mesh.extents, 3)} m")

    print(f"[2] Taubin smooth x{args.smooth} (shrink-free)")
    mesh = taubin(mesh, args.smooth)

    print(f"[3] decimate to ~{faces_target} faces")
    from fast_simplification import simplify as _simplify
    v_s, f_s = _simplify(np.asarray(mesh.vertices, np.float64),
                         np.asarray(mesh.faces, np.int64),
                         target_count=faces_target, preserve_border=True)
    # decimation can leave hair-thin detached shells (two of area 1e-4 m^2 here)
    # which make the result non-manifold even though it has no open edges
    parts = trimesh.Trimesh(vertices=v_s, faces=f_s, process=False).split(only_watertight=False)
    parts.sort(key=lambda p: p.area, reverse=True)
    keep = [p for p in parts if p.area >= 0.005 * parts[0].area]
    mesh = trimesh.util.concatenate(keep)
    dropped = len(parts) - len(keep)
    mesh.merge_vertices()
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    print(f"    {len(mesh.faces)} faces | {len(mesh.vertices)} verts"
          + (f" | dropped {dropped} detached sliver(s)" if dropped else ""))

    print("[4] rebuild photo calibration")
    views = build_views(Path(args.src), out / "masks")

    fit_note = {}
    if args.fit_exact:
        # Carving inherits the photographs' pixel scale; eroding the masks to
        # drop the contact shadow costs a pixel or two on each flank. The
        # residual is under 1% per axis, so correcting it anisotropically to the
        # real car's published dimensions cannot distort the model. The view
        # calibration is divided by the same factors so the photo projection
        # stays registered to the mesh.
        target = np.array([cc.LENGTH, cc.MIRROR_SPAN, cc.HEIGHT])
        before = np.array(mesh.extents)
        scale = target / before
        mesh.vertices = np.asarray(mesh.vertices, np.float64) * scale[None, :]
        for v in views:
            ua, va = np.abs(v.u_axis), np.abs(v.v_axis)
            v.u_aff = (v.u_aff[0] / scale[int(np.argmax(ua))], v.u_aff[1])
            v.v_aff = (v.v_aff[0] / scale[int(np.argmax(va))], v.v_aff[1])
        fit_note = {"before_m": before.round(4).tolist(),
                    "applied_axis_scale": scale.round(4).tolist(),
                    "after_m": np.array(mesh.extents).round(4).tolist()}
        print(f"    exact fit {before.round(3)} -> {np.array(mesh.extents).round(3)} m"
              f" (scale {scale.round(4)})")

    uv_mesh, uv, uv_cols = rm.unwrap(mesh, None)
    print(f"[5] unwrap -> {len(uv_mesh.vertices)} atlas verts")

    glb = out / "model_textured.glb"
    if not args.no_texture:
        print(f"[6] bake {tex_size}px texture by projecting the photographs")
        image, tex_meta = bake_photo_texture(uv_mesh, uv, tex_size, views,
                                             blend_ratio=args.blend_ratio)
        uv_mesh.visual = trimesh.visual.TextureVisuals(uv=uv, image=image)
        image.save(out / "texture.png")
        print(f"    {tex_meta}")
    else:
        tex_meta = {}

    rm.ensure_normals(uv_mesh)
    uv_mesh.export(glb)

    # ---- OBJ + MTL (embedded UVs, external texture) and printable STL
    obj_path = out / "model_textured.obj"
    uv_mesh.export(obj_path)
    if (out / "texture.png").exists():
        mtl = out / "model_textured.mtl"
        mtl.write_text("newmtl material_0\nKa 1.000000 1.000000 1.000000\n"
                       "Kd 1.000000 1.000000 1.000000\nKs 0.000000 0.000000 0.000000\n"
                       "d 1.0\nillum 2\nmap_Kd texture.png\n")

    stl_mesh = mesh.copy()
    stl_mesh.apply_scale(1000.0)          # millimetres
    stl = out / "print_mm.stl"
    stl_mesh.export(stl)

    ext = mesh.extents
    metrics = {
        "tier": args.tier,
        "extents_m": np.round(ext, 4).tolist(),
        "target_dimensions_m": {"width": cc.WIDTH, "height": cc.HEIGHT,
                                "length": cc.LENGTH, "mirror_span": cc.MIRROR_SPAN},
        "real_world_error_pct": {
            "length": round(100 * (ext[0] - cc.LENGTH) / cc.LENGTH, 2),
            "width_including_mirrors": round(100 * (ext[1] - cc.MIRROR_SPAN) / cc.MIRROR_SPAN, 2),
            "height": round(100 * (ext[2] - cc.HEIGHT) / cc.HEIGHT, 2),
        },
        "faces": int(len(mesh.faces)), "vertices": int(len(mesh.vertices)),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "volume_m3": round(float(mesh.volume), 4),
        "taubin_iterations": args.smooth,
        "exact_fit": fit_note,
        "texture": tex_meta,
        "files": {},
        "seconds": round(time.time() - t0, 1),
    }
    for f in sorted(out.iterdir()):
        if f.is_file():
            metrics["files"][f.name] = f.stat().st_size
    (out / "carve_metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"done in {time.time() - t0:.1f}s -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
