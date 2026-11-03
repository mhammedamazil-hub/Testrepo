"""Daylight + interior lighting."""
import math

import bpy
from mathutils import Vector

from . import kit, mats, shell

SUN_EL = 34.0        # degrees above horizon
SUN_AZ = 152.0       # degrees, 0 = +Y (north), clockwise -> from the south-east


def sky(scene, strength=1.0):
    world = bpy.data.worlds.new("VillaSky")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    out.location = (400, 0)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.location = (200, 0)
    bg.inputs["Strength"].default_value = strength
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.location = (-60, 0)
    types = [i.identifier for i in sky.bl_rna.properties["sky_type"].enum_items]
    if "MULTIPLE_SCATTERING" in types:
        sky.sky_type = "MULTIPLE_SCATTERING"
    elif "NISHITA" in types:
        sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(SUN_EL)
    sky.sun_rotation = math.radians(SUN_AZ)
    sky.sun_intensity = 1.0
    for attr, val in (("air_density", 1.0), ("aerosol_density", 2.2),
                      ("ozone_density", 1.0), ("altitude", 60.0), ("dust_density", 1.6)):
        if hasattr(sky, attr):
            try:
                setattr(sky, attr, val)
            except (AttributeError, TypeError):
                pass
    sky.sun_size = math.radians(2.2)
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return sky


def sun(scene, energy=4.6, angle=1.4):
    """A sun lamp matched to the sky texture's direction."""
    el = math.radians(SUN_EL)
    az = math.radians(SUN_AZ)
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    light = bpy.data.lights.new("Sun", type='SUN')
    light.energy = energy
    light.angle = math.radians(angle)
    light.color = (1.0, 0.955, 0.90)
    ob = bpy.data.objects.new("Sun", light)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = (-d).to_track_quat('Z', 'Y').to_euler()
    return ob


def _area(name, loc, size, energy, color=(1.0, 0.90, 0.78), coll=None, shape='DISK',
          rot=(0, 0, 0)):
    light = bpy.data.lights.new(name, type='AREA')
    light.energy = energy
    light.shape = shape
    light.size = size
    light.color = color
    ob = bpy.data.objects.new(name, light)
    (coll or bpy.context.scene.collection).objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def _downlight(x, y, z=2.98, r=0.055, coll=None, energy=14.0):
    """Recessed ceiling spot: visible trim + emissive lens + the actual light."""
    kit.lathe("dl_trim", [(r, 0.0), (r, 0.018), (r * 0.86, 0.02), (r * 0.86, 0.0)],
              (x, y, z), mat="white_paint", seg=20, coll=coll)
    kit.lathe("dl_lens", [(0, 0.0), (r * 0.84, 0.0), (r * 0.84, 0.004), (0, 0.004)],
              (x, y, z - 0.002), mat=mats.warm((1.0, 0.88, 0.72), 18.0, "downlight_lens"), seg=20, coll=coll)
    return _area(f"spot_{x:.1f}_{y:.1f}", (x, y, z - 0.02), 0.10, energy,
                 coll=coll, rot=(0, 0, 0))


# room -> list of downlight positions and per-light wattage
ROOM_LIGHTS = {
    "living":   ([(1.6, 2.0), (4.0, 2.0), (1.6, 5.4), (4.0, 5.4), (6.4, 3.6)], 11),
    "dining":   ([(8.1, 1.6), (9.7, 1.6), (8.1, 5.6), (9.7, 5.6)], 13),
    "kitchen":  ([(11.4, 1.4), (13.6, 1.4), (11.4, 5.9), (13.6, 5.9),
                  (14.6, 3.4), (12.0, 3.4)], 14),
    "utility":  ([(16.2, 1.4), (17.8, 1.4)], 11),
    "foyer":    ([(16.2, 4.6), (17.8, 4.6)], 12),
    "corridor": ([(3.0, 7.2), (6.2, 7.2), (9.4, 7.2), (12.6, 7.2), (15.8, 7.2),
                  (17.6, 7.2)], 11),
    "master":   ([(1.4, 9.0), (3.4, 9.0), (1.4, 11.4), (3.4, 11.4)], 14),
    "robe":     ([(6.5, 8.7)], 12),
    "ensuite":  ([(6.4, 10.4), (6.8, 11.6)], 14),
    "bed2":     ([(8.6, 9.0), (10.4, 9.0), (8.6, 11.4), (10.4, 11.4)], 14),
    "laundry":  ([(12.6, 8.7)], 11),
    "bath2":    ([(12.6, 10.6), (13.0, 11.6)], 13),
    "bed3":     ([(14.6, 9.0), (15.6, 10.6), (14.6, 11.6)], 13),
    "study":    ([(17.6, 9.4), (17.6, 11.2)], 13),
}


