"""Render the interior walkthrough (camera path -> PNG frames -> MP4/GIF)."""
import math
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from villa_src import cameras as C, scene as S  # noqa: E402

FRAMES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "villa",
                                          "walkthrough_frames"))
MP4 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "villa",
                                   "walkthrough.mp4"))
GIF = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "villa",
                                   "walkthrough.gif"))


def catmull(points, t):
    """Catmull-Rom through `points` (list of Vector), t in [0,1]."""
    n = len(points) - 1
    if n < 1:
        return points[0]
    x = min(t * n, n - 1e-6)
    i = int(x)
    f = x - i

    def P(j):
        return points[max(0, min(len(points) - 1, j))]

    p0, p1, p2, p3 = P(i - 1), P(i), P(i + 1), P(i + 2)
    return 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * f * f * f)


def path_points():
    pos = [Vector(p) for p, _, _ in C.WALK]
    tgt = [Vector(t) for _, t, _ in C.WALK]
    return pos, tgt


def render(nframes=180, res=(512, 288), samples=10, fps=15):
    if os.path.isdir(FRAMES_DIR):
        shutil.rmtree(FRAMES_DIR)
    os.makedirs(FRAMES_DIR, exist_ok=True)
    sc, colls = S.build()
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 4
    sc.cycles.adaptive_threshold = 0.03
    cam_data = bpy.data.cameras.new("walk_cam")
    cam_data.lens = 22.0
    cam = bpy.data.objects.new("walk_cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    pos, tgt = path_points()
    import time
    t0 = time.time()
    for i in range(nframes):
        u = i / (nframes - 1)
        p = catmull(pos, u)
        q = catmull(tgt, u)
        cam.location = p
        cam.rotation_euler = (q - p).to_track_quat('-Z', 'Y').to_euler()
        path = os.path.join(FRAMES_DIR, f"f{i:04d}.png")
        S.render(sc, cam, path, res=res, samples=samples)
        if i % 10 == 0:
            print(f"FRAME {i}/{nframes} {time.time()-t0:.0f}s", flush=True)
    encode(fps)
    print(f"DONE walkthrough {time.time()-t0:.0f}s", flush=True)


def encode(fps=15):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-framerate", str(fps), "-i", os.path.join(FRAMES_DIR, "f%04d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
           "-movflags", "+faststart", MP4]
    subprocess.run(cmd, check=True, capture_output=True)
    print("MP4", MP4, os.path.getsize(MP4) / 1e6, "MB", flush=True)
    # a compact GIF too (half size, 12 fps)
    pal = os.path.join(FRAMES_DIR, "palette.png")
    subprocess.run([ff, "-y", "-i", MP4, "-vf", "fps=12,scale=420:-1:flags=lanczos,"
                    "palettegen=stats_mode=diff", pal], check=True, capture_output=True)
    subprocess.run([ff, "-y", "-i", MP4, "-i", pal, "-lavfi",
                    "fps=12,scale=420:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer",
                    GIF], check=True, capture_output=True)
    print("GIF", GIF, os.path.getsize(GIF) / 1e6, "MB", flush=True)


if __name__ == "__main__":
    render()
