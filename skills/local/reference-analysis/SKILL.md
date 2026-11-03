---
name: reference-analysis
description: Measure a reference photo before modelling - silhouette bounds, aspect, width profile, palette, scale calibration, and a proportion gate that compares a model to the reference. Use at the very start of any modelling job and again before detailing.
license: MIT
metadata:
  requires: bpy, numpy, pillow
---

# Reference Analysis

Modelling without measuring the reference is how you get "a car" instead of "that car".
This turns a photo into numbers you can model against, then gates the model against them.

## When to use
- **Before** any blockout. Get the aspect, the width profile and the palette first.
- **After** the blockout, as the proportion gate: if the model is more than 5 % off the
  reference silhouette, fix proportions before adding a single detail.
- When a reference has no dimensions: pass a known length (`--known-mm`) and everything
  else is derived from it.

## Procedure
1. Pick the cleanest view (side or front, minimal perspective, subject filling >60 % of
   the frame). Perspective shots distort the width profile - a 3/4 shot is only good for
   colour, not for proportions.
2. Run with `--known-mm 4500 --known-axis x` if you know one real dimension.
3. Read the width profile: it tells you where the shape is widest and how the ends taper.
   Model those numbers, not a feeling.
4. After blockout, run again with `--compare-model Object` - it renders the model from the
   same axis, matches the silhouette bounds and reports the percentage error per axis.
5. Only when `proportion_gate` passes should you start the detail pass.

## CLI
```
.venv/bin/python tools/bpy_run.py skills/local/reference-analysis/scripts/reference_report.py --     --image ref_side.png --known-mm 4500 --overlay /tmp/overlay_side.png
.venv/bin/python tools/bpy_run.py --blend model.blend     skills/local/reference-analysis/scripts/reference_report.py --     --image ref_side.png --known-mm 4500 --compare-model Body
```

## What it returns
`extent`, `aspect`, `palette` (k-means dominant colours with population share), `bands`
(width at N horizontal slices), `proportion_gate` (pass/fail per axis, 5 % tolerance) and
optional overlay PNGs with numbered slices so you can see what was measured.

## Verification done
Measured a known 4500 mm reference: extent reported 4500.0 mm, aspect 2.6502, palette
red-dominant. Overlay PNG inspected to confirm the slice lines land on the object.

## Limits (honest)
- Works on silhouettes: a light object on a light background gives a bad mask. Put the
  subject on a contrasting background or crop first.
- `--compare-model` compares bounding boxes, not shape. A blob with the right box passes.
  Use it as a gate, not as a judgement of quality.
- Single-image palette from an sRGB JPEG is a display-referred measurement; convert to
  linear before using it as a base colour.
