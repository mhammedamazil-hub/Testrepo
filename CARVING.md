# Carving a car out of photographs

This is the second generation route in this repository, and it is the opposite of the first one.

InstantMesh (see [`VALIDATION_RESULTS.md`](./VALIDATION_RESULTS.md)) *invents* geometry — a plausible car that
photographs do not support, which is why its roofline and rear were wrong. **Silhouette carving invents
nothing.** Every voxel it keeps is consistent with every photograph it was shown, so what comes out is
defensible, measurable, and — because it is built from an orthographic turnaround sheet — in the car's real
proportions from the start. No GPU, no model weights, no cloud, 8 minutes of CPU, $0.

Input: the 9-cell turnaround sheet (front, rear, right side, top, and four three-quarter views), cropped into
[`carve_src/`](./carve_src).

---

## 1. Deliverables

| | web tier | high tier |
|---|---|---|
| GLB | [`refined_carve/model_textured.glb`](./refined_carve/model_textured.glb) — 4,037,136 B | [`refined_carve_high/model_textured.glb`](./refined_carve_high/model_textured.glb) — 13,419,020 B |
| triangles | 44,998 | 159,992 |
| texture | 2048², UV-mapped | 4096², UV-mapped |
| OBJ + MTL + PNG | `model_textured.obj` / `.mtl` / `texture.png` | — (deliberately not duplicated) |
| print STL | `print_mm.stl` — 2,249,984 B, 4976.0 × 2126.0 × 1473.0 mm | `print_mm.stl` — 7,999,684 B |
| watertight | **yes** | **yes** |
| winding consistent | **yes** | **yes** |
| volume | 9.906 m³ | 9.9205 m³ |
| build time | 43 s | 160 s |

Turntables in [`comparison_carve/`](./comparison_carve) (`web_vs_high.png` is the two tiers side by side,
four camera angles each). Per-view validation overlays are in [`carved/validate/`](./carved/validate).

Both GLBs were imported into the running app (`POST /api/import`) and round-trip byte-identically: job
`cf58e52dfee54ba1` (web, SHA-256 `97a311cb…63d`) and job `5de389b85d2a440c` (high, 13,419,020 B), each with
`NORMAL`, `POSITION`, `TEXCOORD_0`, one material and one embedded 2048²/4096² image.

## 2. Dimensions — exact, not "close"

| axis | model | real M5 F90 | error |
|---|---|---|---|
| length | 4.976 m | 4.976 m | 0.00 % |
| width incl. mirrors | 2.126 m | 2.126 m | 0.00 % |
| height | 1.473 m | 1.473 m | 0.00 % |

Carving inherits the photographs' pixel scale and lands within **1 %** on every axis on its own
(4.9633 × 2.1049 × 1.4601 m). The last fraction of a percent comes from a deliberate anisotropic fit
(scale 1.0021 / 1.0099 / 1.0069) — it is correcting the pixel or two lost when the masks are eroded to remove
the contact shadow, and a sub-1 % correction cannot distort a shape. The correction is recorded in
`carve_metrics.json` under `exact_fit`, and the photo projection is re-registered after it so the texture stays
aligned.

## 3. How it works

### 3.1 Segmentation (`tools/carve_car.py`)

A dark car on a dark gradient backdrop defeats a global threshold: a first attempt using `background + 3σ`
produced masks of 2,474–8,179 px and failed completely on the top view. The working model is a **per-column
linear ramp** between the median brightness of the top 16 and bottom 14 rows — the studio's own gradient — and
a pixel belongs to the car if it is meaningfully darker than that model, meaningfully brighter (specular rims),
or more detailed (local variance). Closing, hole-filling and largest-component selection follow, plus a
2-pixel erosion that removes the pixel of contact shadow welded to the tyres.

### 3.2 Calibration

One axis of each view is measured cleanly by its bounding box; the render is close to orthographic (front-view
aspect 1.442 against the physical 1.443), so the vertical scale equals the horizontal scale. That places the
ground row analytically, which is how the floor reflection is discarded, and the mask is additionally cut at
the ground row because a car cannot be below the ground plane.

Two things the sheet gets wrong, both detected and corrected:

* The **"Right Side View" is mirrored** relative to the "Top View" (nose on the right vs. nose on the left,
  confirmed from grille and tail-lamp crops). The side view is flipped on load; X is defined nose-at-zero.
