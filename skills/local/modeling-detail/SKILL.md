---
name: modeling-detail
description: Hard-surface detail pass - mesh audit (non-manifold edges, flipped normals, zero-area faces, n-gons on curved surfaces), automatic repair, boolean panel grooves, and a bevel + smooth-by-angle + weighted-normal stack.
license: MIT
metadata:
  requires: bpy
---

# Modeling Detail

"Finished" is not "more polygons". It is: sound topology, edges that catch light, and panel
breaks that are real geometry. This skill measures first, then changes, then measures again.

## When to use
- After any boolean-heavy blockout (booleans are the main source of n-gons and slivers).
- Before export, always: run `--audit-only` and read `problems`.
- When a render shows shading artefacts: audit for non-manifold edges and flipped normals
  before touching lights or materials.

## Procedure
1. `--audit-only` on the target. Read `problems`, not just `ok`.
2. `--fix` to merge doubles, drop zero-area faces, re-orient normals and triangulate n-gons
   that sit on curved surfaces. Re-audit - `fix` reports what it changed and the final state.
3. Panel lines: `--grooves Y Y ...` cuts vertical shut lines through the shell with one
   boolean (all cutters in one collection - per-cutter booleans leave bridging faces).
4. Detail stack: `--bevel 2 --segments 2 --smooth-angle 40` adds Bevel (angle-limited,
   clamp overlap, harden normals), shade-smooth-by-angle and Weighted Normal.
5. `--apply` bakes the stack for export; keep an un-applied copy as the editable source.

## CLI
```
.venv/bin/python tools/bpy_run.py --blend car.blend     skills/local/modeling-detail/scripts/detail_pass.py -- --objects CarBody --audit-only
.venv/bin/python tools/bpy_run.py --blend car.blend     skills/local/modeling-detail/scripts/detail_pass.py --     --objects CarBody --fix --grooves 1.15 -1.25 --gap 7 --bevel 2 --apply
```

## What the audit measures
verts/faces/tris, non-manifold edges, loose verts and edges, zero-area faces, n-gon count,
n-gons **on curved surfaces** (compared against neighbouring face normals), sharp edges
(>50 deg), signed volume (catches inside-out meshes) and a `problems` list.

## Verification done
On the parametric car body the audit reported 283 non-manifold edges, negative volume and
172 curved n-gons - a real bug in this repository's own loft code, fixed at the source.
After `--fix`: 0 non-manifold, 0 curved n-gons, positive volume, `verdict: MESH SOUND`.
Grooves cut 6140 -> 7156 faces and are visible as shut lines in a 700x394 Cycles render.

## Limits (honest)
- Groove verification is visual plus a face-count change. A geometric "faces crossing the
  gap" test still reports ~44 bridging faces on the underside, so do not claim the slot is
  watertight - check the render.
- `--fix` triangulates only n-gons that are provably on curved surfaces; flat n-gons are
  left alone on purpose (they are fine and cheaper).
- No UV repair, no normal-map transfer, no high-to-low baking here - use the vendored
  `blender-texture-baking` skill for that.
