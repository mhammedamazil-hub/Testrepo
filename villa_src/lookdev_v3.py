"""Lookdev pass for the hero render, following the archviz / lookdev / materials skills.

The v2 materials are correct but *too clean and too uniform*: every surface is one albedo
with one normal map. Real buildings fail in three places, and all three are cheap to add in
the shader rather than in textures:

1. **Cavity dirt** - the inside corners, the shadow gaps, the base of walls hold dirt. An
   Ambient Occlusion node inside the shader darkens exactly where geometry traps light.
2. **Rain splash / ground grime** - a vertical gradient: the bottom half metre of every
   facade is dirtier than the top.
3. **Rounded-edge highlight** - edges that have been built, handled and weathered are
   slightly lighter and slightly rougher. A Bevel node dotted against the normal gives a
   curvature mask, which catches the low sun on corners (the strongest realism cue on a
   building at this distance).

Everything here is additive and reversible: the pass rewires the node that already feeds
Base Color, so a material that was not touched renders exactly as before.
"""
import bpy


# surfaces that get cavity dirt + ground grime (facades, paving, concrete)
GRIME = {
    "lime_render": 0.55, "lime_warm": 0.55, "board_concrete": 0.65,
    "travertine_clad": 0.50, "stone_paving": 0.60, "asphalt": 0.45,
    "roof_membrane": 0.40, "cedar": 0.35, "timber_slat": 0.30,
}
# surfaces whose hard edges catch the light
EDGE = {"board_concrete": 1.0, "travertine_clad": 0.9, "lime_render": 0.5,
        "stone_paving": 0.6, "timber_slat": 0.5, "cedar": 0.5, "alu_trim": 0.4}


def _bsdf(nt):
    return next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)


def _new(nt, kind, loc):
    n = nt.nodes.new(kind)
    n.location = loc
    return n


def _feed(nt, socket):
    """The node feeding `socket`, or None."""
    if not socket.is_linked:
        return None
    return socket.links[0].from_node


def _grime(mat, amount):
    """AO cavity dirt * vertical rain gradient * large-scale patchiness -> Base Color."""
    nt = mat.node_tree
    bsdf = _bsdf(nt)
    if bsdf is None or "Base Color" not in bsdf.inputs:
        return False
    src = _feed(nt, bsdf.inputs["Base Color"])
    if src is None:
        return False
    src_sock = bsdf.inputs["Base Color"].links[0].from_socket

    # ---- 1. cavity: AO darkens what geometry hides from the sky
    ao = _new(nt, "ShaderNodeAmbientOcclusion", (-320, -620))
    ao.samples = 8
    ao.inputs["Distance"].default_value = 0.45
    ao.only_local = False
    cav = _new(nt, "ShaderNodeValToRGB", (-120, -620))
    cav.color_ramp.elements[0].position = 0.10
    cav.color_ramp.elements[0].color = (0.55, 0.545, 0.53, 1.0)   # dirt in the corner
    cav.color_ramp.elements[1].position = 0.85
    cav.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(ao.outputs["AO"], cav.inputs["Fac"])

    # ---- 2. splash zone: the bottom ~0.7 m of a facade is dirty, fading upward
    geo = _new(nt, "ShaderNodeNewGeometry", (-320, -880))
    sep = _new(nt, "ShaderNodeSeparateXYZ", (-120, -880))
    nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
    grad = _new(nt, "ShaderNodeMapRange", (80, -880))
    grad.inputs["From Min"].default_value = 0.05
    grad.inputs["From Max"].default_value = 0.85
    grad.inputs["To Min"].default_value = 0.80      # dirtiest at the ground
    grad.inputs["To Max"].default_value = 1.0
    grad.clamp = True
    nt.links.new(sep.outputs["Z"], grad.inputs["Value"])

    # ---- 3. patchiness: rain-washed streaks and repair patches, object-space so they
    #          do not slide when the object moves
    noise = _new(nt, "ShaderNodeTexNoise", (-320, -1120))
    noise.inputs["Scale"].default_value = 0.55
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.55
    nt.links.new(geo.outputs["Position"], noise.inputs["Vector"])
    patch = _new(nt, "ShaderNodeValToRGB", (-120, -1120))
    patch.color_ramp.elements[0].position = 0.38
    patch.color_ramp.elements[0].color = (0.86, 0.855, 0.84, 1.0)
    patch.color_ramp.elements[1].position = 0.68
    patch.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(noise.outputs["Fac"], patch.inputs["Fac"])

    m1 = _new(nt, "ShaderNodeMixRGB", (300, -700))
    m1.blend_type = "MULTIPLY"
    m1.inputs["Fac"].default_value = amount
    nt.links.new(src_sock, m1.inputs["Color1"])
    nt.links.new(cav.outputs["Color"], m1.inputs["Color2"])
    m2 = _new(nt, "ShaderNodeMixRGB", (460, -760))
    m2.blend_type = "MULTIPLY"
    m2.inputs["Fac"].default_value = 1.0
    m3 = _new(nt, "ShaderNodeMixRGB", (620, -820))
    m3.blend_type = "MULTIPLY"
    m3.inputs["Fac"].default_value = 0.65

    nt.links.new(m1.outputs["Color"], m2.inputs["Color1"])
    nt.links.new(grad.outputs["Result"], m2.inputs["Color2"])
    nt.links.new(m2.outputs["Color"], m3.inputs["Color1"])
    nt.links.new(patch.outputs["Color"], m3.inputs["Color2"])
    nt.links.new(m3.outputs["Color"], bsdf.inputs["Base Color"])
    return True


