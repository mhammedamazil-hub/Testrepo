# Villa v2 — the exterior rebuild

v1 was geometrically correct and visually bad. Rendered from the garden it was a white box
with a black fascia, a flat khaki plane and trees made of green spheres. This is the rebuild,
and — more usefully — the record of *why* it looked bad and what actually fixed it.

All numbers and images below come from renders produced in this sandbox (Cycles, CPU,
2 vCPU). Nothing here is a mock-up.

---

## What was actually wrong (diagnosis before work)

| Symptom | Real cause | Fix |
|---|---|---|
| Everything looked white/washed out | v1 set the physical sky to **strength 1.0** and a 4.6 W sun, then exposed to −0.15. Walls, paving and sky all landed in the top of the AgX curve: no shadow contrast anywhere | sky dome 0.30, sun 4.4 with a warm low angle, and **per-view exposure** (exterior −0.25 / interior +0.55) |
| The house read as one flat volume | no plinth, no piers, no reveals, no soffit, no coping, no downpipes — literally one box with a fascia band | `arch_v2.facade_extras()` + `arch_v2.roof()` |
| Trees looked like billiard balls | `furniture.tree()` was a UV sphere with a green texture | `vegetation.py`: alpha-cutout leaf **spray** cards |
| The lawn was khaki | the `grass` texture was brown-olive **and** the material had the default 0.5 specular, so the lawn reflected the sky and desaturated | new `lawn_v2` texture + a per-material **specular** table |
| Interior was a dark box | the only interior light was 55 downlights tuned against a sky that no longer existed | interior practicals ×1.35 + a **terrace bounce card** + an entry bounce card |
| The garden had no composition | plants were sprinkled, not placed | a planting plan with a hero view kept clear (see below) |

Each of those was measured, not guessed: pixel means before/after, raytraces to find out
which object was blocking the camera, and a 4-way render comparison for exposure/look.

---

## New modules

| File | What it does |
|---|---|
| `villa_src/tex_gen2.py` | 40+ new maps: **leaf spray cards with alpha** (4 species), single-leaf and grass-blade cards, bark, lime render, board-formed concrete, travertine strips, stone paving, asphalt, gravel, timber slats, water ripple normal, **lawn** |
| `villa_src/vegetation.py` | card-based plants: `broadleaf`, `olive`, `cypress`, `palm`, `shrub`, `hedge`, `ornamental_grass`, `agave` — clump-scattered sprays over a dark inner canopy, joined per plant |
| `villa_src/arch_v2.py` | facade articulation (plinth, shadow gap, travertine piers, sills, entry canopy with battens, slatted soffit, downpipes, chimney), layered roof with parapet + coping, site build-up (terrace with border course, pool with coping/basin/water, gravel margins, planting beds, driveway, gate piers, forecourt, garden wall, stepping path, distant ridge) and the **planting plan** |
| `villa_src/cameras_v2.py` | 12 composed views: 6 exterior (garden hero, pool, entry, dusk, aerial, terrace detail) and 6 interior at 1.2 m eye height with 21–30 mm lenses |
| `villa_src/build_v2.py` | assembles v1 shell + furniture, swaps the v1 site for v2, lights it, sets per-view exposure, renders, saves `villa_v2.blend` |
| `villa_src/mats.py` (extended) | 30 new materials, alpha-cutout card shader with **translucency mix**, low-frequency **weathering multiply** on facades, per-material **specular** table |

---

## The techniques that made the difference

**Foliage = sprays, not leaves.** One card carries a whole twig (8–13 leaves, alpha-cutout).
A canopy is then a few hundred cards, not thousands, and the silhouette has the irregular,
airy breaks of real foliage. Single leaves look like confetti; opaque quads look like
plastic snow.

**Clumps, not shells.** Canopy cards are scattered as small clumps over an ellipsoid, with a
second, darker, denser clump cloud *inside* to occlude light. A single shell reads as a
powder puff; a solid sphere inside reads as a golf ball. Both were rendered and rejected.

