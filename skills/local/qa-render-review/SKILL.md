---
name: qa-render-review
description: Self-critique loop - renders front, rear, side and three-quarter views in Cycles, measures exposure/contrast/subject coverage numerically, builds a contact sheet, and returns a PASS/FAIL verdict.
license: MIT
metadata:
  requires: bpy, pillow
---

# Render Review (self-critique)

Rendering one flattering angle hides the mistakes. This renders the four angles a client
and a modeller both look at, measures whether the image is actually usable, and writes a
contact sheet you can inspect at a glance.

## When to use
- After every modelling or material milestone, before showing anything.
- After lighting changes - exposure problems show up in the numbers before your eyes.

## Procedure
1. Run on the finished objects (exclude ground/backdrop via `--objects`).
2. Read the numbers: `mean_luma` (0.15-0.85), `contrast`, `subject_coverage` (0.15-0.80),
   `clipped_black/white` fractions.
3. Look at the contact sheet. Numbers cannot tell you the silhouette is ugly.
4. Fix and re-run. Keep the JSON as the record of the review.

## CLI
```
.venv/bin/python tools/bpy_run.py --blend car.blend     skills/local/qa-render-review/scripts/review_render.py --     --objects CarBody Greenhouse --out /tmp/review --res 640 --samples 24
```

## Verification done
Car body pass -> `verdict PASS`, contact sheet at `/tmp/review/contact_sheet.png`
(front/rear/side/three-quarter), stats computed from the rendered pixels with Pillow.

## Limits (honest)
- **Cycles only.** The vendored Workbench/EEVEE review path cannot run here: the stub
  `libGL` has no `glXQueryExtension`, so any OpenGL-based render crashes. This skill exists
  partly to replace it.
- Measurements are heuristics. A deliberately dark, high-key or silhouette shot will fail
  the ranges while being correct - judgement still required.
