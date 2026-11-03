"""Studio lighting rigs without HDRI downloads (none are reachable in this sandbox).

Three real product-photography rigs, built from area lights with plausible colour
temperatures and power, plus honest alternatives for reflection detail:

  studio3    classic key / fill / rim + soft top light (default, safest)
  softbox    big single softbox + reflector bounce card (beauty / car bodywork)
  hardlight  small sources for crisp speculars (metal, glass, hard-surface)
  automotive long strip lights above + to the sides (long highlights down a car flank)

Because there is no HDRI, reflections are built from geometry: this rig also spawns
optional "card" planes (emissive) that give glass and paint something to reflect.
That is what makes a shiny object read as real instead of as a grey blob.

Usage:
  python tools/bpy_run.py <this> -- --rig softbox --target Car --backdrop
  python tools/bpy_run.py <this> -- --rig automotive --target Car --exposure -0.3
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402

RIGS = ("studio3", "softbox", "hardlight", "automotive")
# colour temperature -> linear RGB (approx, 3200 K tungsten .. 6500 K daylight)
TEMPS = {3200: (1.0, 0.76, 0.53), 4000: (1.0, 0.85, 0.70), 5000: (1.0, 0.95, 0.90),
         5600: (1.0, 0.98, 0.96), 6500: (0.95, 0.98, 1.0)}


def _temp(k):
    return TEMPS[min(TEMPS, key=lambda t: abs(t - k))]


def _area(name, loc, look_at, energy, size, temp=5600, shape="RECTANGLE", size_y=None):
    lg = bpy.data.lights.new(name, "AREA")
    lg.energy = energy
    lg.size = size
    if size_y:
        lg.shape = "RECTANGLE"
        lg.size_y = size_y
    else:
        lg.shape = shape
    lg.color = _temp(temp)
    ob = bpy.data.objects.new(name, lg)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def _card(name, loc, look_at, size=3.0, strength=1.6):
    """Emissive bounce card: gives glossy surfaces a visible reflection."""
    me = bpy.data.meshes.new(name)
    s = size / 2
    me.from_pydata([(-s, 0, -s), (s, 0, -s), (s, 0, s), (-s, 0, s)], [],
                   [(0, 1, 2, 3)])
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = sc.node(nt, "ShaderNodeOutputMaterial")
    em = sc.node(nt, "ShaderNodeEmission", (-250, 0))
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    me.materials.append(mat)
    ob.location = loc
    ob.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    ob.visible_camera = False    # reflect, don't see
    return ob


def build(rig="studio3", target=None, backdrop=True, exposure=0.0, world_strength=0.25,
          scale=1.0):
    if rig not in RIGS:
        raise ValueError(f"rig must be one of {RIGS}")
    scene = bpy.context.scene
    objs = sc.objects([target] if target else None)
    lo, hi = sc.aabb(objs[0])
    for o in objs[1:]:
        l2, h2 = sc.aabb(o)
        lo = Vector([min(a, b) for a, b in zip(lo, l2)])
        hi = Vector([max(a, b) for a, b in zip(hi, h2)])
    center = (lo + hi) / 2
    span = max((hi - lo).length, 0.5)
    s = max(scale, 0.05)
    if target:
        sphere = bpy.data.objects.get(f"{target}_studio_sphere")
        if sphere:
            center, span = sphere.location.copy(), sphere.radius

    # a dim world so shadows are not pure black, but reflections come from geometry
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Studio")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.05, 0.055, 0.065, 1)
    bg.inputs[1].default_value = world_strength

    created = []
    if backdrop:
        bpy.ops.mesh.primitive_plane_add(size=span * 12, location=(center.x, center.y,
                                                                  lo.z - 0.002))
        bpy.context.object.name = "studio_floor"
        fm = bpy.data.materials.new("studio_floor_mat")
        fm.use_nodes = True
        b = sc.principled(fm)
        sc.set_input(b, "Base Color", (0.16, 0.163, 0.17, 1))
        sc.set_input(b, "Roughness", 0.35)
        bpy.context.object.data.materials.append(fm)
        created.append("studio_floor")

    d = span
    if rig == "studio3":
        created += [_area("key", center + Vector((d * 1.1, -d * 1.2, d * 1.5)), center,
                          700 * s, d * 1.2, 5600).name,
                    _area("fill", center + Vector((-d * 1.4, -d * 0.9, d * 0.6)), center,
                          220 * s, d * 1.6, 4000).name,
                    _area("rim", center + Vector((-d * 0.6, d * 1.5, d * 1.2)), center,
                          600 * s, d * 0.5, 6500).name,
                    _area("top", center + Vector((0, 0, d * 2.0)), center, 300 * s,
                          d * 1.4, 5600).name]
    elif rig == "softbox":
        created += [_area("softbox", center + Vector((d * 1.2, -d * 1.6, d * 1.1)), center,
                          1100 * s, d * 2.2, 5600, size_y=d * 1.6).name,
                    _area("fill_card", center + Vector((-d * 2.0, -d * 1.2, d * 0.5)),
                          center, 160 * s, d * 2.5, 4000).name]
        created.append(_card("reflector", center + Vector((-d * 1.4, d * 0.2, d * 0.2)),
                             center, span * 2.0, 1.3).name)
    elif rig == "hardlight":
        created += [_area("spot_key", center + Vector((d * 1.0, -d * 1.0, d * 1.6)), center,
                          900 * s, d * 0.18, 5600).name,
                    _area("kicker", center + Vector((d * 1.6, d * 0.8, d * 0.9)), center,
                          500 * s, d * 0.12, 6500).name,
                    _area("edge_l", center + Vector((-d * 1.2, d * 1.1, d * 0.5)), center,
                          400 * s, d * 0.10, 6500).name]
    else:  # automotive: long overhead strip + two side strips
        created += [_area("strip_top", center + Vector((0, -d * 0.2, d * 2.1)), center,
                          1400 * s, span * 2.4, 5600, size_y=d * 0.35).name,
                    _area("strip_left", center + Vector((-d * 1.7, 0, d * 0.9)), center,
                          800 * s, span * 2.2, 6000, size_y=d * 0.5).name,
                    _area("strip_right", center + Vector((d * 1.7, 0, d * 0.9)), center,
                          800 * s, span * 2.2, 6000, size_y=d * 0.5).name,
                    _area("sweep_front", center + Vector((0, -d * 2.2, d * 0.8)), center,
                          260 * s, d * 2.0, 5000).name]

    sc.look_transform(scene, "AgX - Medium High Contrast", exposure)
    return {"created": created, "center": list(center), "span": span,
            "exposure": exposure}


def run(rig="studio3", target=None, backdrop=True, exposure=0.0, world_strength=0.25,
        scale=1.0, clear=False, **_):
    sc.object_mode()
    if clear:
        for ob in list(bpy.data.objects):
            if ob.type == "LIGHT" or ob.name.startswith(("studio_", "key", "fill", "rim",
                                                         "top", "softbox", "reflector",
                                                         "spot_key", "kicker", "edge_",
                                                         "strip_", "sweep_")):
                bpy.data.objects.remove(ob, do_unlink=True)
    info = build(rig, target, backdrop, exposure, world_strength, scale)
    return {"ok": True, "rig": rig, **info}


if __name__ == "__main__":
    p = sc.add_common(sc.parser(__doc__), save=False)
    p.add_argument("--rig", default="studio3", choices=list(RIGS))
    p.add_argument("--target", default=None, help="object to centre the rig on")
    p.add_argument("--no-backdrop", dest="backdrop", action="store_false")
    p.add_argument("--exposure", type=float, default=0.0)
    p.add_argument("--world-strength", type=float, default=0.25)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--clear", action="store_true", help="remove previous rig objects")
    sc.cli(run, p)
