---
name: materials-glass
description: Physically-plausible glass shaders without textures - architectural, thin, frosted, ribbed, tinted and acrylic, with correct IOR, thickness and tint behaviour. Use for windows, bottles, screens, automotive glazing.
license: MIT
metadata:
  requires: bpy
---

# Glass Materials

Glass fails in two ways: physically wrong (no thickness, IOR 1.0, no shadow tint) and
artistically wrong (frosted where it should be clear, clear where it should be dirty).
This builds the six cases that cover almost every production need.

## When to use
- Windows in architecture/interiors (use `architectural`: real thickness, shadow tint).
- Bottles, glasses, lenses (`thin` for single-surface, `architectural` when the shell has
  real thickness).
- Screens/frosted partitions (`frosted`), reeded/ribbed partitions (`ribbed`).
- Automotive glazing (`tinted`, low roughness, slight tint).

## Procedure
1. Decide thickness first: does the geometry have an inner shell? If not use `thin`.
2. Pick the kind, then set `--tint` (RGB 0-1) rather than hacking the base colour.
3. `--ior`: 1.45 window glass, 1.49 acrylic, 1.52 crown glass, 1.33 water.
4. Render with Cycles. EEVEE needs raytracing enabled for transmission to read.

## CLI
```
.venv/bin/python tools/bpy_run.py --blend scene.blend     skills/local/materials-glass/scripts/glass_materials.py --     --kind architectural --assign-to WindowA WindowB --thickness 6 --tint 0.94 0.97 0.95
```

## Verification done
All six kinds executed on a test scene and returned `ok: true`, with the material assigned
and the node graph built (no missing sockets on Blender 5.0.1).

## Limits (honest)
- No dispersion or caustic-specific setup; caustics are off for speed and would need a
  separate render configuration.
- Procedural ribbing uses a wave texture in the normal, so it will not survive a glTF
  export - bake it if the asset ships.
