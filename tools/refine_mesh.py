#!/usr/bin/env python3
"""CPU mesh refinement pipeline for InstantMesh output.

No GPU, no cloud, no ML. This takes a generated mesh and fixes the things that are
objectively wrong, then bakes a proper texture and exports real deliverables.

What it does (each step is optional and reported):
  1. LOAD      GLB/OBJ -> single Trimesh (Scene gets concatenated)
  2. HEAL      drop degenerate/duplicate faces, unreferenced verts, fill holes,
               make normals outward and winding consistent (Meshy's "facets face
               inward" warning is exactly a winding failure)
  3. PROPORTION anisotropic fit to known real dimensions, so a squat AI mesh
               reads as the right vehicle instead of an SUV. Global fit only.
  4. DENOISE   Taubin smoothing (volume-preserving, unlike Laplacian)
  5. UNWRAP    xatlas UV atlas
  6. BAKE      rasterise per-vertex colours into a real texture map
               (re-projects existing colour: no new information is invented)
  7. EXPORT    web GLB (decimated, textured), engine OBJ+MTL+PNG,
               print STL in millimetres (watertight, outward normals)

Honest limits are printed at the end: this repairs and re-lights an existing
asset. It does not add invented detail and cannot reach Meshy/Tripo quality,
which comes from much larger generative models running on GPUs.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")

# Real BMW M5 F90 (metres): width X, height Y, length Z
M5_DIMS_M = (1.903, 1.473, 4.976)


def log(msg: str) -> None:
    print(f"[refine] {msg}", flush=True)


def load_mesh(path: Path):
    import trimesh

    loaded = trimesh.load(str(path), process=False)
    if isinstance(loaded, trimesh.Scene):
        loaded = loaded.to_geometry() if hasattr(loaded, "to_geometry") else loaded.dump(concatenate=True)
    m = loaded
    if not hasattr(m, "faces") or len(m.faces) == 0:
        raise SystemExit(f"{path} contains no triangles")
    colours = None
    vis = getattr(m, "visual", None)
    if vis is not None and getattr(vis, "vertex_colors", None) is not None:
        colours = np.asarray(vis.vertex_colors, dtype=np.uint8)
    return m, colours


def heal(mesh, colours):
    """Make the surface printable: consistent winding, outward normals, no holes."""
    import trimesh
    from trimesh.repair import fill_holes, fix_normals

    report = {}
    n0, f0 = len(mesh.vertices), len(mesh.faces)
    report["faces_before"] = f0
    report["watertight_before"] = bool(mesh.is_watertight)
    report["winding_consistent_before"] = bool(mesh.is_winding_consistent)

    # drop degenerate + duplicate geometry
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    report["removed_degenerate_or_duplicate"] = f0 - len(mesh.faces)

    # consistent outward normals (this is what Meshy flagged)
    mesh.faces = mesh.faces[:, ::-1] if not mesh.is_winding_consistent else mesh.faces
    trimesh.repair.fix_winding(mesh)
    trimesh.repair.fix_inversion(mesh, multibody=True)
    fix_normals(mesh, multibody=True)
    if not mesh.is_watertight:
        try:
            fill_holes(mesh)
        except Exception as exc:  # noqa: BLE001
            report["fill_holes_error"] = str(exc)

    # last resort: pymeshfix rebuilds the surface
    if not (mesh.is_watertight and mesh.is_winding_consistent):
        try:
            import pymeshfix

            mf = pymeshfix.MeshFix(np.asarray(mesh.vertices), np.asarray(mesh.faces))
            mf.repair(verbose=False)
            if mf.faces is not None and len(mf.faces) > 0:
                cols = None
                if colours is not None:
                    from scipy.spatial import cKDTree

                    _, idx = cKDTree(np.asarray(mesh.vertices)).query(np.asarray(mf.points))
                    cols = colours[idx]
                import trimesh as _tm

                mesh = _tm.Trimesh(vertices=np.asarray(mf.points), faces=np.asarray(mf.faces), process=False)
                colours = cols
                report["pymeshfix_used"] = True
        except Exception as exc:  # noqa: BLE001
            report["pymeshfix_error"] = str(exc)

    report["faces_after_heal"] = len(mesh.faces)
    report["vertices_after_heal"] = len(mesh.vertices)
    report["watertight_after"] = bool(mesh.is_watertight)
    report["winding_consistent_after"] = bool(mesh.is_winding_consistent)
    report["volume"] = float(mesh.volume) if mesh.is_volume else None
    if colours is not None and len(colours) != len(mesh.vertices):
        report["colour_mismatch"] = f"{len(colours)} colours vs {len(mesh.vertices)} verts"
        colours = None
    if n0 and f0:
        report["vertex_delta"] = len(mesh.vertices) - n0
    return mesh, colours, report


def fit_proportions(mesh, target=M5_DIMS_M, strength=1.0):
    """Anisotropic scale so the bounding box matches real dimensions.

    Assumes Y-up (glTF convention) and that the longest axis is the length.
    `strength` blends between the original dimensions (0) and exact fit (1).
    """
    b = mesh.bounds
    dims = b[1] - b[0]
    order = np.argsort(dims)            # smallest -> largest
    length_axis = int(order[-1])
    height_axis = 1 if length_axis != 1 else int(order[0])
    width_axis = ({0, 1, 2} - {length_axis, height_axis}).pop()

    target_by_axis = np.zeros(3)
    target_by_axis[length_axis] = target[2]   # length
    target_by_axis[height_axis] = target[1]   # height
    target_by_axis[width_axis] = target[0]    # width

    correction = target_by_axis / np.where(dims > 0, dims, 1.0)
    applied = 1.0 + (correction - 1.0) * float(np.clip(strength, 0.0, 1.0))

    mesh.apply_scale(applied)
    mesh.vertices -= mesh.bounds.mean(axis=0)          # centre
    if height_axis == 1:
        mesh.vertices[:, 1] -= mesh.bounds[0][1]       # sit on y=0, like a print

    new_dims = mesh.bounds[1] - mesh.bounds[0]
    return {
        "axes": {"length": "XYZ"[length_axis], "height": "XYZ"[height_axis], "width": "XYZ"[width_axis]},
        "dims_before_m": [round(float(d), 4) for d in dims],
        "scale_applied": [round(float(s), 4) for s in applied],
        "dims_after_m": [round(float(d), 4) for d in new_dims],
        "target_m": list(target),
        "strength": strength,
    }


def denoise(mesh, iterations: int):
    import trimesh

    if iterations <= 0:
        return {"smoothing": "skipped"}
    before = len(mesh.vertices)
    trimesh.smoothing.filter_taubin(mesh, lamb=0.5, nu=-0.53, iterations=iterations)
    return {"smoothing": "taubin", "iterations": iterations, "vertices": before}


def transfer_colours(target_mesh, src_vertices, src_colours, k=1):
    """Carry vertex colours onto a re-topologised mesh by nearest neighbour.

    Needed because trimesh's decimation silently replaces vertex colours with a
    uniform grey, which would turn the whole bake black.
    """
    from scipy.spatial import cKDTree

    tree = cKDTree(np.asarray(src_vertices, dtype=np.float64))
    _, idx = tree.query(np.asarray(target_mesh.vertices, dtype=np.float64), k=k)
    idx = np.asarray(idx)
    if k == 1:
        return np.asarray(src_colours, dtype=np.uint8)[idx]
    # average the neighbours for a smoother transfer
    stacked = np.asarray(src_colours, dtype=np.float64)[idx]
    return np.clip(stacked.mean(axis=1), 0, 255).astype(np.uint8)


def unwrap(mesh, colours):
    """xatlas UV unwrap. Returns (unwrapped_mesh, uv_per_vertex, n_new_vertices).

    Two things that are easy to get wrong and were verified empirically:
      * the argument order is (vertices, faces) -- the other way round silently
        returns a degenerate atlas;
      * duplicate vertex positions must be merged first, otherwise xatlas raises
        "Adding mesh failed: Index out of range".
    """
    import trimesh
    import xatlas

    work = mesh.copy()
    work.merge_vertices()
    work.update_faces(work.nondegenerate_faces())
    work.remove_unreferenced_vertices()

    req_colours = colours
    if req_colours is not None and len(req_colours) != len(mesh.vertices):
        raise ValueError(
            f"colour count {len(req_colours)} does not match mesh vertices {len(mesh.vertices)}; "
            "call transfer_colours() first"
        )
    if req_colours is not None and len(work.vertices) != len(mesh.vertices):
        # merge_vertices() collapsed duplicates: re-derive against the pre-merge cloud
        req_colours = transfer_colours(work, mesh.vertices, req_colours)

    vertices = np.ascontiguousarray(work.vertices, dtype=np.float32)
    faces = np.ascontiguousarray(work.faces, dtype=np.uint32)
    vmapping, indices, uvs = xatlas.parametrize(vertices, faces)

    vmapping = np.asarray(vmapping)
    new_vertices = np.asarray(work.vertices, dtype=np.float64)[vmapping]
    new_uv = np.asarray(uvs, dtype=np.float64)
    new_mesh = trimesh.Trimesh(
        vertices=new_vertices, faces=np.asarray(indices, dtype=np.int64), process=False
    )
    new_colours = None
    if req_colours is not None:
        new_colours = np.asarray(req_colours, dtype=np.uint8)[vmapping]
        new_mesh.visual = trimesh.visual.ColorVisuals(mesh=new_mesh, vertex_colors=new_colours)

    # sanity: a valid atlas must be non-degenerate
    if len(new_vertices) == 0 or len(new_uv) != len(new_vertices):
        raise RuntimeError(f"xatlas produced a degenerate atlas ({len(new_uv)} uvs, {len(new_vertices)} verts)")
    if not np.isfinite(new_uv).all():
        raise RuntimeError("xatlas produced non-finite UV coordinates")

    return new_mesh, new_uv, new_colours


def bake_texture(mesh, uv, colours, size: int, dilate_px: int = 4):
    """Rasterise per-vertex colours through the UV atlas into an RGBA texture."""
    from PIL import Image
    from scipy import ndimage

    faces = np.asarray(mesh.faces)
    rgba = np.asarray(colours, dtype=np.float32)
    if rgba.shape[1] == 3:
        rgba = np.concatenate([rgba, np.full((len(rgba), 1), 255.0)], axis=1)
    rgba = rgba / 255.0

    pix = uv * (size - 1)
    colour = np.zeros((size, size, 4), dtype=np.float32)
    weight = np.zeros((size, size), dtype=np.float32)

    p = pix[faces]                                     # (F,3,2)
    c = rgba[faces]                                    # (F,3,4)
    lo = np.floor(p.min(axis=1)).astype(int)
    hi = np.ceil(p.max(axis=1)).astype(int)

    for i in range(len(faces)):
        x0, y0 = lo[i]
        x1, y1 = hi[i]
        if x1 < 0 or y1 < 0 or x0 > size - 1 or y0 > size - 1:
            continue
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(size - 1, x1), min(size - 1, y1)
        if x1 < x0 or y1 < y0:
            continue
        ax, ay = p[i, 0]
        bx, by = p[i, 1]
        cx, cy = p[i, 2]
        area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
        if abs(area) < 1e-9:
            continue
        xs = np.arange(x0, x1 + 1) + 0.5
        ys = np.arange(y0, y1 + 1) + 0.5
        gx, gy = np.meshgrid(xs, ys)
        w0 = ((bx - ax) * (gy - ay) - (gx - ax) * (by - ay)) / area
        w1 = ((gx - ax) * (cy - ay) - (cx - ax) * (gy - ay)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
        if not inside.any():
            continue
        blended = (w0[..., None] * c[i, 0] + w1[..., None] * c[i, 1] + w2[..., None] * c[i, 2])
        sub = np.s_[y0:y1 + 1, x0:x1 + 1]
        mask = inside
        colour[sub] = np.where(mask[..., None], blended, colour[sub])
        weight[sub] = np.where(mask, 1.0, weight[sub])

    empty = weight == 0
    if empty.any():
        # bleed colour outward so bilinear sampling at chart edges does not sample black
        idx = ndimage.distance_transform_edt(empty, return_distances=False, return_indices=True)
        colour = colour[tuple(idx)]
    colour[..., 3] = 1.0
    # colour was normalised to 0..1 for blending; scale back to 8-bit before writing
    img = Image.fromarray(np.clip(colour * 255.0, 0, 255).astype(np.uint8), mode="RGBA")
    coverage = float((~empty).mean())
    return img, {"texture_size": size, "uv_coverage": round(coverage, 4)}


def ensure_normals(mesh):
    """Attach smoothed vertex normals so viewers/engines shade correctly.

    Without NORMAL in the GLB a viewer must recompute normals itself and often
    falls back to flat faceting, which looks far worse than the geometry is.
    """
    mesh.vertex_normals = mesh.vertex_normals  # force computation + attach
    return mesh


def apply_texture(mesh, uv, image):
    import trimesh

    mesh.visual = trimesh.visual.TextureVisuals(uv=uv, image=image)
    return mesh


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CPU refinement of an InstantMesh GLB/OBJ")
    ap.add_argument("input")
    ap.add_argument("--out", default="refined")
    ap.add_argument("--fit-proportions", action="store_true", help="anisotropic fit to real M5 dims")
    ap.add_argument("--fit-strength", type=float, default=1.0, help="0..1 blend toward exact fit")
    ap.add_argument("--smooth-iterations", type=int, default=2)
    ap.add_argument("--texture-size", type=int, default=2048)
    ap.add_argument("--web-faces", type=int, default=25000)
    ap.add_argument("--no-texture", action="store_true")
    ap.add_argument("--sharpen", type=float, default=0.0,
                    help="mild unsharp mask on the baked texture (0 = off, 1.5 = noticeable)")
    args = ap.parse_args(argv)

    src = Path(args.input)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    metrics: dict = {"input": str(src), "steps": {}}
    t_all = time.time()

    log(f"loading {src}")
    mesh, colours = load_mesh(src)
    metrics["input_mesh"] = {
        "faces": int(len(mesh.faces)), "vertices": int(len(mesh.vertices)),
        "has_vertex_colours": colours is not None,
        "dims": [round(float(d), 4) for d in (mesh.bounds[1] - mesh.bounds[0])],
    }

    log("healing (winding, normals, holes)")
    mesh, colours, repair = heal(mesh, colours)
    metrics["steps"]["heal"] = repair
    log(f"  watertight={repair['watertight_after']} winding_consistent={repair['winding_consistent_after']}")

    if args.fit_proportions:
        log(f"fitting proportions (strength {args.fit_strength})")
        metrics["steps"]["proportions"] = fit_proportions(mesh, strength=args.fit_strength)
        log(f"  dims {metrics['steps']['proportions']['dims_before_m']} -> {metrics['steps']['proportions']['dims_after_m']} m")

    log("denoising")
    metrics["steps"]["denoise"] = denoise(mesh, args.smooth_iterations)

    # ---------- print deliverable: full resolution, millimetres ----------
    import trimesh

    stl_path = out / "print_mm.stl"
    print_mesh = ensure_normals(mesh.copy())
    print_mesh.apply_scale(1000.0)          # m -> mm
    print_mesh.export(str(stl_path))
    metrics["exports"] = metrics.get("exports", {})
    metrics["exports"]["stl"] = {
        "file": stl_path.name, "bytes": stl_path.stat().st_size,
        "faces": int(len(print_mesh.faces)),
        "watertight": bool(print_mesh.is_watertight),
        "winding_consistent": bool(print_mesh.is_winding_consistent),
        "dims_mm": [round(float(d), 1) for d in (print_mesh.bounds[1] - print_mesh.bounds[0])],
        "volume_cm3": round(float(print_mesh.volume) / 1000.0, 2) if print_mesh.is_volume else None,
    }
    log(f"  STL {stl_path.stat().st_size} bytes, dims {metrics['exports']['stl']['dims_mm']} mm")

    # ---------- web + engine deliverables ----------
    full_faces = len(mesh.faces)
    if args.web_faces and full_faces > args.web_faces:
        web_mesh = mesh.simplify_quadric_decimation(face_count=args.web_faces)
        colour_transfered = True
    else:
        web_mesh, colour_transfered = mesh.copy(), False

    if colours is not None:
        colour_src_vertices = np.array(mesh.vertices, copy=True)
        colour_src_colours = np.array(colours, copy=True)

    if colours is not None and not args.no_texture:
        log("unwrapping UVs (xatlas) and baking texture")
        t0 = time.time()
        web_colours = transfer_colours(web_mesh, colour_src_vertices, colour_src_colours)
        unwrapped, uv, baked_colours = unwrap(web_mesh, web_colours)
        src_colours = baked_colours if baked_colours is not None else unwrapped.visual.vertex_colors
        img, bake_meta = bake_texture(unwrapped, uv, src_colours, args.texture_size)
        nverts = len(unwrapped.vertices)
        apply_texture(unwrapped, uv, img)
        if args.sharpen > 0:
            from PIL import Image, ImageFilter

            rgb = img.convert("RGB").filter(
                ImageFilter.UnsharpMask(radius=1.6, percent=int(60 * args.sharpen), threshold=3)
            )
            img = Image.merge("RGBA", (*rgb.split(), img.split()[3]))
            bake_meta["sharpen"] = args.sharpen
        png_path = out / "texture.png"
        img.save(png_path)
        bake_meta.update({"unwrap_s": round(time.time() - t0, 1), "uv_vertices": int(nverts),
                          "texture_file": png_path.name, "texture_bytes": png_path.stat().st_size})
        metrics["steps"]["texture"] = bake_meta
        log(f"  texture {args.texture_size}px, coverage {bake_meta['uv_coverage']}, {png_path.stat().st_size} bytes")

        ensure_normals(unwrapped)
        glb_path = out / "model_textured.glb"
        unwrapped.export(str(glb_path))
        obj_path = out / "model_textured.obj"
        unwrapped.export(str(obj_path))
        metrics["exports"]["glb"] = {
            "file": glb_path.name, "bytes": glb_path.stat().st_size,
            "faces": int(len(unwrapped.faces)), "textured": True,
            "decimated_from": full_faces if colour_transfered else None,
        }
        metrics["exports"]["obj"] = {
            "file": obj_path.name, "bytes": obj_path.stat().st_size,
            "mtl": (out / "model_textured.mtl").name if (out / "model_textured.mtl").exists() else None,
            "texture": png_path.name,
        }
        log(f"  GLB {glb_path.stat().st_size} bytes | OBJ {obj_path.stat().st_size} bytes")
    else:
        ensure_normals(mesh)
        glb_path = out / "model_vertexcolour.glb"
        mesh.export(str(glb_path))
        metrics["exports"]["glb"] = {"file": glb_path.name, "bytes": glb_path.stat().st_size,
                                     "faces": int(len(mesh.faces)), "textured": False}
        log(f"  GLB (vertex colours) {glb_path.stat().st_size} bytes")

    metrics["total_s"] = round(time.time() - t_all, 1)
    metrics["honest_limits"] = [
        "Repair + re-projection only: no geometric detail is invented.",
        "Proportion fit is a global anisotropic scale, so surface features stretch with it.",
        "Texture is baked from existing vertex colours; resolution is limited by the mesh, not the PNG size.",
        "This cannot reach Meshy/Tripo quality, which comes from far larger generative models on GPUs.",
    ]
    (out / "refine_metrics.json").write_text(json.dumps(metrics, indent=2))
    log(f"done in {metrics['total_s']}s -> {out}")
    print(json.dumps({k: metrics[k] for k in ("total_s", "exports")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
