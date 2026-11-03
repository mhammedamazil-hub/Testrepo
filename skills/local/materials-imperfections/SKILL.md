---
name: materials-imperfections
description: Add wear, dust, grime, scratches and fingerprints to any material via a shared, idempotent node group - the difference between "CG clean" and "photographed".
license: MIT
metadata:
  requires: bpy
---

# Material Imperfections

A perfectly uniform surface reads as CG. Real objects have wear where hands and feet
touch, dust on upward faces, grime in crevices. This adds those layers to an existing
material without rebuilding it.

## When to use
- Before the final render of anything close enough to see the surface.
- Never on a blockout: it hides proportion mistakes and wastes render time.

## Procedure
1. Build the base material first (glass/paint/surfaces).
2. Add imperfections with moderate values: wear 0.3-0.5, dust 0.2-0.4, grime 0.2,
   scratches 0.15, fingerprints 0.1.
3. Point/object-coordinate driven, so the effect stays put when the object moves.
4. Re-running is safe (idempotent): it updates the existing node group instead of stacking
   a second one.

## CLI
```
.venv/bin/python tools/bpy_run.py --blend scene.blend     skills/local/materials-imperfections/scripts/imperfections.py --     --objects CarBody --wear 0.45 --dust 0.3 --grime 0.2 --scratches 0.15
```

## Verification done
Added to the test scene and rendered in the material grid; running twice produced one node
group, not two (idempotency checked by node-group count).

## Limits (honest)
- Procedural masks driven by geometry/pointiness: no UV-space dirt maps, no baked AO
  directionality.
- Masks are not exportable to glTF without baking.