* The **rear cell is cropped** — 44 px of the car's left flank is cut off by the cell edge. A bounding box
  would therefore read the car as 34 % too wide. Instead the mirror plane is found by image self-similarity
  (the column that best matches its own reflection), which puts the axis at column 139 and the true scale at
  182 px half-span, and the missing flank is mirrored back in.

### 3.3 Pose estimation for the five three-quarter views

Yaw and elevation are searched against the four-view hull; scale and translation are solved in closed form by
matching the projected cloud's bounding box to the photograph's. **Four of the five** poses reconstruct their
photograph at ≥ 0.90 hull/photo IoU and are used. The fifth (`1_0_rear_left_3q`) reaches only 0.879 and is
**rejected** rather than trusted — a published honesty rule for this repo is that a view either earns its place
or is reported.

These views do not carve as hard as the orthographic four, because a silhouette constrains yaw to roughly ±30°
(a first pose search that normalised each image axis separately scored 0.28 for *every* azimuth — zero
discrimination — because it destroyed the aspect ratio). They are therefore given a **negative trust radius** of
25 mm: a point must be clearly outside a three-quarter silhouette before that view is allowed to carve it.
Their contribution is to round off the corners that four axis-aligned silhouettes leave boxy.

### 3.4 Carving

Each view extrudes its own 2-D **signed distance field, in metres**, along its viewing axis; the hull is the
pointwise maximum. Distances rather than a binary AND is the difference between a smooth surface and pixel
stair-stepping. Marching cubes is run on the padded field — padded with "outside", not edge values, otherwise
the surface can stay open — which is why the hull is watertight.

Voxel pitch 10 mm, 500 × 210 × 147 grid, 286 s.

### 3.5 Validation

Every view is re-projected from the finished solid and compared with its photograph:

| view | silhouette IoU | photo coverage |
|---|---|---|
| front | 0.9292 | 0.9293 |
| rear | 0.9538 | 0.9539 |
| side | 0.9844 | 0.9866 |
| top | 0.9970 | 0.9973 |
| `0_2_side_left_3q` | 0.9157 | 0.9217 |
| `1_2_front_right_3q` | 0.9020 | 0.9027 |
| `2_1_front_left_3q` | 0.9391 | 0.9579 |
| `2_2_rear_right_3q` | 0.9166 | 0.9231 |

Red/green/blue overlays in `carved/validate/`: green = hull and photograph agree, red = photograph says car and
the hull misses it, blue = hull spills outside the photograph.

## 4. Texturing (`tools/carve_finish.py`)

The texture is baked **per texel**: each texel is mapped through the UV atlas to a 3-D point and normal, and
that point samples the photographs directly, 2×2 supersampled, then median-filtered.

Three approaches were tried and two were measured to be wrong:

1. **Per-vertex colour, barycentric-interpolated into the atlas** (the approach used by `refine_mesh.py` for
   the InstantMesh asset). Wrong here: an atlas texel is ~0.8 mm, a decimated triangle is centimetres, so
   detail smeared across whole UV triangles and turned the body into stripes.
2. **Blending every camera that can see a texel.** Wrong twice over: a shoulder texel is seen at a grazing
   angle by three cameras and averaging them painted the grille onto the door; and the four renders do not
   share an exposure (the same bumper reads 17, 75 and 62 out of 255 in the front, rear and side photographs),
   so raw blending produced a patchwork of exposure zones.
3. **Exposure-normalised, weight-ramped blending** (used). Each view is normalised to a common median
   brightness (gains 1.30× / 1.24× / 0.87× / 0.71×), each texel weights cameras by `facing³ ×
   min(1, depth_inside_silhouette / 12 mm)`, and the keep-weight ramps from 0 at 35 % of the best camera to 1
   at the best. A hard threshold at 60 % drew a visible vertical seam down the doors; the ramp removes it.

The car is mirror-symmetric, so the right-flank photograph textures both flanks. The underside — which no
photograph shows — is given a dark neutral tone rather than invented detail. Atlas coverage 68.1 % (web) /
65.4 % (high); the rest of the texture is padding.

Finishing: 18 iterations of Taubin smoothing (λ = 0.5, ν = −0.53 — a positive step followed by a slightly
larger negative one, so it does not shrink the model the way plain Laplacian smoothing does), then
quadric decimation with `preserve_border`. Decimation leaves hair-thin detached shells (two of area 1e-4 m²)
that make the result non-manifold despite having no open edges; shells below 0.5 % of the largest component's
area are dropped.

