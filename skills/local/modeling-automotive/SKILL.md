---
name: modeling-automotive
description: Parametric car body builder - lofted lower body plus greenhouse with tumblehome, boolean wheel arches, wheels on the real track, and a package-proportion gate (wheelbase/length, tyre/height, greenhouse share, overhangs).
license: MIT
metadata:
  requires: bpy
---

# Automotive Body

A car is a *package* before it is a surface: wheelbase, track, tyre diameter, beltline and
greenhouse share decide whether the result reads as a vehicle at all. This builds that
package as geometry, so the silhouette can be judged in minutes instead of after days of
surfacing.

## When to use
- Any vehicle: car, van, truck cab, sci-fi transport (override the presets).
- As the base for `modeling-detail` (panel grooves, bevel stack) and `materials-automotive-paint`.

## Procedure
1. Pick a preset (`sedan`, `suv`, `coupe`, `hatch`) or pass real figures from the brief.
2. Build. Check `proportion_ok` and the five ratios in the JSON: wheelbase/length
   0.55-0.63, tyre/height 0.40-0.60, height/width 0.70-0.95, greenhouse 0.22-0.40,
   overhang <= 0.22 per side.
3. Build order matters: loft the lower body -> subdivide -> cut wheel arches -> add the
   greenhouse -> wheels -> proportions.
4. Hand off to `modeling-detail --fix` (the boolean arches leave n-gons) and then to the
   materials and camera skills.

## CLI
```
.venv/bin/python tools/bpy_run.py skills/local/modeling-automotive/scripts/car_body.py --     --preset sedan --render --out /tmp/car.png --save /tmp/car.blend
.venv/bin/python tools/bpy_run.py skills/local/modeling-automotive/scripts/car_body.py --     --preset suv --length 4800 --track 1640 --no-wheels
```

## Construction notes (measured, not assumed)
- **Two lofts, not one.** Lower body: slab sides with a shoulder and a crowned deck.
  Greenhouse: a second loft with tumblehome sitting on that deck. One loft gives a loaf of
  bread; the split also makes the glass/paint assignment fall out of the face normals.
- **Subdivide before boolean.** Cutting wheel arches into the 392-quad cage tears holes.
  Apply the subdivision, then cut.
- **Ring construction.** The half-section's two x=0 endpoints must not be duplicated when
  mirroring in the vertex table, or you get degenerate quads and non-manifold edges at the
  centre line (283 of them, found by `modeling-detail --audit-only`).
- **Normals.** `recalc_face_normals` after lofting, otherwise the shell has negative volume.
- **Rocker height is fixed.** If the sill follows the drooping deck, the bumpers dive
  below the wheels.
- **Wheels sit on the track line** (`x = +/- track/2`), not inset by half a tyre.

## Verification done
Sedan preset renders at 700x394, 32 spp (11 s, CPU). Reported body dims 1849 x 4893 x 798 mm
against a 1860 x 4900 spec; `proportion_ok: true` on all five ratios; ~11.5 k tris.
Audited clean by `modeling-detail` (manifold, outward normals) after `--fix`.

## Limits (honest)
- This is a **package-accurate blockout**, not a finished car. Surfaces are generic: no
  feature lines, no realistic bumpers/lights/grille. Judge proportions with it, then model.
- The greenhouse is a single loft; a real car has separate A/B/C pillars and a windscreen
  rake that differs from the rear screen. Both are approximations here.
- No interior, no wheel arch liners, no underbody.
