"""Material library: PBR image-texture materials built from villa/tex/*.png.

Same materials drive the Cycles renders and the exported glTF, so the walkable GLB
matches the stills.
"""
import os
import bpy

TEX = os.path.join(os.path.dirname(__file__), "..", "villa", "tex")

# name -> (albedo base, tile metres per texture repeat, roughness, metallic,
#          normal strength, extra kwargs)
SPEC = {
    "oak_floor":     (2.40, 0.42, 0.0, 0.9),
    "oak_veneer":    (1.20, 0.44, 0.0, 0.7),
    "walnut":        (1.00, 0.38, 0.0, 0.7),
    "plaster_warm":  (3.00, 0.86, 0.0, 0.5),
    "plaster_white": (3.00, 0.88, 0.0, 0.4),
    "microcement":   (2.50, 0.72, 0.0, 0.6),
    "marble":        (1.20, 0.14, 0.0, 0.25),
    "limestone_tile": (1.80, 0.34, 0.0, 0.7),
    "bath_tile":     (1.20, 0.20, 0.0, 0.8),
    "linen_sand":    (0.40, 0.94, 0.0, 0.7),
    "linen_graphite": (0.40, 0.93, 0.0, 0.7),
    "boucle_cream":  (0.32, 0.95, 0.0, 0.9),
    "velvet_olive":  (0.30, 0.72, 0.0, 0.5),
    "leather_cognac": (0.28, 0.44, 0.0, 0.6),
    "rug_wool":      (2.00, 0.96, 0.0, 1.4),
    "rug_ochre":     (2.00, 0.96, 0.0, 1.4),
    "leaf":          (0.30, 0.55, 0.0, 1.0),
    "steel":         (0.80, 0.30, 1.0, 0.7),
    "brass":         (0.60, 0.34, 1.0, 0.6),
    "black_steel":   (0.80, 0.40, 1.0, 0.6),
    "grass":         (2.00, 0.95, 0.0, 1.2),
    "leaf_dark":     (0.30, 0.55, 0.0, 1.0),
    "paint_1":       (1.00, 0.75, 0.0, 0.3),
    "paint_2":       (1.00, 0.75, 0.0, 0.3),
    "paint_3":       (1.00, 0.75, 0.0, 0.3),
    "paint_4":       (1.00, 0.75, 0.0, 0.3),
}

# plain (untextured) materials: name -> (rgb, roughness, metallic, extras)
PLAIN = {
    "white_paint":   ((0.90, 0.90, 0.89), 0.35, 0.0, {}),
    "black_paint":   ((0.030, 0.030, 0.032), 0.42, 0.0, {}),
    "ceramic":       ((0.92, 0.92, 0.91), 0.12, 0.0, {}),
    "glass":         ((1.0, 1.0, 1.0), 0.0, 0.0, {"transmission": 1.0, "ior": 1.45}),
    "glass_ribbed":  ((0.98, 0.99, 1.0), 0.08, 0.0, {"transmission": 0.92, "ior": 1.45}),
    "mirror":        ((1.0, 1.0, 1.0), 0.02, 1.0, {}),
    "quartz_white":  ((0.93, 0.92, 0.90), 0.12, 0.0, {}),
    "tv_screen":     ((0.012, 0.013, 0.015), 0.10, 0.0, {}),
    "soil":          ((0.055, 0.045, 0.035), 0.95, 0.0, {}),
    "terracotta":    ((0.42, 0.22, 0.14), 0.75, 0.0, {}),
    "linen_throw":   ((0.62, 0.55, 0.44), 0.92, 0.0, {}),
    "towel":         ((0.80, 0.79, 0.76), 0.95, 0.0, {}),
    "candle_wax":    ((0.88, 0.84, 0.76), 0.55, 0.0, {}),
    "chrome":        ((0.85, 0.85, 0.86), 0.10, 1.0, {}),
    "steel_soft":    ((0.66, 0.67, 0.68), 0.30, 0.6, {}),
    "paper":         ((0.88, 0.86, 0.80), 0.85, 0.0, {}),
    "mattress":      ((0.90, 0.90, 0.88), 0.68, 0.0, {}),
    "pillow":        ((0.93, 0.92, 0.90), 0.72, 0.0, {}),
    "curtain_sheer": ((0.84, 0.82, 0.78), 0.90, 0.0, {"transmission": 0.0}),
    "book_red":      ((0.28, 0.09, 0.07), 0.75, 0.0, {}),
    "book_blue":     ((0.09, 0.13, 0.22), 0.75, 0.0, {}),
    "book_cream":    ((0.72, 0.66, 0.52), 0.78, 0.0, {}),
    "art_1":         ((0.55, 0.36, 0.22), 0.85, 0.0, {}),
    "art_2":         ((0.20, 0.26, 0.24), 0.85, 0.0, {}),
    "art_3":         ((0.72, 0.66, 0.58), 0.85, 0.0, {}),

    "bark":          ((0.09, 0.075, 0.065), 0.92, 0.0, {}),
    "water":         ((0.02, 0.09, 0.11), 0.03, 0.0, {"transmission": 0.7, "ior": 1.33}),
    "pool_tile":     ((0.10, 0.30, 0.36), 0.18, 0.0, {}),
}

