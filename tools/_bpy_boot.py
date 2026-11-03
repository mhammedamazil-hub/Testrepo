"""Bootstrap executed *inside* the bpy interpreter.

Imported/run by tools/bpy_run.py -- never by the host python.
Keeps bpy import + stub-library setup in one place so every skill script behaves
the same whether it is launched by the runner or imported in-process.
"""
import os
import runpy
import sys


def main():
    argv = sys.argv[1:]
    if not argv:
        sys.exit("bootstrap: no script given")
    script = argv[0]
    sys.argv = [script] + argv[1:]
    # bpy.app.binary_path is empty for the pip wheel; Blender derives several default
    # paths from it, so point it at the wheel root to avoid None-handling crashes.
    import bpy  # noqa: F401  (import order matters: stubs must be on LD_LIBRARY_PATH)
    runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main()