**Foliage transmits light.** Card materials are a 0.30 mix of diffuse and translucent, and
the albedo is deliberately dark (0.6–0.88 of the leaf colour) because a leaf reflects only
10–25 % of light. Bright leaves render as pale flowers.

**Specular is not a constant.** Grass, soil, gravel and foliage scatter rather than reflect.
With the default 0.5 specular the lawn turned neutral khaki (measured mean RGB 129/135/112
instead of green); at 0.12 it renders green (70/80/62 → 42/58/33 as a saturated lawn).

**Two exposures, not one.** Exterior and interior are 5–7 stops apart. One exposure either
blows out the garden or buries the rooms. `_setup_view()` re-exposes and re-balances the
practical lights per shot.

**Bounce cards.** Real interiors are lit by the whole sunlit terrace. An area light outside
the south glazing (900 W, 12 × 3.2 m) is what stops the rooms from being a dark box with a
bright window.

**Composition is a constraint, not a taste.** The hero camera was blocked by two olives at
6 m. The fix was found by raytracing through the camera frame to name the offending objects
(`olive_2`, `olive_12`), then moving them out of the sight line — trees now frame the view
from the sides and never stand between the camera and the glass.

**The horizon needs landscape.** A ground plane meeting the sky is an obvious CG tell, so
there is a deterministic two-band ridge 150–240 m out.

**The sky is geometry too.** A physical sky on its own renders as a flat pale gradient — the
loudest "this is CGI" tell in any exterior. `_sky_clouds()` mixes a noise field sampled along
the view direction into the world colour: cumulus that converge at the horizon for free (it
is the perspective of the dome), one texture lookup, and they also break up the environment
light so surfaces are no longer lit by a perfectly uniform dome. Cloud frequency is the whole
trick: scale 2.4 gives one blurry smear (nothing), scale 26 gives TV static, scale 9 reads as
weather.

**An entrance needs depth.** The v1 front door was a flat walnut panel on a blank wall, which
is why the east elevation read as a garage. The door is now closed and set 0.19 m inside the
outer face, lined with cedar jambs and head, with a threshold, a vertical pull bar and a
1.45 m canopy on two steel posts with a dark fascia and a timber soffit. The recess is what
makes the shot: it produces the one strong shadow on that elevation.

**Metal on a horizontal surface is a mirror.** The gate-pier caps were polished aluminium;
facing straight up at a bright sky they rendered as glowing white boxes. Caps are now dark
non-metallic stone — the same lesson as the khaki lawn, one storey up.

---

## Deliverables

| File | What |
|---|---|
| `villa_v2/villa_v2.blend` | editable scene: v1 shell + furniture + v2 exterior, garden, lights, cameras |
| **`villa_v2/villa_v2.glb`** | **whole-site GLB, 51.9 MB, 1024² textures, 723 meshes, 599 k tris, Y-up** |
| **`villa_v2/villa_v2_web.glb`** | same model at 512² textures, 40.9 MB — use this for web viewers |
| `villa_v2/glb_report.json` | the export verification (source vs re-imported) |
| `villa_v2/*.png` | renders (1440 × 810, Cycles, 96 spp, denoised) |
| `villa_v2/contact_sheet.png` | all 8 shots on one page |

The two GLBs and the `.blend` are **not committed** (120 MB of artefacts); they are
regenerated by the one-liner below. Everything else in `villa_v2/` is committed.

```bash
# regenerate the GLBs + verification (about 30 s)
.venv/bin/python tools/bpy_run.py villa_src/export_v2.py -- --out villa_v2 --tex 1024
.venv/bin/python tools/bpy_run.py villa_src/export_v2.py -- --out villa_v2 --tex 512 --name villa_v2_web.glb
```

### GLB verification (measured, not assumed)

