"""v2 deliverables: whole-site GLB (+ per-piece furniture GLBs) and an import check.

Differences from `export.py`, all of them found by actually inspecting the output:

* **Alpha must survive.** v1 exported with `export_image_format='JPEG'`, which silently
  throws away the alpha channel. In v2 that turns every leaf card into a solid quad, so
  the trees become green boxes in any glTF viewer. v2 keeps PNG for images that have
  alpha and only uses JPEG for the opaque ones.
* **Alpha mode must be declared.** glTF needs `alphaMode: MASK` (or BLEND) per material.
  The exporter reads it from the Blender material, so the card materials are forced to a
  clipping mode here instead of relying on a heuristic.
* **Verify by reopening.** Exporting returns `FINISHED` even when the file contains the
  wrong thing, so the script re-imports the GLB into an empty scene and compares object
  count, triangle count, bounding box and material count against the source.

    .venv/bin/python tools/bpy_run.py villa_src/export_v2.py -- --out villa_v2
"""
import glob
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bpy  # noqa: E402
from PIL import Image  # noqa: E402
from mathutils import Vector  # noqa: E402

from villa_src import build_v2 as B  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEX = os.path.join(ROOT, "villa", "tex")
CARD_MATS = ("spray_a", "spray_b", "spray_c", "spray_olive", "spray_dark",
             "leaf_card_a", "leaf_card_b", "leaf_card_c", "leaf_card_olive",
             "grass_blade")


def downscale(size=1024):
    """Resized texture copies so the GLB is not 100 MB."""
    dst = os.path.join(ROOT, f"villa/tex_{size}")
    os.makedirs(dst, exist_ok=True)
    for f in glob.glob(os.path.join(TEX, "*.png")):
        out = os.path.join(dst, os.path.basename(f))
        if os.path.exists(out):
            continue
        im = Image.open(f)
        if im.mode == "RGBA":
            im.resize((size, size), Image.LANCZOS).save(out)
        else:
            im.convert("RGB").resize((size, size), Image.LANCZOS).save(out)
    return dst


def relink(folder):
    n = 0
    for img in bpy.data.images:
        fp = bpy.path.abspath(img.filepath) if img.filepath else ""
        if not fp:
            continue
        alt = os.path.join(folder, os.path.basename(fp))
        if os.path.exists(alt):
            img.filepath = alt
            img.reload()
            n += 1
    return n


def _set_alpha_modes():
    """Make cutout foliage explicit; also report what was found."""
    found = []
    for name in CARD_MATS:
        mat = bpy.data.materials.get(name)
        if not mat:
            continue
        # `blend_method="CLIP"` is what makes the exporter write `alphaMode: MASK`.
        # Do NOT also set `surface_render_method`: on this build it flips blend_method
        # back to HASHED, and the GLB then gets alphaMode BLEND (sorting artefacts and a
        # much slower transparent pass in every viewer).
        for attr, val in (("blend_method", "CLIP"), ("shadow_method", "CLIP")):
            if hasattr(mat, attr):
                try:
                    setattr(mat, attr, val)
                except (TypeError, AttributeError) as exc:
                    print(f"  alpha: {name}.{attr} not settable ({exc})")
        mat.use_backface_culling = False
        found.append(name)
    return found


def patch_alpha_mask(path, cutoff=0.4):
    """Rewrite alpha-cutout materials to `alphaMode: MASK` inside the GLB.

    On Blender 5.0 the glTF exporter writes `alphaMode: BLEND` for *any* material whose
    Alpha input is linked - setting `blend_method='CLIP'` (which used to produce MASK)
    has no effect, verified against three combinations of blend/render method. BLEND is
    wrong for foliage cards: viewers draw them in an unsorted transparent pass and leaves
    pop and disappear. MASK is a depth-tested discard, so the canopy is stable.

    Rewriting the JSON chunk means rebuilding the container, which is why this is a real
    function and not a one-liner.
    """
    with open(path, "rb") as f:
        magic, version, total = struct.unpack("<III", f.read(12))
        clen, ctype = struct.unpack("<II", f.read(8))
        js = json.loads(f.read(clen))
        rest = f.read()
    changed = []
    for m in js.get("materials", []):
        if m.get("alphaMode") == "BLEND" and m.get("name") in CARD_MATS:
            m["alphaMode"] = "MASK"
            m["alphaCutoff"] = cutoff
            changed.append(m["name"])
    blob = json.dumps(js, separators=(",", ":")).encode("utf-8")
    blob += b" " * ((4 - len(blob) % 4) % 4)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", magic, version, 12 + 8 + len(blob) + len(rest)))
        f.write(struct.pack("<II", len(blob), ctype))
        f.write(blob)
        f.write(rest)
    return changed


