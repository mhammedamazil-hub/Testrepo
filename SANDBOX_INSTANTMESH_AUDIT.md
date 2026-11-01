# SANDBOX_INSTANTMESH_AUDIT

**Scope:** Can `TencentARC/InstantMesh` (image → 3D mesh) actually be run for this project, and what is the
cheapest *genuine* execution path?

**Audit date:** 2026-11-01 · **Sandbox:** arena VM `e2b.local`, Debian 12 (bookworm), kernel 6.1.158+
**Upstream audited:** `github.com/TencentARC/InstantMesh` @ [`08822c5`](https://github.com/TencentARC/InstantMesh/commit/08822c52fdc399b93ea00e4fa9e596344ed52ccc) (last commit 2025-01-03)
**Weights audited:** `huggingface.co/TencentARC/InstantMesh` @ `b785b4ec` (metadata verified via Hub API)

> **Bottom line:** InstantMesh **cannot** run in this sandbox — not because of RAM or disk, but because
> the sandbox has **no GPU** and its egress proxy **TLS-blocks `huggingface.co`**. Real inference is
> impossible here. It *is* achievable for **$0** via the official ZeroGPU Space or a free Colab/Kaggle GPU,
> and for **~$0.14/run** via Replicate. A working, provider-abstracted app and a free-GPU notebook are
> delivered alongside this report. **No fake 3D was produced: the only mesh generated in this sandbox comes
> from the explicitly-labelled `mock` provider and is watermarked `SIMULATED_NOT_AI`.**

---

## 1. Verified environment

Every number below was measured in this sandbox during the audit, not assumed.

### 1.1 CPU

| Property | Value | Source |
|---|---|---|
| Model | `Intel(R) Xeon(R) Processor @ 2.60GHz` (family 6, model 106 — Ice Lake server class) | `lscpu` |
| Architecture | `x86_64`, 64-bit, little endian | `lscpu` |
| Virtualisation | KVM guest (`Hypervisor vendor: KVM`, full virt) | `lscpu` |
| L1d / L1i / L2 / L3 | 48 KiB / 32 KiB / 1.3 MiB / 54 MiB | `lscpu` |
| Address sizes | 46-bit physical, 48-bit virtual | `lscpu` |

**Instruction sets present:** `sse4_2`, `avx`, `avx2`, `fma`, `f16c`, `bmi2`, `aes`, `sha_ni`,
`avx512f`, `avx512dq`, `avx512bw`, `avx512vl`, `avx512_vnni`, `avx512_bitalg`, `avx512_vpopcntdq`,
`avx512_vbmi`, `avx512_vbmi2`, `avx512ifma`, `vaes`, `gfni`.
**Notably absent:** `avx512_fp16`, `avx512_bf16`, `amx_*`. Consequence: no CPU matrix acceleration beyond
AVX-512 FMA/VNNI — a fp16 diffusion model would still be emulated, not accelerated.

### 1.2 Cores

| Property | Value |
|---|---|
| Physical cores | **1** (1 core/socket × 1 socket) |
| Threads per core | 2 (SMT) |
| Logical CPUs (`nproc`, `lscpu`, `os.cpu_count()`) | **2** |
| BogoMIPS | 5200.02 |

### 1.3 Memory

```
               total        used        free      shared  buff/cache   available
Mem:           3.8Gi       231Mi       3.7Gi       1.0Mi       116Mi       3.6Gi
Swap:             0B          0B          0B
```

**3.8 GiB RAM, 0 B swap.** With no swap, any overcommit is an immediate OOM kill.
The sandbox is *not* cgroup-limited below these numbers (`/sys/fs/cgroup/memory.max` is unreadable here),
so 3.8 GiB is the real ceiling.

### 1.4 Disk

| Mount | Size | Used | Avail | FS |
|---|---|---|---|---|
| `/dev/root` (`/`, `/home/user`, `/tmp`) | 21 GB | 927 MB | **20 GB** | ext2/3-style virtual block device (5,330,792 × 4 KiB blocks) |

20 GB is *nominally* enough for the ~7.3 GB of InstantMesh weights. Disk is **not** the blocker.
The workspace snapshot has a soft cap of ~128 MB / 10,000 files for persisted artifacts, so weights and
generated meshes must stay out of git (see `.gitignore`).

### 1.5 GPU

```
$ which nvidia-smi   → not found
$ nvidia-smi         → command not found
$ ls /dev/nvidia*    → no /dev/nvidia*
$ which nvcc         → no nvcc
```

**No NVIDIA GPU and no NVIDIA driver interface.** There is no device to bind to, so no `torch.cuda`
device can exist regardless of what wheel is installed.

### 1.6 CUDA

**No CUDA.** No driver, no toolkit (`nvcc` absent), no `/dev/nvidia*`. `CUDA_VISIBLE_DEVICES` is
irrelevant because the kernel exposes no device nodes.

### 1.7 PyTorch

**Not installed.**

```
$ python3 -c "import torch"
ModuleNotFoundError: No module named 'torch'
```

Installing it is possible (PyPI is reachable) but pointless: a `cu121` wheel would install and then
report `torch.cuda.is_available() == False`, and a CPU wheel still cannot run InstantMesh (see §3.B).

### 1.8 Python

| Property | Value |
|---|---|
| Version | **3.11.2** |
| Interpreter | `/usr/bin/python3` |
| pip | 23.0.1 |
| OS | Debian GNU/Linux 12 (bookworm) |

InstantMesh recommends Python ≥ 3.10 — 3.11 satisfies that. (Its `transformers==4.34.1` /
`diffusers==0.20.2` pins are old but do install on 3.11.)

### 1.9 Network access (the decisive finding)

| Endpoint | Result | Notes |
|---|---|---|
| `github.com` | **200** ✅ | clone works |
| `api.github.com` | **200** ✅ | |
| `codeload.github.com` | **200** ✅ | tarball download works |
| `pypi.org` | **200** ✅ | `pip install` works |
| `files.pythonhosted.org` | **200** ✅ | wheels download |
| `registry.npmjs.org` | **200** ✅ | |
| `huggingface.co` | **TLS failure** ❌ | `OpenSSL SSL_connect: SSL_ERROR_SYSCALL` |
| `hf.co`, `cdn-lfs.huggingface.co` | **TLS failure** ❌ | LFS/CDN also blocked |
| `*.hf.space` (e.g. `tencentarc-instantmesh.hf.space`) | **TLS failure** ❌ | Spaces apps blocked |
| `replicate.com`, `api.replicate.com` | **TLS failure** ❌ | |
| `raw.githubusercontent.com` | **TLS failure** ❌ | (but `codeload` + `git` work) |
| `colab.research.google.com`, `kaggle.com` | **TLS failure** ❌ | |

**Mechanism (measured, not guessed):**

```
$ getent ahostsv4 huggingface.co         → 108.138.94.52     (public IP resolves fine)
$ curl -4 https://huggingface.co         → SSL_ERROR_SYSCALL  (TCP connects, TLS dies)
$ bash -c 'cat < /dev/null > /dev/tcp/huggingface.co/443'  → OK
```

TCP/443 completes and DNS resolves, but the TLS handshake is reset. That is **SNI-based filtering at the
egress proxy**, not IP blocking. Practical consequence: no domain-fronting, no alternate-CDN, and no
"just use a different mirror host" workaround exists. `git clone https://github.com/...` works because
github.com's SNI is allowlisted.

> The host-allowlist for this session is: `github.com`, `codeload.github.com`, `api.github.com`,
> `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`. I did not attempt to circumvent the egress
> policy (proxying inference through GitHub, tunnels, etc.) — that boundary is intentional.

**Consequence:** the sandbox can *read the code* (GitHub ✅) but can never *fetch the weights* (HF ❌) and
can never *call a hosted GPU* (HF Spaces ❌, Replicate ❌). Both halves of real inference are cut.

### 1.10 Outbound bandwidth (measured)

| Test | Bytes | Time | Throughput |
|---|---|---|---|
| `codeload.github.com` InstantMesh tarball | 13,493,187 | 0.714 s | **18.9 MB/s ≈ 151 Mbit/s** |
| `files.pythonhosted.org` wheel | 2,110,226 | 0.136 s | **15.5 MB/s ≈ 124 Mbit/s** |

Bandwidth is excellent (~150 Mbit/s) — downloading 7.3 GB of weights would take ~7 minutes *if the host
were reachable*. Bandwidth is not the constraint; the allowlist is.

---

## 2. Official model requirements (and what is measured vs. claimed)

### 2.1 Architecture

InstantMesh is a two-stage, feed-forward pipeline — no per-object optimisation (no SDS, no test-time
fitting), which is why it is fast:

```
input image (RGBA, any size)
        │
        ▼  rembg (u2net) + resize_foreground(0.85)      [optional]
        │
 ┌──────┴─────────────────────────────────────────────────────────┐
 │ STAGE 1 — Zero123++ v1.2 (fine-tuned SD-2 UNet, white bg)      │
 │   one image → 6 novel views, emitted as a 3×2 grid (960×640)   │
 │   → split into 6 × 320×320 views with known cameras            │
 └──────┬─────────────────────────────────────────────────────────┘
        │  (this is the "sparse-view" input: 6 views @ radius 4.0)
        ▼
 ┌────────────────────────────────────────────────────────────────┐
 │ STAGE 2 — LRM / Instant3D sparse-view reconstruction           │
 │   DINOv2 ViT-B/16 image encoder (feat dim 768, facebook/…)     │
 │        → 16-layer / 1024-dim / 16-head transformer decoder     │
 │        → triplane  [3 planes, 32×32 low + 64×64 high, dim 80]  │
 │        → FlexiCubes geometry branch  (grid_res 128, scale 2.1) │
 │          or NeRF branch (128 samples/ray) for neural rendering │
 └──────┬─────────────────────────────────────────────────────────┘
        ▼
   mesh: vertices + faces + vertex colours          →  OBJ / GLB
        + optional xatlas UV unwrap + baked texture →  OBJ + MTL + PNG
        + optional 120-frame turntable               →  MP4 (h264)
```

Config actually used by default (`configs/instant-mesh-large.yaml`):

```yaml
model_config:  src.models.lrm_mesh.InstantMesh
  encoder_feat_dim: 768   encoder_model_name: facebook/dino-vitb16
  transformer_dim: 1024   transformer_layers: 16   transformer_heads: 16
  triplane_low_res: 32    triplane_high_res: 64    triplane_dim: 80
  rendering_samples_per_ray: 128  grid_res: 128  grid_scale: 2.1
infer_config:  texture_resolution: 1024   render_resolution: 512
```

Four reconstruction variants ship: `instant-{mesh,nerf}-{base,large}`. `mesh` = FlexiCubes (fast mesh),
`nerf` = neural rendering (nicer previews, slower mesh extraction at iso-resolution 256).

### 2.2 Weight sizes (verified against the Hub API, with LFS SHA-256)

| File | Bytes | GiB | SHA-256 (LFS) |
|---|---:|---:|---|
| `instant_mesh_large.ckpt` | 1,514,818,077 | 1.41 | `329f7aae9b583fd7c1b27d0221463db7b808a03c48a1f7aa26649af6a03b91a1` |
| `instant_mesh_base.ckpt` | 1,253,574,354 | 1.17 | `22701cd25201d624ebb1568b93cf91b43a2c32006835c08fe73e1f3c9f6c44b5` |
| `instant_nerf_large.ckpt` | 1,514,088,389 | 1.41 | `530a344ea9b856e012492b9644ab73532ddf7c06d548f60c489e49a528322fb9` |
| `instant_nerf_base.ckpt` | 1,253,151,890 | 1.17 | `bcbfff8be8545f8206110f432afddedfb4311abc1146b843ab2bdb6678f8d9c9` |
| `diffusion_pytorch_model.bin` (white-bg UNet) | 1,732,056,502 | 1.61 | `9d78d78421d1feb6871d13e13e86ed8099628648d7d9c51ffca9015b7d5fa3c4` |

Repo totals: `TencentARC/InstantMesh` **7.28 GB** of storage across all variants.
**Dependencies fetched at runtime, not bundled:**

* `sudo-ai/zero123plus-v1.2` — `usedStorage` 5.76 GB; 865,910,724 parameters held as **F32** safetensors
  (so the pipeline is loaded fp32 on disk and cast to fp16 at run time).
* `facebook/dino-vitb16` — ~0.33 GB.
* `rembg` u2net ONNX — 176 MB downloaded on first use.

**Realistic first-run download: ~7.3 GB** (the exact figure a GPU host advertises for a full pull, which
matches 1.51 + 1.73 + 5.76 + 0.33 GB minus the unused variants). It fits in the 20 GB disk here — but
cannot be fetched (§1.9).

### 2.3 Dependencies (from `requirements.txt`, verbatim)

```
pytorch-lightning==2.1.2   gradio==3.41.2        huggingface-hub
einops                     omegaconf            torchmetrics
webdataset                 accelerate           tensorboard
PyMCubes                   trimesh              rembg
transformers==4.34.1       diffusers==0.20.2    bitsandbytes
imageio[ffmpeg]            xatlas               plyfile
git+https://github.com/NVlabs/nvdiffrast/
```

Plus, per the README: `torch==2.1.0 + torchvision==0.16.0 + torchaudio==2.1.0` (cu121 wheel index) and
`xformers==0.0.22.post7`. `nvdiffrast` compiles from source and needs `libEGL1-mesa-dev` + `libglib2.0-0`
(the shipped Dockerfile installs exactly those). Docker image base: `nvidia/cuda:12.4.1-runtime-ubuntu22.04`.

**Two audit findings worth knowing before you build:**

1. **`gradio==3.41.2` is a dead pin.** The repo's `app.py` uses the Gradio 3 API. The official **Space now
   runs `sdk_version: 5.50.0`** with a modified `app.py`, so the pip pin in the repo does not describe what
   actually serves the demo. Don't build an integration on the repo's `app.py` as-is.
2. **CUDA is hard-coded.** `app.py:82` and `run.py:95` both do `device = torch.device('cuda')` with no CPU
   fallback. There is no supported CPU path, not even a broken one — patching it is a research project, not a flag.

### 2.4 GPU / VRAM

| Claim | Status | Detail |
|---|---|---|
| VRAM requirement stated by the authors | **Not stated** | The README gives no VRAM figure. No official number exists to quote. |
| Official demo hardware | **Verified via Hub API** | `runtime.hardware.current = "zero-a10g"` → **NVIDIA A10G, 24 GB**, 4 replicas, stage `RUNNING` (2026-11-01). |
| Multi-GPU supported | **Official (README)** | Demo auto-splits across 2 GPUs (diffusion on `cuda:0`, reconstruction on `cuda:1`) for "lower memory"; `CUDA_VISIBLE_DEVICES=0` forces one. That design implies real single-GPU pressure. |
| ~15 GiB peak for `instant-mesh-large`, 24 GB recommended | **Third-party, unverified** | Published by a GPU-rental vendor, not by Tencent. Treat as an estimate until you measure it — the wrapper script in this repo logs `torch.cuda.max_memory_allocated()`. |
| ZeroGPU "large" tier | **Verified** | 48 GB (half RTX Pro 6000 Blackwell) at 1× quota; "xlarge" 96 GB at 2× quota. |

**Practical stance:** plan for **≥16 GB VRAM, prefer 24 GB**. 16 GB (T4/P100) can work with
`instant-mesh-base` and/or the two-device split; it is not guaranteed, so the notebook ships a
base/large switch.

### 2.5 Inference pipeline (the exact call sequence)

`app.py` (demo) and `run.py` (CLI) differ in **outputs**, which matters for an app:

| Step | CLI (`run.py`) | Demo (`app.py`) / API |
|---|---|---|
| Load Zero123++ + white-bg UNet | auto-download from Hub | same |
| Load reconstruction ckpt | `instant_mesh_large.ckpt` | same |
| Multi-view sampling | 75 steps (default), seed 42 | 30–75 slider, seed default 42 |
| Triplane + mesh | `model.forward_planes` → `model.extract_mesh` | same |
| **Exports** | **OBJ only** (`save_obj`) + optional `--export_texmap` (OBJ+MTL+PNG), `--save_video` (MP4) | **OBJ *and* GLB** (`save_obj` + `save_glb`) |

* **Input formats:** `png`, `jpg/jpeg`, `webp` (`run.py` filters on exactly those extensions). A single
  image of a single object. An alpha mask is honoured via `--no_rembg`.
* **Output formats:** `.obj` with **vertex colours** (no material file), `.glb` (binary glTF 2.0 with
  `COLOR_0` vertex colours), optional `.obj + .mtl + .png` texture set, optional `.mp4` turntable.
  **No animated rig, no PBR (metallic/roughness) maps, no quad topology.**
* **Known export quirk (documented by the authors):** "Downloaded `.obj` model will be flipped. Export
  `.glb` instead or manually flip it." The `.glb` is the safe interchange format — which is why this
  project's app downloads GLB by default.
* **Texture export cost:** `--export_texmap` runs an xatlas UV unwrap; for NeRF variants the authors warn
  this "may cost long time" at the default iso-resolution 256 (lower it in the config).

### 2.6 Limitations (honest list)

1. **Single object, single image.** Cluttered scenes, multiple objects, and heavy occlusion degrade badly.
2. **Back-side hallucination.** Six views constrain the object; anything never visible is invented.
3. **Thin/transparent geometry fails** — wires, glass, foliage, chainmail, open books.
4. **No PBR / no animation.** Vertex-coloured or single baked diffuse map only; not game-ready out of the box.
5. **No CPU path**, no Apple MPS path, no ROCm notes — CUDA-only by construction.
6. **Result variance.** The authors themselves say results "highly depend on the quality of generated
   multi-view images; try a different **seed**."
7. **Stale repository** — last commit 2025-01-03; pins are from the SD-1.5/SD-2 era (`transformers==4.34.1`),
   which conflicts with modern toolchains. Reproducing the environment is the hard part, not the model.
8. **Licensing:** code Apache-2.0 ✅, model card `license: apache-2.0` ✅. But **`sudo-ai/zero123plus-v1.2`
   declares no license tag in its Hub metadata**, and it is a stage-1 dependency you cannot avoid.
   Confirm that before commercial deployment.
9. **Quality baseline:** InstantMesh (2024) is no longer SOTA. Newer open options (TRELLIS, Hunyuan3D-2,
   TripoSR) generally beat it on fidelity/geometry; InstantMesh's edge is speed and a small, simple codebase.

---

## 3. Execution strategies — what actually works

| # | Strategy | Verdict | Evidence / restriction |
|---|---|---|---|
| **A** | **Native in this sandbox** | ❌ **Impossible** | No GPU (§1.5), no CUDA (§1.6), and `huggingface.co` TLS-blocked so weights are unfetchable (§1.9). Even with weights, `run.py` dies at `torch.device('cuda')`. |
| **B** | **CPU-only in this sandbox** | ❌ **Not viable** | Code path is CUDA-hard-coded (no `device='cpu'` branch to flip). Even hypothetically: 1 physical core, 3.8 GiB RAM, 0 swap must hold a fp16 UNet (~1.7 GB) + triplane transformer (~1.5 GB) + activations for 75 diffusion steps at 960×640 plus a 128³ FlexiCubes extraction. Expect **many hours to days** per image, with OOM near-certain at 3.8 GiB. Not attempted — it would burn the disk and the session for zero result. |
| **C** | **Official HF Space (ZeroGPU)** | ✅ **Operational — verified** | Hub API: `stage: RUNNING`, `hardware: zero-a10g`, `replicas: 4`, `sdk 5.50.0`. Gradio API enumerated at `/gradio_api/info`: `/check_input_image`, `/preprocess`, `/generate_mvs`, `/make3d`. **Free quota: 5 GPU-min/day** (free account), **~2 min/day unauthenticated**, resets 24 h after first use; PRO 40 min/day, overage $1/10 min. **Not reachable from this sandbox** (§1.9). Usage caveat in §3.C below. |
| **D** | **Free/low-cost cloud GPU** | ✅ **Works** | *Colab free*: T4 16 GB, ~15–30 GPU-h/week (dynamic, unpublished), 12 h sessions, ~90 min idle disconnect, no card required. *Kaggle*: T4/P100 16 GB, **30 GPU-h/week**, 9–12 h sessions, no card. *Modal*: advertised $30/month free credits (per-second billing) — unverified in this audit. *RunPod/Lambda/Vast*: paid, ~$0.19–0.54/GPU-h for 24 GB. *HF dedicated GPU Space*: T4 $0.40/h, A10G $1.00/h, A100 $2.50/h (vendor-listed). |
| **E** | **Remote inference API** | ⚠️ **Partially** | **Replicate `aryamansital/instant_mesh` is live** (verified 2026-11-01): inputs `image_path, remove_background, export_video, export_texmap, sample_steps, seed`; outputs multiview PNG + MP4 + OBJ + GLB; **A100-80GB, ~103 s, ≈$0.14/run**. **`camenduru/instantmesh` — the one linked from the official README — is now a 404.** No official Tencent-hosted API. HF "Inference Providers" do **not** cover image-to-3D custom models. Replicate has **no permanent free tier** for arbitrary public models (free runs are limited to a curated "try for free" collection; new accounts use prepaid credits). |
| **F** | **Colab / Kaggle notebook** | ✅ **Delivered & ready** | `notebooks/instantmesh_free_gpu.ipynb` — official repo, official `run.py`, then trimesh OBJ→GLB, plus downloads. **Cannot be executed from this sandbox** (colab/kaggle TLS-blocked); you run it in a browser on a free GPU. |

### 3.C — the one real caveat on the official Space

Its API is **stateful in a way that is not visible in the OpenAPI-style listing**:

```
/generate_mvs (image, steps, seed) → multiview grid image   [ gr.State holds the grid server-side ]
/make3d       ()                   → (OBJ, GLB)             [ no parameters — reads that State ]
```

`gr.State` is keyed by Gradio **session hash**, so `/make3d` only works if it is called on the *same*
`gradio_client.Client` instance that just ran `/generate_mvs`. A naive one-call integration silently
breaks. The `hf_space` provider in the delivered app does exactly this chaining and **fails loudly** if
the state is missing rather than returning something plausible. For a production contract, deploy
`space/app.py` from this repo (single `/generate` call, both formats) — that is the "own Space" path.

---

## 4. What works / what does not (in *this* sandbox)

### Works ✅
* Reading the entire upstream repository (`git clone` via GitHub — 27 MB, 90 files, commit `08822c5`).
* Installing any PyPI package (`fastapi`, `uvicorn`, `pytest`, `httpx` were installed during the audit).
* Running the delivered FastAPI app and its full HTTP contract (13/13 tests pass).
* Generating a **valid GLB** — from the `mock` provider only (explicitly labelled, see §6).
* Probing provider reachability from the server and surfacing it in the UI/API (this is how the egress
  restriction is *proved at runtime* rather than asserted).
* ~150 Mbit/s outbound throughput to allowlisted hosts.

### Does not work ❌
* Any GPU work. No CUDA device exists.
* Downloading InstantMesh weights (`huggingface.co` / `cdn-lfs.huggingface.co` TLS-reset).
* Calling the official HF Space, any `*.hf.space`, Replicate, Colab, or Kaggle.
* Running the official `app.py` (needs CUDA + old Gradio) or `run.py` (needs CUDA).
* Therefore: **no real AI 3D asset can be produced inside this sandbox.** Not attempted, not faked.

---

## 5. Network restrictions (summary)

| Category | Hosts | Status |
|---|---|---|
| Code hosting | `github.com`, `api.github.com`, `codeload.github.com` | ✅ allowed |
| Package registries | `pypi.org`, `files.pythonhosted.org`, `registry.npmjs.org` | ✅ allowed |
| Model weights | `huggingface.co`, `hf.co`, `cdn-lfs.huggingface.co` | ❌ TLS blocked |
| Hosted demos | `*.hf.space`, `replicate.com`, `api.replicate.com` | ❌ TLS blocked |
| Notebooks | `colab.research.google.com`, `kaggle.com` | ❌ TLS blocked |
| Raw GitHub content | `raw.githubusercontent.com`, `objects.githubusercontent.com` | ❌ TLS blocked (!) |

Mechanism: TLS SNI filtering at the egress proxy (TCP connects, handshake dies). Allowlist is per-session
and not user-configurable from inside the sandbox.

---

## 6. Delivered artifacts

| Path | What it is |
|---|---|
| `app/` | FastAPI + vanilla-JS **image-to-3D application**: upload, job queue, real stage progress, 3D preview, GLB/OBJ/multi-view/MP4 downloads, provider status table. |
| `app/server/providers/` | **Provider abstraction**: `hf_space` (official Space, Gradio API), `replicate` (Cog model), `local_gpu` (official repo on your GPU), `mock` (simulation, labelled). |
| `notebooks/instantmesh_free_gpu.ipynb` | **The $0 path to a real asset** — official pipeline on a free Colab T4 / Kaggle GPU. |
| `space/` | Deployable **ZeroGPU Gradio Space** with a clean single-call `/generate` API (replaces the fragile stateful chain). |
| `integrations/local_gpu/instantmesh_generate.py` | Wrapper that adds **GLB export** to the official CLI (which only writes OBJ) and reports peak VRAM. |
| `app/tests/` | 7 unit + 6 API tests. Mock tests are named as simulations; a real-provider-without-credentials test asserts honest failure. |

**Nothing in this repo fakes inference.** The `mock` provider emits a procedurally generated cube, names
every file `SIMULATED_NOT_AI.*`, tags the job `simulated: true`, prefixes the download filename, and the
UI shows a red banner. It exists solely to prove upload → queue → progress → preview → download plumbing.

---

## 7. Cost model

| Path | Cost | Rate limit | Real inference? |
|---|---|---|---|
| **Official HF Space (ZeroGPU)** | **$0** | 5 GPU-min/day per free account (~2 min anonymous); ~10–20 runs/day | ✅ yes |
| **Your own ZeroGPU Space** (§3.C contract fix) | **$0** | same 5 GPU-min/day pool; 2 Spaces max on a free account (account >30 days old) | ✅ yes |
| **Colab free (T4 16 GB)** | **$0** | ~15–30 GPU-h/week (dynamic); 12 h sessions | ✅ yes |
| **Kaggle (T4/P100 16 GB)** | **$0** | 30 GPU-h/week; 9–12 h sessions | ✅ yes |
| **Colab Pro** | $9.99/mo | 100 compute units ≈ 80–90 T4-h | ✅ yes |
| **Replicate** (`aryamansital/instant_mesh`) | **≈$0.14/run** (A100-80, ~103 s) | per-second, no free tier for this model | ✅ yes |
| **HF dedicated GPU Space** | T4 $0.40/h · A10G $1.00/h · A100 $2.50/h | billed hourly | ✅ yes |
| **Rented 24 GB GPU** (RunPod/Vast class) | ≈$0.19–0.54/h → **< $0.05 for a 10-image batch** after ~30 min setup | hourly | ✅ yes |
| **This sandbox** | $0 | — | ❌ impossible |

Per-asset marginal cost: **$0** on the free tiers (until the daily/weekly quota), **≈$0.14** on Replicate,
**< $0.01** on an hourly rented GPU once warm. The dominant cost of self-hosting is not GPU time, it is the
**~30–60 min environment build** (torch 2.1 + xformers + compiling `nvdiffrast`) and the **7.3 GB pull** —
which is precisely why an API/Space beats self-hosting below ~100 assets/month.

Third-party price quotes are dated 2026 to the extent the sources allow; treat vendor numbers as
"listed at audit time", not contractual.

---

## 8. Recommended architecture

```
┌────────────────────────┐        ┌───────────────────────────────────────────────┐
│ Browser (you)          │        │ App server (FastAPI, this repo)               │
│ • upload / drag-drop   │  HTTPS │ • receives image, validates magic bytes       │
│ • live stage progress  │───────▶│ • job queue (thread pool) + job store         │
│ • <model-viewer> GLB   │◀───────│ • provider adapter  ──┐                       │
│ • GLB/OBJ downloads    │        │ • secrets only here   │                       │
└────────────────────────┘        └───────────────────────┼───────────────────────┘
                                                          │  (server-side, bearer token)
                        ┌─────────────────────────────────┼─────────────────────────┐
                        ▼                                 ▼                         ▼
            1st choice: own ZeroGPU Space      fallback: Replicate         batch: local GPU /
            (/generate → OBJ+GLB)              (≈$0.14/run)                Colab notebook
            free, 5 GPU-min/day                paid, no quota              free, high quota
```

Load order rationale:

1. **Own ZeroGPU Space (**`space/`**)** — $0, real inference, and *you* own the API contract (one call,
   both formats, no `gr.State` fragility). 5 GPU-min/day covers ~10–20 assets/day.
2. **Replicate `aryamansital/instant_mesh`** — $0.14/run, no quota anxiety, one HTTP call. Keep it as the
   fallback so a ZeroGPU quota exhaustion is not an outage. (Do **not** target `camenduru/instantmesh`; it's 404.)
3. **Official upstream Space** — fine for a demo, but the stateful `/make3d` chain is a liability in production.
4. **Free Colab/Kaggle notebook** — for batch work and for producing the first real asset *today* at $0;
   not an API.
5. **`local_gpu` provider** — only if you already own a ≥16 GB (ideally 24 GB) NVIDIA card. Then the
   marginal cost is electricity and the app is fully offline-capable.

**Deployment requirement (non-negotiable):** the app server must run somewhere with open egress to
`huggingface.co` and/or `api.replicate.com` — Fly.io, Render, a VPS, or an HF Space itself. **It cannot
run in this sandbox**; the sandbox build is for development and for the `mock` path only.

Other production notes:
* `JobStore` is in-process by design (~120 lines). Swap for Redis + RQ/Celery when you need multiple replicas.
* Artifacts land in `app/storage/<job_id>/` with a 24 h TTL cleanup (`IM_JOB_TTL_HOURS`); move to S3/R2 and
  signed URLs for production.
* Add a per-IP rate limit before exposing a free-tier-backed provider publicly, or one user can drain the
  daily ZeroGPU quota.
* Keep the request timeout ≥180 s: cold starts on ZeroGPU plus 75 diffusion steps plus mesh extraction are
  not fast.

---

## 9. Exact next steps

**Step 0 — see the app run (2 min, happens here):** the server is already running on port 8000 in mock
mode. Provider table → `hf_space`/`replicate` show **unreachable**, which is this audit's network finding
rendered live. Mock jobs produce a labelled `SIMULATED_NOT_AI.glb`.

**Step 1 — get a real asset, free, today (10–25 min):**
1. Open `notebooks/instantmesh_free_gpu.ipynb` in Google Colab → *Runtime → Change runtime type → T4 GPU*.
2. Run all cells; upload one clean object photo (or use `examples/fox.jpg`).
3. Expect `mesh.glb` + `mesh.obj` + the 6-view grid. If you hit CUDA OOM, set
   `CONFIG = "configs/instant-mesh-base.yaml"`.
4. Validate the GLB at <https://github.khronos.org/glTF-Validator/> — this is your proof-of-real-output gate.

**Step 2 — point the app at a real provider:**
```bash
# A) zero-cost, free quota — the official Space
export IM_PROVIDER=hf_space
export HF_SPACE_ID=TencentARC/InstantMesh
export HF_TOKEN=hf_xxx           # optional: uses your 5 min/day instead of the 2 min anonymous pool
pip install gradio_client        # required by this provider only

# B) no quota, ~$0.14/run — Replicate
export IM_PROVIDER=replicate
export REPLICATE_API_TOKEN=r8_xxx
export REPLICATE_MODEL=aryamansital/instant_mesh

python -m uvicorn app.server.main:app --host 0.0.0.0 --port 8000
```
Then open `/api/providers`: `reachable: true` means you are on a host with open egress. If it still says
false, you are still behind the sandbox allowlist — move the server.

**Step 3 — remove the stateful-chain risk:** deploy `space/` as your own ZeroGPU Space (free account,
>30 days old, verified email → 2 ZeroGPU Spaces allowed) and set `HF_SPACE_ID=<you>/<space>`. Your app then
calls one `/generate` endpoint you control.

**Step 4 — if you own a GPU:** clone InstantMesh, build the env per `README.md`, then
```bash
export IM_PROVIDER=local_gpu
export LOCAL_GPU_REPO=/path/to/InstantMesh
python -m uvicorn app.server.main:app --port 8000
```
The wrapper reports `peak_vram_gb` in the job metadata — **use it to replace the third-party "~15 GiB" estimate
with a measured number for your card.**

**Step 5 — before shipping:** confirm the `sudo-ai/zero123plus-v1.2` licence (no licence tag on the Hub),
add rate limiting, and decide retention for uploaded images (they are user content).

---

## 10. Verification log (what was actually executed)

| Check | Command | Result |
|---|---|---|
| CPU/mem/disk/GPU inventory | `lscpu`, `free -h`, `df -h`, `which nvidia-smi` | as tabulated in §1 |
| Egress matrix | `curl` ×13 hosts + `/dev/tcp` checks | GitHub/PyPI 200; HF/Replicate/Colab/Kaggle TLS-reset |
| Bandwidth | `curl -w %{speed_download}` ×2 | 18.9 MB/s, 15.5 MB/s |
| Repo access | `git clone` + `git ls-remote` | ✅ `08822c5` (2025-01-03) |
| Deps/inference code | read `requirements.txt`, `app.py`, `run.py`, `configs/*.yaml`, `src/utils/*` | CUDA hard-coded; CLI=OBJ only, demo=OBJ+GLB |
| Weight sizes | Hub API `?blobs=true` | 5 files, SHA-256 recorded (§2.2) |
| Official Space status | Hub API `/api/spaces/TencentARC/InstantMesh` | `RUNNING`, `zero-a10g`, 4 replicas |
| Official Space API contract | `…hf.space/gradio_api/info` | 4 endpoints; `/make3d` takes **no** params |
| Hosted paid endpoint | `replicate.com/aryamansital/instant_mesh` | live, ~$0.14/run, A100-80GB |
| Dead endpoint check | `replicate.com/camenduru/instantmesh` | **404** |
| App tests | `pytest app/tests` | **13 passed** (7 unit + 6 API) |
| Mock end-to-end | `POST /api/jobs` → poll → download | GLB magic `glTF`, header length == file size, `SIMULATED_NOT_AI` filename |
| **Real inference** | — | **not executed (impossible here); no real asset produced or claimed** |

*Audit prepared 2026-11-01. Vendor pricing and quotas change; re-verify §7 before committing budget.*

---

# 11. Validation milestone (real end-to-end image-to-3D)

Objective: one photograph → genuine InstantMesh inference → real textured mesh → downloadable GLB →
verified rendering. This section records what was verified, what was **empirically tested**, and what is
still outstanding.

## 11.1 Notebook fidelity to the official pipeline — verified ✅

`notebooks/instantmesh_real_validation.ipynb` was line-checked against the official `README.md` and `run.py`:

| Official requirement | Notebook | Status |
|---|---|---|
| `git clone` official repo | cell 2 | ✅ same commit line |
| `torch==2.1.0 + torchvision 0.16.0 + torchaudio 2.1.0` (cu121 index) | cell 2 | ✅ exact pins, with a documented fallback |
| `xformers==0.0.22.post7` | cell 2 | ✅ |
| `pip install -r requirements.txt` (incl. `nvdiffrast` from source) | cell 2 | ✅ |
| Auto-download of `instant_mesh_large.ckpt` + `diffusion_prompt…bin` + Zero123++ | cells 3 | ✅ pre-fetched into `ckpts/`, which `run.py` prefers |
| `python run.py configs/instant-mesh-large.yaml <img> --seed 42 --diffusion_steps 75` | cell 5 | ✅ verbatim |
| Texture map export `--export_texmap` | cell 5 (attempt 1) | ✅ added — required by the "textured" criterion |
| Output layout `outputs/<config>/meshes/*.obj` | cell 6 glob | ✅ matches `run.py` |

**One documented deviation:** the official CLI writes **OBJ only** (no GLB). The notebook converts with
`trimesh` and validates the GLB header before offering it for download. This is an export step, not a
change to the model or the inference path. (The official *Gradio demo* does the same thing in-process via
`src/utils/mesh_util.save_glb`.)

Two bugs were found and fixed during this review:
1. **Peak-VRAM measurement was wrong.** `torch.cuda.max_memory_allocated()` in the notebook's parent
   process reads ~0 when inference runs in a subprocess. Replaced with `nvidia-smi memory.used` sampled
   every 0.5 s during the child process (plus a recorded baseline).
2. **Textured OBJ loads as a `trimesh.Scene`, not a `Trimesh`.** `len(mesh.faces)` raises on a Scene, so the
   conversion cell now concatenates scene geometry and reports the visual kind.

## 11.2 Official Space contract — verified from live source *and* empirically ✅

The repository's `app.py` and the **live Space's** `app.py` are different files. The live one
(`huggingface.co/spaces/TencentARC/InstantMesh/raw/main/app.py`, fetched 2026-11-01) shows:

```python
mv_images = gr.State()

submit.click(fn=check_input_image, inputs=[input_image]).success(
    fn=preprocess,   inputs=[input_image, do_remove_background], outputs=[processed_image],
).success(
    fn=generate_mvs, inputs=[processed_image, sample_steps, sample_seed],
                     outputs=[mv_images, mv_show_images],
).success(
    fn=make3d,       inputs=[mv_images],          # ← state consumed here
                     outputs=[output_model_obj, output_model_glb],
)
```

Findings:

1. **`/make3d` advertises no parameters** while its Python signature *is* `make3d(images)`. That is Gradio
   hiding `gr.State` inputs from the API schema — not a bug in the Space.
2. **The state is server-side and session-scoped.** To confirm the consequence rather than assume it, the
   identical wiring was reproduced locally (Gradio 5.50, same versions as the Space) and driven with
   `gradio_client` 1.14:

   | Test | Result |
   |---|---|
   | Same `Client`: `generate_mvs` → `make3d()` | ✅ works — state persisted between `predict()` calls |
   | Fresh `Client`: `make3d()` with no prior call | ❌ `AppError` — server raised `ValueError: make3d received None: the gr.State was not populated in this session` |
   | Passing the state explicitly: `make3d(grid)` | ❌ `IndexError: list index out of range` — State cannot be supplied by a client |

   **Therefore an integration must keep one Gradio session alive and call the steps in order.** It cannot
   be parallelised, cannot be retried from a cold client, and silently produces wrong/failed results if any
   step is skipped. This is exactly the fragility the `hf_space` provider in this repo guards against by
   failing loudly.
3. **The Space cannot produce a textured mesh.** Its live code calls
   `model.extract_mesh(planes, use_texture_map=False, **infer_config)` — vertex colours only. The turntable
   video is also commented out. So the Space route **cannot** satisfy the "textured" requirement.
4. The Space builds `nvdiffrast` at runtime on first GPU call (`@spaces.GPU(duration=210)`) against a
   hard-coded `CUDA_HOME = /cuda-image/usr/local/cuda-13.0`, and raises a clear error if nvcc moved. ZeroGPU
   hardware has also moved to RTX Pro 6000 Blackwell (48 GB / 96 GB), not A10G.

## 11.3 Which free route is actually most reliable

| Route | Free? | Produces **textured** mesh? | Effort for you | Verdict |
|---|---|---|---|---|
| **Colab free (T4 16 GB)** | ✅ | **✅ yes** (`--export_texmap`) | 3 clicks, one file back | **recommended** |
| Kaggle (T4/P100, 30 GPU-h/wk) | ✅ | ✅ yes | 3 clicks + 1-line tweak | good alternative |
| Official HF Space (ZeroGPU) | ✅ 5 GPU-min/day | ❌ **no** (vertex colours only) | needs app hosted with open egress | not sufficient for this criterion |
| Your own ZeroGPU Space (`space/`) | ✅ | ⚠️ only if you enable `use_texture_map=True` and accept slower runs | deploy + 115 s GPU budget/run | possible, more work |
| Replicate | ❌ ~$0.14/run | ✅ | 1 API call | **excluded** (no paid credits) |

**Conclusion: Colab free is the only genuinely free route that satisfies "textured mesh".** It is also the
only one where the GPU is not time-sliced mid-run, which matters because a 75-step diffusion pass plus
128³ FlexiCubes extraction should not be interrupted.

## 11.4 Application can accept the resulting mesh — implemented & tested ✅

`POST /api/import` (multipart: `files[]`, optional `metrics`, optional `origin_note`):

* accepts `.glb`, or `.obj` + `.mtl` + texture images (siblings are retained as extra downloads)
* **structurally validates the GLB before accepting it** — bufferView bounds, accessor sizes, magic, total length
* stamps `origin: "external_import"`, `provider: "external_import"`, message *"External mesh imported (not
  generated by this server)"* — an imported mesh can never be reported as inference
* returns byte-identical artefacts (verified by SHA-256 roundtrip test)
* the UI shows a persistent badge: `imported mesh — not generated by this server`

## 11.5 In-sandbox verification tooling — built and proven ✅

`tools/verify_mesh.py` (stdlib only: no numpy, no GPU, no browser):

* `inspect` — parses the GLB container byte-by-byte per the glTF 2.0 spec, checks every bufferView stays
  inside the BIN chunk, counts vertices/triangles, detects `TEXCOORD_0` + `baseColorTexture` (textured) vs
  `COLOR_0` (vertex-coloured), decodes embedded PNGs.
* `render` — software rasteriser (perspective projection, z-buffer, flat shading, UV texture sampling,
  embedded PNG decoding incl. all five PNG filter types) writing real turntable PNGs. **This is the
  "opens in a 3D viewer" evidence that does not depend on the notebook's own preview.**

Proven against a purpose-built fixture (`tools/make_test_mesh.py`, a 9,216-triangle UV-mapped
checkerboard sphere with an embedded 512×512 PNG): the verifier reports `uv_mapped: true`, and its rendered
output shows the checkerboard correctly from all angles, so a failure on a real mesh means the *mesh* is bad,
not the tool.

**Test suite: 22 tests passing** (`python -m pytest app/tests -q`), including corrupt-GLB rejection,
byte-identical import roundtrip, OBJ+MTL+texture retention, and "import is never labelled inference".

## 11.6 Evidence status

| Claim | Status |
|---|---|
| Sandbox cannot run InstantMesh | ✅ proven (no GPU, weights unreachable) |
| Official Space API is stateful and fragile | ✅ proven (live source + local empirical reproduction) |
| Space cannot output textures | ✅ proven (live source: `use_texture_map=False`) |
| App accepts and validates external meshes | ✅ proven (byte-identical roundtrip, corrupt file rejected) |
| Verifier can render a real GLB | ✅ proven on a synthetic textured fixture |
| Notebook follows the official pipeline | ✅ verified line-by-line (+ 3 bugs fixed) |
| **A real InstantMesh mesh was generated** | ⏳ **pending the Colab run — cannot be done in this sandbox** |

**Real generation time, GPU, peak VRAM and output size are deliberately left blank rather than guessed.**
They will be filled from `metrics.json` returned by the Colab run — see `RUN_VALIDATION.md`.

## 11.7 GitHub Actions as a runner — investigated, and it splits in two

The question "can't you use a GitHub workflow?" has two different answers.

### (a) Can Actions *compute* the inference for free? — **No.**

| Runner | GPU? | Cost |
|---|---|---|
| `ubuntu-latest` (standard, public repo) | ❌ none | **free, unlimited** |
| `ubuntu-latest` (standard, private repo) | ❌ none | 2,000 min/month free |
| Larger runner, **4-core + NVIDIA T4 (16 GB)** | ✅ T4 | **$0.052/min ($3.12/h)**, Team/Enterprise plan + card |

Verified against GitHub's runner reference and billing docs (Oct 2026): standard runners are CPU-only;
GPU runners are "larger runners", which are **always billed even on public repositories**, require the
Team/Enterprise plan and a payment method, and never draw on included minutes. Self-hosted runners are
free *of GitHub charges* but you must own the GPU — which is circular for this task.

So a free GitHub Actions job cannot run InstantMesh. It would also fail on resources even if CUDA were
patched out: the public runner is 4 vCPU / 16 GB with no CUDA toolkit and a 6 h job ceiling.

### (b) Can Actions *drive* a free GPU host? — **Yes in principle, blocked in this repo.**

Runners have open egress, unlike this sandbox. So `.github/workflows/instantmesh-zerogpu.yml` +
`tools/hfspace_inference.py` were written to: probe egress → call the Space's three endpoints on one
client (the session-bound `gr.State` chain) → download the mesh → verify it with `tools/verify_mesh.py` →
render turntable frames → upload everything as a workflow artifact. That would make the real-mesh run
**zero-touch**.

Empirically blocked here:

```
GET  /repos/.../actions/workflows        → 200 {"total_count": 0, "workflows": []}
POST /repos/.../actions/workflows/instantmesh-zerogpu.yml/dispatches → 403 Resource not accessible by integration
GET  /repos/mhammedamazil-hub/Testrepo   → permissions.admin = true   (but App token lacks actions:write)
```

The workflow file is present on the branch (verified via the contents API), so this is not a push problem:
Actions is either disabled for the repository or the GitHub connection lacks Actions write. Enabling it
needs a human in `Settings → Actions → General → Allow all actions`, or a reconnection of the Arena GitHub
integration with Actions permission.

### Why (b) is still not a full substitute for Colab

Even once enabled, this route produces a **vertex-coloured** mesh: the live Space calls
`extract_mesh(..., use_texture_map=False)` (§11.2). It also runs against the free ZeroGPU quota
(~2 GPU-min/day anonymous, ~5 authenticated), and a 75-step diffusion pass plus FlexiCubes extraction can
exceed the anonymous allowance, so it would want an `HF_TOKEN` repository secret.

**Net:** Actions is a legitimate free *orchestrator* and a poor free *computer*. For a textured mesh with
predictable quota, free Colab (T4, ~15–30 GPU-h/week) remains the reliable route — `RUN_VALIDATION.md`.
