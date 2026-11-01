# InstantMesh Studio — app

Image → 3D mesh application on top of [`TencentARC/InstantMesh`](https://github.com/TencentARC/InstantMesh),
with a **provider abstraction** so the frontend never changes when you change where inference runs.

```
upload ──▶ POST /api/jobs ──▶ job queue ──▶ provider.generate() ──▶ storage/<job>/
                                                    │
        GET /api/jobs/{id} (poll) ◀─────────────────┘
        GET /api/jobs/{id}/download/{glb|obj|multiview|video}
```

## Quick start

```bash
pip install -r app/requirements.txt
cp app/.env.example .env && set -a && . ./.env && set +a
python -m uvicorn app.server.main:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

Defaults to `IM_PROVIDER=mock`, which produces an explicitly-labelled placeholder cube so you can test the
whole pipeline with no GPU, no network, and no API keys. **It is not AI output and the UI says so.**

## Providers

| name | real inference | needs | notes |
|---|---|---|---|
| `mock` | ❌ | — | placeholder cube, watermarked `SIMULATED_NOT_AI`; for plumbing tests only |
| `hf_space` | ✅ | `pip install gradio_client`, optional `HF_TOKEN` | official `TencentARC/InstantMesh` Space (ZeroGPU). Free quota ≈5 GPU-min/day (~2 anonymous). Chains `/preprocess → /generate_mvs → /make3d`. |
| `replicate` | ✅ | `REPLICATE_API_TOKEN` | `aryamansital/instant_mesh`, ~$0.14/run on A100. No free tier for this model. |
| `local_gpu` | ✅ | CUDA GPU + cloned repo + env | runs `integrations/local_gpu/instantmesh_generate.py`; adds GLB export the official CLI lacks |

Add a provider: subclass `ImageTo3DProvider` in `app/server/providers/`, implement `generate()` + `probe()`,
register it in `registry.py`. Nothing else changes.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness + non-secret config summary |
| GET | `/api/providers` | per-provider `configured` / `reachable` / `probe_detail` + active provider |
| POST | `/api/jobs` | multipart: `image`, `provider?`, `seed`, `steps`, `remove_background`, `export_texmap`, `export_video` → `202 {id}` |
| GET | `/api/jobs/{id}` | status, stage, progress, files, metadata |
| GET | `/api/jobs/{id}/download/{kind}` | `glb` · `obj` · `multiview` · `video` |
| DELETE | `/api/jobs/{id}` | remove job + artifacts |
| GET | `/api/jobs` | last 50 jobs |

Errors are typed: `provider_unavailable` (not configured / unreachable) vs `inference_failed` (model ran and
failed) vs `internal_error`. A provider that cannot run **never** returns a substitute mesh.

## Security model

* All credentials are read from the **server** environment (`app/server/config.py`). The frontend only ever
  receives booleans (`configured`, `reachable`), never a token — asserted by a test.
* Uploads are validated by magic bytes (not just extension), size-capped (`IM_MAX_UPLOAD_BYTES`), and stored
  under a random job id.
* Artifacts expire after `IM_JOB_TTL_HOURS` (default 24 h) on `JobStore.cleanup()`.

## Tests

```bash
python -m pytest app/tests -q      # 13 tests
```

The suite deliberately separates the two kinds of evidence:

* **Simulation tests** (`test_mock_job_end_to_end`, `MockProvider`) prove the plumbing works — they assert
  `simulated is True` and that the filename contains `SIMULATED`.
* **Honesty test** (`test_unconfigured_real_provider_fails_honestly`) asserts that a real provider without
  credentials fails with `provider_unavailable` and zero files, rather than emitting a plausible mesh.

Neither is a model-quality test. Real inference must be verified on a machine with a GPU or open egress —
see `../SANDBOX_INSTANTMESH_AUDIT.md` §9.

## Deployment requirements

* **Open egress** to `huggingface.co` and/or `api.replicate.com`. A server behind an egress allowlist
  (like the audit sandbox) will show every real provider as `reachable: false`.
* Python ≥3.10. No Docker needed; the included `requirements.txt` is enough.
* For >1 replica, replace the in-process `JobStore` with Redis + RQ/Celery and move artifacts to object
  storage with signed URLs.

## Known limits

* Gradio's `gr.State` means the upstream Space's `/make3d` only works on the same session that ran
  `/generate_mvs`; the `hf_space` provider honours that and fails loudly otherwise. Deploy `../space/` if you
  want a stable single-call contract.
* The page's 3D viewer uses `<model-viewer>` from a CDN (browser side only). GLB is previewable; OBJ is
  download-only.
* Sample thumbnails are from the upstream repo's `examples/` (Apache-2.0), copied for convenience.
