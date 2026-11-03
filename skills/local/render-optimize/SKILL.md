---
name: render-optimize
description: Two-point calibration of Cycles on the actual machine, then a sample/bounce plan that fits a time budget across a shot list. Prevents the classic "one frame took 40 minutes" failure.
license: MIT
metadata:
  requires: bpy
---

# Render Optimisation

On 2 CPU cores a careless 4K shot is an hour. This measures the machine, then tells you
what sample count and resolution actually fit your budget - before you start.

## When to use
- Before any multi-shot render (turntables, review passes, client deliverables).
- When someone asks "can we do 4K?" - run this instead of guessing.

## Procedure
1. Calibrate: it renders two small frames at different sample counts to get seconds per
   sample per kilopixel (a one-point calibration is unreliable because sub-0.3 s timings
   are timer noise).
2. Pass `--budget-min` for the whole job and `--shots` for the count; it returns the max
   sample count that fits, plus a per-shot table.
3. Use denoising and adaptive sampling unless you have a reason not to - both are on by
   default in this build.
4. If the plan does not fit, cut resolution before samples: halving resolution is 4x
   faster, halving samples is only 2x and costs more noise.

## CLI
```
.venv/bin/python tools/bpy_run.py --blend scene.blend     skills/local/render-optimize/scripts/render_plan.py --     --res 1280 720 --shots 12 --budget-min 20 --samples 400
```

## Verification done
Calibrated on the sandbox: 0.348 s overhead, 0.00036 s per sample-kpixel -> 144 spp for
12 shots at 1280x720 in ~9.6 min. The prediction was used to size the material grid render
(1500x900, 16 spp, ~58 s measured).

## Limits (honest)
- Calibrates on the current scene: a scene with heavy volumetrics or many lights will cost
  more than the plan says. Re-run after big scene changes.
- Timings vary with what else is running in the sandbox; treat the plan as +/-30 %.
