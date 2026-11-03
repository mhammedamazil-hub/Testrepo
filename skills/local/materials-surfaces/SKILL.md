---
name: materials-surfaces
description: Eight production surface shaders with no textures - rubber, leather, carbon twill, brushed metal, anodised, chrome, powdercoat, black plastic - built procedurally so they work offline.
license: MIT
metadata:
  requires: bpy
---

# Surface Materials

Everything that is not glass, paint or a hero texture: tyres, interior leather, carbon
panels, brushed aluminium, anodised trim, powder-coated steel, matte black plastic.

## When to use
- Filling out an asset after the hero materials are done.
- When you have no texture library (this environment has no internet asset access) and need
  plausible surfaces anyway.

## Procedure
1. `--kind` picks the shader family; `--color` overrides the base where it makes sense.
2. Rubber: keep roughness high (0.75+) and specular low, or tyres look like plastic.
3. Brushed/anodised: the anisotropy direction follows the object's local Z - rotate the
   object, not the texture, when the grain must run the other way.
4. Carbon twill: check the weave scale against the part size; a 5 mm weave on a bonnet is
   right, on a phone case it is wrong.

## CLI
```
.venv/bin/python tools/bpy_run.py --blend car.blend     skills/local/materials-surfaces/scripts/surface_materials.py --     --kind rubber --assign-to Tyre_00 Tyre_01 Tyre_10 Tyre_11
```

## Verification done
8/8 kinds returned `ok: true`; all eight appear distinctly in the material grid render.

## Limits (honest)
- All procedural: none of these survive a glTF export without baking.
- Carbon twill is a stylised weave, not a measured tow geometry.
