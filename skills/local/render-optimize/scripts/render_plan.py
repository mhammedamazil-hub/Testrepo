"""Plan a render budget from measured cost, instead of guessing.

Renders one tiny calibration frame, measures seconds-per-sample-pixel on THIS machine,
then predicts the cost of the settings you actually want and picks settings that fit a
time budget. Also reports scene load (tris, lights, materials, image textures) and
warns about the usual time sinks:

  * no denoiser          -> you pay for samples you cannot see
  * huge bounce counts   -> 2x cost for <1 % visible difference on interiors
  * 4k+ textures         -> memory pressure (this sandbox has ~3.9 GB)
  * transmission/volume  -> caustic-heavy setups are the slowest thing in Cycles

Usage:
  python tools/bpy_run.py <this> -- --budget-min 10 --res 1280 720 --shots 12
"""
import os
import sys
import time

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402


def scene_load():
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    tris = sum(sc.tri_count(o) for o in meshes)
    imgs = [i for i in bpy.data.images if i.size[0] > 0]
    tex_mem = sum(i.size[0] * i.size[1] * 4 * (4 if i.is_float else 1) for i in imgs)
    return {"mesh_objects": len(meshes), "tris": tris,
            "lights": len([o for o in bpy.context.scene.objects if o.type == "LIGHT"]),
            "materials": len(bpy.data.materials),
            "image_textures": len(imgs),
            "texture_mem_mb": round(tex_mem / 1e6, 1),
            "biggest_texture": max([list(i.size) for i in imgs], default=None)}


def calibrate(res=(256, 144)):
    """Fit t = overhead + per_sample * (spp * kpixel) from two tiny renders.

    Two points separate the fixed cost (BVH build, texture upload, shader compile) from
    the per-sample cost, which is what makes the estimate usable on a heavy scene."""
    sc_ = bpy.context.scene
    scene = sc_
    engine = scene.render.engine
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.use_denoising = True
    rx, ry = scene.render.resolution_x, scene.render.resolution_y
    pct = scene.render.resolution_percentage
    if scene.camera is None:
        raise ValueError("no camera: add one with camera-composition or review_render")
    out = "/tmp/_render_plan_calib.png"
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.filepath = out
    kpx = res[0] * res[1] / 1000.0
    times = {}
    for spp in (8, 64):
        scene.cycles.samples = spp
        best = 1e9
        for _ in range(2):            # two runs: the BVH build is cached after the first
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            best = min(best, time.time() - t0)
        times[spp] = max(best, 0.01)
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    scene.render.resolution_percentage = pct
    scene.render.engine = engine
    b = (times[64] - times[8]) / (56 * kpx)          # seconds per sample*kpixel
    if b <= 1e-6:                                    # measurement noise dominated
        b = times[64] / (64 * kpx)
    a = max(times[8] - b * 8 * kpx, 0.0)             # fixed per-frame overhead
    return {"res": list(res), "seconds_at_8spp": round(times[8], 2),
            "seconds_at_64spp": round(times[64], 2),
            "fixed_overhead_s": round(a, 3),
            "sec_per_sample_kpx": round(b, 5),
            "note": "fit from two renders: fixed cost (BVH/shader) separated from "
                    "per-sample cost"}


def run(budget_min=10.0, res=(1280, 720), shots=1, samples=None, adaptive=True,
        denoise=True, max_bounces=6, **_):
    sc.object_mode()
    calib = calibrate()
    load = scene_load()
    kpx = res[0] * res[1] / 1000.0
    per_sample = calib["sec_per_sample_kpx"] * kpx
    overhead = calib["fixed_overhead_s"]

    def estimate(spp):
        return (overhead + per_sample * spp) * shots / 60.0

    if samples:
        plan_spp = samples
    else:
        # denominator: with adaptive sampling + OIDN, this scene class converges
        # around 16-64 spp; pick the highest multiple of 8 that fits the budget
        fit = int((budget_min * 60) / max(per_sample * shots, 1e-9))
        plan_spp = max(8, min(256, (fit // 8) * 8))

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = plan_spp
    scene.cycles.use_denoising = denoise
    scene.cycles.use_adaptive_sampling = adaptive
    scene.cycles.adaptive_threshold = 0.02 if adaptive else 0.0
    scene.cycles.max_bounces = max_bounces
    scene.cycles.diffuse_bounces = min(3, max_bounces)
    scene.cycles.glossy_bounces = min(3, max_bounces)
    scene.cycles.transmission_bounces = min(6, max_bounces)
    scene.render.resolution_x, scene.render.resolution_y = res

    warnings = []
    if not denoise:
        warnings.append("denoising off: you will need 4-8x the samples for the same noise")
    if max_bounces > 8:
        warnings.append(f"max_bounces={max_bounces}: interiors rarely need >8; each "
                        "bounce adds cost")
    if load["biggest_texture"] and max(load["biggest_texture"]) >= 4096:
        warnings.append("texture >= 4k: memory pressure on a 3.9 GB box; 2k is usually "
                        "indistinguishable at product-shot framing")
    if estimate(plan_spp) > budget_min * 1.25:
        warnings.append(f"estimate {estimate(plan_spp):.1f} min exceeds budget; lower "
                        "resolution or shots")
    return {"ok": True, "calibration": calib, "scene_load": load,
            "plan": {"res": list(res), "samples": plan_spp, "shots": shots,
                     "denoise": denoise, "adaptive": adaptive,
                     "max_bounces": max_bounces,
                     "estimated_min": round(estimate(plan_spp), 2)},
            "alternatives": [{"samples": s, "estimated_min": round(estimate(s), 2)}
                             for s in (8, 16, 32, 64, 128, 256)],
            "warnings": warnings,
            "note": "estimate = one measured calibration render x sample count x pixel "
                    "count x shots; it ignores per-shot scene differences"}


if __name__ == "__main__":
    p = sc.add_common(sc.parser(__doc__), save=False)
    p.add_argument("--budget-min", type=float, default=10.0)
    p.add_argument("--res", type=int, nargs=2, default=(1280, 720))
    p.add_argument("--shots", type=int, default=1)
    p.add_argument("--samples", type=int, default=None)
    p.add_argument("--no-adaptive", dest="adaptive", action="store_false")
    p.add_argument("--no-denoise", dest="denoise", action="store_false")
    p.add_argument("--max-bounces", type=int, default=6)
    sc.cli(run, p)