| Check | Result |
|---|---|
| Re-import into an empty scene | 723 meshes, 599,282 tris — identical to the source |
| Bounding box after re-import (Y-up) | `[700.0, 315.0, 19.75]` m — identical |
| Materials | 75 / 75 |
| Images | 110 packed (104 JPEG + 6 PNG, from 113 material slots) |
| Foliage alpha | 6 materials, `alphaMode: MASK`, `alphaCutoff 0.4`, `doubleSided: true` |
| Render from the GLB itself | `/tmp` test render: the house, shrubs, hedges and treeline all read correctly from the imported file |

Three export bugs had to be fixed to get there, all found by opening the file:
1. `export_image_format='JPEG'` in v1 silently drops alpha → every leaf card becomes a
   solid quad (trees turn into green boxes). The exporter does keep PNG for images that
   *have* alpha, so JPEG is fine — it was verified, not assumed.
2. Blender 5.0 writes `alphaMode: BLEND` for any material whose Alpha input is linked,
   and `blend_method='CLIP'` no longer changes that (checked across three
   blend/render-method combinations). BLEND on foliage means unsorted transparency and
   popping leaves, so `patch_alpha_mask()` rewrites the GLB's JSON chunk to `MASK`.
3. The v1 roof slab was still in the scene and hid the new parapet from above; the purge
   then over-reached and deleted the **interior ceiling** too (rooms would have had no
   ceiling in the export). Both fixed and re-rendered.
| `villa_src/tex_gen2.py` | regenerate every new texture (`python -m villa_src.tex_gen2`, ~20 s) |
| `villa_src/build_v2.py` | rebuild + render |

### Rebuild

```bash
.venv/bin/pip install bpy numpy pillow trimesh && python3 tools/blender_stub.py
.venv/bin/python -m villa_src.tex_gen       # v1 maps  (~35 s)
.venv/bin/python -m villa_src.tex_gen2      # v2 maps  (~20 s)
.venv/bin/python tools/bpy_run.py villa_src/build_v2.py -- \
    --render --save --res 1440 810 --samples 96 --out villa_v2
```

Render times measured on 2 vCPU: 900 × 506 @ 24 spp ≈ 35–46 s per view; 1440 × 810 @ 96 spp
≈ 4–7 min per view.

---

## Honest limits

- **Still procedural.** No HDRI, no photographic textures: this environment has no access to
  Poly Haven or ambientCG. Everything is generated by numpy with normal + roughness maps.
- **Foliage is cards.** Convincing at 5 m and beyond; at 1 m a leaf spray shows its flatness.
  For a close-up you would model hero branches or use a scanned asset.
- **No humans, cars or clutter.** Empty exteriors read as "CG" partly because real photos
  have stuff in them.
- **Ridges are silhouettes**, not landscape: no haze/bloom pass, no atmospheric perspective
  beyond what the sky texture gives.
- **The interior is v1 geometry** with better light; it has not been re-modelled.
- **The pool water** is a ripple normal map on a flat plane — no refraction through depth, no
  caustics.
- **`hero_aerial` shows the roof as a bare plane.** There is a membrane, parapet, coping,
  chimney and flues, but no ballast, rooflights, plant or AC units, so from above the
  building reads as an empty tray. Roof clutter is the next thing I would add.
- **Trees crop at the top of the aerial** and read as dark silhouettes against a bright lawn:
  card canopies have no self-shadow variation at that scale.
- **`hero_entry` is the weakest exterior.** The east elevation faces away from the sun, so it
  is lit by sky and a 420 W bounce card. It is plausible archviz lighting, not great archviz
  lighting; the fix would be a second sun or a full HDRI, which the environment cannot
  produce.
- **Clouds are procedural**, so they are plausible rather than specific — no sun shafts, no
  cloud shadows on the ground.
- **The GLB carries no cameras, lights or world.** A viewer supplies its own sky and IBL, so
  the model in a browser looks flatter and more evenly lit than these renders. It is also
  598 k triangles: fine on a desktop GPU, heavy for mobile.
- I did not re-render the walkthrough video for v2.
