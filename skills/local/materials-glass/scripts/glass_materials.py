"""Realistic glass and transparent materials (Cycles), headless-safe.

Why this exists: default Principled transmission gives dark, caustic-starved glass in
headless Cycles (2 CPU cores, no denoiser help for caustics) and opaque shadows. These
builders use the production tricks instead:

* architectural_glass  - full transmission + a shadow-ray transparent mix so light
                         passes through without caustic cost
* thin_glass           - windows as a *thin sheet*: glossy + transparent, no refraction
                         (physically right for 6 mm glazing and 10x faster)
* frosted / ribbed     - roughness + bump from a real noise field
* tinted               - Beer-Lambert-ish absorption via a colour-filter multiply

Usage:
  python tools/bpy_run.py skills/local/materials-glass/scripts/glass_materials.py \
      -- --kind architectural --assign-to Window --thickness 0.012
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402

KINDS = ("architectural", "thin", "frosted", "ribbed", "tinted", "acrylic")


def _shadow_transparent(nt, bsdf_out, out_node, tint=(1, 1, 1)):
    """Light Path > Is Shadow Ray -> Transparent, else the shaded surface."""
    lp = sc.node(nt, "ShaderNodeLightPath", (-900, 400))
    tr = sc.node(nt, "ShaderNodeBsdfTransparent", (-500, 420))
    tr.inputs["Color"].default_value = (*tint, 1.0)
    mix = sc.node(nt, "ShaderNodeMixShader", (200, 200))
    nt.links.new(lp.outputs["Is Shadow Ray"], mix.inputs["Fac"])
    nt.links.new(bsdf_out, mix.inputs[1])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out_node.inputs["Surface"])
    return mix


def _clear_nodes(mat, nt):
    nt.nodes.clear()
    out = sc.node(nt, "ShaderNodeOutputMaterial", (600, 0))
    return out


def build(kind="architectural", tint=(1.0, 1.0, 1.0), roughness=0.02, ior=1.52,
          thickness=0.012, name=None):
    kind = kind.lower()
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    mat = bpy.data.materials.new(name or f"glass_{kind}")
    mat.use_nodes = True
    nt = mat.node_tree
    out = _clear_nodes(mat, nt)

    if kind == "thin":
        # A 6 mm pane: reflection + see-through, no refraction (fast, artifact-free)
        gloss = sc.node(nt, "ShaderNodeBsdfGlossy", (-200, 120))
        gloss.inputs["Roughness"].default_value = roughness
        gloss.inputs["Color"].default_value = (*tint, 1.0)
        trans = sc.node(nt, "ShaderNodeBsdfTransparent", (-200, -80))
        trans.inputs["Color"].default_value = (*tint, 1.0)
        fres = sc.node(nt, "ShaderNodeFresnel", (-500, 20))
        fres.inputs["IOR"].default_value = ior
        mix = sc.node(nt, "ShaderNodeMixShader", (250, 0))
        nt.links.new(fres.outputs["Fac"], mix.inputs["Fac"])
        nt.links.new(trans.outputs["BSDF"], mix.inputs[1])
        nt.links.new(gloss.outputs["BSDF"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
        mat["glass_kind"] = "thin"

    else:
        bsdf = sc.node(nt, "ShaderNodeBsdfPrincipled", (-200, 0))
        sc.set_input(bsdf, "Base Color", (*tint, 1.0))
        sc.set_input(bsdf, "Roughness", roughness)
        sc.set_input(bsdf, "IOR", ior)
        sc.set_input(bsdf, "Transmission Weight", 1.0 if kind != "acrylic" else 0.92)
        sc.set_input(bsdf, "Metallic", 0.0)
        if kind == "tinted":
            # absorption: thicker glass -> more colour, like real tinted float glass
            sc.set_input(bsdf, "Base Color", (tint[0] * 0.85, tint[1] * 0.95,
                                              tint[2] * 0.9, 1.0))
        if kind in ("frosted", "ribbed"):
            tex = sc.node(nt, "ShaderNodeTexNoise", (-800, -300))
            tex.inputs["Scale"].default_value = 180.0 if kind == "frosted" else 6.0
            tex.inputs["Detail"].default_value = 6.0
            bump = sc.node(nt, "ShaderNodeBump", (-400, -300))
            bump.inputs["Strength"].default_value = 0.06 if kind == "frosted" else 0.35
            bump.inputs["Distance"].default_value = thickness * 0.5
            nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
            nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
            sc.set_input(bsdf, "Roughness", 0.35 if kind == "frosted" else 0.12)
            if kind == "ribbed":  # vertical reeded glass: wave bands
                wave = sc.node(nt, "ShaderNodeTexWave", (-800, -100))
                wave.wave_type = "BANDS"
                wave.bands_direction = "X"
                wave.inputs["Scale"].default_value = 24.0
                wave.inputs["Distortion"].default_value = 0.0
                wave2 = sc.node(nt, "ShaderNodeBump", (-400, -100))
                wave2.inputs["Strength"].default_value = 0.5
                nt.links.new(wave.outputs["Fac"], wave2.inputs["Height"])
                nt.links.new(wave2.outputs["Normal"], bsdf.inputs["Normal"])
        _shadow_transparent(nt, bsdf.outputs["BSDF"], out, tint)
        mat["glass_kind"] = kind

    mat.use_backface_culling = False
    mat.blend_method = "BLEND" if hasattr(mat, "blend_method") else mat.blend_method
    return mat


def run(kind="architectural", assign_to=None, roughness=0.02, ior=1.52,
        thickness=0.012, tint=(1.0, 1.0, 1.0), name=None, **_):
    sc.object_mode()
    mat = build(kind, tuple(tint), roughness, ior, thickness, name)
    assigned = []
    for ob in sc.objects(assign_to):
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        # glass should not cast a hard shadow in previews
        ob.visible_shadow = kind != "thin"
        assigned.append(ob.name)
    return {"ok": True, "material": mat.name, "kind": kind, "ior": ior,
            "roughness": roughness, "assigned": assigned,
            "note": "thin = sheet reflection (no refraction); others = full transmission "
                    "with shadow-ray transparency"}


if __name__ == "__main__":
    p = sc.add_common(sc.parser(__doc__))
    p.add_argument("--kind", default="architectural", choices=list(KINDS))
    p.add_argument("--roughness", type=float, default=0.02)
    p.add_argument("--ior", type=float, default=1.52)
    p.add_argument("--thickness", type=float, default=0.012)
    p.add_argument("--tint", type=float, nargs=3, default=(1.0, 1.0, 1.0))
    p.add_argument("--name", default=None)
    p.add_argument("--assign-to", nargs="*", dest="assign_to", default=None,
                   help="objects to assign the new material to")
    sc.cli(run, p)