def interior(scene, colls):
    c = colls.get("lights")
    for room, (pts, watt) in ROOM_LIGHTS.items():
        for (x, y) in pts:
            _downlight(x, y, 2.98, 0.055, c, watt)

    # ambient fill: a very soft ceiling-wide area light per major zone, simulating
    # the bounce light a real room gets (keeps shadow noise down at low samples)
    for name, (x, y, sx, sy, w) in {
        "fill_living": (4.6, 3.6, 6.2, 5.6, 26),
        "fill_kitchen": (12.9, 3.4, 4.2, 5.8, 20),
        "fill_dining": (8.9, 3.3, 3.4, 5.6, 14),
        "fill_master": (2.8, 10.0, 4.8, 4.2, 18),
        "fill_corridor": (9.5, 7.2, 15.0, 1.1, 12),
    }.items():
        lg = bpy.data.lights.new(name, type='AREA')
        lg.energy = w
        lg.shape = 'RECTANGLE'
        lg.size = sx
        lg.size_y = sy
        lg.color = (1.0, 0.93, 0.85)
        ob = bpy.data.objects.new(name, lg)
        (c or scene.collection).objects.link(ob)
        ob.location = (x, y, 2.86)
    return c


def exterior_props(colls):
    """A few trees and hedges so the glazing has something to look at."""
    site = colls["site"]
    from . import furniture as F
    from . import kit as K
    F.tree(7.2, 2.4, coll=site, seed=1).location = (3.0, -7.5, 0)
    F.tree(5.4, 2.0, coll=site, seed=2).location = (14.5, -9.0, 0)
    F.tree(6.6, 2.2, coll=site, seed=3).location = (20.5, -3.0, 0)
    # north garden so the bedroom windows have depth
    F.tree(7.8, 2.6, coll=site, seed=4).location = (2.2, 16.5, 0)
    F.tree(6.4, 2.2, coll=site, seed=5).location = (9.8, 18.0, 0)
    F.tree(8.2, 2.6, coll=site, seed=6).location = (16.2, 16.0, 0)
    F.tree(5.0, 1.8, coll=site, seed=7).location = (-5.0, 12.0, 0)
    # organic shrub row along the terrace edge
    import random
    rnd = random.Random(11)
    for i in range(9):
        r = rnd.uniform(0.42, 0.62)
        K.sphere(f"shrub_{i}", r, (0.4 + i * 1.35 + rnd.uniform(-0.2, 0.2), -4.8,
                                   r * 0.55), "leaf", seg=16, rings=10, coll=site,
                 scale=(1.0, 1.0, rnd.uniform(0.8, 1.05)))
    F.tree(9.0, 3.0, coll=site, seed=8).location = (9.0, -22.0, 0)
    F.tree(7.0, 2.4, coll=site, seed=9).location = (24.0, -14.0, 0)
    # west + east tree lines
    for i in range(7):
        F.tree(6.0 + (i % 3) * 1.6, 2.6, coll=site,
               seed=40 + i).location = (-30.0 - (i % 4) * 7.0, 2.0 + i * 9.0, 0)
    for i in range(6):
        F.tree(6.0 + (i % 3) * 1.4, 2.4, coll=site,
               seed=60 + i).location = (46.0 + (i % 3) * 7.0, -6.0 + i * 8.0, 0)
    # distant tree line so the horizon is not a hard edge
    for i in range(14):
        x = -22 + i * 5.6 + (i % 3) * 1.4
        F.tree(6.5 + (i % 4) * 1.4, 2.6 + (i % 3) * 0.5, coll=site,
               seed=20 + i).location = (x, -26.0 - (i % 5) * 2.6, 0)
    return site
