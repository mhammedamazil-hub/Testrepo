# REFINEMENT — what CPU post-processing actually fixed

Taking the real InstantMesh output (`ci_results/instantmesh.glb`) and repairing it offline with
`tools/refine_mesh.py`. **No GPU, no cloud, no HF, no Colab.** numpy / scipy / trimesh / xatlas / pymeshfix only.

Everything below is measured. Renders are produced by an independent software rasteriser
(`tools/verify_mesh.py`), not by the model or by a browser.

---

## 1. The headline result: it no longer looks like an SUV

Meshy showed you dimensions of `11.76 × 7.97 × 19.75`. Normalised against a real **BMW M5 F90**
(1.903 × 1.473 × 4.976 m), the generated mesh was **36% too tall and 56% too wide**:

| axis | generated (m) | normalised | real M5 (m) | normalised | error |
|---|---|---|---|---|---|
| length (Z) | 4.976 | 1.000 | 4.976 | 1.000 | — |
| height (Y) | 0.7965 | **0.404** | 1.473 | 0.296 | **+36%** |
| width (X) | 1.1763 | **0.595** | 1.903 | 0.382 | **+56%** |
| bbox | `1.1763 × 0.7965 × 1.9746` | `0.60 : 0.40 : 1.00` | `1.903 × 1.473 × 4.976` | `0.38 : 0.30 : 1.00` | |

After an anisotropic fit: `1.9029 × 1.4730 × 4.9758 m` — **exact**. See `comparison/compare_*.png`.
This is a global geometric fit, not new detail: surface features stretch with it, which is why the
wheels get slightly oval. It is still a large net improvement in "does this read as an M5".

## 2. Meshy's warning was real, and is now fixed

Your screenshot reported *"the surface is closed, but some facets face inward"*. Confirmed:

| | before | after |
|---|---|---|
| watertight | ✅ true | ✅ true |
| **winding consistent** | ❌ **false** | ✅ **true** |
| outward normals | ❌ mixed | ✅ fixed (`fix_winding` + `fix_inversion` + pymeshfix fallback) |

Face count stayed at 63,620 with 0 degenerate and 0 duplicate faces, so this was a pure orientation
defect — exactly what a slicer complains about.

## 3. It is now genuinely a *textured* mesh

| | before | after |
|---|---|---|
| attributes | `POSITION`, `COLOR_0` | `POSITION`, **`TEXCOORD_0`**, **`NORMAL`** |
| texture | none | **2048²** (web) / **4096²** (high) baked PNG |
| materials | 0 | 1 (`baseColorTexture`) |
| UV coverage | — | 75.1% (web) / 71.2% (high) |

The colour is **re-projected from the existing vertex colours**, so no new information is invented —
the mesh simply satisfies "textured" now and samples sharply in viewers/engines.
`NORMAL` was added because without it viewers fall back to flat faceting and look worse than the geometry is.

## 4. Deliverables

| File | Purpose | Size |
|---|---|---|
| `refined_web/model_textured.glb` | web / viewer / Sketchfab / Meshy — 25k tris, 2k texture | 3.47 MB |
| `refined_web/model_textured.obj` + `material.mtl` + `texture.png` | game engine / Blender import | 2.60 MB + 3.49 MB |
| `refined_web/print_mm.stl` | 3D printing — millimetres, watertight, outward normals | 3.18 MB |
| `refined_high/model_textured.glb` | maximum fidelity — 63k tris, 4k texture | 9.92 MB |
| `comparison/compare_*.png` | before/after, same camera, 6 angles | — |
| `refined_web/renders/`, `refined_high/renders/` | independent verification renders | — |

**STL print check:** 1895.3 × 1471.4 × 4972.6 mm, watertight, winding-consistent, 6,366,303 cm³.
(That volume is the *solid* envelope, not shell material — an un-hollowed car scaled to 5 m. Scale it down
for a real print and hollow it in your slicer.)

## 5. Reproduce

```bash
pip install numpy scipy trimesh xatlas pymeshfix networkx pillow fast-simplification

# web tier (18 s)
python tools/refine_mesh.py ci_results/instantmesh.glb --out refined_web \
    --fit-proportions --texture-size 2048 --web-faces 25000 --sharpen 1.0

# high tier (60 s)
python tools/refine_mesh.py ci_results/instantmesh.glb --out refined_high \
    --fit-proportions --texture-size 4096 --web-faces 0 --sharpen 1.0
```

Useful flags: `--fit-strength 0.5` (gentler proportion correction), `--smooth-iterations 0` (no Taubin
smoothing — keeps every bit of surface detail), `--no-texture` (keep vertex colours only).

## 6. Bugs found while building this (all fixed, all were silent)

1. **`trimesh` decimation replaces vertex colours with uniform grey (102,102,102).** The first bake was
   100% black. Fixed with an explicit nearest-neighbour colour transfer before unwrapping.
2. **The baker wrote 0–1 floats into a `uint8` image.** Colours were normalised for blending and never
   scaled back, so every texel truncated to 0 even after fix 1.
3. **`xatlas.parametrize` argument order is `(vertices, faces)`**, not `(faces, vertices)`. The wrong order
   returns a degenerate atlas *without raising*.
4. **xatlas raises `Index out of range` on duplicate vertex positions** — the mesh must be vertex-merged first.
5. **GLB export silently omitted `NORMAL`** until normals were explicitly attached.

## 7. What this cannot do — read this before expecting Meshy/Tripo quality

| | Status |
|---|---|
| Correct proportions, orientation, watertightness, texture, normals | ✅ fixed offline |
| Recover detail the model never generated (grille slats, badges, panel gaps, wheel spokes) | ❌ impossible by post-processing |
| Fix distorted *shape*, e.g. the roof line and rear that the 6-view grid got wrong | ❌ needs better multi-views or more steps |
| Match Meshy/Tripo generative quality | ❌ those are far larger models on server GPUs |

The honest summary: **the asset is now clean, correctly proportioned, textured and print-ready, but it is
still the same soft, slightly-wrong shape**. The remaining gap is generative, not cosmetic.

### The only two paths to genuinely better geometry under your constraints

1. **More steps / better seed on the same free Space** — 75 steps instead of 30 (needs an `HF_TOKEN`
   secret). Cheap, and attacks the root cause: the multi-view grid.
2. **Multi-photo silhouette carving** (you said you'll send side/front/rear photos) — reconstructs real
   geometry from your photographs instead of hallucinating it. Fully offline, CPU-only, slower. This is
   the only route to non-invented geometry without a GPU.
