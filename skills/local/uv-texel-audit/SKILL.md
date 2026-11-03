---
name: uv-texel-audit
description: UV health audit - texel density per object (px per metre at a target texture size), UV utilisation, island spread, stretch and overlapping UVs. Use before baking or texturing.
license: MIT
metadata:
  requires: bpy
---

# UV / Texel Audit

Two objects with different texel density look like two assets from different projects.
This measures density in **pixels per metre** so a scene can be normalised, and catches
overlapping UVs before a bake turns them into smeared texture.

## When to use
- After unwrapping and before any texturing or baking.
- When a bake looks smeared or a texture looks soft on one object only.
- Before export, as part of the asset QA gate.

## Procedure
1. Unwrap first (vendored `blender-retopology-uv`), then audit.
2. Pick the target resolution (`--res 2048`) and the minimum density (`--min-density`).
3. Fix in this order: overlaps -> density -> utilisation -> stretch.
4. Re-audit; numbers should converge, not drift.

## CLI
```
.venv/bin/python tools/bpy_run.py --blend scene.blend     skills/local/uv-texel-audit/scripts/texel_audit.py --     --objects Box Sphere --res 2048 --min-density 512
```

## Verification done
Test scene: Ball 1757 px/m, Box 853 px/m at 2048, 0 overlaps, verdict `UV OK`.

## Limits (honest)
- Density is estimated from UV area / world area; strongly curved or boolean-cut geometry
  is approximate.
- Overlap detection is AABB-of-islands based, so it can flag false positives on packed
  islands that are close but legal.
