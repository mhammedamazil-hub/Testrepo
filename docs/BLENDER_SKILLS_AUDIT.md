# Blender Skill System — Audit, Research and Test Record

Date: 2026-11-03. All figures below were measured in this sandbox, not copied from upstream
documentation. Anything that could not be tested is listed as untested, not as working.

---

## 1. Environment audit (Phase 1)

| Item | Result |
|---|---|
| Blender | **5.0.1** (`bpy.app.version_string == "5.0.1"`, `(5, 0, 1)`) |
| Distribution | `bpy` wheel on PyPI. `bpy.app.binary_path` is **empty** — there is no `blender` executable |
| Python | CPython 3.11.2, x86_64 Linux |
| CPU / RAM / disk | 2 cores, 3.9 GB RAM, ~19 GB free |
| GPU | none; Cycles falls back to CPU |
| Render engines | `bpy.types.RenderEngine` lists `BLENDER_EEVEE`; **Cycles is an addon** (`cycles` present in `bpy.context.preferences.addons`) and works on CPU |
| Addons available | `bl_pkg, cycles, io_anim_bvh, io_curve_svg, io_mesh_uv_layout, io_scene_fbx, io_scene_gltf2, pose_library` |
| Import/export ops | glTF 2.0, FBX, OBJ (`wm.obj_import/export`), STL, USD |
| Python modules present | numpy, PIL, trimesh, requests |
| Python modules **missing** | scipy, imageio, skimage, cv2, matplotlib, pygltflib, open3d, fast_simplification |
| OpenGL | stub `libGL` only; `glXQueryExtension` is **absent** → every Workbench/EEVEE render crashes |
| Network | `pypi.org` reachable; `raw.githubusercontent.com`, `ambientcg.com`, `polyhaven.com` **unreachable** → no HDRI, no textures, no sample assets |

### Consequences that shaped the build
1. Everything runs through `tools/bpy_run.py`, which boots `bpy` in-process, sets
   `LD_LIBRARY_PATH` to the GL stub, optionally loads a `.blend`, and collects `@@JSON@@`
   result lines. `--selftest` renders a frame (17,852 B) and exports a GLB (24,816 B) in 1.1 s.
2. Cycles only. The vendored `review_shots.py` (Workbench) and `render_batch.py` (EEVEE path)
   cannot run here; a local Cycles-based replacement (`qa-render-review`) was written.
3. All materials are procedural — there is no way to fetch a texture or an HDRI.
4. Render planning matters: 2 cores means a careless 4K shot is an hour.

---

## 2. Repository research (Phase 2)

Method: cloned every candidate, read the README **and** the source, checked licence, Blender
compatibility, headless behaviour, dependencies, overlap and actual usefulness. Descriptions
were not trusted.

| Repo | Licence | What it actually contains | Headless? | Verdict |
|---|---|---|---|---|
| `EL4CTEO/blender-skills` | MIT | 28 skills, real Python in `skills/*/scripts` (e.g. `apply_stack.py`, `bake_maps.py`, `gn_builder.py`, `export_asset.py`). Targets 5.2. Driver `run_in_blender.py` shells out to a `blender` binary | yes, **but** needs the `blender` exe (absent here) | **Adopted**: 17 skills vendored, one API patch; scripts are called directly through `bpy_run.py` |
| `RobLe3/cc-blender-skill` | MIT | 30 `SKILL.md` + knowledge docs, **no scripts**; every procedure is "call the Blender MCP server" | no | Rejected: MCP-centric, violates the no-unnecessary-MCP constraint, and adds nothing runnable |
| `dcc-mcp/dcc-mcp-blender` | MIT | MCP server scaffolding + 2 skills | no | Rejected: infrastructure only, no modelling knowledge |
| `hotspoons/blender-agent` | (app) | A self-hosted agent application plus ~8 short skill texts (`boolean-modeling`, `fillets-and-bevels`, `kitbash-axis-stacking`, `make-manifold`, `lighting-setups`, `texturing-basics`, `animating-basics`) | no | Not vendored: it is an app, and the skill texts duplicate what the adopted set covers better |
| `pedcorr/uv-toolkit` | **GPL-3.0** | Blender addon (4.2+), MaxRects packing, seam tools — operator/UI driven | no | Not vendored: GPL-3.0 into an MIT tree plus a UI-only workflow. Noted as an optional interactive addon |
| Poly Haven / ambientCG | — | asset CDNs | — | **Unreachable** (network blocked) |
| `KhronosGroup/glTF-Sample-Assets` | — | 1.79 GB of conformance models | — | Unreachable and oversized; not used |

Overlap analysis: the adopted set covers hard-surface, retopo/UV, sculpting, GN, baking,
rendering, scene setup and export as *method*; what it did not provide was measurable,
headless-executable QA, proportion gating and material systems for this build. That gap is
what `skills/local/` fills.