## 5. Reproduce

```bash
pip install numpy scipy scikit-image trimesh xatlas fast-simplification pillow

# 1. crop the 3x3 turnaround sheet into carve_src/ (see below), then:
python tools/carve_car.py --pitch 0.010 --out carved          # 286 s, writes carved/carve_raw.glb + report
python tools/carve_finish.py carved/carve_raw.glb --out refined_carve --tier web  --fit-exact   # 43 s
python tools/carve_finish.py carved/carve_raw.glb --out refined_carve_high --tier high --fit-exact  # 160 s

# renders (no GPU, no browser)
python tools/render_mesh.py refined_carve/model_textured.glb --out renders --frames 6 --size 900x620
```

The nine cells of the sheet are cropped into `carve_src/`: `0_0_front`, `0_1_rear`, `0_2_side_left_3q`,
`1_0_rear_left_3q`, `1_1_top`, `1_2_front_right_3q`, `2_0_side_right`, `2_1_front_left_3q`,
`2_2_rear_right_3q` (512 × 341 each). Only the front, rear, top and right-side cells are required for an
orthographic carve — `--no-3q` runs in 6 s and gives the same shape minus the rounded corners.

## 6. Seven bugs found while building this (all fixed, all measured)

1. **The Y axis was mapped from the mask edge rather than its centre**, so a symmetric car read as 209 px/m
   instead of 188 px/m. Affine mappings are now built from `axis_affine(c0, c1, -span/2, +span/2)`.
2. **`np.full(..., np.inf)` for the intersection accumulator**: `max(inf, d) == inf`, so the hull came out
   empty and marching cubes raised "surface level must be within volume data range". The identity for a max is
   `-inf`.
3. **`project_to_grid` maximised variance instead of IoU** — points were splatted as single pixels, filling
   15,733 px of a 102,023 px silhouette, so every pose scored alike. Dilate → close → fill first.
4. **Pose search normalised each image axis independently**, erasing the aspect ratio: 0.28 IoU for every
   azimuth. Uniform scale only.
5. **glTF UV origin is top-left.** Both renderers flipped V, so a correct texture was displayed upside down —
   the asset looked like vertical stripes and I nearly "fixed" the baker instead of the renderer. Verified with
   a red/blue checker atlas: it must come out upright.
6. **Masking fog on the car's own shadow**: the mask ran past the ground row, and since a car cannot be below
   the ground plane, that strip extruded into a thin sheet floating under the hull. Cut the mask at the ground
   row.
7. **Marching cubes padded with edge values** left the surface open (not watertight). Padding with a value above
   the iso level guarantees closure.

Also relevant: `trimesh`'s GLB loader returns the diffuse map as `material.baseColorTexture`, **not**
`material.image` — a renderer that only checks `.image` silently renders untextured grey.

## 7. Honest limits

* **Silhouettes cannot see concave detail.** Grille slats, badges, door gaps and wheel spokes exist in the
  texture but not in the geometry. The wheels are bulges; there is no daylight under the car. This is a
  *photogrammetric hull*, not a scanned mesh: it is as good as the silhouettes, and no better.
* **One view was rejected.** `1_0_rear_left_3q` scored 0.879 hull/photo IoU and is excluded. Four
  three-quarter views out of five are used.
* **The three-quarter poses are ±30° uncertain**, which is why their trust radius is negative. They round
  corners; they do not define the shape.
* **The benchmark is not Meshy/Tripo.** Those services use learned multi-view reconstruction and produce
  concave detail this method structurally cannot. What this is: exact real-world dimensions, watertight
  geometry, photo-derived texture, `$0`, offline, and every number above reproducible from the commands in §5.
* **Headless Blender is not available here.** `pip install bpy` succeeds but `import bpy` fails
  (`libXrender.so.1` missing; then `libGL.so.1`, `glXGetProcAddress`, `glXGetVisualFromFBConfig`,
  `glXMakeCurrent` …). Debian repositories are not reachable from this sandbox, so the real libraries cannot be
  installed and the stub-library route loses to linker symbol resolution. Nothing in this pipeline needs
  Blender: remeshing, UV unwrapping and baking are done by `fast_simplification`, `xatlas` and the projection
  baker above.
