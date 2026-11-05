"""Hero still: the "ultra realistic" delivery render.

Built on the v2 scene and the `blender-skills` workflow (archviz -> lookdev -> rendering ->
compositing). Every stage below is switched on by measurement, not by faith:

  build      v2 scene (textured, planted, lit) + lookdev pass (cavity grime, edge wear)
  camera     35 mm, 1.65 m eye, verticals corrected with shift_y, DOF f/5.6 on the entry
  light      late-afternoon sky + sun, plus volumetric mist so the trees have depth
  render     Cycles CPU, adaptive sampling, OIDN, 16 bounces, caustics for the pool
  grade      compositor: exposure -> look -> glare (fog glow) -> lens dispersion ->
             vignette, all reversible and agnostic of the view transform
  delivery   PNG 16-bit + a JPEG, plus a sidecar JSON with every setting used

    .venv/bin/python tools/bpy_run.py villa_src/render_hero.py -- \
        --shot hero_garden --res 2560 1440 --samples 192 --out villa_v2/hero

Stage timings and the actual sample/time trade-off are printed, because "512 samples" on
2 vCPU is a day, not a render.
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from villa_src import build_v2 as B  # noqa: E402
from villa_src import lookdev_v3 as L  # noqa: E402
from villa_src import scene as S  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Hero camera set. "35 mm at 1.65 m with corrected verticals" is the archviz default; the
# wides are 28 mm and only used where perspective is wanted.
HERO_CAMS = {
    # name: (location, target, lens_mm, shift_y, fstop, focus_point)
    "hero_garden": ((6.60, -18.20, 2.35), (9.40, 1.40, 2.00), 30.0, 0.060, 7.1,
                    (9.4, -1.2, 1.1)),
    "hero_pool": ((27.20, -7.60, 2.20), (11.60, 1.00, 1.45), 30.0, 0.040, 6.3,
                  (15.0, -1.6, 0.6)),
    "hero_entry": ((26.40, 10.30, 1.95), (19.35, 5.05, 1.55), 38.0, 0.050, 5.0,
                   (19.2, 5.05, 1.4)),
    "hero_aerial": ((11.20, -25.60, 13.40), (9.80, 2.40, 0.60), 40.0, 0.020, 9.0,
                    (9.8, 2.4, 3.0)),
    "hero_corner": ((20.80, -12.60, 1.70), (14.20, 1.60, 2.10), 28.0, 0.060, 7.1,
                    (16.0, -0.8, 1.2)),
}


def setup_camera(sc, name):
    loc, tgt, lens, shift, fstop, focus = HERO_CAMS[name]
    cam = S.camera("CAM_Hero_" + name, loc, tgt, lens=lens)
    cam.data.sensor_width = 36.0
    cam.data.shift_y = shift          # keeps the verticals vertical
    cam.data.shift_x = 0.0
    # depth of field: focus on a point, a real aperture, not f/0.1
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = (Vector(loc) - Vector(focus)).length
    cam.data.dof.aperture_fstop = fstop
    cam.data.dof.aperture_blades = 7
    sc.camera = cam
    return cam


def setup_sun(sc, elevation=22.0, azimuth=205.0, energy=4.6):
    """Raking but not grazing: at 232 deg the south facade is edge-lit and reads flat.

    The azimuth is measured the same way as v2 (0 = sun due north, clockwise). 205 deg puts
    the sun front-left of the hero camera, which gives the glazing a shadow pattern and the
    travertine piers a lit face plus a dark face - the pair is what makes a facade read 3D.
    """
    sky = next((n for n in sc.world.node_tree.nodes if n.type == "TEX_SKY"), None) \
        if sc.world and sc.world.node_tree else None
    if sky:
        sky.sun_elevation = math.radians(elevation)
        sky.sun_rotation = math.radians(azimuth)
        sky.sun_intensity = 1.0
        sky.aerosol_density = 1.55
        sky.altitude = 40.0
    sun = bpy.data.objects.get("Sun")
    if sun:
        el, az = math.radians(elevation), math.radians(azimuth)
        d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        sun.rotation_euler = (-d).to_track_quat("Z", "Y").to_euler()
        sun.data.energy = energy
        sun.data.angle = math.radians(0.85)
        sun.data.color = (1.0, 0.855, 0.70)
    return {"sun_elevation": elevation, "sun_azimuth": azimuth, "sun_energy": energy}


def setup_mist(sc, start=18.0, depth=280.0, amount=0.62):
    """Aerial perspective through the Mist pass instead of a world volume.

    A uniform volume scatters the sky as well as the landscape: at 0.0022/m the 700 m ridge
    was lit through an optical depth of 1.5 and the whole sky went to 20 % brightness
    (measured). The Mist pass gives the same depth cue with none of that, and it is what a
    compositor is for.
    """
    vl = sc.view_layers[0]
    vl.use_pass_mist = True
    if sc.world:
        sc.world.mist_settings.start = start
        sc.world.mist_settings.depth = depth
        sc.world.mist_settings.falloff = "QUADRATIC"
    return {"mist_start": start, "mist_depth": depth, "mist_amount": amount}


def setup_cycles(sc, samples, res, bounces=12, caustics=False):
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.005
    sc.cycles.adaptive_min_samples = max(32, samples // 8)
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    # NOTE: two Cycles processes in parallel OOM-killed this 3.9 GB box at ~3.8 GB RSS.
    # One render at a time, 12 bounces, caustics off by default: the pool reads fine without
    # them and they are the most expensive thing in the scene.
    sc.cycles.max_bounces = bounces
    sc.cycles.diffuse_bounces = 5
    sc.cycles.glossy_bounces = 6
    sc.cycles.transmission_bounces = 10
    sc.cycles.transparent_max_bounces = 12
    sc.cycles.caustics_reflective = caustics
    sc.cycles.caustics_refractive = caustics
    sc.cycles.blur_glossy = 0.5          # slightly wider GGX: real glass and stone
    sc.cycles.use_light_tree = True
    sc.cycles.sample_clamp_indirect = 8.0
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "16"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -0.55
    sc.view_settings.gamma = 1.0
    sc.render.use_persistent_data = False   # memory, not speed: this box has 3.9 GB


def setup_compositor(sc, glare=0.12, vignette=0.16, dispersion=0.008, mist_amount=0.62,
                     mist_tint=(0.74, 0.80, 0.90)):
    """Beauty stack: exposure -> balance -> aerial mist -> glare -> lens -> vignette.

    Verified semantics in Blender 5.0's compositor (each node rendered and measured, because
    they are not documented and two of them are the opposite of what you would guess):

      * `CompositorNodeAlphaOver` factor 1 = ENTIRELY the Foreground image, 0 = Background;
      * `ShaderNodeMix` (RGBA) blends toward B at factor 1;
      * `CompositorNodeEllipseMask` is white inside the ellipse, so a vignette needs 1-mask;
      * the classic CompositorNodeComposite / MixRGB / Math nodes no longer exist.
    """
    ng = bpy.data.node_groups.new("COMP_Hero", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    sc.compositing_node_group = ng
    sc.render.use_compositing = True
    n, ln = ng.nodes, ng.links

    rl = n.new("CompositorNodeRLayers")
    rl.location = (-1000, 0)
    rl.scene = sc

    ex = n.new("CompositorNodeExposure")
    ex.location = (-820, 0)
    ex.inputs["Exposure"].default_value = 0.0
    ln.new(rl.outputs["Image"], ex.inputs["Image"])

    cb = n.new("CompositorNodeColorBalance")
    cb.location = (-660, 0)
    try:
        cb.correction_method = "LIFT_GAMMA_GAIN"
    except Exception:
        pass
    for socket_name, rgb in (("Lift", (0.985, 0.995, 1.02)),
                             ("Gamma", (1.0, 1.0, 1.0)),
                             ("Gain", (1.04, 1.005, 0.97))):
        cols = [i for i in cb.inputs if i.name == socket_name and i.type == "RGBA"]
        if cols:
            cols[0].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    ln.new(ex.outputs["Image"], cb.inputs["Image"])

    # ---- aerial perspective: far geometry drifts toward the sky colour
    mist = n.new("ShaderNodeMath")
    mist.location = (-660, -300)
    mist.operation = "MULTIPLY"
    mist.inputs[1].default_value = mist_amount
    mist.use_clamp = True
    ln.new(rl.outputs["Mist"], mist.inputs[0])
    sky = n.new("CompositorNodeRGB")
    sky.location = (-480, -420)
    sky.outputs[0].default_value = (mist_tint[0], mist_tint[1], mist_tint[2], 1.0)
    mists = n.new("ShaderNodeMix")
    mists.location = (-360, 0)
    mists.data_type = "RGBA"
    ln.new(mist.outputs["Value"], mists.inputs[0])
    ln.new(cb.outputs["Image"], mists.inputs[6])
    ln.new(sky.outputs[0], mists.inputs[7])

    # ---- glare, only on genuinely blown highlights
    gl = n.new("CompositorNodeGlare")
    gl.location = (-180, 0)
    try:
        gl.inputs["Type"].default_value = "Fog Glow"
        gl.inputs["Quality"].default_value = "High"
    except Exception:
        pass
    for k, v in (("Threshold", 1.6), ("Strength", glare), ("Smoothness", 0.25)):
        if k in gl.inputs:
            try:
                gl.inputs[k].default_value = v
            except Exception:
                pass
    ln.new(mists.outputs[2], gl.inputs["Image"])

    ld = n.new("CompositorNodeLensdist")
    ld.location = (0, 0)
    ld.inputs["Distortion"].default_value = 0.0
    ld.inputs["Dispersion"].default_value = dispersion
    ln.new(gl.outputs["Image"], ld.inputs["Image"])

    # ---- vignette: darkening = (1 - mask) * strength, applied through AlphaOver whose
    #      factor is the *foreground* amount, so the factor is 1 - darkening
    em = n.new("CompositorNodeEllipseMask")
    em.location = (0, -360)
    em.inputs["Size"].default_value = (0.78, 0.78)
    em.inputs["Position"].default_value = (0.5, 0.52)
    bl = n.new("CompositorNodeBlur")
    bl.location = (160, -360)
    bl.inputs["Size"].default_value = (260, 260)
    ln.new(em.outputs["Mask"], bl.inputs["Image"])
    inv = n.new("ShaderNodeMath")
    inv.location = (330, -360)
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    ln.new(bl.outputs["Image"], inv.inputs[1])
    scale = n.new("ShaderNodeMath")
    scale.location = (470, -360)
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = vignette
    ln.new(inv.outputs["Value"], scale.inputs[0])
    keep = n.new("ShaderNodeMath")
    keep.location = (610, -360)
    keep.operation = "SUBTRACT"
    keep.inputs[0].default_value = 1.0
    ln.new(scale.outputs["Value"], keep.inputs[1])

    dark = n.new("CompositorNodeRGB")
    dark.location = (330, -560)
    dark.outputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
    ao = n.new("CompositorNodeAlphaOver")
    ao.location = (800, 0)
    ln.new(dark.outputs[0], ao.inputs["Background"])
    ln.new(ld.outputs["Image"], ao.inputs["Foreground"])
    ln.new(keep.outputs["Value"], ao.inputs["Factor"])

    out = n.new("NodeGroupOutput")
    out.location = (1000, 0)
    ln.new(ao.outputs["Image"], out.inputs[0])
    return ng


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", default="hero_garden", choices=sorted(HERO_CAMS))
    ap.add_argument("--res", type=int, nargs=2, default=[2560, 1440])
    ap.add_argument("--samples", type=int, default=192)
    ap.add_argument("--out", default=os.path.join("villa_v2", "hero"))
    ap.add_argument("--dirt", type=float, default=1.25)
    ap.add_argument("--mist", type=float, default=0.62,
                    help="aerial-perspective strength (0 = off, 1 = heavy)")
    ap.add_argument("--no-comp", action="store_true")
    ap.add_argument("--sun-el", type=float, default=22.0)
    ap.add_argument("--sun-az", type=float, default=205.0)
    ap.add_argument("--sun-energy", type=float, default=4.6)
    ap.add_argument("--exposure", type=float, default=-0.35)
    ap.add_argument("--bounces", type=int, default=12)
    ap.add_argument("--caustics", action="store_true")
    ap.add_argument("--look", default="AgX - Medium High Contrast")
    ns = ap.parse_args(argv)

    t0 = time.time()
    sc, ext = B.build()
    t_build = time.time() - t0
    look = L.run(dirt=ns.dirt)
    cam = setup_camera(sc, ns.shot)
    setup_cycles(sc, ns.samples, tuple(ns.res), bounces=ns.bounces, caustics=ns.caustics)
    sun_info = setup_sun(sc, ns.sun_el, ns.sun_az, ns.sun_energy)
    mist_info = setup_mist(sc, amount=ns.mist)
    sc.view_settings.exposure = ns.exposure
    try:
        sc.view_settings.look = ns.look
    except TypeError:
        pass
    if not ns.no_comp:
        setup_compositor(sc, mist_amount=ns.mist)

    out_dir = os.path.join(ROOT, ns.out)
    os.makedirs(os.path.dirname(out_dir) or ".", exist_ok=True)
    base = f"{ns.shot}_{ns.res[0]}x{ns.res[1]}_{ns.samples}spp"
    path = out_dir + "_" + os.path.basename(base) + ".png"
    sc.render.filepath = path
    os.makedirs(os.path.dirname(path), exist_ok=True)

    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    t_render = time.time() - t1

    info = {
        "shot": ns.shot, "res": ns.res, "samples": ns.samples,
        "camera": HERO_CAMS[ns.shot][:3], "lens_mm": HERO_CAMS[ns.shot][2],
        "shift_y": HERO_CAMS[ns.shot][3], "fstop": HERO_CAMS[ns.shot][4],
        "view_transform": sc.view_settings.view_transform,
        "look": sc.view_settings.look, "exposure": sc.view_settings.exposure,
        "mist": mist_info, "sun": sun_info, "lookdev": look,
        "build_seconds": round(t_build, 1), "render_seconds": round(t_render, 1),
        "file": path, "bytes": os.path.getsize(path),
        "render": {"max_bounces": sc.cycles.max_bounces,
                   "adaptive_threshold": sc.cycles.adaptive_threshold,
                   "denoiser": sc.cycles.denoiser,
                   "caustics": [sc.cycles.caustics_reflective, sc.cycles.caustics_refractive]},
        "villa": {"objects": len(bpy.data.objects),
                  "polygons": sum(len(o.data.polygons) for o in bpy.data.objects
                                  if o.type == "MESH"),
                  "materials": len(bpy.data.materials)},
    }
    with open(os.path.splitext(path)[0] + ".json", "w") as f:
        json.dump(info, f, indent=1)
    print("HERO", json.dumps(info), flush=True)
    print(f"HERO DONE {path} ({t_render/60:.1f} min render, {t_build:.0f} s build)", flush=True)


if __name__ == "__main__":
    main()
