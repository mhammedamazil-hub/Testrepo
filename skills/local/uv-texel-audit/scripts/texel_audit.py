"""UV quality audit: texel density, UV utilisation, overlap and stretch.

The vendored uv_pack/texel_density scripts *set* density; this one *measures* the mesh
and refuses to let a bad unwrap through. Per object:

  uv_area          fraction of the 0-1 tile covered by islands (utilisation)
  texel_density    px per metre at the requested map size (mean + min/max)
  density_spread   max/min of per-face density: >2x means the resolution is uneven
  stretch_mean     distribution of world-area vs uv-area distortion (0 = uniform)
  overlap_faces    faces whose uv centroid lands inside another face -> shared texels
  out_of_bounds    faces outside 0..1 (UDIM or sloppy unwrap)

Usage:
  python tools/bpy_run.py <this> -- --objects Car --res 2048 --min-density 512
"""
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402


def audit(ob, res=2048):
    me = ob.data
    if not me.uv_layers:
        return {"object": ob.name, "error": "no UV layer"}
    me.calc_loop_triangles()
    uvl = me.uv_layers.active.data
    tri = me.loop_triangles
    nt = len(tri)

    uv = np.empty((nt, 3, 2))
    for i, t in enumerate(tri):
        for j, li in enumerate(t.loops):
            uv[i, j] = uvl[li].uv
    world = np.empty((nt, 3, 3))
    mw = np.array(ob.matrix_world)
    for i, t in enumerate(tri):
        for j, vi in enumerate(t.vertices):
            co = np.array(me.vertices[vi].co)
            world[i, j] = (mw[:3, :3] @ co) + mw[:3, 3]

    def areas(p):
        return 0.5 * np.abs((p[:, 1, 0] - p[:, 0, 0]) * (p[:, 2, 1] - p[:, 0, 1])
                            - (p[:, 2, 0] - p[:, 0, 0]) * (p[:, 1, 1] - p[:, 0, 1]))

    uv_a = areas(uv)
    w_a = areas(world)
    good = w_a > 1e-12
    ratio = np.where(good, np.sqrt(np.maximum(uv_a, 1e-12) / np.where(good, w_a, 1)), 0.0)
    # ratio = uv-length per world length -> px/m = ratio * res
    dens = ratio * res
    uv_area_total = float(uv_a.sum())
    out_of_bounds = int(((uv < -1e-6) | (uv > 1 + 1e-6)).any(axis=2).any(axis=1).sum())

    # overlap: bin face centroids on a grid and look for collisions (cheap approximation)
    cen = uv.mean(axis=1)
    inside = ((cen >= 0) & (cen <= 1)).all(axis=1)
    cells = {}
    overlaps = 0
    q = 128
    for i in np.nonzero(inside)[0]:
        key = (int(cen[i, 0] * q), int(cen[i, 1] * q))
        if key in cells:
            overlaps += 1
        else:
            cells[key] = i

    d = dens[dens > 0]
    return {
        "object": ob.name,
        "tris": int(nt),
        "uv_area_used": round(uv_area_total, 4),
        "texel_density_px_per_m": {
            "mean": round(float(d.mean()), 1) if len(d) else 0,
            "min": round(float(d.min()), 1) if len(d) else 0,
            "max": round(float(d.max()), 1) if len(d) else 0,
            "res": res,
        },
        "density_spread": round(float(d.max() / max(d.min(), 1e-9)), 2) if len(d) else 0,
        "stretch": {
            "mean_dev_from_1": round(float(np.abs(ratio[good] - ratio[good].mean()).mean()
                                           / max(ratio[good].mean(), 1e-9)), 4)
            if good.any() else 0,
            "interpretation": "0 = perfectly uniform; >0.5 = visibly stretched islands",
        },
        "overlap_faces_approx": overlaps,
        "out_of_bounds_faces": out_of_bounds,
        "uv_layers": len(me.uv_layers),
    }


def run(objects=None, res=2048, min_density=256.0, **_):
    sc.object_mode()
    reports, problems = [], []
    for ob in sc.objects(objects):
        r = audit(ob, res)
        reports.append(r)
        if "error" in r:
            problems.append(f"{ob.name}: {r['error']}")
            continue
        td = r["texel_density_px_per_m"]["mean"]
        if td < min_density:
            problems.append(f"{ob.name}: texel density {td} px/m < {min_density} "
                            f"at {res}px (raise resolution or scale UVs)")
        if r["uv_area_used"] < 0.25:
            problems.append(f"{ob.name}: only {r['uv_area_used']*100:.0f} % of the UV "
                            "tile used - pack tighter")
        if r["density_spread"] > 3.0:
            problems.append(f"{ob.name}: density spread {r['density_spread']}x - "
                            "islands are at different resolutions")
        if r["overlap_faces_approx"] > max(4, 0.02 * r["tris"]):
            problems.append(f"{ob.name}: {r['overlap_faces_approx']} possibly overlapping "
                            "faces (mirrored/shared UVs are OK if intentional)")
        if r["out_of_bounds_faces"]:
            problems.append(f"{ob.name}: {r['out_of_bounds_faces']} faces outside 0-1")
    return {"ok": True, "target": {"res": res, "min_density_px_per_m": min_density},
            "objects": reports, "problems": problems,
            "verdict": "UV OK" if not problems else "UV PROBLEMS"}


if __name__ == "__main__":
    p = sc.add_common(sc.parser(__doc__), save=False)
    p.add_argument("--res", type=int, default=2048, help="target texture size")
    p.add_argument("--min-density", type=float, default=256.0)
    sc.cli(run, p)
