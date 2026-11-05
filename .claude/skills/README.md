# blender-skills (vendored subset)

Source: <https://github.com/arjun988/blender-skills> (MIT, v1.3.0), cloned and used for the
hero-render pass. The upstream pack has 94 skills; only the ones this project actually used
are vendored here, because the rest is per-genre art direction (horror, anime, voxel, ...)
that has nothing to do with architectural visualisation:

| skill | used for |
|---|---|
| `archviz` | scale check, camera set, HDRI/practical lighting, delivery |
| `lighting` | sun/sky calibration, bounce cards, colour temperature |
| `lookdev` | the grey-pass -> materials -> light -> screenshot iteration loop |
| `materials` | PBR values, micro-detail by distance |
| `rendering` | Cycles settings, samples, denoiser, passes, colour management |
| `compositing` | the beauty stack (exposure, grade, glare, lens, vignette) |
| `camera-cinematography` | lens choice, framing, DoF |
| `realistic-style` | real-world scale references, PBR accuracy table |
| `qa-review` | the final checklist |

What was actually applied is recorded in `docs/HERO_RENDER.md`, including the two places
where the skills' advice had to be overridden because it does not hold in a headless
Blender 5.0 without an HDRI library (no HDRI on disk -> the sky is a physical sky plus a
procedural cloud field; "512-2048 samples" -> 160 adaptive samples at 2560x1440, which is
what a 2-vCPU box can finish in a night).
