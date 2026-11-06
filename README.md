# InstantMesh feasibility audit + image-to-3D app

This repository answers one question honestly: **can InstantMesh run here, and if not, what is the cheapest
path to a genuine image-to-3D asset?**

## 🏠 Modern villa (fully furnished, procedural)

**[`VILLA.md`](./VILLA.md)** — a 19 × 12.5 m single-storey modern villa: 3 bed + 2 bath,
open-plan living / dining / kitchen, every room furnished and styled. Built entirely from
code in Blender (bpy 5.0.1) — procedural PBR textures, 113 parametric furniture pieces,
Cycles stills, a camera walkthrough, an editable `.blend`, a whole-house GLB and one
pivoted GLB per furniture piece. Cost **$0**.

## 🎮 Villa Garden — a playable APK of the villa

**[`android/game/README.md`](./android/game/README.md)** — a first-person game built out of
the villa model: eight orbs scattered over the 87 × 84 m garden, a timer, a thumb stick.
Blender makes the assets, `tools/villa_pack.py` packs them **and bakes the sun and ambient
occlusion into the vertices**, `tools/game_level.py` bakes the collision level from the actual
triangles, and a ~1 900-line C++/GLES2 renderer draws it at up to 1080p with wind, moving
pool water, reflected glazing, bloom and god rays. GitHub Actions builds the APK.