---

## 3. What was built

**Vendored (17 skills, 552 KB, 38 scripts, MIT)** — see `skills/vendor/ATTRIBUTION.md`.

**Original local skills (13):**

| Skill | Purpose | Tested with |
|---|---|---|
| reference-analysis | measure a reference, proportion gate | a 4500 mm test image: extent 4500.0, aspect 2.6502 |
| modeling-blockout | JSON-spec blockout with drift + envelope checks | envelope `[4.5, 1.9, 1.42]`, drift `[0, 0, 0]` |
| modeling-automotive | lofted body + greenhouse + arches + wheels | sedan render 700x394 @32 spp, 5/5 proportion ratios pass |
| modeling-detail | audit / repair / grooves / bevel stack | found 283 non-manifold edges + inverted normals in our own loft; repair → `MESH SOUND` |
| materials-glass | 6 glass kinds | 6/6 `ok: true` |
| materials-automotive-paint | 6 paint kinds | 6/6 `ok: true` |
| materials-surfaces | 8 surface kinds | 8/8 `ok: true` |
| materials-imperfections | wear/dust/grime/scratch/fingerprints | applied twice → one node group (idempotent) |
| lighting-studio | 4 rigs + emissive cards | 4/4 `ok: true` |
| camera-composition | framing, lens, DOF, ortho, thirds guide | perspective + ortho renders inspected |
| render-optimize | two-point calibration → plan | 0.348 s overhead, 0.00036 s/sample·kpx |
| uv-texel-audit | density, utilisation, stretch, overlaps | Ball 1757 px/m, Box 853 px/m, 0 overlaps |
| qa-render-review | 4-view Cycles review + contact sheet | `verdict PASS` |
| qa-export-verify | reopen and compare an export | 972 → 972 tris, 0.00 % delta, `EXPORT VERIFIED` |

Support: `tools/bpy_run.py`, `tools/_bpy_boot.py`, `skills/local/_shared/skill_common.py`,
`skills/tests/probe_skills.py` (import tier + functional tier), `skills/tests/visual/material_grid.py`.

---

## 4. Test evidence and honest failures

The probe matrix (`skills/tests/probe_skills.py`) runs two tiers: import + `--help` for every
script, and a curated functional run on a purpose-built scene. `probe_report.json` holds the
per-script result.

**Notable bugs this testing caught (all fixed):**
1. `bpy_run` did not insert the `--` separator, so argparse saw no arguments and *every*
   functional test "passed" without doing anything. Found by printing real scene state.
2. glTF export writes only **selected** objects; the verification scene exported a stale GLB
   and produced a 54 % size delta.
3. `compose.py` ortho scale was ~24x too large because `matrix_world` was read before a
   view-layer update.
4. `camera()` used Blender's default clip range: a millimetre-scale scene rendered as a flat
   grey frame because the subject sat 19,000 units away with `clip_end = 1000`.
5. `skill_common.objects()` fell back to the current selection, so "frame all" framed one
   leftover selected object.
6. The car loft duplicated its x=0 ring vertices, producing 283 non-manifold edges and a
   negative volume. Found by `modeling-detail --audit-only`, fixed in the loft.
7. Booleans on the 392-quad cage tore holes; subdivide first, then cut.

**Cannot be tested here (do not claim otherwise):**
- Vendored `run_in_blender.py` (needs the `blender` executable).
- `review_shots.py` and `render_batch.py --engine EEVEE` (need real GLX).
- Any HDRI-lit or texture-mapped workflow (no asset downloads).
- Blender 5.2-specific code paths (this build is 5.0.1). One 5.2-only GN input mode is
  documented as unsupported in the patched `gn_builder.py`.

**Known weak spots in the delivered skills:**
- `modeling-automotive` produces a **package-accurate blockout**, not a finished car: generic
  surfaces, no lights/grille/bumper detail, no interior.
- `detail_pass --grooves` is verified visually (shut lines visible in a render, +1,016 faces);
  an automated "faces crossing the gap" check still reports bridging faces on the underside,
  so the slot is not proven watertight.
- Procedural materials do not survive glTF export without baking (vendored baking skill
  covers the bake, but the bake was only exercised as a self-bake, not high-to-low).
- QA thresholds are heuristics; a deliberately dark or high-key image can fail the ranges
  while being correct.

---

## 5. References consulted during the build

- Blender 5.0 Python API (`bpy` introspection in this sandbox) — authoritative for every API
  used, preferred over 5.2 documentation.
- Upstream skill sources for `gn_builder.py` and `apply_stack.py` (read to port the 5.2 calls).
- No external tutorial or asset was downloaded; the asset hosts are unreachable.
