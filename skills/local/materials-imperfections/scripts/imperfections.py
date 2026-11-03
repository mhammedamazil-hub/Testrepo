"""Surface imperfections: edge wear, dust, scratches, fingerprints, cavity grime.

"Photoreal" usually fails because every surface is uniformly clean. This inserts a
masking chain into an existing material WITHOUT destroying it:

  base colour -> [edge wear] -> [dust] -> [grime] -> BSDF
  roughness  -> [scratches] -> [fingerprints] -> BSDF

Masks are geometry-driven, so they cost nothing to author and need no textures:
  edge wear   Geometry > Pointiness -> ColorRamp (convex = wear)
  cavity grime Geometry > Pointiness -> ColorRamp (concave = grime)  (+ Ambient Occlusion)
  dust        Noise (large scale) * upward-facing normal (Geometry > Normal > Z)
  scratches   stretched Noise/Wave -> high-frequency roughness spurs + fine bump
  fingerprints Voronoi smudges that *reduce* roughness locally

Usage:
  python tools/bpy_run.py <this> -- --objects Body --wear 0.6 --dust 0.3 \
      --scratches 0.4 --fingerprints 0.2 --grime 0.4
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import skill_common as sc  # noqa: E402

WEAR_COLOR = (0.55, 0.56, 0.58)     # exposed metal / primer under the paint
DUST_COLOR = (0.42, 0.40, 0.36)
GRIME_COLOR = (0.09, 0.08, 0.065)


def _socket_link(nt, bsdf, name):
    """Return the node+socket feeding a BSDF input, if any."""
    for l in nt.links:
        if l.to_node == bsdf and l.to_socket.name == name:
            return l.from_node, l.from_socket
    return None, None


def _mix_color(nt, fac_socket, a_socket_or_rgba, b_socket_or_rgba, loc):
    m = sc.node(nt, "ShaderNodeMix", loc)
    m.data_type = "RGBA"
    nt.links.new(fac_socket, m.inputs["Factor"])
    for idx, val in ((6, a_socket_or_rgba), (7, b_socket_or_rgba)):
        sock = m.inputs[idx]
        if isinstance(val, bpy.types.NodeSocket):
            nt.links.new(val, sock)
        else:
            sock.default_value = (*val, 1.0) if len(val) == 3 else val
    return m


def _ramp(nt, src_socket, stops, loc):
    r = sc.node(nt, "ShaderNodeValToRGB", loc)
    ramp = r.color_ramp
    while len(ramp.elements) > 2:
        ramp.elements.remove(ramp.elements[-1])
    ramp.elements[0].position, ramp.elements[0].color = stops[0][0], (1, 1, 1, 1)
    ramp.elements[1].position, ramp.elements[1].color = stops[1][0], (0, 0, 0, 1)
    if len(stops) > 2:
        for pos in stops[2:]:
            e = ramp.elements.new(pos[0])
            e.color = pos[1]
    nt.links.new(src_socket, r.inputs["Fac"])
    return r


def add_imperfections(mat, wear=0.0, dust=0.0, scratches=0.0, fingerprints=0.0,
                      grime=0.0, scale=1.0, wear_color=WEAR_COLOR, dust_color=DUST_COLOR,
                      grime_color=GRIME_COLOR):
    """Insert the masks into `mat`. Idempotent: calling twice rebuilds the chain."""
    if mat.get("_imperfections"):
        return mat
    nt = mat.node_tree
    bsdf = sc.principled(mat)
    geo = sc.node(nt, "ShaderNodeNewGeometry", (-1600, 0))
    co = sc.node(nt, "ShaderNodeTexCoord", (-1600, 400))

    color_src = _socket_link(nt, bsdf, "Base Color")
    if color_src[1] is not None:
        current = color_src[1]                      # an output socket: can be mixed
    else:
        # no texture on base colour -> feed the mix chain from an RGB node holding it
        rgb = sc.node(nt, "ShaderNodeRGB", (-1350, 500))
        rgba = tuple(bsdf.inputs["Base Color"].default_value)
        rgb.outputs[0].default_value = rgba if len(rgba) == 4 else (*rgba, 1.0)
        current = rgb.outputs[0]

    y = -600
    # ---- edge wear (convex edges) ------------------------------------------------
    if wear > 0:
        ramp = _ramp(nt, geo.outputs["Pointiness"], [(0.5 + 0.06, (0, 0, 0, 1)),
                                                     (0.5 + 0.16, (1, 1, 1, 1))],
                     (-1350, y))
        mul = sc.node(nt, "ShaderNodeMath", (-1150, y))
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = wear
        nt.links.new(ramp.outputs["Color"], mul.inputs[0])
        m = _mix_color(nt, mul.outputs[0], current, wear_color, (-900, y))
        current = m.outputs[2]
        y -= 320

    # ---- cavity grime -------------------------------------------------------------
    if grime > 0:
        ao = sc.node(nt, "ShaderNodeAmbientOcclusion", (-1350, y))
        ao.samples = 8
        ao.inputs["Distance"].default_value = 0.08 * scale
        ramp = _ramp(nt, ao.outputs["AO"], [(0.45, (0, 0, 0, 1)), (0.85, (1, 1, 1, 1))],
                     (-1100, y))
        mul = sc.node(nt, "ShaderNodeMath", (-900, y))
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = grime
        nt.links.new(ramp.outputs["Color"], mul.inputs[0])
        m = _mix_color(nt, mul.outputs[0], current, grime_color, (-700, y))
        current = m.outputs[2]
        y -= 320

    # ---- dust: noise * upward-facing -------------------------------------------------
    if dust > 0:
        noise = sc.node(nt, "ShaderNodeTexNoise", (-1350, y))
        noise.inputs["Scale"].default_value = 6.0 * scale
        noise.inputs["Detail"].default_value = 8.0
        nt.links.new(co.outputs["Object"], noise.inputs["Vector"])
        sep = sc.node(nt, "ShaderNodeSeparateXYZ", (-1350, y - 200))
        nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
        up = sc.node(nt, "ShaderNodeMath", (-1150, y - 200))
        up.operation = "MULTIPLY"
        up.inputs[1].default_value = 1.0
        nt.links.new(sep.outputs["Z"], up.inputs[0])
        mul = sc.node(nt, "ShaderNodeMath", (-950, y))
        mul.operation = "MULTIPLY"
        nt.links.new(noise.outputs["Fac"], mul.inputs[0])
        nt.links.new(up.outputs[0], mul.inputs[1])
        mul2 = sc.node(nt, "ShaderNodeMath", (-780, y))
        mul2.operation = "MULTIPLY"
        mul2.inputs[1].default_value = dust
        nt.links.new(mul.outputs[0], mul2.inputs[0])
        m = _mix_color(nt, mul2.outputs[0], current, dust_color, (-600, y))
        current = m.outputs[2]
        y -= 320

    # hook the colour chain back into the BSDF
    nt.links.new(current, bsdf.inputs["Base Color"])

    # ---- roughness: scratches + fingerprints ---------------------------------------
    rough_in = bsdf.inputs["Roughness"]
    src = _socket_link(nt, bsdf, "Roughness")
    if src[1] is not None:
        nt.links.remove([l for l in nt.links
                         if l.to_node == bsdf and l.to_socket.name == "Roughness"][0])
        rough_socket = src[1]
    else:
        rough_socket = None

    def _math(op, a, b, loc, clamp=False):
        n = sc.node(nt, "ShaderNodeMath", loc)
        n.operation = op
        n.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if isinstance(v, bpy.types.NodeSocket):
                nt.links.new(v, n.inputs[i])
            else:
                n.inputs[i].default_value = v
        return n.outputs[0]

    if scratches > 0:
        mp = sc.node(nt, "ShaderNodeMapping", (-1350, y))
        mp.inputs["Scale"].default_value = (1.0, 90.0, 1.0)
        nt.links.new(co.outputs["Object"], mp.inputs["Vector"])
        noise = sc.node(nt, "ShaderNodeTexNoise", (-1150, y))
        noise.inputs["Scale"].default_value = 40.0
        noise.inputs["Detail"].default_value = 6.0
        nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])
        ramp = _ramp(nt, noise.outputs["Fac"], [(0.62, (0, 0, 0, 1)),
                                                (0.70, (1, 1, 1, 1))], (-950, y))
        amt = _math("MULTIPLY", ramp.outputs["Color"], scratches * 0.35, (-750, y))
        if rough_socket is not None:
            base_rough = _math("ADD", rough_socket, 0.0, (-950, y - 160))
        else:
            base_rough = None
        if base_rough is not None:
            rough_new = _math("ADD", base_rough, amt, (-550, y), clamp=True)
            rough_socket = rough_new
        else:
            rough_in.default_value = min(0.95, rough_in.default_value + 0.03 * scratches)
        b = sc.node(nt, "ShaderNodeBump", (-550, y - 220))
        b.inputs["Strength"].default_value = 0.08 * scratches
        b.inputs["Distance"].default_value = 0.0003
        nt.links.new(ramp.outputs["Color"], b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
        y -= 420

    if fingerprints > 0:
        vor = sc.node(nt, "ShaderNodeTexVoronoi", (-900, y))
        vor.feature = "SMOOTH_F1"
        vor.inputs["Scale"].default_value = 14.0 * scale
        nt.links.new(co.outputs["Object"], vor.inputs["Vector"])
        ramp = _ramp(nt, vor.outputs["Distance"], [(0.08, (1, 1, 1, 1)),
                                                   (0.22, (0, 0, 0, 1))], (-700, y))
        amt = _math("MULTIPLY", ramp.outputs["Color"], fingerprints * 0.18, (-500, y))
        if rough_socket is not None:
            rough_socket = _math("SUBTRACT", rough_socket, amt, (-320, y), clamp=True)
        y -= 260

    if rough_socket is not None:
        nt.links.new(rough_socket, bsdf.inputs["Roughness"])

    mat["_imperfections"] = {"wear": wear, "dust": dust, "scratches": scratches,
                             "fingerprints": fingerprints, "grime": grime}
    return mat


def run(objects=None, wear=0.0, dust=0.0, scratches=0.0, fingerprints=0.0, grime=0.0,
        scale=1.0, **_):
    sc.object_mode()
    done = []
    for ob in sc.objects(objects):
        for slot in ob.material_slots:
            if slot.material and slot.material.use_nodes:
                add_imperfections(slot.material, wear, dust, scratches, fingerprints,
                                  grime, scale)
                done.append(slot.material.name)
    return {"ok": True, "materials": sorted(set(done)),
            "masks": {"wear": wear, "dust": dust, "scratches": scratches,
                      "fingerprints": fingerprints, "grime": grime},
            "note": "geometry-driven masks; no image maps needed (and none exported)"}


if __name__ == "__main__":
    p = sc.add_common(sc.parser(__doc__))
    p.add_argument("--wear", type=float, default=0.0)
    p.add_argument("--dust", type=float, default=0.0)
    p.add_argument("--scratches", type=float, default=0.0)
    p.add_argument("--fingerprints", type=float, default=0.0)
    p.add_argument("--grime", type=float, default=0.0)
    p.add_argument("--scale", type=float, default=1.0)
    sc.cli(run, p)
