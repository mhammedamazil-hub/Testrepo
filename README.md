# InstantMesh feasibility audit + image-to-3D app

This repository answers one question honestly: **can InstantMesh run here, and if not, what is the cheapest
path to a genuine image-to-3D asset?**

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

## What's in here

| Path | Contents |
|---|---|
| `SANDBOX_INSTANTMESH_AUDIT.md` | the audit (Phases 1–5) |
| `app/` | FastAPI + vanilla-JS image-to-3D app: upload, progress, 3D preview, GLB/OBJ downloads, provider abstraction |
| `app/server/providers/` | `hf_space` · `replicate` · `local_gpu` · `mock` |
| `notebooks/instantmesh_free_gpu.ipynb` | official pipeline on a free Colab T4 / Kaggle GPU → real GLB |
| `space/` | your own ZeroGPU Gradio Space with a clean single-call `/generate` API |
| `integrations/local_gpu/instantmesh_generate.py` | GLB export for the official CLI (which only writes OBJ) |

```bash
pip install -r app/requirements.txt
python -m uvicorn app.server.main:app --host 0.0.0.0 --port 8000   # mock mode by default
python -m pytest app/tests -q                                      # 13 tests
```

InstantMesh is © TencentARC, Apache-2.0. This repo is an independent client and bundles no weights.
