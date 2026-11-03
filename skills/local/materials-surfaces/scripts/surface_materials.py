"""Rubber, leather, carbon fibre and metal - the four surfaces that most often look fake.

Each builder returns a node-based material with the measured roughness/metallic ranges
real materials have, plus the micro-structure that sells them:

  rubber       roughness 0.75-0.9, no metallic, subtle mould-release sheen, crack grain
  leather      grain via Voronoi + bump, roughness 0.35-0.55 with crease variation
  carbon_twill 2x2 twill weave (two rotated wave textures, checker-masked),
               anisotropic-looking roughness, clear-coat on top
  brushed      anisotropic highlights from a stretched noise driving anisotropy
  anodised     coloured metal, roughness 0.25, coat 0.2

Usage:
  python tools/bpy_run.py <this> -- --kind carbon_twill --assign-to Hood
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402

KINDS = ("rubber", "leather", "carbon_twill", "brushed", "anodised", "chrome",
         "powdercoat", "plastic_black")


def _fresh(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = sc.node(nt, "ShaderNodeOutputMaterial", (700, 0))
    bsdf = sc.node(nt, "ShaderNodeBsdfPrincipled", (300, 0))
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, nt, bsdf, out


def _bump(nt, bsdf, height_socket, strength=0.2, distance=0.001, target="Normal"):
    b = sc.node(nt, "ShaderNodeBump", (-200, -200))
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bsdf.inputs[target])
    return b


def build(kind="rubber", color=None, name=None):
    kind = kind.lower()
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    mat, nt, bsdf, out = _fresh(name or f"surf_{kind}")
    co = sc.node(nt, "ShaderNodeTexCoord", (-1100, 0))

    if kind == "rubber":
        base = color or (0.022, 0.022, 0.024)
        sc.set_input(bsdf, "Base Color", (*base, 1))
        sc.set_input(bsdf, "Roughness", 0.82)
        sc.set_input(bsdf, "Specular IOR Level", 0.35)
        noise = sc.node(nt, "ShaderNodeTexNoise", (-700, -200))
        noise.inputs["Scale"].default_value = 320.0
        noise.inputs["Detail"].default_value = 8.0
        noise.inputs["Roughness"].default_value = 0.65
        nt.links.new(co.outputs["Object"], noise.inputs["Vector"])
        _bump(nt, bsdf, noise.outputs["Fac"], 0.18, 0.0005)
        # mould-release sheen variation
        mr = sc.node(nt, "ShaderNodeMapRange", (-400, 60))
        mr.inputs["To Min"].default_value = 0.72
        mr.inputs["To Max"].default_value = 0.90
        nt.links.new(noise.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])

    elif kind == "leather":
        base = color or (0.085, 0.045, 0.022)
        sc.set_input(bsdf, "Base Color", (*base, 1))
        vor = sc.node(nt, "ShaderNodeTexVoronoi", (-700, -200))
        vor.feature = "DISTANCE_TO_EDGE"
        vor.inputs["Scale"].default_value = 420.0
        nt.links.new(co.outputs["Object"], vor.inputs["Vector"])
        _bump(nt, bsdf, vor.outputs["Distance"], 0.45, 0.0008)
        mr = sc.node(nt, "ShaderNodeMapRange", (-400, 60))
        mr.inputs["To Min"].default_value = 0.32
        mr.inputs["To Max"].default_value = 0.58
        nt.links.new(vor.outputs["Distance"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
        sc.set_input(bsdf, "Coat Weight", 0.15)
        sc.set_input(bsdf, "Coat Roughness", 0.4)

    elif kind == "carbon_twill":
        # two wave textures rotated 90 deg, checker-masked -> 2x2 twill
        w1 = sc.node(nt, "ShaderNodeTexWave", (-900, 200))
        w1.wave_type = "BANDS"
        w1.bands_direction = "X"
        w1.inputs["Scale"].default_value = 120.0
        w1.inputs["Distortion"].default_value = 0.0
        w2 = sc.node(nt, "ShaderNodeTexWave", (-900, -60))
        w2.wave_type = "BANDS"
        w2.bands_direction = "Y"
        w2.inputs["Scale"].default_value = 120.0
        chk = sc.node(nt, "ShaderNodeTexChecker", (-900, -320))
        chk.inputs["Scale"].default_value = 120.0
        chk.inputs["Color1"].default_value = (1, 1, 1, 1)
        chk.inputs["Color2"].default_value = (0, 0, 0, 1)
        for n in (w1, w2, chk):
            nt.links.new(co.outputs["Object"], n.inputs["Vector"])
        mix = sc.node(nt, "ShaderNodeMix", (-620, 60))
        mix.data_type = "FLOAT"
        nt.links.new(chk.outputs["Fac"], mix.inputs["Factor"])
        nt.links.new(w2.outputs["Fac"], mix.inputs["A"])
        nt.links.new(w1.outputs["Fac"], mix.inputs["B"])
        ramp = sc.node(nt, "ShaderNodeValToRGB", (-420, 60))
        ramp.color_ramp.elements[0].color = (0.012, 0.012, 0.014, 1)
        ramp.color_ramp.elements[1].color = (0.085, 0.088, 0.095, 1)
        nt.links.new(mix.outputs["Result"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        _bump(nt, bsdf, mix.outputs["Result"], 0.25, 0.0006)
        sc.set_input(bsdf, "Roughness", 0.30)
        sc.set_input(bsdf, "Anisotropic", 0.65)
        sc.set_input(bsdf, "Coat Weight", 1.0)          # carbon is always clear-coated
        sc.set_input(bsdf, "Coat Roughness", 0.03)
        sc.set_input(bsdf, "Coat IOR", 1.5)

    elif kind == "brushed":
        base = color or (0.78, 0.78, 0.80)
        mp = sc.node(nt, "ShaderNodeMapping", (-900, -200))
        mp.inputs["Scale"].default_value = (1.0, 60.0, 1.0)   # stretch along X
        nt.links.new(co.outputs["Object"], mp.inputs["Vector"])
        noise = sc.node(nt, "ShaderNodeTexNoise", (-700, -200))
        noise.inputs["Scale"].default_value = 400.0
        noise.inputs["Detail"].default_value = 3.0
        nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])
        sc.set_input(bsdf, "Base Color", (*base, 1))
        sc.set_input(bsdf, "Metallic", 1.0)
        sc.set_input(bsdf, "Roughness", 0.22)
        sc.set_input(bsdf, "Anisotropic", 0.8)
        tan = sc.node(nt, "ShaderNodeTangent", (-900, -420))
        tan.direction_type = "RADIAL"
        tan.axis = "Z"
        nt.links.new(tan.outputs["Tangent"], bsdf.inputs["Tangent"])
        _bump(nt, bsdf, noise.outputs["Fac"], 0.06, 0.0002)

    elif kind == "anodised":
        base = color or (0.05, 0.10, 0.35)
        sc.set_input(bsdf, "Base Color", (*base, 1))
        sc.set_input(bsdf, "Metallic", 1.0)
        sc.set_input(bsdf, "Roughness", 0.26)
        sc.set_input(bsdf, "Coat Weight", 0.2)
        sc.set_input(bsdf, "Coat Roughness", 0.15)

    elif kind == "chrome":
        sc.set_input(bsdf, "Base Color", (0.92, 0.92, 0.94, 1))
        sc.set_input(bsdf, "Metallic", 1.0)
        sc.set_input(bsdf, "Roughness", 0.03)

    elif kind == "powdercoat":
        base = color or (0.04, 0.04, 0.045)
        sc.set_input(bsdf, "Base Color", (*base, 1))
        sc.set_input(bsdf, "Roughness", 0.42)
        noise = sc.node(nt, "ShaderNodeTexNoise", (-700, -200))
        noise.inputs["Scale"].default_value = 240.0
        nt.links.new(co.outputs["Object"], noise.inputs["Vector"])
        _bump(nt, bsdf, noise.outputs["Fac"], 0.12, 0.0004)

    else:  # plastic_black
        sc.set_input(bsdf, "Base Color", (0.024, 0.024, 0.026, 1))
        sc.set_input(bsdf, "Roughness", 0.36)
        noise = sc.node(nt, "ShaderNodeTexNoise", (-700, -200))
        noise.inputs["Scale"].default_value = 900.0
        nt.links.new(co.outputs["Object"], noise.inputs["Vector"])
        _bump(nt, bsdf, noise.outputs["Fac"], 0.05, 0.0002)

    mat["surface_kind"] = kind
    return mat


def run(kind="rubber", color=None, assign_to=None, name=None, **_):
    sc.object_mode()
    mat = build(kind, tuple(color) if color else None, name)
    assigned = []
    for ob in sc.objects(assign_to):
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        assigned.append(ob.name)
    bsdf = sc.principled(mat)
    return {"ok": True, "material": mat.name, "kind": kind, "assigned": assigned,
            "roughness": round(bsdf.inputs["Roughness"].default_value, 3),
            "metallic": round(bsdf.inputs["Metallic"].default_value, 3)}


if __name__ == "__main__":
    p = sc.add_common(sc.parser(__doc__))
    p.add_argument("--kind", default="rubber", choices=list(KINDS))
    p.add_argument("--color", type=float, nargs=3, default=None)
    p.add_argument("--name", default=None)
    p.add_argument("--assign-to", nargs="*", dest="assign_to", default=None,
                   help="objects to assign the new material to")
    sc.cli(run, p)
