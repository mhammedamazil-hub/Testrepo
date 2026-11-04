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
    # ---- v2 facade + site (tex_gen2) ----
    "lime_render":   (2.20, 0.86, 0.0, 0.5),
    "lime_warm":     (2.20, 0.88, 0.0, 0.5),
    "board_concrete": (2.60, 0.74, 0.0, 1.6),
    "travertine_clad": (2.40, 0.58, 0.0, 2.2),
    "stone_paving":  (2.40, 0.66, 0.0, 1.8),
    "asphalt":       (3.00, 0.82, 0.0, 1.4),
    "gravel":        (1.20, 0.82, 0.0, 2.6),
    "timber_slat":   (1.20, 0.54, 0.0, 1.5),
    "water_ripple":  (1.60, 0.05, 0.0, 1.1),
    "bark":          (1.00, 0.88, 0.0, 3.0),
    "lawn_v2":       (0.90, 0.94, 0.0, 1.4),
}

# Foliage: alpha-cutout cards. name -> (tile metres, roughness, double-sided)
CARDS = {
    "leaf_card_a":  (0.42, 0.50, True),
    "leaf_card_b":  (0.34, 0.50, True),
    "leaf_card_c":  (0.52, 0.52, True),
    "leaf_card_olive": (0.30, 0.55, True),
    "grass_blade":  (0.55, 0.62, True),
    # twig sprigs: one card carries a whole spray of leaves
    "spray_a":      (0.40, 0.52, True),
    "spray_b":      (0.30, 0.52, True),
    "spray_c":      (0.46, 0.54, True),
    "spray_olive":  (0.30, 0.55, True),
    "spray_dark":   (0.36, 0.58, True),
}

# plain (untextured) materials: name -> (rgb, roughness, metallic, extras)
PLAIN = {
    "white_paint":   ((0.90, 0.90, 0.89), 0.35, 0.0, {}),
    "black_paint":   ((0.030, 0.030, 0.032), 0.42, 0.0, {}),
    "ceramic":       ((0.92, 0.92, 0.91), 0.12, 0.0, {}),
    "glass":         ((0.98, 0.99, 1.0), 0.0, 0.0, {"transmission": 1.0, "ior": 1.45}),
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
    # ---- v2 site / detail ----
    "soil_wet":      ((0.035, 0.028, 0.021), 0.82, 0.0, {}),
    "mulch":         ((0.055, 0.040, 0.026), 0.90, 0.0, {}),
    "plant_leaf":    ((0.085, 0.16, 0.045), 0.55, 0.0, {}),
    "plant_leaf_lo": ((0.055, 0.105, 0.030), 0.58, 0.0, {}),
    "canopy_shadow": ((0.012, 0.022, 0.008), 0.72, 0.0, {}),
    "edging":         ((0.30, 0.295, 0.28), 0.72, 0.0, {}),
    "ridge_dark":     ((0.028, 0.042, 0.030), 0.95, 0.0, {}),
    "planting_bed":   ((0.030, 0.040, 0.020), 0.96, 0.0, {}),
    "ridge_far":      ((0.070, 0.095, 0.080), 0.95, 0.0, {}),
    "palm_frond":    ((0.10, 0.19, 0.05), 0.52, 0.0, {}),
    "bed_gravel":    ((0.42, 0.40, 0.37), 0.85, 0.0, {}),
    "cedar":         ((0.16, 0.095, 0.055), 0.62, 0.0, {}),
    "roof_membrane": ((0.085, 0.085, 0.090), 0.78, 0.0, {}),
    "alu_trim":      ((0.52, 0.53, 0.545), 0.28, 1.0, {}),
    "downpipe":      ((0.10, 0.10, 0.105), 0.42, 0.8, {}),
}

# Specular level per material. Physically, base Fresnel is ~0.04 (Specular IOR Level 0.5);
# but vegetation, soil and gravel have a *microscopic* surface that scatters rather than
# reflects, and at grazing angles a 0.5-specular ground turns the whole lawn into a sheet
# of sky (measured: a saturated green albedo rendered as neutral khaki).
SPECULAR = {
    "lawn_v2": 0.12, "grass": 0.12, "gravel": 0.18, "mulch": 0.10, "soil": 0.10,
    "soil_wet": 0.16, "bed_gravel": 0.18, "bark": 0.18, "leaf": 0.20, "leaf_dark": 0.20,
    "plant_leaf": 0.20, "plant_leaf_lo": 0.18, "canopy_shadow": 0.10,
    "spray_a": 0.18, "spray_b": 0.18, "spray_c": 0.18, "spray_dark": 0.14,
    "spray_olive": 0.18, "leaf_card_a": 0.18, "leaf_card_b": 0.18, "leaf_card_c": 0.18,
    "leaf_card_olive": 0.18, "grass_blade": 0.14, "asphalt": 0.25,
    "lime_render": 0.30, "lime_warm": 0.30, "board_concrete": 0.25,
    "travertine_clad": 0.35, "stone_paving": 0.35, "timber_slat": 0.22,
    "roof_membrane": 0.12, "edging": 0.25, "alu_trim": 0.5, "downpipe": 0.5,
}

