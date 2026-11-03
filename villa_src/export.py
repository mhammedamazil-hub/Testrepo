"""Deliverable export: .blend, whole-house GLB, and one GLB per furniture piece.

Per-piece GLBs keep the piece's authored pivot (centre of the footprint, on the
floor, front facing -Y).
"""
import os
import re
import glob

import bpy
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEX = os.path.join(ROOT, "villa", "tex")
OUT = os.path.join(ROOT, "villa")


def downscale(size=512):
    """Create villa/tex_<size>/ with resized copies, return the folder."""
    dst = os.path.join(ROOT, f"villa/tex_{size}")
    os.makedirs(dst, exist_ok=True)
    for f in glob.glob(os.path.join(TEX, "*.png")):
        out = os.path.join(dst, os.path.basename(f))
        if os.path.exists(out):
            continue
        im = Image.open(f)
        im.resize((size, size), Image.LANCZOS).save(out)
    return dst


def relink_textures(folder):
    """Point every loaded villa texture at the copies inside `folder`."""
    n = 0
    for img in bpy.data.images:
        fp = bpy.path.abspath(img.filepath) if img.filepath else ""
        if not fp or not os.path.exists(fp):
            continue
        name = os.path.basename(fp)
        alt = os.path.join(folder, name)
        if os.path.exists(alt):
            img.filepath = alt
            img.reload()
            n += 1
    return n


def _gltf(path, **kw):
    args = dict(filepath=path, export_format='GLB', export_apply=True,
                export_yup=True, export_texcoords=True, export_normals=True,
                export_materials='EXPORT', export_image_format='JPEG',
                export_cameras=False, export_lights=False,
                export_extras=False, export_animations=False)
    args.update(kw)
    bpy.ops.export_scene.gltf(**args)
    return os.path.getsize(path)


def export_house(path, tex_size=1024):
    if tex_size != 1024:
        relink_textures(downscale(tex_size))
    for ob in bpy.data.objects:
        ob.select_set(True)
    size = _gltf(path, use_selection=False, export_image_quality=88)
    print(f"house GLB {path} {size/1e6:.2f} MB")
    return size


def export_pieces(outdir, tex_size=512, prefix=""):
    os.makedirs(outdir, exist_ok=True)
    if tex_size != 1024:
        relink_textures(downscale(tex_size))
    fur = bpy.data.collections.get("Furniture")
    allowed = set(o.name for o in fur.objects) if fur else set()
    pieces = [o for o in bpy.data.objects if o.get("piece") and o.name in allowed]
    total = 0
    manifest = []
    for ob in sorted(pieces, key=lambda o: o.name):
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", ob.name)
        path = os.path.join(outdir, f"{prefix}{safe}.glb")
        size = _gltf(path, use_selection=True, export_image_quality=85)
        total += size
        manifest.append((ob.name, os.path.basename(path), ob.get("piece"), size))
    print(f"exported {len(manifest)} pieces, {total/1e6:.1f} MB total")
    return manifest


def save_blend(path):
    bpy.ops.wm.save_as_mainfile(filepath=path, relative_remap=True, compress=True)
    print("blend", path, f"{os.path.getsize(path)/1e6:.1f} MB")
    return os.path.getsize(path)
