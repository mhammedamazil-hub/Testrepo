# Professional Modelling Workflow (19 steps) and Photorealism Rules

This is the procedure the skills in this directory implement. It is deliberately
front-loaded on proportion and back-loaded on detail, because that is the order that
prevents rework.

Every step names the skill that executes or verifies it. Nothing here is optional for a
hero asset; for a blockout, steps 1-8 are enough.

---

## A. Reference and proportion (steps 1-4)

1. **Collect references and measure them.** No modelling from memory. Run
   `reference-analysis/reference_report.py` on the cleanest view: bounds, aspect, width
   profile, palette, and a scale if one dimension is known.
2. **Write the spec as numbers.** Length, width, height, wheelbase/track (vehicles),
   floor-to-ceiling (architecture), grip diameter (products). These numbers go into the
   blockout spec, not into a prose description.
3. **Blockout at real scale.** `modeling-blockout/blockout.py` (or
   `modeling-automotive/car_body.py` for vehicles). Units in millimetres, one metre = 1000
   units, `Ctrl+A` scale applied before anything else.
4. **Run the proportion gate.** Compare the blockout envelope to the reference
   (`reference_report.py --compare-model`) and check the package ratios. **Do not proceed
   while any axis is more than 5 % off.** This is the step most often skipped and the one
   that causes the most rework.

## B. Primary form (steps 5-8)

5. **Settle the silhouette from four views.** Front, rear, side, three-quarter. If the
   silhouette only works from one angle, it is not settled. Use
   `qa-render-review/review_render.py` for the contact sheet.
6. **Get the big planes right before any curve.** Flat panels flat, shoulders straight,
   radii consistent. Subdivision surfaces hide a wrong plane, they do not fix it.
7. **Decide the workflow**: mid-poly (bevel + weighted normals), subdivision (support loops)
   or high-to-low (bake). Write the decision down — see the vendored
   `blender-hardsurface-modeling` skill for the trade-offs.
8. **Build the modifier stack before the detail**: Mirror -> Booleans -> Bevel ->
   Weighted Normal, never applied until export. `modeling-detail` audits the result.

## C. Secondary and tertiary form (steps 9-13)

9. **Cut real panel breaks.** Grooves cut as shallow booleans (`detail_pass.py --grooves`),
   not decals. Real geometry catches light from every angle.
10. **Bevel consistently.** Width proportional to part size (0.5-2 %), angle limit 30 deg,
    clamp overlap on, harden normals on. One asset = one bevel language.
11. **Shading check.** Shade smooth by angle (not "smooth everything"); weighted normals on
    hard-surface parts. Audit for non-manifold edges and flipped normals *before* blaming
    the lighting.
12. **UV and texel density.** Unwrap after the boolean work (vendored
    `blender-retopology-uv`), then audit with `uv-texel-audit/texel_audit.py`. Fix overlaps
    first, then density, then utilisation.
13. **Materials in layers.** Base surface (`materials-surfaces`), hero shaders
    (`materials-glass`, `materials-automotive-paint`), then imperfections
    (`materials-imperfections`). Never start with dirt.

## D. Light, camera, render (steps 14-17)

14. **Camera before lights.** `camera-composition/compose.py`: preset by subject, elevation
    8-15 deg for vehicles, margin ~1.15, DOF focused on the subject centre, thirds guide for
    review.
15. **Light for form, not for brightness.** `lighting-studio/studio_lighting.py`: key
    30-45 deg off axis, fill at 30-40 % of key, rim to separate from background, emissive
    cards for reflections. A subject with no highlight along its form is under-modelled in
    the light, not in the mesh.
16. **Plan the render.** `render-optimize/render_plan.py` calibrates the machine and returns
    the sample count that fits the budget. Never start a 4K render without this number.
17. **Render deliverable views** at planned settings; keep the .blend and the JSON reports
    next to the images.

## E. QA and delivery (steps 18-19)

18. **Self-critique loop.** `qa-render-review/review_render.py` renders front/rear/side/
    three-quarter, measures exposure, contrast, subject coverage and clipping, and returns a
    verdict. Fix, re-render, keep the report. Numbers cannot judge composition — look at the
    contact sheet too.
19. **Verify the export by reopening it.** `qa-export-verify/verify_export.py` reimports the
    file into a clean scene and compares triangles, dimensions, materials, UVs and textures.
    An export that only contains the selected objects still returns `FINISHED`; only the
    reimport tells the truth.

---

## Photorealism rules

These are the rules that separate a render that reads as a photograph from one that reads
as CG. They are ordered by how often they are the actual cause of a "CG look".

1. **Nothing is perfectly clean or perfectly uniform.** Every surface gets wear where it is
   touched, dust on upward faces, and a roughness variation. Small amounts only.
2. **Every edge has a real radius.** Zero-width edges produce the classic razor highlight.
   Bevel or chamfer every manufactured edge; 0.5-2 % of part size.
3. **Light with size.** Big sources (soft), or small sources plus bounce cards. A single
   small point light is the number-one CG giveaway.
4. **Reflections must have something to reflect.** Without an HDRI (not available here),
   place emissive cards and a gradient world. A mirror surface in an empty world looks like
   a defect.
5. **Value structure before colour.** Squint: the subject should separate from the
   background by value. If it only separates by hue, the render will look flat.
6. **Composition is physical.** Long lens for products (85-135 mm), wide for interiors
   (18-24 mm), low elevation for vehicles. Free camera placement is what makes renders look
   like screenshots of a viewport.
7. **Depth of field, but shallow-at-the-right-place.** Focus on the subject's near third;
   f/2.8-4 for closeups, f/8-11 for products, f/11+ for architecture.
8. **Physically plausible scale for material properties.** Glass needs thickness and an
   IOR; car paint needs a clear coat; fabric needs sheen. Roughness without IOR is not glass.
9. **Breaks and gaps.** Panel gaps, seams, chips, and slightly-open doors are what convince
   the eye that the object is real.
10. **Render noise is not detail.** Denoise; do not ship speckle as "grain".

---

## Self-critique loop (how to actually improve a render)

```
render 4 views -> measure -> list 3 concrete faults -> fix the biggest -> re-render
```

Rules for the loop:
- Name faults as geometry/material/light/camera, never "looks bad".
- Compare against the reference, not against the previous render.
- One change per iteration; two changes at once teaches nothing.
- Stop when the remaining faults are textural, not structural.
