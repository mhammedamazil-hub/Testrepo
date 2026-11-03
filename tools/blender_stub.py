#!/usr/bin/env python3
"""Rebuild the no-op X11/GL stub library that lets headless Blender (bpy wheel) load
in a container with no X libraries installed.

Only X / XKB / GLX / GL / EGL / DRI / GBM / Xi symbols are stubbed -- stubbing every
undefined symbol makes Blender segfault, because TBB/MaterialX/etc. must resolve to the
real .so files shipped inside the wheel.

Usage:  python3 tools/blender_stub.py [--venv .venv]
Then:   LD_LIBRARY_PATH=$PWD/.glstub .venv/bin/python your_script.py
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

STUB_DIR = ".glstub"
PATTERN = re.compile(r"^(_?X|xkb|glX|gl[A-Z_]|egl|dri|gbm|Xi)")

# sonames Blender's libs ask for (dlopen / NEEDED); all get the same stub handle.
SONAMES = [
    "libGL.so.1", "libGL.so", "libGLX.so.0", "libEGL.so.1", "libGLdispatch.so.0",
    "libOpenGL.so.0", "libX11.so.6", "libX11.so", "libXext.so.6", "libXi.so.6",
    "libXrender.so.1", "libXfixes.so.3", "libXrandr.so.2", "libXcursor.so.1",
    "libXinerama.so.1", "libXxf86vm.so.1", "libXt.so.6", "libSM.so.6", "libICE.so.6",
    "libxkbcommon.so.0", "libxkbcommon-x11.so.0", "libxcb.so.1", "libxcb-dri2.so.0",
    "libxcb-dri3.so.0", "libxcb-glx.so.0", "libxcb-shm.so.0", "libxcb-render.so.0",
    "libxcb-present.so.0", "libxcb-sync.so.1", "libxcb-xfixes.so.0",
    "libxshmfence.so.1", "libgbm.so.1", "libdrm.so.2", "libwayland-client.so.0",
    "libwayland-cursor.so.0", "libwayland-egl.so.1",
]


def undefined_symbols(paths):
    syms = set()
    for so in paths:
        try:
            out = subprocess.run(
                ["nm", "-D", "--undefined-only", so],
                capture_output=True, text=True, check=False).stdout
        except OSError:
            continue
        for line in out.splitlines():
            parts = line.split()
            if parts:
                name = parts[-1]
                # strip version suffix e.g. XOpenDisplay@libX11.so.6
                syms.add(name.split("@")[0])
    return syms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venv", default=".venv")
    args = ap.parse_args()

    site = None
    for root, dirs, files in os.walk(args.venv):
        if os.path.basename(root) == "bpy" and "lib" in dirs:
            site = root
            break
    if not site:
        sys.exit("bpy package not found -- pip install bpy first")

    libs = []
    for root, _, files in os.walk(site):
        for f in files:
            if f.endswith(".so") or ".so." in f:
                libs.append(os.path.join(root, f))
    print(f"scanning {len(libs)} shared objects under {site}")

    wanted = sorted(s for s in undefined_symbols(libs) if PATTERN.match(s))
    print(f"{len(wanted)} X/GL symbols to stub")

    os.makedirs(STUB_DIR, exist_ok=True)
    lines = ["/* auto-generated no-op stubs for headless Blender */",
             "void *gl_stub_trampoline(void) { return 0; }"]
    for s in wanted:
        lines.append(f"void {s}(void) {{ }}")
    src = os.path.join(STUB_DIR, "stub.c")
    with open(src, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(STUB_DIR, "syms.txt"), "w") as f:
        f.write("\n".join(wanted) + "\n")

    so = os.path.join(STUB_DIR, "libstub.so")
    subprocess.run(["gcc", "-shared", "-fPIC", "-O1", "-o", so, src], check=True)
    for name in SONAMES:
        dst = os.path.join(STUB_DIR, name)
        if os.path.lexists(dst):
            os.remove(dst)
        shutil.copyfile(so, dst)
    print(f"built {so} and {len(SONAMES)} soname copies")


if __name__ == "__main__":
    main()
