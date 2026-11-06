#!/usr/bin/env python3
"""Catch, on the host, the build failures that only show up at NDK link time.

`g++ -fsyntax-only` (what CI used to run) proves the sources parse. It does not prove that a
function another file calls actually exists - and the v7 build died in Gradle on a CMake
mistake that a link check would have shown up immediately. This script:

  1. compiles every native unit to an object with the same stub headers the type check uses;
  2. derives the undefined symbols and the defined symbols from those objects;
  3. fails if a symbol that belongs to *this* project is undefined - i.e. declared and called
     but never implemented, or lost to a signature change;
  4. fails if any unit still mentions JNI;
  5. asserts the CMake project enables C (the NDK glue is a .c file).

Platform symbols (AAsset*, AMotion*, egl*, gl*, the app glue, libc, libstdc++) are expected to
be undefined here: they come from libandroid / libEGL / libGLESv2 / the glue at link time on
the device.
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CPP = ROOT / "android/game/app/src/main/cpp"
VIEWER = ROOT / "android/viewer/app/src/main/cpp"
STUB = ROOT / "tools/android_stub"

UNITS = ["game.cpp", "main_android.cpp", "hud.cpp"]
SHARED = [VIEWER / "vpk.cpp"]

# prefixes that belong to the NDK / platform / compiler runtime
PLATFORM = re.compile(
    r"^(_|std::|__|operator|A[A-Z]\w+Event|AAsset|ALooper|ANativeActivity|ANativeWindow|"
    r"android_app|egl|gl[A-Z]|mem|str|snprintf|vsnprintf|sscanf|printf|fprintf|fopen|fclose|"
    r"fwrite|fread|fseek|ftell|fgetc|ungetc|feof|ferror|malloc|free|realloc|calloc|clock_gettime|"
    r"abort|qsort|atoi|strtod|time$|pow|sin|cos|tan|atan|sqrt|exp|log|floor|ceil|fmod|fabs|"
    r"fmin|fmax|round|hypot|isnan|isfinite|stbi_)"
)

# symbols that must exist somewhere in the project because the app calls them directly
REQUIRED = [
    "game_init", "game_resize", "game_frame", "game_shutdown", "game_status",
    "game_orbs", "game_total", "game_time", "game_state", "game_bearing", "game_reset",
    "hud_init", "hud_begin", "hud_end", "hud_on_gl_lost", "hud_shutdown", "hud_diag",
    "hud_text", "hud_text_right", "hud_text_centered", "hud_text_width", "hud_rect",
    "hud_panel", "hud_disc", "hud_ring", "hud_dim", "hud_crosshair", "hud_chevron",
]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def nm_symbols(obj, kind):
    r = run(["nm", "-C", "--format=posix", "--" + kind + "-only", str(obj)])
    if r.returncode != 0:
        return set()
    names = set()
    for line in r.stdout.splitlines():
        parts = line.split()
        if parts:
            names.add(parts[0])
    return names


def main():
    cmake = (CPP / "CMakeLists.txt").read_text()
    problems = []

    if not re.search(r"project\(\s*villagame\s+C\s+CXX\s*\)", cmake):
        problems.append("CMakeLists.txt: project() must enable C and CXX "
                        "(the NDK app glue is a .c file)")
    if "android_native_app_glue.c" not in cmake:
        problems.append("CMakeLists.txt: the glue source is not compiled")

    for unit in UNITS:
        text = (CPP / unit).read_text()
        if "JNIEXPORT" in text or "Java_ai_arena" in text:
            problems.append(f"{unit}: still contains JNI")

    objs = []
    with tempfile.TemporaryDirectory() as tmp:
        for src in [CPP / u for u in UNITS] + SHARED:
            obj = Path(tmp) / (src.stem + ".o")
            r = run(["g++", "-c", "-O1", "-std=c++17", f"-I{STUB}", f"-I{CPP}", f"-I{VIEWER}",
                     str(src), "-o", str(obj)])
            if r.returncode != 0:
                problems.append(f"{src.name}: does not compile\n{r.stderr.strip()[:800]}")
                continue
            objs.append(obj)
        if problems:
            for p in problems:
                print("FAIL:", p)
            return 1

        defined, undefined = set(), set()
        for o in objs:
            defined |= nm_symbols(o, "defined")
            undefined |= nm_symbols(o, "undefined")

        # nm -C prints demangled names with their parameter list, so compare the base name
        def base_of(sym):
            return re.split(r"[\(\s]", sym, 1)[0]

        defined_bases_pre = {base_of(s) for s in defined}
        missing_required = [s for s in REQUIRED if s not in defined_bases_pre]
        if missing_required:
            problems.append("these app functions are required but never defined: "
                            + ", ".join(sorted(missing_required)))

        # any undefined symbol that looks like ours (not platform) is a missing definition
        base = base_of
        defined_bases = defined_bases_pre
        orphans = sorted({
            base(s) for s in undefined
            if not PLATFORM.match(s) and base(s) not in defined_bases
        })
        if orphans:
            problems.append("undefined project symbols (called but not implemented): "
                            + ", ".join(orphans[:12]))

    print(f"objects: {len(objs)}, defined symbols: {len(defined)}, undefined: {len(undefined)}")
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    print("PASS: every native unit compiles and every project symbol it uses exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())
