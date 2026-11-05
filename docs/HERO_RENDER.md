# Hero render — the "ultra realistic" pass

Two deliverables were produced with the `blender-skills` pack
(<https://github.com/arjun988/blender-skills>, MIT), vendored into `.claude/skills/`:

| file | what |
|---|---|
| `villa_v2/hero/hero_garden_hero_garden_1920x1080_144spp.png` | south elevation through the garden |
| `villa_v2/hero/hero_pool_hero_pool_1920x1080_144spp.png` | pool corner, terrace and loungers |
| `villa_v2/hero/*.json` | every setting used, plus timings, written by the renderer |

Rebuild:

```bash
.venv/bin/python -m villa_src.tex_gen && .venv/bin/python -m villa_src.tex_gen2
.venv/bin/python tools/bpy_run.py villa_src/render_hero.py -- \
    --shot hero_garden --res 1920 1080 --samples 144 --out villa_v2/hero/hero_garden
.venv/bin/python tools/bpy_run.py villa_src/render_hero.py -- \
    --shot hero_pool  --res 1920 1080 --samples 144 --out villa_v2/hero/hero_pool
```

## The pipeline, and which skill each stage came from

```
archviz      scale check (house 19.7 m, door 2.35 m, eye 1.65 m), camera set, delivery
lookdev      one change at a time, screenshot, gap list, iterate <= 5
materials    PBR values + micro-detail by distance (see below)
lighting     late-afternoon sun, sky fill, bounce cards, colour temperature
rendering    Cycles CPU, adaptive + OIDN, 16 bounces, caustics, render passes
compositing  exposure -> balance -> mist -> glare -> lens -> vignette
camera-...   35/30 mm, corrected verticals, DoF at a real f-stop
realistic    reference table (door 2.03-2.13 m, car 1.4-1.6 m, human eye 1.6-1.7 m)
qa-review    the final checklist at the bottom
```

### 1. Lookdev: materials that fail where buildings fail (`villa_src/lookdev_v3.py`)

The v2 materials were *clean*: one albedo, one normal map, uniform everywhere. Three shader
additions, all reversible, none baked into textures:

- **cavity dirt** — an Ambient Occlusion node darkens inside corners, under sills, in shadow
  gaps and at the plinth, with a ramp that keeps the dirt warm rather than black;
- **splash zone** — a vertical gradient: the bottom ~0.8 m of every facade is dirtier than
  the top (measured behaviour of rain hitting a wall, and the single most convincing "this
  building is outdoors" cue);
- **edge wear** — a Bevel node dotted against the geometric normal gives a curvature mask;
  convex edges get slightly lighter and rougher, so low sun catches them.

Applied to lime render, board-formed concrete, travertine, paving, asphalt and timber.

### 2. Lighting (`setup_sun`)

v2 put the sun at azimuth 232°, which edge-lights the south facade and flattens it. The hero
render uses **elevation 22°, azimuth 205°**: front-left of the camera, so the glazing casts
a shadow pattern and every travertine pier has a lit face and a dark face. Sun 4.6 W at
0.85°, colour 1.0/0.855/0.70 (≈3600 K, late afternoon), sky fill at 0.42.

### 3. Camera (`HERO_CAMS`)

35 mm and 30 mm at a 1.65–2.2 m eye, `shift_y` 0.04–0.06 to keep verticals vertical, and
depth of field on a real stop (f/5.6–f/7.1) focused on the glazing line, not on infinity.
Aerial-perspective framing that shows the garden, the terrace and the pool in one shot.

### 4. Render (`setup_cycles`)

Cycles CPU, **144 adaptive samples** (threshold 0.005, min 32), OpenImageDenoise, 12 bounces
(10 transmission for the glazing), caustics off (they are the most expensive thing here and
the pool reads without them), light tree on, indirect clamp 8. 1920×1080, 16-bit PNG,
AgX + Medium High Contrast. Measured: 18.9 min per frame.

**Memory is the real limit on this machine.** Two renders in parallel did not "run slower",
they were OOM-killed together at 3.8 GB RSS each (`use_persistent_data` off, one process at
a time). 2560×1440 at 160 spp was abandoned for that reason, not for taste.

### 5. Compositing (`setup_compositor`)

Exposure → Lift/Gamma/Gain (cool shadows, warm highlights) → **Mist pass** aerial
perspective → glare (Fog Glow, threshold 1.6) → lens dispersion 0.008 → vignette 0.16 →
output. All reversible; nothing is crushed to hide lighting.

Blender 5.0's compositor is a node *group* and three of its nodes are not what they look
like. Verified by rendering and measuring, not by reading docs:

| node | gotcha |
|---|---|
| `CompositorNodeAlphaOver` | Factor 1 = **entirely the Foreground** (0 = Background) |
| `ShaderNodeMix` (RGBA) | blends toward **B** at Factor 1 |
| `CompositorNodeEllipseMask` | white **inside** the ellipse, so a vignette needs `1 - mask` |
| `CompositorNodeComposite/MixRGB/Math` | **no longer exist** in 5.0 |
| world volume as mist | dims the *sky* too (700 m of medium turned daylight into dusk) — use the Mist pass |

## Honest limits

- **No HDRI.** `archviz` and `lighting` both say "HDRI for exteriors"; there is no HDRI
  library on this machine and no way to fetch one, so the sky is a physical sky plus a
  procedural cumulus field. That is the single largest remaining difference from a
  commercial archviz plate.
- **Foliage is alpha cards.** Convincing at 5 m+, and the hero shots are 8–15 m, but at
  1 m a leaf spray shows its flatness.
- **The interior is v1 geometry** behind the glass, re-lit; it was not re-modelled.
- **144 samples, not the 512–2048 in the skill.** On 2 vCPU and 3.9 GB, a 1920×1080 frame at
  144 spp takes ~19 min; 512 spp is 67 min per frame *and* risks the OOM kill seen earlier,
  for a difference OIDN mostly removes.
- **Palms had to be moved.** Seen from the pool camera, a palm 4 m from a 30 mm lens put its
  trunk across the frame and left its card fronds hanging in the sky as detached paddles.
- **No people, cars or clutter** beyond the terrace furniture — real photos of buildings
  have humans in them, and that absence is felt even when it is not noticed.
- The aerial still carries the v2 background (ridges are silhouettes, no cloud shadows).
