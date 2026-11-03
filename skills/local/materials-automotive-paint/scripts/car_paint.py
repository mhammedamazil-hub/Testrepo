"""Automotive paint: metallic base coat + flake + clear coat (+ optional pearl/peel).

Physically motivated values (measured ranges from car-refinish data sheets):
  clear coat IOR 1.50-1.52, coat roughness 0.02-0.06, base metallic 0.6-0.9 for metallic
  paints (0.0 for solid colours), base roughness 0.25-0.40, flake size 10-40 um.

The flake layer is procedural (Voronoi -> bump) because no texture downloads are possible
in this sandbox; it reads correctly at product-shot distance and survives glTF via the
bump/normal that it generates at render time (glTF gets the flat factors - see SKILL.md).

Usage:
  python tools/bpy_run.py <this> -- --color 0.02,0.06,0.16 --kind metallic \
      --assign-to Body --flake 0.35
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402

PAINT_KINDS = ("metallic", "solid", "pearl", "matte", "chrome", "primer")


def build(color=(0.02, 0.06, 0.16), kind="metallic", flake=0.35, coat_rough=0.03,
          base_rough=None, peel=0.0, name=None):
    kind = kind.lower()
    if kind not in PAINT_KINDS:
        raise ValueError(f"kind must be one of {PAINT_KINDS}")
    mat = bpy.data.materials.new(name or f"paint_{kind}")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = sc.node(nt, "ShaderNodeOutputMaterial", (700, 0))
    bsdf = sc.node(nt, "ShaderNodeBsdfPrincipled", (300, 0))

    if kind == "solid":
        metallic, base_rough, coat = 0.0, 0.32 if base_rough is None else base_rough, 1.0
    elif kind == "metallic":
        metallic, base_rough, coat = 0.75, 0.28 if base_rough is None else base_rough, 1.0
    elif kind == "pearl":
        metallic, base_rough, coat = 0.55, 0.25 if base_rough is None else base_rough, 1.0
    elif kind == "matte":
        metallic, base_rough, coat = 0.05, 0.55 if base_rough is None else base_rough, 0.15
    elif kind == "chrome":
        metallic, base_rough, coat = 1.0, 0.04, 0.0
    else:  # primer
        metallic, base_rough, coat = 0.0, 0.62 if base_rough is None else base_rough, 0.0

    sc.set_input(bsdf, "Base Color", (*color, 1.0))
    sc.set_input(bsdf, "Metallic", metallic)
    sc.set_input(bsdf, "Roughness", base_rough)
    sc.set_input(bsdf, "IOR", 1.5)
    sc.set_input(bsdf, "Coat Weight", coat)
    sc.set_input(bsdf, "Coat Roughness", coat_rough)
    sc.set_input(bsdf, "Coat IOR", 1.5)

    if kind == "pearl":
        # interference-ish tint shift: color ramp on layer weight
        lw = sc.node(nt, "ShaderNodeLayerWeight", (-700, -260))
        lw.inputs["Blend"].default_value = 0.35
        ramp = sc.node(nt, "ShaderNodeValToRGB", (-480, -260))
        ramp.color_ramp.elements[0].position = 0.25
        ramp.color_ramp.elements[0].color = (color[0], color[1], color[2], 1)
        ramp.color_ramp.elements[1].position = 0.85
        ramp.color_ramp.elements[1].color = (min(1, color[0] + 0.25),
                                             min(1, color[1] + 0.18),
                                             min(1, color[2] + 0.30), 1)
        nt.links.new(lw.outputs["Fresnel"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    if flake > 0 and kind in ("metallic", "pearl"):
        vor = sc.node(nt, "ShaderNodeTexVoronoi", (-900, 260))
        vor.feature = "F1"
        vor.inputs["Scale"].default_value = 2400.0     # ~0.4 mm flakes at car scale
        vor.inputs["Randomness"].default_value = 1.0
        bump = sc.node(nt, "ShaderNodeBump", (-380, 260))
        bump.inputs["Strength"].default_value = 0.05 * flake
        bump.inputs["Distance"].default_value = 0.0002
        nt.links.new(vor.outputs["Distance"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        # flakes also break up the base roughness a touch
        mr = sc.node(nt, "ShaderNodeMapRange", (-380, 60))
        mr.inputs["To Min"].default_value = max(0.05, base_rough - 0.06)
        mr.inputs["To Max"].default_value = base_rough + 0.05
        nt.links.new(vor.outputs["Distance"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])

    if peel > 0:
        # "orange peel": low-frequency waviness in the clear coat, seen in reflections
        noise = sc.node(nt, "ShaderNodeTexNoise", (-900, -520))
        noise.inputs["Scale"].default_value = 90.0
        noise.inputs["Detail"].default_value = 2.0
        b2 = sc.node(nt, "ShaderNodeBump", (-380, -520))
        b2.inputs["Strength"].default_value = 0.04 * peel
        b2.inputs["Distance"].default_value = 0.0005
        nt.links.new(noise.outputs["Fac"], b2.inputs["Height"])
        nt.links.new(b2.outputs["Normal"], bsdf.inputs["Coat Normal"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat["paint_kind"] = kind
    mat["coat_roughness"] = coat_rough
    return mat


def run(color=(0.02, 0.06, 0.16), kind="metallic", flake=0.35, coat_rough=0.03,
        base_rough=None, peel=0.0, assign_to=None, name=None, **_):
    sc.object_mode()
    mat = build(tuple(color), kind, flake, coat_rough, base_rough, peel, name)
    assigned = []
    for ob in sc.objects(assign_to):
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        assigned.append(ob.name)
    return {"ok": True, "material": mat.name, "kind": kind, "assigned": assigned,
            "colorspace": "pass linear RGB (0-1), not sRGB hex",
            "gltf_note": "procedural flake/peel do not export; bake a normal map with "
                         "blender-texture-baking if the GLB must match"}


if __name__ == "__main__":
    p = sc.add_common(sc.parser(__doc__))
    p.add_argument("--color", type=float, nargs=3, default=(0.02, 0.06, 0.16))
    p.add_argument("--kind", default="metallic", choices=list(PAINT_KINDS))
    p.add_argument("--flake", type=float, default=0.35)
    p.add_argument("--coat-rough", type=float, default=0.03)
    p.add_argument("--base-rough", type=float, default=None)
    p.add_argument("--peel", type=float, default=0.0)
    p.add_argument("--name", default=None)
    p.add_argument("--assign-to", nargs="*", dest="assign_to", default=None,
                   help="objects to assign the new material to")
    sc.cli(run, p)