# facades that get the low-frequency weathering multiply
WEATHERED = {"lime_render", "lime_warm", "board_concrete", "travertine_clad",
             "microcement", "plaster_warm", "plaster_white", "stone_paving"}

_CACHE = {}
_TILE = {}


def reset_cache():
    """Drop cached materials/tile sizes -- required after read_factory_settings()."""
    _CACHE.clear()
    _TILE.clear()


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

    def set_spec():
        lvl = SPECULAR.get(name)
        if lvl is not None and "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = lvl

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
        set_spec()
        if rgh is not None:
            rt = _node(nt, "ShaderNodeTexImage", (-380, -120))
            rt.image = rgh
            rt.image.colorspace_settings.name = "Non-Color"
            nt.links.new(uv.outputs["UV"], rt.inputs["Vector"])
            nt.links.new(rt.outputs["Color"], bsdf.inputs["Roughness"])
        if name in WEATHERED:
            # Real facades are never one flat albedo: a low-frequency multiply keeps big
            # surfaces from reading as a solid colour under a moving sun.
            dust = _node(nt, "ShaderNodeTexNoise", (-380, 380))
            dust.inputs["Scale"].default_value = 1.6
            dust.inputs["Detail"].default_value = 6.0
            dust.inputs["Roughness"].default_value = 0.62
            ramp = _node(nt, "ShaderNodeValToRGB", (-180, 380))
            ramp.color_ramp.elements[0].position = 0.35
            ramp.color_ramp.elements[0].color = (0.78, 0.77, 0.75, 1.0)
            ramp.color_ramp.elements[1].position = 0.72
            ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
            mix = _node(nt, "ShaderNodeMixRGB", (60, 320))
            mix.blend_type = "MULTIPLY"
            mix.inputs["Fac"].default_value = 0.55
            nt.links.new(uv.outputs["Object"], dust.inputs["Vector"])
            nt.links.new(dust.outputs["Fac"], ramp.inputs["Fac"])
            nt.links.new(tex.outputs["Color"], mix.inputs["Color1"])
            nt.links.new(ramp.outputs["Color"], mix.inputs["Color2"])
            nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
        if nrm is not None:
            nm = _node(nt, "ShaderNodeNormalMap", (0, -260))
            nm.inputs["Strength"].default_value = nstr
            ni = _node(nt, "ShaderNodeTexImage", (-380, -320))
            ni.image = nrm
            nt.links.new(uv.outputs["UV"], ni.inputs["Vector"])
            nt.links.new(ni.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    elif name in CARDS:
        tile, rough, two_sided = CARDS[name]
        _TILE[name] = tile
        alb = _img(name, "alb")
        nrm = _img(name, "nrm", non_color=True)
        uv = _node(nt, "ShaderNodeTexCoord", (-620, 0))
        tex = _node(nt, "ShaderNodeTexImage", (-380, 120))
        tex.image = alb
        nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        setv("Roughness", rough)
        set_spec()
        if alb is not None and "Alpha" in tex.outputs:
            nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        if nrm is not None:
            nm = _node(nt, "ShaderNodeNormalMap", (0, -260))
            nm.inputs["Strength"].default_value = 0.8
            ni = _node(nt, "ShaderNodeTexImage", (-380, -320))
            ni.image = nrm
            nt.links.new(uv.outputs["UV"], ni.inputs["Vector"])
            nt.links.new(ni.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
        # Foliage transmits light: a mix of diffuse and translucent is what makes a
        # canopy glow at the edges instead of reading as painted cardboard. Kept low
        # (0.30) because full translucency washes the leaves out to near-white.
        tr = _node(nt, "ShaderNodeBsdfTranslucent", (0, 120))
        nt.links.new(tex.outputs["Color"], tr.inputs["Color"])
        mix = _node(nt, "ShaderNodeMixShader", (300, 60))
        mix.inputs["Fac"].default_value = 0.30
        nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
        nt.links.new(tr.outputs["BSDF"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
        # A cutout leaf seen from behind is still a leaf: render both sides equally.
        mat.use_backface_culling = not two_sided
        mat.blend_method = "CLIP" if hasattr(mat, "blend_method") else mat.blend_method
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