_CACHE = {}
_TILE = {}


def _img(name, suffix, non_color=False):
    path = os.path.abspath(os.path.join(TEX, f"{name}_{suffix}.png"))
    if not os.path.exists(path):
        return None
    img = bpy.data.images.get(os.path.basename(path)) or bpy.data.images.load(path)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def _node(nt, kind, loc):
    n = nt.nodes.new(kind)
    n.location = loc
    return n


def build(name):
    """Create (or fetch) a Blender material by name."""
    if name in _CACHE:
        return _CACHE[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = _node(nt, "ShaderNodeOutputMaterial", (600, 0))
    bsdf = _node(nt, "ShaderNodeBsdfPrincipled", (280, 0))
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    def setv(key, val):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = val

    if name in SPEC:
        tile, rough, metal, nstr = SPEC[name]
        _TILE[name] = tile
        alb = _img(name, "alb")
        nrm = _img(name, "nrm", non_color=True)
        rgh = _img(name, "rough", non_color=True)
        uv = _node(nt, "ShaderNodeTexCoord", (-620, 0))
        tex = _node(nt, "ShaderNodeTexImage", (-380, 120))
        tex.image = alb
        nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        setv("Roughness", rough)
        setv("Metallic", metal)
        if rgh is not None:
            rt = _node(nt, "ShaderNodeTexImage", (-380, -120))
            rt.image = rgh
            rt.image.colorspace_settings.name = "Non-Color"
            nt.links.new(uv.outputs["UV"], rt.inputs["Vector"])
            nt.links.new(rt.outputs["Color"], bsdf.inputs["Roughness"])
        if nrm is not None:
            nm = _node(nt, "ShaderNodeNormalMap", (0, -260))
            nm.inputs["Strength"].default_value = nstr
            ni = _node(nt, "ShaderNodeTexImage", (-380, -320))
            ni.image = nrm
            nt.links.new(uv.outputs["UV"], ni.inputs["Vector"])
            nt.links.new(ni.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    elif name in PLAIN:
        rgb, rough, metal, extra = PLAIN[name]
        setv("Base Color", (*rgb, 1.0))
        setv("Roughness", rough)
        setv("Metallic", metal)
        if "transmission" in extra:
            setv("Transmission Weight", extra["transmission"])
        if "ior" in extra:
            setv("IOR", extra["ior"])
        if extra.get("transmission"):
            mat.use_backface_culling = False
    else:
        setv("Base Color", (0.6, 0.6, 0.6, 1.0))
        setv("Roughness", 0.6)
    _CACHE[name] = mat
    return mat


def tile_m(name):
    """Physical size of one texture repeat, in metres."""
    return _TILE.get(name, SPEC.get(name, (1.0,))[0])


def warm(rgb, strength=1.0, tag="lamp"):
    """Emissive material for light fixtures."""
    key = f"emit_{tag}"
    if key in _CACHE:
        return _CACHE[key]
    mat = bpy.data.materials.new(key)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = _node(nt, "ShaderNodeOutputMaterial", (300, 0))
    em = _node(nt, "ShaderNodeEmission", (0, 0))
    em.inputs["Color"].default_value = (*rgb, 1.0)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    _CACHE[key] = mat
    return mat