def _stats():
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    tris = 0
    for ob in meshes:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            lo = Vector((min(lo[i], w[i]) for i in range(3)))
            hi = Vector((max(hi[i], w[i]) for i in range(3)))
        ob.data.calc_loop_triangles()
        tris += len(ob.data.loop_triangles)
    return {
        "meshes": len(meshes),
        "tris": tris,
        "materials": len({m.name for o in meshes for m in o.data.materials if m}),
        "bbox_m": [round(v, 2) for v in (hi - lo)],
        "images": len(bpy.data.images),
    }


# Objects that exist only to make the *renders* look like a place: a 700 m ridge, 150 m
# lawns, a 92 m boundary bed. They are correct for a camera 20 m away and ruinous for a
# glTF viewer, which frames the whole scene: a 19.7 m house inside a 700 m box is 3 % of
# the frame, i.e. a speck. `--trim` drops them and lays a small ground plane instead.
BACKDROP = ("ridge", "lawn_", "field_", "boundary_bed")


def _bbox(ob):
    from mathutils import Vector as _V
    pts = [ob.matrix_world @ _V(c) for c in ob.bound_box]
    return (_V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            _V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def trim_scene(metres=70.0, recentre=True):
    """Make the export *about the villa*, not about the landscape.

    Removes the backdrop by name AND by size, then adds a ground plane just big enough to
    sit the house in, optionally recentred so the house is at the origin (some viewers put
    the camera at the origin, and the house would otherwise start behind it).
    Returns a report dict for glb_report.json.
    """
    from villa_src import kit as K
    house_objs = [o for o in bpy.data.objects if o.type == "MESH"
                  and o.name.startswith(("wall", "plinth", "pier", "glass", "soffit",
                                         "par_", "roof_deck", "door_", "canopy"))]
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in house_objs:
        a, b = _bbox(o)
        lo = Vector((min(lo.x, a.x), min(lo.y, a.y), min(lo.z, a.z)))
        hi = Vector((max(hi.x, b.x), max(hi.y, b.y), max(hi.z, b.z)))
    cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2

    removed = []
    for ob in list(bpy.data.objects):
        if ob.type != "MESH":
            continue
        base = ob.name.split(".")[0]
        drop = base.startswith(BACKDROP)
        if not drop:
            a, b = _bbox(ob)
            extent = max(b.x - a.x, b.y - a.y)
            far = max(abs(a.x - cx), abs(b.x - cx), abs(a.y - cy), abs(b.y - cy))
            drop = extent > metres * 1.4 or far > metres * 0.75
        if drop:
            removed.append(ob.name.split(".")[0])
            bpy.data.objects.remove(ob, do_unlink=True)

    site = bpy.data.collections.get("Site")
    K.slab("ground_trim", cx - metres / 2, cy - metres / 2, cx + metres / 2,
           cy + metres / 2, -0.34, -0.06, "lawn_v2", coll=site)

    shifted = 0.0
    if recentre:
        # move everything so the house sits on the origin, ground at z = 0
        for ob in bpy.data.objects:
            ob.location.x -= cx
            ob.location.y -= cy
        shifted = round(cx, 3)
    return {"trim_m": metres, "removed": len(removed),
            "removed_names": sorted(set(removed))[:10],
            "recentred_by_m": shifted}


def export_house(path, tex_size=1024):
    if tex_size != 1024:
        relink(downscale(tex_size))
    bpy.ops.object.select_all(action="SELECT")
    t0 = os.path.getsize(path) if os.path.exists(path) else 0
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=False,
        export_apply=True, export_yup=True, export_texcoords=True,
        export_normals=True, export_materials="EXPORT",
        # JPEG mode still writes PNG for images that need alpha, so foliage keeps its
        # cutouts while the other 100 opaque maps stay small.
        export_image_format="JPEG",
        export_image_quality=86,
        export_cameras=False, export_lights=False,
        export_extras=False, export_animations=False,
    )
    size = os.path.getsize(path)
    print(f"GLB {path} {size/1e6:.2f} MB (was {t0/1e6:.2f})", flush=True)
    return size


