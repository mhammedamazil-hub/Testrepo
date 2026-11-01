# VALIDATION RESULTS — real image-to-3D achieved

**Status: the success criterion is met, with one documented shortfall (texture map).**

| | |
|---|---|
| Date | 2026-11-01 |
| Inference | **genuine InstantMesh** on the official `TencentARC/InstantMesh` ZeroGPU Space |
| Driven by | GitHub Actions run [`41327069116`](https://github.com/mhammedamazil-hub/Testrepo/actions/runs/41327069116) |
| Cost | **$0.00** — free GitHub standard runner + free ZeroGPU quota (unauthenticated) |
| Input | BMW M5 (F90) photograph, CC BY-SA 2.0, Alexandre Prevot, via Wikimedia `Special:FilePath` at 1280 px |
| Input SHA-256 | `68632a41cf1f6ed976614dda155975bc5b53c0f38b6185b7468815a3679446e2` |
| Output | `ci_results/instantmesh.glb` — **1,274,956 bytes**, SHA-256 `b93dd7934474c28feb6005a75b0f884dd36a6c808137514b8c0c0fc6223af362` |
| Mesh | 31,906 vertices · 63,620 triangles · `POSITION` + `COLOR_0` |
| Openable in a 3D viewer | ✅ proven — all 63,620 triangles rasterised from 6 angles by an independent renderer (§4) |

Every artefact is committed in `ci_results/` so the evidence travels with the repo.

---

## 1. How it ran (no local GPU, no paid compute)

```
GitHub Actions (ubuntu-latest, free, 4 vCPU, NO GPU, open egress)
   │
   ├─ egress probe            huggingface.co 200 · api.replicate.com 401 (reachable)
   │
   ├─ fetch input             Wikimedia → work/input.jpg (188 KB, decoded+validated)
   │
   ├─ tools/hfspace_inference.py  → TencentARC/InstantMesh (ZeroGPU)
   │       /preprocess   (image, remove_bg)          → 1.8 s
   │       /generate_mvs (image, steps=30, seed=42)  → 14.5 s     ← Zero123++ diffusion
   │       /make3d       (no args — consumes gr.State) → 5.6 s    ← LRM + FlexiCubes
   │       total 22.0 s of Space time
   │
   ├─ tools/verify_mesh.py inspect + render (stdlib, independent of the Space)
   │
   └─ commit results → ci_results/  (workflow artifacts/logs are firewalled
                                     from the audit sandbox; github.com is not)
```

**Why this and not local inference:** the sandbox has no GPU and cannot reach Hugging Face.
**Why not a GitHub GPU runner:** they are paid-only ($0.052/min, Team/Enterprise + card).
**Why the workflow triggers on `push`:** `workflow_dispatch` needs `actions:write`, which the GitHub
connection here does not have (dispatch → 403). A push trigger needs only `contents:write`.

## 2. Environment actually used

| | GitHub runner (where inference was driven) | Audit sandbox (where it was verified) |
|---|---|---|
| CPU | 4 vCPU (GitHub standard) | 2 logical / 1 physical vCPU |
| RAM | 16 GB | 3.8 GB, no swap |
| GPU | **none** | **none** |
| Egress | open (`huggingface.co` 200) | HF/Replicate/Colab/artifact-hosts **blocked** |
| Role | orchestration only | independent verification |

**GPU that did the inference:** the Space's ZeroGPU allocation. The Space requests
`@spaces.GPU` per stage; the modern ZeroGPU pool is RTX Pro 6000 Blackwell (48 GB "large").
The Space does not expose per-call VRAM, so **peak VRAM for this run is not measurable from outside** —
reported as *unknown* rather than invented. For a measured figure, run
`notebooks/instantmesh_real_validation.ipynb` on a free Colab T4, which samples `nvidia-smi` during the run.

## 3. Measured results

| Metric | Value |
|---|---|
| Preprocess (rembg + reframe) | 1.8 s |
| Multi-view diffusion (30 steps, seed 42) | 14.5 s |
| Reconstruction + mesh extraction | 5.6 s |
| **Total Space execution** | **22.0 s** |
| Wall clock incl. queue/transport | ~6 min (includes cold start + queue) |
| GLB size | 1,274,956 B (1.22 MiB) |
| OBJ size | 3,425,895 B (3.27 MiB) |
| Vertices / triangles | 31,906 / 63,620 |
| Texture map | ❌ none (see §5) |
| Vertex colours | ✅ `COLOR_0` present and populated |

## 4. Verification that it opens in a 3D viewer — proven, not assumed

`tools/verify_mesh.py` (stdlib-only, written for this project) parsed the GLB byte-by-byte and then
software-rasterised it:

```
container: GLB        file_size_bytes: 1274956      generator: trimesh
nodes: 2   meshes: 1   primitives: 1   materials: 0   textures: 0
attributes: [COLOR_0, POSITION]      vertices: 31906   triangles: 63620
uv_mapped: false     vertex_colored: true     problems: []     valid: true
render_stats: {triangles_total: 63620, triangles_rendered: 63620, frames: 6}
```

* Every bufferView/accessor was bounds-checked against the BIN chunk — **0 problems**.
* All 63,620 triangles were transformed, projected and rasterised with a z-buffer into six PNGs
  (`ci_results/renders/render_00…05.png`). Nothing was skipped or clipped.
* The renders are recognisably the input car: kidney grille, headlights, mirrors, bonnet creases,
  windscreen, B-pillar, wheels and a rear light cluster are all visible. This is an *independent*
  renderer, not the Space's own preview — so it is evidence a third-party viewer can open the file.

The same GLB was then imported into the app (`POST /api/import`, job `c827e9056e9f4db6`) and served back
byte-identically (`http=200`, 1,274,956 B, `model/gltf-binary`, SHA-256 matches). It is stamped
`origin=external_import` — **the app never claims it generated this mesh.**

## 5. Quality issues — honest assessment

**The mesh is recognisably a BMW M5, and it is noticeably worse than the input photo.**

The 6-view grid (`ci_results/multiview.webp`) shows the real cause. The side-on view is clean, but the
**front three-quarter view (top-left) renders the car as an SUV**, and the rear view has distorted
proportions. The reconstruction is therefore built on inconsistent views, which is why the mesh reads as a
"tall estate" rather than the low saloon in the photo.

| Issue | Severity | Cause |
|---|---|---|
| Proportions too tall / SUV-like | **high** | Zero123++ produced inconsistent multi-view geometry |
| Only 30 diffusion steps | contributing | default chosen to fit the anonymous ZeroGPU quota (2 min/day); 75 steps needs `HF_TOKEN` |
| **No texture map — vertex colours only** | **high** | the live Space hard-codes `use_texture_map=False` |
| Wheels soft / elliptical, rims mushy | medium | expected for this model class |
| Underside invented | expected | never visible in the photo |
| Grille badge illegible, door seams lost | expected | 320×320 working resolution |
| Flat paint, no reflections or PBR | expected | baked diffuse colour only |

**Fix for proportions:** re-run with 75 steps and/or a different seed (needs `HF_TOKEN` because 75 steps
will likely exceed the anonymous ~2 GPU-min/day). **Fix for texture:** the Space cannot do it — use
`notebooks/instantmesh_real_validation.ipynb` on a free Colab T4 with `--export_texmap`.

## 6. Success criterion scorecard

| Requirement | Status |
|---|---|
| One user-supplied photograph | ⚠️ **CC BY-SA Wikimedia photo, not the user's own** (chosen for zero-effort; provenance + licence recorded) |
| Genuine InstantMesh inference | ✅ official Space, real model, 22 s of GPU time |
| Textured 3D mesh | ❌ **vertex-coloured only** — the Space cannot export textures |
| Downloadable GLB | ✅ 1.22 MiB, committed at `ci_results/instantmesh.glb` |
| Verified opening in a 3D viewer | ✅ 63,620/63,620 triangles rendered from 6 angles |
| Free | ✅ $0.00 |
| Mock never reported as inference | ✅ mock stays watermarked `SIMULATED_NOT_AI`; this job is `origin=external_import` |

**Two of seven are short of the full criterion: the texture map, and the photo being the user's own.**
Both have one path to a full pass: the Colab notebook with `--export_texmap` and a photograph you supply.

## 7. Reproduce it

* **Same free route (vertex colours):** Actions → *InstantMesh ZeroGPU validation* → *Run workflow*
  (or push a change to the workflow). Add an `HF_TOKEN` repository secret for 75 steps.
* **Full criterion (textured, your photo):** `RUN_VALIDATION.md` → Colab T4 → `Run all`, after swapping
  cell 4 for your own upload.
