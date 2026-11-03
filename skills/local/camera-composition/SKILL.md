---
name: camera-composition
description: Camera placement that fits the subject with a chosen lens and margin, subject presets (product 100 mm, car 60 mm, interior 20 mm, architecture 24 mm), physically plausible DOF, orthographic reference views and a rule-of-thirds review overlay.
license: MIT
metadata:
  requires: bpy, pillow (for --guide)
---

# Camera Composition

Most bad renders are bad framing: dead-centre subject, wrong focal length, everything in
focus, horizon through the middle. This does the arithmetic that fixes all four.

## When to use
- Before every render. Always.
- Orthographic front/rear/side for reference comparison and for the QA loop.
- `--guide` when you want the thirds grid burned into the image for self-review.

## Procedure
1. Pick `--preset` by subject, not by taste: interiors cannot be shot at 100 mm.
2. Use `--az/--el`: elevation 8-15 deg for cars (higher makes them look like toys), 10-20
   for products (0 flattens the top plane), 0-3 for architecture.
3. `--margin 1.15` leaves breathing room; 1.0 crops to the bounds.
4. `--ortho front|rear|left|right|top` for technical views - it fits both axes for the
   render aspect, so nothing is cropped.
5. `--guide` writes a `_thirds.png` next to the render. Check the subject's optical centre
   falls on an intersection, not on the centre cross.

## CLI
```
.venv/bin/python tools/bpy_run.py --blend car.blend     skills/local/camera-composition/scripts/compose.py --     --target CarBody --preset car --az -58 --el 9 --render --guide --out /tmp/shot.png
```

## Construction notes (measured)
- **Aspect matters.** A 36 mm sensor is fitted to the wider dimension, so a 16:9 frame is
  much tighter vertically. Framing on the diagonal alone crops the subject top and bottom.
- **Clip range.** Blender's default 0.1 / 1000 clip silently renders an empty frame for a
  scene modelled in millimetres (a car 19 m from camera). Camera creation now sets clip
  start/end from the subject distance.
- **Studio furniture is ignored** when no `--target` is given: framing "all meshes" fits the
  ground plane and the car becomes a speck.
- **DOF focus** is the distance to the subject's bounding-box centre, not to its near corner.

## Verification done
Product preset on a test scene: 100 mm f/8, focus 10.1 mm, thirds overlay inspected.
Ortho front on the same scene: scale 2.098 (matches the 1.8 m object plus margin) after
fixing a stale `matrix_world` that made it 50.5. Car ortho left/front on the car blend
render correctly framed.

## Limits (honest)
- `--guide` is a review aid, not an auto-critique: it does not score the composition.
- No physical lens distortion, no vignetting, no anamorphic behaviour.
