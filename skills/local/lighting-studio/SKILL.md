---
name: lighting-studio
description: Four headless lighting rigs with emissive reflection cards - studio3, softbox, hardlight and automotive - sized and scaled to the subject automatically. No HDRI required.
license: MIT
metadata:
  requires: bpy
---

# Studio Lighting

There are no HDRI downloads in this environment, so every render must be lit with real
lights and emissive cards. That is also the better habit: a rig you control beats a random
studio HDRI for product work.

## When to use
- Every render that is not a QA silhouette pass.
- `automotive`: long strip cards for paint reflections.
- `hardlight`: single small source, hard shadows, for drama and for reading form.
- `softbox`: neutral, low-contrast, for material evaluation.

## Procedure
1. Frame the subject first (`camera-composition`), then light it.
2. `--rig` picks the setup; `--scale` multiplies distance for very large/small subjects.
3. Add `--exposure` to bring the render to a sane level instead of changing wattage.
4. Check the render: if the subject has no highlight running along its form, the rig is
   too frontal. Move the key 30-45 deg off axis.

## CLI
```
.venv/bin/python tools/bpy_run.py --blend car.blend     skills/local/lighting-studio/scripts/studio_lighting.py --     --rig automotive --target CarBody --exposure 0.2
```

## Verification done
4/4 rigs returned `ok: true` on the test scene; the automotive rig was used for the car
renders (700x394, 32 spp, ~11 s on 2 CPU cores).

## Limits (honest)
- No HDRI, so no environment reflections of a real world; emissive cards fake them.
- Wattage is scaled by subject size empirically - always check the first render instead of
  trusting the numbers for a new scene scale.
