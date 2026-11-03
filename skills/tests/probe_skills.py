#!/usr/bin/env python3
"""Probe every skill script against the installed Blender build.

Tier A: import + `--help` (catches import-time API breakage and argparse errors).
Tier B: curated functional runs on a purpose-built test scene (real geometry in,
         real JSON out). Run with --functional.

Writes skills/tests/probe_report.json and prints a table.

    python skills/tests/probe_skills.py [--functional] [--only NAME]
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import bpy_run  # noqa: E402

SK = os.path.join(ROOT, "skills")
VENDOR = os.path.join(SK, "vendor", "blender-skills")


def scripts():
    out = []
    for p in sorted(glob.glob(os.path.join(SK, "**", "scripts", "*.py"), recursive=True)):
        if os.path.basename(p).startswith("_"):
            continue
        name = os.path.basename(p)[:-3]
        if name in ("run_in_blender", "env_report"):
            continue
        out.append((os.path.relpath(p, ROOT), name))
    return out


def tier_a(path):
    """Import + --help inside Blender."""
    code = (
        "import runpy, sys, io, contextlib\n"
        f"sys.path.insert(0, {os.path.dirname(os.path.join(ROOT, path))!r})\n"
        f"sys.argv = [{path!r}, '--', '--help']\n"
        "buf = io.StringIO()\n"
        "try:\n"
        f"    with contextlib.redirect_stdout(buf):\n"
        f"        runpy.run_path({os.path.join(ROOT, path)!r}, run_name='__main__')\n"
        "except SystemExit as e:\n"
        "    print('SELFTEST_OK exit', e.code)\n"
        "print('SELFTEST_DONE')\n"
    )
    return run_code(code)


def run_code(code):
    fd, p = tempfile.mkstemp(suffix=".py")
    with os.fdopen(fd, "w") as f:
        f.write(code)
    try:
        return bpy_run.run_script(p, [], quiet=True)
    finally:
        os.unlink(p)


def test_scene():
    """A small but realistic scene: beveled hard-surface part, organic sphere,
    UV-mapped, textured, multi-material."""
    path = "/tmp/skilltest_scene.blend"
    if os.path.exists(path):
        return path
    code = f'''
import bpy, math, os, json
bpy.ops.wm.read_factory_settings(use_empty=True)
# hard-surface box with bevel + weighted normals
bpy.ops.mesh.primitive_cube_add(size=0.4, location=(0,0,0.2))
box = bpy.context.object; box.name = "Box"
b = box.modifiers.new("Bevel", "BEVEL"); b.width = 0.02; b.segments = 3
box.select_set(True); bpy.context.view_layer.objects.active = box
bpy.ops.object.modifier_apply(modifier=b.name)
bpy.ops.object.shade_smooth()
with bpy.context.temp_override(object=box, active_object=box,
                               selected_objects=[box], selected_editable_objects=[box]):
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
# organic sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25, location=(0.7,0,0.25))
sph = bpy.context.object; sph.name = "Sphere"; bpy.ops.object.shade_smooth()
# textured material on the box
mat = bpy.data.materials.new("Painted"); mat.use_nodes = True
nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]
img = bpy.data.images.new("Albedo", 64, 64)
tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
nt.links.new(tex.outputs["Color"], bsdf.inputs["Roughness"])
box.data.materials.append(mat)
# export a reference GLB for the export tests
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.camera_add(location=(1.4,-1.6,1.1), rotation=(1.15,0,0.72))
bpy.context.scene.camera = bpy.context.object
bpy.ops.object.light_add(type="AREA", location=(1.5,-1.5,2.2))
bpy.context.object.data.energy = 200; bpy.context.object.data.size = 2
bpy.ops.object.select_all(action="DESELECT")
box.select_set(True); bpy.context.view_layer.objects.active = box
bpy.ops.export_scene.gltf(filepath="/tmp/skilltest_src.glb", export_format="GLB")
bpy.ops.wm.save_as_mainfile(filepath={path!r})
print("@@JSON@@", json.dumps({{"ok": True}}))
'''
    r = run_code(code)
    if r["returncode"] != 0:
        print(r["stderr"][-2000:])
        raise SystemExit("test scene build failed")
    _fixtures()
    return path


def _fixtures():
    """Small inputs the local skills need: a blockout spec and a reference image."""
    spec = {"parts": [
        {"name": "Hull", "type": "box", "size": [4500, 1900, 1400], "at": [0, 0, 700]},
        {"name": "Cabin", "type": "box", "size": [2400, 1600, 500], "at": [0, 120, 1600]},
    ]}
    with open("/tmp/sk_blockout.json", "w") as f:
        json.dump(spec, f)
    if not os.path.exists("/tmp/sk_ref.png"):
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (600, 240), (245, 245, 245))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([40, 70, 560, 200], radius=30, fill=(150, 20, 25))
        im.save("/tmp/sk_ref.png")


# name -> (args, description) functional cases
FUNCTIONAL = {
    # name -> CLI args (after "--"). Verified against each script's own --help.
    "qa_check": ["--objects", "Box", "Sphere", "--profile", "render"],
    "scene_audit": [],
    "uv_pack": ["--objects", "Box"],
    "texel_density": ["--objects", "Box", "--res", "512"],
    "export_asset": ["--objects", "Box", "--preset", "gltf", "--out", "/tmp/sk_export"],
    "render_batch": ["--out", "/tmp/sk_render/####", "--res", "160", "120",
                     "--samples", "8", "--preset", "preview", "--engine", "CYCLES"],
    "turntable": ["--frames", "4", "--rig", "studio"],
    "bake_maps": ["--low", "Box", "--res", "256", "--maps", "normal", "ao"],
    "build_pbr_material": ["--name", "ProbeMat"],
    "apply_stack": ["--objects", "Box"],
    "make_lods": ["--objects", "Sphere", "--ratios", "0.5", "0.25"],
    "mesh_stats": ["--objects", "Box", "Sphere", "--budget", "web"],
    "gn_builder": ["--spec", "/tmp/gn_spec.json", "--apply", "Sphere",
                   "--set", "Density=120"],
    "batch_process": ["--in", "/tmp/skilltest_src.glb", "--op", "report"],
    "auto_retopo": ["--objects", "Sphere", "--method", "decimate", "--tris", "2000"],
    "sculpt_ops": ["--objects", "Sphere", "--ops", "smooth=2", "detail=0.002,0.05"],
    "decal": ["--target", "Box", "--at", "0", "0", "0.4", "--size", "0.1"],
    "smart_material": ["--objects", "Box", "--wear", "0.5", "--grime", "0.3"],
    "scene_mood": ["--time", "golden"],
    # ---- local skills (this repository) ----
    "compose": ["--target", "Box", "--preset", "product", "--render", "--res", "240",
                "--samples", "4", "--out", "/tmp/sk_compose.png"],
    "glass_materials": ["--kind", "architectural", "--assign-to", "Box"],
    "car_paint": ["--kind", "metallic", "--assign-to", "Box"],
    "surface_materials": ["--kind", "rubber", "--assign-to", "Box"],
    "imperfections": ["--objects", "Box", "--wear", "0.3", "--dust", "0.2"],
    "blockout": ["--spec", "/tmp/sk_blockout.json"],
    "review_render": ["--objects", "Box", "Sphere", "--out", "/tmp/sk_review",
                      "--res", "240", "--samples", "8"],
    "verify_export": ["--objects", "Box", "--file", "/tmp/skilltest_src.glb"],
    "studio_lighting": ["--rig", "studio3", "--target", "Box"],
    "render_plan": ["--res", "320", "180", "--shots", "2", "--budget-min", "1"],
    "texel_audit": ["--objects", "Box", "--res", "512"],
    "reference_report": ["--image", "/tmp/sk_ref.png", "--known-mm", "4500"],
    "detail_pass": ["--objects", "Box", "--fix", "--bevel", "0.004"],
    "car_body": ["--preset", "sedan", "--no-wheels", "--subsurf", "1"],
}

# functional cases that need an input file that may not exist
NEEDS_FILE = {"reference_report": "/tmp/sk_ref.png"}


def tier_b(name, path):
    args = FUNCTIONAL.get(name)
    if args is None:
        return None
    need = NEEDS_FILE.get(name)
    if need and not os.path.exists(need):
        return None
    p = os.path.join(VENDOR, name) if os.path.isabs(name) else None
    match = glob.glob(os.path.join(SK, "**", "scripts", f"{name}.py"), recursive=True)
    if not match:
        return {"ok": False, "error": "script not found"}
    return bpy_run.run_script(match[0], args, blend=path, quiet=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--functional", action="store_true")
    ap.add_argument("--only")
    ns = ap.parse_args()

    scene = test_scene() if ns.functional else None
    if ns.functional:
        _fixtures()
    rows = []
    for rel, name in scripts():
        if ns.only and ns.only not in rel:
            continue
        a = tier_a(rel)
        ok_a = a["returncode"] == 0 and "SELFTEST_DONE" in a["stdout"]
        row = {"script": rel, "import_ok": ok_a,
               "err": "" if ok_a else (a["stderr"].strip().splitlines() or [""])[-1][:180]}
        if ns.functional:
            b = tier_b(name, scene)
            if b is not None:
                row["func_ok"] = b["returncode"] == 0 and bool(b["results"])
                row["func_err"] = "" if row["func_ok"] else (
                    (b["stderr"].strip().splitlines() or [""])[-1][:180]
                    or str(b["results"])[:180])
                row["result"] = b["results"][:1]
        rows.append(row)
        print(("%-62s import=%s" % (rel.replace("skills/vendor/blender-skills/", ""),
                                    "OK " if ok_a else "FAIL"))
              + (f" func={row.get('func_ok')}" if "func_ok" in row else ""))
        if not ok_a:
            print("    ", row["err"])
    out = os.path.join(SK, "tests", "probe_report.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(rows, f, indent=1)
    print("\nwrote", out, "| import ok:", sum(r["import_ok"] for r in rows), "/", len(rows))


if __name__ == "__main__":
    main()
