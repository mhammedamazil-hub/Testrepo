---
name: materials-automotive-paint
description: Automotive paint shader with the layered stack real car paint has - metallic flake, clear coat, orange peel, and six finishes (metallic, solid, pearl, matte, chrome, primer).
license: MIT
metadata:
  requires: bpy
---

# Automotive Paint

Car paint is three layers: pigment base, metallic flake, clear coat. Artists that skip the
coat get plastic; artists that skip the flake get flat colour. This builds all three, with
flake density/scale and a subtle orange-peel normal.

## When to use
- Vehicle bodies, product shots of painted metal, hard-surface props with a coat.
- `primer` for blockouts you plan to paint later (it hides the material work while you
  check shape).

## Procedure
1. Choose the finish. `metallic` for 90 % of cars, `solid` for older/flat colours,
   `pearl` for the two-tone flip, `matte` for wraps, `chrome` for trim, `primer` for WIP.
2. Set `--color` in linear-ish values (0.42 0.03 0.03 is a deep red).
3. `--flake` controls Voronoi flake scale: 200-400 is fine flake, 80 is heavy metal.
4. `--peel` adds the clear-coat orange peel; keep it under 0.15 or it looks like a hammer
   finish.
5. Light it with a long soft strip (see `lighting-studio --rig automotive`) - paint only
   reads with long reflections.

## CLI
```
.venv/bin/python tools/bpy_run.py --blend car.blend     skills/local/materials-automotive-paint/scripts/car_paint.py --     --kind metallic --color 0.42 0.03 0.03 --flake 260 --peel 0.06 --assign-to CarBody
```

## Verification done
All six kinds returned `ok: true` on a test scene; the material grid render
(`skills/tests/visual/material_grid.py`, 1500x900, 16 spp) shows the metallic variants
reading differently under the same lighting.

## Limits (honest)
- Flake and peel are procedural and **will not survive glTF/FBX export**. Bake to a normal
  + base colour if the asset ships to a game engine.
- No real measured spectral flake (no measured BRDF, no gonio data).
