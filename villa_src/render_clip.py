"""Render a short camera move to MP4.

Stills answer "what does it look like"; a clip answers "is it real". This is the animation
version of `render_hero.py`: same build, lookdev, sun, mist and grade, but the camera is
keyframed and the frames go through an encoder.

The bpy wheel has **no FFMPEG support** (its image_settings.file_format enum stops at
TIFF), so frames are rendered as PNG and encoded with the static ffmpeg that ships inside
`imageio-ffmpeg`. That also means a crash mid-render does not lose the frames already done.

    .venv/bin/python tools/bpy_run.py villa_src/render_clip.py -- \
        --res 960 540 --samples 20 --frames 100 --out villa_v2/video/villa_tour.mp4
"""
import json
import math
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from villa_src import build_v2 as B  # noqa: E402
from villa_src import lookdev_v3 as L  # noqa: E402
from villa_src import render_hero as R  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# One motivated move: crane down behind the garden hedge, drift east along the terrace and
# settle on the pool corner. Slow, eased, no cuts - the archviz "reveal", not a flythrough.
# (position, aim point) at the start and the end; the aim interpolates too.
CAM_A = ((5.20, -21.60, 5.60), (9.60, 1.20, 2.60))
CAM_B = ((23.90, -8.40, 1.90), (12.20, 0.60, 1.55))


def build_camera(sc, lens=32.0, shift_y=0.05, fstop=6.3, focus=None):
    """Camera + an empty it tracks. Both are keyframed later."""
    aim = bpy.data.objects.new("EMPTY_CamAim", None)
    sc.collection.objects.link(aim)
    aim.empty_display_size = 0.4

    cam_data = bpy.data.cameras.new("CAM_Tour")
    cam_data.lens = lens
    cam_data.sensor_width = 36.0
    cam_data.shift_y = shift_y
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = fstop
    cam_data.dof.aperture_blades = 7
    cam = bpy.data.objects.new("CAM_Tour", cam_data)
    sc.collection.objects.link(cam)
    con = cam.constraints.new("TRACK_TO")
    con.target = aim
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    sc.camera = cam
    if focus:
        cam_data.dof.focus_distance = (Vector(CAM_A[0]) - Vector(focus)).length
    return cam, aim


def _fcurves(ob):
    """Blender 5.0 actions are slotted: fcurves live under layers/strips/channelbags."""
    act = ob.animation_data.action
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    out = []
    for layer in getattr(act, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cb in getattr(strip, "channelbags", []):
                out.extend(cb.fcurves)
    return out


def keyframe_move(cam, aim, frames):
    """Ease-in/ease-out over the whole clip (Bezier with auto-clamped handles)."""
    a, b = Vector(CAM_A[0]), Vector(CAM_B[0])
    ta, tb = Vector(CAM_A[1]), Vector(CAM_B[1])
    for f, t in ((1, 0.0), (frames, 1.0)):
        # smoothstep, so the move starts and stops without a jolt
        s = t * t * (3.0 - 2.0 * t)
        cam.location = a.lerp(b, s)
        aim.location = ta.lerp(tb, s)
        cam.keyframe_insert("location", frame=f)
        aim.keyframe_insert("location", frame=f)
    for ob in (cam, aim):
        for fc in _fcurves(ob):
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    # a mid keyframe keeps the camera from cutting the corner through the hedge
    cam.location = a.lerp(b, 0.5) + Vector((0.0, -1.6, 0.35))
    aim.location = ta.lerp(tb, 0.5)
    cam.keyframe_insert("location", frame=frames // 2)
    aim.keyframe_insert("location", frame=frames // 2)


def encode(frames_dir, out_path, fps, pattern="%04d.png"):
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = [exe, "-y", "-framerate", str(fps), "-i", os.path.join(frames_dir, pattern),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path]
    print("ENCODE", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, capture_output=True)
    return os.path.getsize(out_path)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, nargs=2, default=[960, 540])
    ap.add_argument("--samples", type=int, default=20)
    ap.add_argument("--frames", type=int, default=100)
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--out", default=os.path.join("villa_v2", "video", "villa_tour.mp4"))
    ap.add_argument("--frames-dir", default="/tmp/tour_frames")
    ap.add_argument("--no-comp", action="store_true")
    ns = ap.parse_args(argv)

    sc, ext = B.build()
    look = L.run(dirt=1.25)
    cam, aim = build_camera(sc)
    keyframe_move(cam, aim, ns.frames)
    R.setup_sun(sc)
    R.setup_mist(sc)
    R.setup_cycles(sc, ns.samples, tuple(ns.res), bounces=8, caustics=False)
    # video: looser adaptive threshold and no 16-bit output, or the clip takes a night
    sc.cycles.adaptive_threshold = 0.02
    sc.render.image_settings.color_depth = "8"
    sc.render.fps = ns.fps
    sc.frame_start, sc.frame_end = 1, ns.frames
    if not ns.no_comp:
        R.setup_compositor(sc, mist_amount=0.62)

    if os.path.isdir(ns.frames_dir):
        shutil.rmtree(ns.frames_dir)
    os.makedirs(ns.frames_dir, exist_ok=True)
    sc.render.filepath = os.path.join(ns.frames_dir, "")
    sc.render.image_settings.file_format = "PNG"

    t0 = time.time()
    bpy.ops.render.render(animation=True)
    dt = time.time() - t0

    frames = sorted(f for f in os.listdir(ns.frames_dir) if f.endswith(".png"))
    if len(frames) < ns.frames:
        print(f"WARN only {len(frames)}/{ns.frames} frames rendered", flush=True)
    out = os.path.join(ROOT, ns.out)
    size = encode(ns.frames_dir, out, ns.fps)
    info = {"frames": len(frames), "fps": ns.fps, "res": ns.res, "samples": ns.samples,
            "seconds": round(len(frames) / ns.fps, 2), "render_minutes": round(dt / 60, 1),
            "per_frame_s": round(dt / max(1, len(frames)), 1),
            "camera": {"from": CAM_A[0], "to": CAM_B[0]},
            "file": out, "bytes": size, "mb": round(size / 1e6, 2), "lookdev": look}
    with open(os.path.splitext(out)[0] + ".json", "w") as f:
        json.dump(info, f, indent=1)
    print("CLIP", json.dumps(info), flush=True)
    print(f"CLIP DONE {out} ({dt/60:.1f} min, {len(frames)} frames)", flush=True)


if __name__ == "__main__":
    main()
