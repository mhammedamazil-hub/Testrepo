---
name: qa-export-verify
description: Prove an export is intact - reimports the GLB/GLTF/FBX/OBJ/STL/USD file into a clean scene and compares triangle count, dimensions, materials, UVs and textures against the source.
license: MIT
metadata:
  requires: bpy
---

# Export Verification

Export success is not asset success. `export_scene.gltf` happily writes a file containing
only the selected objects, or drops materials, and still returns `FINISHED`. The only proof
is to reopen the file and compare.

## When to use
- After every export, always.
- Before delivery, with `--tri-tol 1 --size-tol 0.5` to tighten the tolerances.
- When a client says "the model looks wrong in the viewer".

## Procedure
1. Export (vendored `blender-export-pipelines`), remembering that glTF exports the
   **selection** - select the objects first.
2. Import the file into a fresh scene with the same axis convention.
3. Compare tris, bounding dimensions, material count, UV layers, image textures.
4. Read `pass` and the per-field deltas; a 50 % size delta means the wrong axis or the
   wrong units, not a rounding issue.

## CLI
```
.venv/bin/python tools/bpy_run.py --blend scene.blend     skills/local/qa-export-verify/scripts/verify_export.py --     --objects Box --file /tmp/asset.glb --tri-tol 2 --size-tol 1
```

## Verification done
972 tris in -> 972 tris out, dimension delta 0.00 %, materials 1/1, UVs present,
`pass: true`, `EXPORT VERIFIED`. Before fixing the material check, the same run reported a
false failure; that bug was found by this skill, on this repository's own export path.

## Limits (honest)
- Compares counts and bounds, not shading: a model with inverted normals will pass.
- Procedural node materials export as approximations; the check compares material *count*
  and *names*, not how a shader will look in a game engine.
- Textures are compared by presence, not by pixel content.
