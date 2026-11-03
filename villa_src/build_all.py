"""One-shot deliverable builder.

    python villa_src/build_all.py [--skip-stills] [--skip-walk] [--skip-export]

Prerequisites: `.venv/bin/python villa_src/tex_gen.py` (procedural textures) and
`LD_LIBRARY_PATH=$PWD/.glstub` for headless Blender.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bpy  # noqa: E402

from villa_src import cameras as C, export as E, scene as S  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VILLA = os.path.join(ROOT, "villa")


def manifest(sc):
    pieces = []
    fur = bpy.data.collections.get("Furniture")
    allowed = set(o.name for o in fur.objects) if fur else set()
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        if not ob.get("piece") or ob.name not in allowed:
            continue
        pieces.append({
            "name": ob.name,
            "kind": ob.get("piece"),
            "file": f"furniture/{ob.name}.glb",
            "pivot": [round(v, 3) for v in ob.location],
            "rotation_deg": round(ob.rotation_euler.z * 57.2957795, 1),
        })
    data = {
        "house": "modern single-storey villa, 19.0 x 12.5 m, 3.0 m ceilings",
        "rooms": {k: list(v[:4]) for k, v in __import__("villa_src.shell", fromlist=["x"]).ROOMS.items()},
        "pieces": pieces,
        "counts": {"pieces": len(pieces),
                   "objects": len(bpy.data.objects),
                   "polygons": sum(len(o.data.polygons) for o in bpy.data.objects
                                   if o.type == 'MESH')},
    }
    path = os.path.join(VILLA, "manifest.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
    print("manifest", path, data["counts"])
    return data


def main():
    os.makedirs(VILLA, exist_ok=True)
    os.makedirs(os.path.join(VILLA, "furniture"), exist_ok=True)
    sc, colls = S.build()

    # ---- exports
    E.export_house(os.path.join(VILLA, "villa.glb"), tex_size=1024)
    E.relink_textures(E.downscale(512))
    E.export_pieces(os.path.join(VILLA, "furniture"), tex_size=512)
    # pack the (512) textures so the .blend is self-contained
    try:
        bpy.ops.file.pack_all()
    except RuntimeError as exc:
        print("pack_all:", exc)
    E.save_blend(os.path.join(VILLA, "villa.blend"))
    manifest(sc)
    print("BUILD OK")


if __name__ == "__main__":
    main()
