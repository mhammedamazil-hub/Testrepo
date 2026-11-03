#!/usr/bin/env python3
"""Headless Blender runner for the bpy *pip module* (no `blender` binary here).

The skills in this repo follow the common `blender -b script.py -- args` convention.
This runner provides the same contract on top of the `bpy` wheel:

    python tools/bpy_run.py [--blend FILE] [--json] SCRIPT.py [-- script args]
    python tools/bpy_run.py --expr "import bpy; print(bpy.app.version_string)"
    python tools/bpy_run.py --which          # show resolved interpreter/paths
    python tools/bpy_run.py --selftest       # prove headless render works

Environment quirks it handles:
  * the bpy wheel needs the no-op X/GL stubs in .glstub (see tools/blender_stub.py);
    they are rebuilt automatically if missing;
  * `bpy` must be imported *after* LD_LIBRARY_PATH is set, hence the subprocess;
  * scripts print machine-readable results on `@@JSON@@` lines.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUB = os.path.join(ROOT, ".glstub")
VENV_PY = os.path.join(ROOT, ".venv", "bin", "python")
BOOT = os.path.join(ROOT, "tools", "_bpy_boot.py")
MARK = "@@JSON@@"


def python_exe():
    return VENV_PY if os.path.exists(VENV_PY) else sys.executable


def ensure_stubs(verbose=True):
    """Build .glstub/libstub.so + sonames if they are not already present."""
    lib = os.path.join(STUB, "libstub.so")
    if os.path.exists(lib) and os.path.exists(os.path.join(STUB, "libXrender.so.1")):
        return STUB
    if verbose:
        print("[bpy_run] stub library missing -> building", file=sys.stderr)
    subprocess.run([python_exe(), os.path.join(ROOT, "tools", "blender_stub.py")],
                   cwd=ROOT, check=True)
    return STUB


def env_for_bpy():
    env = dict(os.environ)
    stub = ensure_stubs()
    old = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = os.pathsep.join(p for p in (stub, old) if p)
    env.setdefault("PYTHONHASHSEED", "0")
    return env


def run_script(script, args, blend=None, timeout=None, quiet=False):
    # skills read their arguments after a literal "--" (the Blender convention);
    # insert it once so `bpy_run.py script.py --objects Foo` behaves like `blender -b`.
    args = list(args)
    if args and args[0] != "--":
        args = ["--"] + args
    cmd = [python_exe(), BOOT, os.path.abspath(script)] + args
    if blend:
        cmd = [python_exe(), "-c",
               "import sys,runpy;sys.argv=['x','%s'];import bpy;"
               "bpy.ops.wm.open_mainfile(filepath=r'%s');"
               "sys.argv=['%s']+%r;runpy.run_path(r'%s',run_name='__main__')"
               % (blend, os.path.abspath(blend), os.path.abspath(script),
                  list(args), os.path.abspath(script))]
    proc = subprocess.run(cmd, cwd=ROOT, env=env_for_bpy(), capture_output=True,
                          text=True, timeout=timeout)
    out, err = proc.stdout, proc.stderr
    results = [json.loads(ln[len(MARK):]) for ln in out.splitlines()
               if ln.startswith(MARK)]
    if not quiet:
        if out:
            print(out.rstrip())
        if err and proc.returncode != 0:
            print(err.rstrip(), file=sys.stderr)
    return {"returncode": proc.returncode, "stdout": out, "stderr": err,
            "results": results}


def selftest():
    """Real render + real export, so 'it works' means something."""
    import tempfile
    code = r'''
import bpy, os, json, tempfile
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.mesh.primitive_uv_sphere_add(radius=1)
bpy.ops.object.shade_smooth()
bpy.ops.object.camera_add(location=(0,-4,1.2), rotation=(1.35,0,0))
sc.camera = bpy.context.object
bpy.ops.object.light_add(type='AREA', location=(2,-2,3)); bpy.context.object.data.energy=400
mat = bpy.data.materials.new("m"); mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.4,0.2,0.1,1)
bpy.data.objects["Sphere"].data.materials.append(mat)
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 8
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 160, 120
d = tempfile.mkdtemp()
sc.render.filepath = os.path.join(d, "t.png")
bpy.ops.render.render(write_still=True)
glb = os.path.join(d, "t.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB")
print("@@JSON@@", json.dumps({
    "version": bpy.app.version_string,
    "render_bytes": os.path.getsize(sc.render.filepath),
    "glb_bytes": os.path.getsize(glb)}))
'''
    print("selftest: rendering + exporting ...", file=sys.stderr)
    res = run_script_text(code)
    if res["returncode"] != 0:
        print(res["stderr"][-800:], file=sys.stderr)
    print("selftest:", res["returncode"], res["results"])
    return res


def run_script_text(code):
    """Run a code string inside the bpy interpreter (used by selftest/tests)."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        return run_script(path, [], quiet=True)
    finally:
        os.unlink(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("script", nargs="?")
    ap.add_argument("--blend")
    ap.add_argument("--expr")
    ap.add_argument("--which", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--timeout", type=int, default=None)
    ap.add_argument("args", nargs=argparse.REMAINDER)
    ns = ap.parse_args()

    if ns.which:
        print("python:", python_exe())
        print("stub  :", ensure_stubs(False))
        print("boot  :", BOOT)
        return 0
    if ns.selftest:
        return 0 if selftest()["returncode"] == 0 else 1
    if ns.expr:
        res = run_script_text(ns.expr)
        return res["returncode"]
    if not ns.script:
        ap.error("need SCRIPT.py, --expr, --which or --selftest")
    args = [a for a in ns.args if a != "--"]
    res = run_script(ns.script, args, ns.blend, ns.timeout, ns.quiet)
    return res["returncode"]


if __name__ == "__main__":
    sys.exit(main())