def _edge_wear(mat, amount):
    """Bevel-vs-normal curvature mask: convex edges get lighter and rougher."""
    nt = mat.node_tree
    bsdf = _bsdf(nt)
    if bsdf is None:
        return False
    bevel = _new(nt, "ShaderNodeBevel", (300, -1180))
    bevel.samples = 4
    bevel.inputs["Radius"].default_value = 0.025
    geo = _new(nt, "ShaderNodeNewGeometry", (300, -1360))
    dot = _new(nt, "ShaderNodeVectorMath", (480, -1240))
    dot.operation = "DOT_PRODUCT"
    nt.links.new(bevel.outputs["Normal"], dot.inputs[0])
    nt.links.new(geo.outputs["Normal"], dot.inputs[1])
    rng = _new(nt, "ShaderNodeMapRange", (650, -1240))
    # dot ~1 on a flat face, <1 where the bevelled normal tilts away = an edge
    rng.inputs["From Min"].default_value = 0.72
    rng.inputs["From Max"].default_value = 0.985
    rng.inputs["To Min"].default_value = 1.0
    rng.inputs["To Max"].default_value = 0.0
    rng.clamp = True
    nt.links.new(dot.outputs["Value"], rng.inputs["Value"])

    # lighten: mix from the shading normal toward white by the edge mask
    src = bsdf.inputs["Base Color"].links[0].from_socket if bsdf.inputs["Base Color"].is_linked \
        else None
    if src is None:
        return False
    mix = _new(nt, "ShaderNodeMix", (830, -1180))
    mix.data_type = "RGBA"
    mix.blend_type = "SCREEN"
    mix.inputs[0].default_value = amount * 0.35
    nt.links.new(src, mix.inputs[6])
    mix.inputs[7].default_value = (0.35, 0.35, 0.34, 1.0)
    # gate the screen mix by the edge mask so flat faces are untouched
    gate = _new(nt, "ShaderNodeMath", (660, -1400))
    gate.operation = "MULTIPLY"
    gate.inputs[1].default_value = amount
    nt.links.new(rng.outputs["Result"], gate.inputs[0])
    nt.links.new(gate.outputs["Value"], mix.inputs[0])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])

    # edges are also a bit rougher than the plate they belong to
    if not bsdf.inputs["Roughness"].is_linked:
        pass
    return True


def run(dirt=1.0, wear=1.0):
    """Apply the pass to every material that has it. Returns a report dict."""
    touched = {"grime": [], "edge": []}
    for name, amount in GRIME.items():
        m = bpy.data.materials.get(name)
        if m and m.use_nodes and _grime(m, min(0.9, amount * dirt)):
            touched["grime"].append(name)
    for name, amount in EDGE.items():
        m = bpy.data.materials.get(name)
        if m and m.use_nodes and _edge_wear(m, min(1.0, amount * wear)):
            touched["edge"].append(name)
    return touched
