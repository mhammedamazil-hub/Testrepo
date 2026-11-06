#!/usr/bin/env python3
"""Static tripwires for the bugs that only showed up on the Android device.

This sandbox has no GPU, no emulator and no phone, so the device path is checked two ways:
`tools/gles_shader_check.py` links the GLSL statically, and this script pins the handful of
contracts that a screenshot from a real phone proved were broken in v3.0. It is deliberately
narrow - it asserts *exactly* the invariants that were violated, so that a refactor cannot
quietly bring them back:

  1. post-process quad   - the full-screen quad carries clip-space -1..1, so a texture
                           coordinate derived from it must be remapped to 0..1. v3.0 passed
                           clip space straight into texture2D(), so half of every frame
                           sampled the edge texel of the scene target: the "mangled mesh".
  2. camera basis        - the skybox and the orb billboards must use the same right/up
                           vectors as mat4_lookat (right = fwd x world-up). v3.0 used
                           (cos yaw, 0, -sin yaw), which is the exact opposite, so the sky
                           rendered rotated by 180 degrees.
  3. baked attribute     - the model shader samples the AO/sun pair from vertex bytes 6..7
                           with a 20-byte stride, at attribute slot 3.
  4. texture unit        - every model texture is uploaded and bound on GL_TEXTURE0, because
                           the post chain leaves a different unit active.
  5. input signs         - stick up is forward, drag up looks up. Both were inverted.

Exit status is 0 only when every check passes.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME_CPP = ROOT / "android/game/app/src/main/cpp/game.cpp"
SURFACE = ROOT / "android/game/app/src/main/java/ai/arena/villagame/GameSurface.java"

failures = []
checks = 0


def check(ok, name, detail=""):
    global checks
    checks += 1
    if ok:
        print(f"  ok    {name}")
    else:
        print(f"  FAIL  {name}" + (f"\n        {detail}" if detail else ""))
        failures.append(name)


def shader_body(src, name):
    """Return the C string literal block that defines `name`."""
    m = re.search(rf'static const char\* {name} =\n(.*?);\n', src, re.S)
    return m.group(1) if m else ""


def main():
    src = GAME_CPP.read_text()
    java = SURFACE.read_text()

    print("post-process quad")
    qvs = shader_body(src, "kPostQuadVS")
    check(bool(qvs), "kPostQuadVS exists")
    # the remap can be written a few ways; all of them must touch 0.5
    check("0.5" in qvs and "v_uv" in qvs, "quad VS remaps clip space into 0..1 uv",
          "v_uv is derived from a_p without a 0.5 remap, so texture2D sees negative uvs")
    check("gl_Position = vec4(a_p" in qvs, "quad VS still writes clip space to gl_Position")

    print("camera basis")
    check("static void camera_basis(" in src, "camera_basis() exists")
    body = src[src.index("static void camera_basis("):]
    body = body[: body.index("\n}\n")]
    check("right[0] = -fwd[2] / rl" in body and "right[2] = fwd[0] / rl" in body,
          "right = fwd x world-up = (-fwd.z, 0, fwd.x)",
          "a different right axis mirrors or rotates the skybox")
    check("up[0] = right[1] * fwd[2] - right[2] * fwd[1]" in body, "up = right x fwd")
    check("camera_basis(yaw, pitch, fwd, right, up)" in src, "draw_sky uses camera_basis")
    # and the view matrix really does use f x up - assert the shared source of truth
    shade = (ROOT / "android/viewer/app/src/main/cpp/shade.h").read_text()
    check("f[1] * up[2] - f[2] * up[1]" in shade, "mat4_lookat right axis = f x up")

    print("vertex attribute contract")
    fs = shader_body(src, "kModelFS")
    vs = shader_body(src, "kModelVS")
    check("attribute vec2 a_ao;" in vs, "a_ao declared as vec2")
    check('"a_pos", "a_nrm", "a_uv", "a_ao"' in src, "attribute slots bound in order 0..3")
    check("glVertexAttribPointer(3, 2, GL_UNSIGNED_BYTE, GL_TRUE, VPK_VERTEX_STRIDE, (void*)6)"
          in src, "a_ao reads bytes 6..7 of the 20-byte vertex")
    check("float ao = 0.26 + 0.74 * (v_ao.x * v_ao.x);" in fs, "fragment stage uses v_ao.x for ao")
    check("float sv = 0.10 + 0.90 * v_ao.y;" in fs, "fragment stage uses v_ao.y for sun visibility")

    print("texture units")
    up = src[src.index("static void upload_texture("):]
    up = up[: up.index("\n}\n")]
    check("glActiveTexture(GL_TEXTURE0)" in up,
          "upload_texture selects unit 0 itself",
          "the post chain leaves unit 2 active; uploading there is invisible to the shader")
    check("glBindTexture(GL_TEXTURE_2D, G.white_tex)" in src,
          "a missing texture binds a white texel instead of texture 0 (black in ES2)")

    print("input signs")
    check("stick.y = -dy / r;" in java, "stick y = -dy (drag up is forward)")
    check("pendingPitch -= dy * LOOK_SENS;" in java, "drag up looks up")
    check("G.game.update(dt, jy, jx, dyaw, dpitch);" in src,
          "nativeFrame passes the stick through without a second negation",
          "negating here again inverts the stick")

    print("look constants")

    def vec3_after(pattern):
        m = re.search(pattern, src)
        if not m:
            return None
        return tuple(round(float(x), 4) for x in m.groups())

    # the sky quad
    quad_zen = vec3_after(r"const float zen\[3\] = \{([-\d.]+)f, ([-\d.]+)f, ([-\d.]+)f\}")
    quad_hor = vec3_after(r"const float hor\[3\] = \{([-\d.]+)f, ([-\d.]+)f, ([-\d.]+)f\}")
    # sky_at() inside the model fragment shader, used for glass and water reflections
    sh_zen = vec3_after(r"vec3 zen = vec3\(([-\d.]+), ([-\d.]+), ([-\d.]+)\);")
    sh_hor = vec3_after(r"vec3 hor = vec3\(([-\d.]+), ([-\d.]+), ([-\d.]+)\);")
    check(quad_zen is not None and quad_zen == sh_zen,
          "sky zen in draw_sky equals sky_at() in the model shader",
          f"sky quad {quad_zen} vs reflections {sh_zen}: glass and water reflect a different sky")
    check(quad_hor is not None and quad_hor == sh_hor,
          "sky horizon in draw_sky equals sky_at() in the model shader",
          f"sky quad {quad_hor} vs reflections {sh_hor}")
    check(quad_zen is not None and sum(quad_zen) > 0.45,
          "the sky is authored as a daytime sky, not dusk",
          f"zenith {quad_zen} is a dusk value: the garden reads as night")

    print()
    if failures:
        print(f"FAIL: {len(failures)} of {checks} device contracts broken")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"PASS: {checks} device contracts hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
