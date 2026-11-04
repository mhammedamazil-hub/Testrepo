"""Villa v2 — professional-looking rebuild of the exterior (and the interior light).

    .venv/bin/python tools/bpy_run.py villa_src/build_v2.py -- --render --out /tmp/v2

Why v2 exists: v1 was geometrically correct and completely flat to look at. One white
volume, a black fascia, a flat lawn, trees made of spheres. The fixes are, in the order
they matter for realism:

1. **Light.** v1 lit the exterior with a 1.0-strength physical sky and a 4.6 W sun, which
   pushed every surface into the top of the AgX curve: white walls, white sky, no shadow
   contrast. v2 uses a low, raking late-afternoon sun with a much weaker sky dome.
2. **Relief.** A plinth, piers, deep overhang with a slatted soffit, window reveals,
   downpipes, coping, a chimney. Architecture reads through shadow lines.
3. **Real foliage.** Card-based trees, olives, cypresses, palms, hedges and grasses
   (`vegetation.py`) instead of UV spheres.
4. **Site.** Terrace with joints, a pool with coping and water, gravel margins, planting
   beds, a drive with gate piers, a garden wall — so the house sits in a place.
5. **Materials.** Lime render over board-formed concrete, travertine, timber, asphalt,
   gravel: all image-textured with normal + roughness maps (`tex_gen2.py`).

Run `python -m villa_src.tex_gen && python -m villa_src.tex_gen2` first.
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from villa_src import arch_v2 as A  # noqa: E402
from villa_src import cameras_v2 as C  # noqa: E402
from villa_src import lighting, mats, shell  # noqa: E402
from villa_src import scene as S  # noqa: E402
from villa_src import vegetation as V  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "villa_v2")

# site objects from v1 that v2 rebuilds from scratch
V1_SITE = ("terrace", "lawn", "drive", "pool_shell", "pool_water", "tree_", "shrub_")
# v1 roof pieces are replaced by the layered roof in arch_v2.roof(): leaving them in
# hides the new parapet, the coping and the dark membrane under a lit microcement slab
V1_ROOF = ("roof_slab", "fascia_")


def _purge_v1_site():
    coll = bpy.data.collections.get("Site")
    if not coll:
        return 0
    n = 0
    for ob in list(coll.objects):
        base = ob.name.split(".")[0]
        if any(base.startswith(p) for p in V1_SITE):
            bpy.data.objects.remove(ob, do_unlink=True)
            n += 1
    return n


def _purge_v1_roof():
    n = 0
    for ob in list(bpy.data.objects):
        if ob.name.split(".")[0].startswith(V1_ROOF) or "fascia" in ob.name:
            bpy.data.objects.remove(ob, do_unlink=True)
            n += 1
    return n


def _ground(coll):
    """Lawns + a distant field: the horizon needs grass, not world colour."""
    out = []
    for name, (x, y, sx, sy) in {
        "lawn_s": (9.5, -34.0, 150.0, 60.0),
        "lawn_n": (9.5, 44.0, 150.0, 60.0),
        "lawn_w": (-40.0, 0.0, 70.0, 150.0),
        "lawn_e": (58.0, 0.0, 70.0, 150.0),
    }.items():
        out.append(A.K.slab(name, x - sx / 2, y - sy / 2, x + sx / 2, y + sy / 2,
                            -0.30, -0.02, "lawn_v2", coll=coll))
    return out


def _grass_fringe(coll, n=240, seed=3):
    """Upright blade tufts along the terrace edge.

    A flat card lying on the ground renders as a green shard on the paving: the alpha
    cuts the spray shape, but there is no vertical extent to read as grass. Cards are
    therefore stood upright and anchored at the soil line.
    """
    import random
    rnd = random.Random(seed)
    pts = []
    for i in range(n):
        x = rnd.uniform(-1.0, 23.0)
        y = rnd.uniform(-8.3, -6.4)
        w = rnd.uniform(0.20, 0.34)
        h = w * rnd.uniform(1.5, 2.3)
        # centre placed half a card above the ground so the base sits at z=0
        p = Vector((x, y, h * 0.5))
        # mostly vertical, with a lean and a random facing
        nrm = Vector((rnd.uniform(-0.55, 0.55), rnd.uniform(-0.55, 0.55), 1.0))
        pts.append((p, nrm.normalized(), w, h))
    return [V.card_cloud("grass_fringe", pts, "grass_blade", coll, seed=seed)]


def build(with_site=True):
    sc_, _colls = S.build(with_site=False)          # shell, glazing, furniture, lights
    ext = bpy.data.collections.get("Shell")
    site = bpy.data.collections.get("Site")
    ceiling = bpy.data.collections.get("Ceiling")
    veg = bpy.data.collections.new("Planting")
    sc_.collection.children.link(veg)

    removed = _purge_v1_site()
    removed_roof = _purge_v1_roof()
    t0 = time.time()
    A.facade_extras(ext)
    A.roof(ceiling)
    A.roof_plant(ceiling)
    if with_site:
        _ground(site)
        A.site_v2(site)
        A.terrace_detail(site, veg)
        objs = A.garden(veg, site)
        _grass_fringe(site)
    print(f"site+planting {time.time() - t0:.1f}s ({removed} v1 site objects replaced, "
          f"{removed_roof} v1 roof objects replaced)", flush=True)

    lighting_v2(sc_)
    setup_render(sc_)
    return sc_, ext


def _sky_clouds(world, scale=9.0, cover0=0.50, cover1=0.61, brightness=3.1):
    """Put a cumulus field in the world shader.

    A physical sky on its own renders as a flat, pale gradient, which is the loudest
    "this is CGI" tell in an exterior. Clouds are a noise field sampled along the view
    direction: they converge at the horizon for free (perspective of the dome), cost one
    texture lookup, and they also break up the environment light so surfaces are not lit
    by a perfectly uniform dome.
    """
    if not (world and world.node_tree):
        return None
    nt = world.node_tree
    bg = next((n for n in nt.nodes if n.type == "BACKGROUND"), None)
    if bg is None or not bg.inputs["Color"].links:
        return None
    base = bg.inputs["Color"].links[0].from_socket
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-1000, 300)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-820, 420)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.location = (-820, 200)
    mp.inputs["Scale"].default_value = (1.0, 1.0, 2.6)   # squash z: flat, layer-like cloud
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.location = (-620, 240)
    n1.inputs["Scale"].default_value = scale
    n1.inputs["Detail"].default_value = 5.0
    n1.inputs["Roughness"].default_value = 0.58
    n1.inputs["Distortion"].default_value = 0.18
    nt.links.new(mp.outputs["Vector"], n1.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-420, 240)
    ramp.color_ramp.elements[0].position = cover0
    ramp.color_ramp.elements[1].position = cover1
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    # no clouds below the horizon (they would show through the ground edges)
    hmask = nt.nodes.new("ShaderNodeMapRange")
    hmask.location = (-420, 20)
    hmask.inputs["From Min"].default_value = 0.03
    hmask.inputs["From Max"].default_value = 0.30
    nt.links.new(sep.outputs["Z"], hmask.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.location = (-200, 140)
    nt.links.new(ramp.outputs["Color"], mul.inputs[0])
    nt.links.new(hmask.outputs["Result"], mul.inputs[1])
    clim = nt.nodes.new("ShaderNodeRGB")
    clim.location = (-200, -120)
    clim.outputs[0].default_value = (brightness, brightness * 0.985, brightness * 0.96, 1.0)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.location = (60, 40)
    mix.inputs[0].default_value = 0.0
    nt.links.new(mul.outputs["Value"], mix.inputs[0])
    nt.links.new(base, mix.inputs[6])
    nt.links.new(clim.outputs[0], mix.inputs[7])
    nt.links.new(mix.outputs[2], bg.inputs["Color"])
    return mix


def lighting_v2(sc):
    """Late-afternoon raking sun: the single biggest change in the whole rebuild."""
    world = sc.world
    if world and world.node_tree:
        sky = next((n for n in world.node_tree.nodes if n.type == "TEX_SKY"), None)
        bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
        if sky:
            sky.sun_elevation = math.radians(20.0)      # late afternoon, long shadows
            sky.sun_rotation = math.radians(232.0)      # from the south-west, low
            sky.sun_intensity = 1.0
            sky.altitude = 40.0
            sky.aerosol_density = 1.55
            sky.air_density = 1.1
        if bg:
            bg.inputs["Strength"].default_value = 0.42   # sky as light (fill for shade)
    _sky_clouds(world)
    sun = bpy.data.objects.get("Sun")
    if sun:
        el = math.radians(20.0)
        az = math.radians(232.0)
        d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el),
                    math.sin(el)))
        sun.rotation_euler = (-d).to_track_quat("Z", "Y").to_euler()
        sun.data.energy = 4.4
        sun.data.angle = math.radians(0.9)
        sun.data.color = (1.0, 0.84, 0.68)
    # Interior practicals: v1's wattages were tuned for a 1.0-strength sky. With the sky
    # dome down to 0.30 the interiors need their own level, so the interior set is boosted
    # rather than the whole scene (and the exterior stays contrasty).
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.name.startswith(("fill_", "spot_")):
            ob.data.energy *= 1.35
    # A large soft "terrace bounce" card outside the south glazing. Real interiors are lit
    # by the whole sunlit terrace; without it the rooms read as a dark box with a bright
    # window. This is the standard archviz bounce-card trick.
    lg = bpy.data.lights.new("terrace_bounce", type="AREA")
    lg.shape = "RECTANGLE"
    lg.size, lg.size_y = 12.0, 3.2
    lg.energy = 900.0
    lg.color = (1.0, 0.95, 0.90)
    ob = bpy.data.objects.new("terrace_bounce", lg)
    sc.collection.objects.link(ob)
    ob.location = (6.6, -2.6, 0.9)
    ob.rotation_euler = (math.radians(-70.0), 0.0, 0.0)
    # second bounce card for the entry side, which faces away from the sun and would
    # otherwise be the only dead-black wall on the house
    lg2 = bpy.data.lights.new("entry_bounce", type="AREA")
    lg2.shape = "RECTANGLE"
    lg2.size, lg2.size_y = 6.0, 4.0
    lg2.energy = 420.0
    lg2.color = (1.0, 0.92, 0.84)
    ob2 = bpy.data.objects.new("entry_bounce", lg2)
    sc.collection.objects.link(ob2)
    ob2.location = (24.5, 5.2, 2.2)
    ob2.rotation_euler = (0.0, math.radians(78.0), math.radians(-14.0))
    return sun


def setup_render(sc):
    S.setup_render(sc)
    sc.cycles.samples = 128
    sc.cycles.adaptive_threshold = 0.012
    sc.cycles.max_bounces = 10
    sc.cycles.diffuse_bounces = 5
    sc.cycles.glossy_bounces = 4
    sc.cycles.transmission_bounces = 8
    sc.cycles.sample_clamp_indirect = 6.0
    sc.view_settings.exposure = 0.0
    return sc


def cameras(sc, res=(1440, 810)):
    out = {}
    for name, (loc, tgt, lens) in C.SHOTS.items():
        out[name] = S.camera("cam_" + name, loc, tgt, lens=lens)
    return out


def _setup_view(name):
    """Per-view exposure, exactly as an architectural photographer would shoot each room.

    Exterior and interior cannot share one exposure: the exterior is 5-7 stops brighter.
    Rendering both at one setting is what makes archviz look either blown out or murky.
    """
    interior = name in ("living", "living_wide", "kitchen", "dining", "master", "corridor",
                        "foyer", "bed2", "bath", "study")
    sc = bpy.context.scene
    sc.view_settings.exposure = (0.55 if interior else -0.55)
    for ob in bpy.data.objects:
        if ob.type != "LIGHT":
            continue
        if ob.name.startswith(("fill_", "spot_", "terrace_bounce", "entry_bounce")):
            ob.data.energy = ob.get("_base", ob.data.energy)
            if "_base" not in ob:
                ob["_base"] = ob.data.energy
            # the terrace bounce stays for every view; the entry bounce is only ever
            # there to lift the shaded east facade, so it is *not* cut on exteriors
            if not interior and ob.name not in ("terrace_bounce", "entry_bounce"):
                ob.data.energy *= 0.35
    return interior


def render_set(sc, cams, names=None, res=(1440, 810), samples=96, out=OUT):
    os.makedirs(out, exist_ok=True)
    times = {}
    for name, cam in cams.items():
        if names and name not in names:
            continue
        _setup_view(name)
        path = os.path.join(out, f"{name}.png")
        t = time.time()
        S.render(sc, cam, path, res=res, samples=samples)
        times[name] = round(time.time() - t, 1)
        print(f"RENDER {name} {times[name]}s -> {path}", flush=True)
    return times


def main():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--shots", nargs="*", default=None)
    ap.add_argument("--res", type=int, nargs=2, default=[1440, 810])
    ap.add_argument("--samples", type=int, default=96)
    ns = ap.parse_args(argv)

    sc, ext = build()
    cams = cameras(sc)
    stats = {"objects": len(bpy.data.objects),
             "polygons": sum(len(o.data.polygons) for o in bpy.data.objects
                             if o.type == "MESH"),
             "materials": len(bpy.data.materials)}

    def walk(ob):
        n = 0
        for c in bpy.data.collections:
            if ob.name in c.objects:
                n += 1
                n += walk(c) if c.name not in ("", ) else 0
        return n

    stats["planting_objects"] = len(bpy.data.collections["Planting"].objects)
    if ns.save:
        os.makedirs(ns.out, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ns.out, "villa_v2.blend"))
    if ns.render:
        stats["render_seconds"] = render_set(sc, cams, ns.shots, res=tuple(ns.res),
                                             samples=ns.samples, out=ns.out)
    print("V2 BUILT", json.dumps(stats), flush=True)


if __name__ == "__main__":
    main()