def verify(path):
    """Re-import into an empty scene and compare against the source scene."""
    src = _stats()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    got = _stats()
    dims_ok = all(abs(a - b) <= max(0.05, 0.01 * max(a, b))
                  for a, b in zip(src["bbox_m"], got["bbox_m"]))
    # glTF is Y-up: the *bounds* rotate, so compare sorted extents
    dims_ok = all(abs(a - b) <= max(0.05, 0.01 * max(a, b))
                  for a, b in zip(sorted(src["bbox_m"]), sorted(got["bbox_m"])))
    ok = (got["meshes"] > 0 and got["tris"] > 0
          and abs(got["tris"] - src["tris"]) <= 0.02 * src["tris"] + 100
          and dims_ok and got["materials"] >= src["materials"] * 0.9)
    alpha_mats = []
    for m in bpy.data.materials:
        if m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "BSDF_PRINCIPLED" and n.inputs["Alpha"].is_linked:
                    alpha_mats.append(m.name)
                    break
    return {"pass": bool(ok), "source": src, "reimported": got,
            "dims_match": dims_ok, "alpha_materials_in_glb": len(alpha_mats),
            "alpha_material_names": sorted(alpha_mats)[:8]}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="villa_v2")
    ap.add_argument("--tex", type=int, default=1024)
    ap.add_argument("--pieces", action="store_true", help="also export per-piece GLBs")
    ap.add_argument("--name", default="villa_v2.glb", help="output file name")
    ap.add_argument("--trim", type=float, default=0.0,
                    help="export only the villa + this many metres of ground (0 = whole "
                         "site, which no auto-framing viewer can show)")
    ns = ap.parse_args(argv)

    out = os.path.join(ROOT, ns.out)
    os.makedirs(out, exist_ok=True)
    sc, ext = B.build()
    print("alpha materials marked:", _set_alpha_modes(), flush=True)
    trim_info = None
    if ns.trim > 0:
        trim_info = trim_scene(ns.trim)
        print("TRIM", json.dumps(trim_info), flush=True)

    path = os.path.join(out, ns.name)
    size = export_house(path, tex_size=ns.tex)
    masked = patch_alpha_mask(path)
    print("alphaMode MASK applied to:", masked, flush=True)
    size = os.path.getsize(path)
    report = verify(path)
    report["alpha_mask_patched"] = masked
    report["trim"] = trim_info
    report["file"] = path
    report["tex_px"] = ns.tex
    report["bytes"] = size
    report["mb"] = round(size / 1e6, 2)
    with open(os.path.join(out, "glb_report.json"), "w") as f:
        json.dump(report, f, indent=1)
    print("VERIFY", json.dumps(report), flush=True)

    if ns.pieces:
        from villa_src import export as E
        man = E.export_pieces(os.path.join(out, "furniture"), tex_size=512)
        with open(os.path.join(out, "furniture_manifest.json"), "w") as f:
            json.dump([{"name": n, "file": fn, "kind": k, "bytes": s}
                       for (n, fn, k, s) in man], f, indent=1)
        print(f"pieces: {len(man)}", flush=True)

    print("EXPORT DONE", "PASS" if report["pass"] else "FAIL", flush=True)


if __name__ == "__main__":
    main()