**[⬇ Download `villa-garden.apk`](https://github.com/mhammedamazil-hub/Testrepo/releases/tag/villa-garden-v5)** (≈ 29 MB, Android 5.0+, phone or tablet).

## 🎛️ Blender skill system (13 local skills + 17 vendored)

**[`skills/README.md`](./skills/README.md)** — the router. **Read a skill's `SKILL.md`
before every Blender operation.** Local skills cover reference measurement, spec-driven
blockout, parametric automotive bodies, hard-surface detail/repair, glass/paint/surface
materials, lighting rigs without HDRI, camera composition, render planning, texel audit and
two QA gates (multi-view self-critique, export round-trip verification).

- **[`skills/WORKFLOW.md`](./skills/WORKFLOW.md)** — the 19-step modelling procedure, the
  photorealism rules and the self-critique loop.
- **[`docs/BLENDER_SKILLS_AUDIT.md`](./docs/BLENDER_SKILLS_AUDIT.md)** — environment audit,
  the eight researched repositories and their verdicts, real test numbers and honest limits.
- **[`skills/vendor/ATTRIBUTION.md`](./skills/vendor/ATTRIBUTION.md)** — MIT attribution for
  the vendored `EL4CTEO/blender-skills` subset and the one local patch.

## Read this first

**[`SANDBOX_INSTANTMESH_AUDIT.md`](./SANDBOX_INSTANTMESH_AUDIT.md)** — full technical audit: verified
sandbox environment, official model requirements (weights, VRAM, deps, pipeline, limits), every execution
strategy tested, network restrictions, costs, recommended architecture, next steps.

### Short version

| | |
|---|---|
| Sandbox CPU / RAM / disk | 2 logical (1 physical) vCPU · 3.8 GiB RAM, no swap · 20 GB free |
| GPU / CUDA / PyTorch | **none / none / not installed** |
| Egress | GitHub + PyPI ✅ · **Hugging Face, Replicate, Colab, Kaggle ❌ (TLS SNI blocked)** |
| Native inference here | **impossible** — no GPU *and* no way to fetch the 7.3 GB of weights |
| Free path to a real asset | official ZeroGPU Space (5 GPU-min/day) or the Colab/Kaggle notebook (< $0) |
| Paid path | Replicate `aryamansital/instant_mesh` ≈ **$0.14/run** |

No fake 3D was produced. The only mesh generated in-sandbox came from the `mock` provider and every artifact
is named `SIMULATED_NOT_AI.*`.

## 🔧 CPU refinement pipeline

**[`REFINEMENT.md`](./REFINEMENT.md)** — `tools/refine_mesh.py` repairs and upgrades the generated asset
offline: fixes Meshy's inward-facet warning, corrects the 36%-too-tall / 56%-too-wide proportions to real
M5 dimensions, bakes a real UV texture, adds normals, and exports print-ready STL + web GLB + engine OBJ.
Before/after renders in [`comparison/`](./comparison), deliverables in [`refined_web/`](./refined_web) and
[`refined_high/`](./refined_high).

## 🏀 Photoreal basketball — full PBR material

**[`BASKETBALL.md`](./BASKETBALL.md)** — a size-7 ball built to be looked at close up: analytic seam grooves
cut into the mesh, a pebble grain synthesised on the sphere, and a complete PBR stack (base colour + normal +
ORM) that survives the trip into a glTF viewer.

| | |
|---|---|
| diameter | **241.86 mm**, circumference 760.3 mm, watertight |
| seams | 5.2 mm wide × **1.9 mm deep grooves in the geometry**, 8 panels from four great circles |
| grain | 24,000 pebbles at a 2.1 mm pitch, 0.34 mm relief in the normal map |
| web GLB | 20,480 tris, 2 k maps, **3.07 MB** |
| high GLB | 81,920 tris, 4 k maps, **9.98 MB** |
| runtime / cost | 6 s / 22 s, CPU only, **$0** |

Renders, a 30-frame turntable and a contact sheet in [`basketball/renders/`](./basketball/renders).

## 🪨 Photo carving — geometry the photographs actually support

**[`CARVING.md`](./CARVING.md)** — the opposite approach to generation: carve the car out of the 9-view
turnaround sheet so nothing is invented. Four orthographic silhouettes plus four pose-estimated three-quarter
views are intersected in signed-distance space (voxel pitch 10 mm), marched to a **watertight** surface, then
textured by projecting the photographs per texel through a UV atlas.

| | |
|---|---|
| dimensions | **4.976 × 2.126 × 1.473 m** — the real M5 F90, to the millimetre |
| silhouette agreement | front 0.929 · rear 0.954 · side 0.984 · top 0.997 · 3/4 views 0.90–0.94 IoU |
| web tier | 45k tris, 2048² texture, 4.0 MB GLB, watertight |
| high tier | 160k tris, 4096² texture, 13.4 MB GLB, watertight |
| runtime / cost | 286 s carve + 43 s bake, CPU only, **$0** |

Deliverables in [`refined_carve/`](./refined_carve) and [`refined_carve_high/`](./refined_carve_high),
turntables in [`comparison_carve/`](./comparison_carve), per-view IoU overlays in
[`carved/validate/`](./carved/validate).

## ✅ Real generation achieved

**[`VALIDATION_RESULTS.md`](./VALIDATION_RESULTS.md)** — a genuine InstantMesh mesh of a BMW M5 was produced
through the official ZeroGPU Space, driven by GitHub Actions, for **$0**. 1.22 MiB GLB, 31,906 vertices,
63,620 triangles, verified by an independent software renderer. Artefacts in [`ci_results/`](./ci_results).

Known shortfall: the Space exports **vertex colours, not a texture map** — use the Colab notebook with
`--export_texmap` for a textured mesh.

## 👉 Next action

**[`RUN_VALIDATION.md`](./RUN_VALIDATION.md)** — the 3-click Colab run that produces the real mesh.
Nothing else in this repo can generate a genuine asset from here: the sandbox has no GPU and no route to
one. Everything needed on this side (notebook, verifier, import endpoint) is built and tested.

## What's in here

| Path | Contents |
|---|---|
| `SANDBOX_INSTANTMESH_AUDIT.md` | the audit (Phases 1–5) |
| `app/` | FastAPI + vanilla-JS image-to-3D app: upload, progress, 3D preview, GLB/OBJ downloads, provider abstraction |
| `app/server/providers/` | `hf_space` · `replicate` · `local_gpu` · `mock` |
| `notebooks/instantmesh_free_gpu.ipynb` | official pipeline on a free Colab T4 / Kaggle GPU → real GLB |
| `space/` | your own ZeroGPU Gradio Space with a clean single-call `/generate` API |
| `integrations/local_gpu/instantmesh_generate.py` | GLB export for the official CLI (which only writes OBJ) |
| `notebooks/instantmesh_real_validation.ipynb` | the free-T4 inference run + metrics collection |
| `tools/verify_mesh.py` | stdlib GLB inspector **and software renderer** (evidence without a browser) |
| `tools/make_test_mesh.py` | textured fixture that proves the verifier itself works |
| `tools/carve_car.py` | segment + calibrate the turnaround sheet, estimate 3/4-view poses, carve the visual hull |
| `tools/carve_finish.py` | Taubin smooth, decimate, xatlas unwrap, per-texel photo bake, GLB/OBJ/STL export |
| `tools/basketball.py`, `tools/ball_material.py`, `tools/pebble_field.py` | parametric basketball: seam layout, pebble field, PBR map bake |
| `tools/ball_render.py` | ray tracer with GGX specular, environment lighting and a studio sweep |
| `basketball/`, `basketball_high/` | the ball, web and high tier |
| `tools/render_mesh.py` | dependency-free triangle rasteriser with per-pixel texturing (the verifier's renderer subsamples big meshes and samples textures per triangle) |
| `carve_src/` | the nine cells of the turnaround sheet |
| `refined_carve/`, `refined_carve_high/` | carved deliverables (web and high tier) |

```bash
pip install -r app/requirements.txt
python -m uvicorn app.server.main:app --host 0.0.0.0 --port 8000   # mock mode by default
python -m pytest app/tests -q                                      # 28 tests
```

InstantMesh is © TencentARC, Apache-2.0. This repo is an independent client and bundles no weights.
