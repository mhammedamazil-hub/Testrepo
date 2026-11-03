"""Verify an exported asset by *reopening it*, not by trusting the exporter's exit code.

Round-trip check for GLB/GLTF, FBX, OBJ, STL, USD:
  1. import the file into a fresh empty scene
  2. compare geometry against the source objects: tri count, bbox size and position
  3. check materials and image textures survived (names, count, image size)
  4. check UVs survived, and flag meshes that lost them
  5. flag axis/unit surprises: glTF is Y-up (a 90 deg X change is expected), so
     extents are compared as a sorted triple unless --strict-axis is given

Exit status is reported in JSON: pass/fail plus the numbers that justify it.

Usage:
  python tools/bpy_run.py <this> -- --objects Car --file /tmp/car.glb
  python tools/bpy_run.py <this> -- --file /tmp/car.fbx --strict-axis
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402


def _import(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=path)
    elif ext == ".usd" or ext == ".usdc":
        bpy.ops.wm.usd_import(filepath=path)
    else:
        raise ValueError(f"unsupported extension {ext}")
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def run(objects=None, file=None, strict_axis=False, tri_tol=0.02, size_tol=0.02, **_):
    sc.object_mode()
    if not file:
        raise ValueError("--file is required")
    path = bpy.path.abspath(file)
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    src = sc.objects(objects)
    src_tris = sum(sc.tri_count(o) for o in src)
    lo, hi = sc.aabb(src[0])
    for o in src[1:]:
        l2, h2 = sc.aabb(o)
        lo = [min(a, b) for a, b in zip(lo, l2)]
        hi = [max(a, b) for a, b in zip(hi, h2)]
    src_size = [round(h - l, 4) for l, h in zip(lo, hi)]
    src_mats = sorted({s.material.name for o in src for s in o.material_slots
                       if s.material})
    src_uv = sum(1 for o in src if o.data.uv_layers)

    # fresh scene, then re-import
    bpy.ops.wm.read_factory_settings(use_empty=True)
    meshes = _import(path)
    if not meshes:
        return {"ok": False, "error": "import produced no mesh objects"}
    out_tris = sum(sc.tri_count(o) for o in meshes)
    lo2, hi2 = sc.aabb(meshes[0])
    for o in meshes[1:]:
        l3, h3 = sc.aabb(o)
        lo2 = [min(a, b) for a, b in zip(lo2, l3)]
        hi2 = [max(a, b) for a, b in zip(hi2, h3)]
    out_size = [round(h - l, 4) for l, h in zip(lo2, hi2)]
    out_mats = sorted({s.material.name for o in meshes for s in o.material_slots
                       if s.material})
    out_uv = sum(1 for o in meshes if o.data.uv_layers)
    images = [{"name": i.name, "size": list(i.size), "packed": bool(i.packed_file)}
              for i in bpy.data.images if i.size[0] > 0]

    a = sorted(src_size) if not strict_axis else src_size
    b = sorted(out_size) if not strict_axis else out_size
    size_err = [abs(y - x) / max(x, 1e-6) for x, y in zip(a, b)]
    tri_err = abs(out_tris - src_tris) / max(src_tris, 1)
    checks = {
        "tri_count": {"src": src_tris, "imported": out_tris,
                      "delta_pct": round(100 * tri_err, 2),
                      "pass": tri_err <= tri_tol},
        "size": {"src_dims_m": src_size, "imported_dims_m": out_size,
                 "max_delta_pct": round(100 * max(size_err), 2),
                 "pass": max(size_err) <= size_tol,
                 "axis_note": "sorted triple unless --strict-axis" if not strict_axis
                              else "axis exact"},
        "materials": {"src": src_mats, "imported": out_mats,
                      "pass": len(out_mats) >= len(src_mats),
                      "missing": sorted(set(src_mats) - set(out_mats))},
        "uvs": {"src_objects_with_uv": src_uv, "imported_objects_with_uv": out_uv,
                "pass": out_uv >= src_uv},
        "textures": {"count": len(images), "images": images[:12],
                     "pass": len(images) > 0},
    }
    # textures are only expected when the source had image textures
    src_has_img = any(any(n.type == "TEX_IMAGE" for n in bpy.data.materials[m].node_tree.nodes)
                      for m in src_mats if bpy.data.materials.get(m)
                      and bpy.data.materials[m].use_nodes)
    checks["textures"]["expected"] = src_has_img
    checks["textures"]["pass"] = len(images) > 0 if src_has_img else True
    ok = all(c["pass"] for c in checks.values())
    return {"ok": True, "pass": ok, "file": path,
            "file_mb": round(os.path.getsize(path) / 1e6, 3), "checks": checks,
            "verdict": "EXPORT VERIFIED" if ok else "EXPORT PROBLEM"}


if __name__ == "__main__":
    p = sc.add_common(sc.parser(__doc__), save=False)
    p.add_argument("--file", required=True)
    p.add_argument("--strict-axis", action="store_true")
    p.add_argument("--tri-tol", type=float, default=0.02)
    p.add_argument("--size-tol", type=float, default=0.02)
    sc.cli(run, p)
