#!/usr/bin/env python3
"""
Compile GLSL shaders to SPIR-V for the Vulkan renderer.

Usage:
    python scripts/compile_shaders.py [glslang_validator_path]

If glslangValidator is not found, the script will print instructions
for manual compilation. The Vulkan renderer loads .spv files at runtime,
so shaders must be compiled before running the engine with Vulkan.
"""

import os
import sys
import subprocess
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SHADER_DIR = os.path.join(PROJECT_ROOT, "engine", "rendering", "vulkan", "shaders")


def find_glslang_validator(path=None):
    """Find glslangValidator executable."""
    if path and os.path.isfile(path):
        return path

    # Common locations
    candidates = [
        "glslangValidator",
        "glslangValidator.exe",
        "/usr/bin/glslangValidator",
        "/usr/local/bin/glslangValidator",
    ]
    for cand in candidates:
        if shutil.which(cand):
            return cand
    return None


def compile_shader(glslang_validator, shader_path, output_path):
    """Compile a single GLSL shader to SPIR-V."""
    cmd = [glslang_validator, "-V", "-o", output_path, shader_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"ERROR: Failed to compile {shader_path}")
            print(result.stderr)
            return False
        print(f"Compiled: {os.path.basename(shader_path)} -> {os.path.basename(output_path)}")
        return True
    except subprocess.TimeoutExpired:
        print(f"ERROR: Timeout compiling {shader_path}")
        return False
    except FileNotFoundError:
        print(f"ERROR: glslangValidator not found: {glslang_validator}")
        return False


def main():
    glslang_validator = sys.argv[1] if len(sys.argv) > 1 else None
    glslang_validator = find_glslang_validator(glslang_validator)

    if not glslang_validator:
        print("=" * 60)
        print("glslangValidator not found!")
        print("=" * 60)
        print()
        print("To compile shaders, install the Vulkan SDK and provide the")
        print("path to glslangValidator:")
        print()
        print("  python scripts/compile_shaders.py /path/to/glslangValidator")
        print()
        print("Or install via your package manager:")
        print("  Ubuntu/Debian: sudo apt-get install vulkan-tools libvulkan-dev")
        print("  macOS:         brew install glslang")
        print("  Windows:       Download Vulkan SDK from lunarg.com")
        print()
        print("Shader source files are in: engine/rendering/vulkan/shaders/")
        print("Compiled SPIR-V output goes to the same directory.")
        print()
        print("Without compiled shaders, the Vulkan renderer will run but")
        print("with no shader programs (draw calls will not produce pixels).")
        print()
        return 1

    # Shader files to compile
    shaders = [
        ("pbr.vert", "pbr.vert.spv"),
        ("pbr.frag", "pbr.frag.spv"),
    ]

    success = True
    for src, dst in shaders:
        shader_path = os.path.join(SHADER_DIR, src)
        output_path = os.path.join(SHADER_DIR, dst)
        if not os.path.isfile(shader_path):
            print(f"ERROR: Shader source not found: {shader_path}")
            success = False
            continue
        if not compile_shader(glslang_validator, shader_path, output_path):
            success = False

    if success:
        print()
        print("All shaders compiled successfully.")
        return 0
    else:
        print()
        print("Some shaders failed to compile.")
        return 1


if __name__ == "__main__":
    sys.exit(main())