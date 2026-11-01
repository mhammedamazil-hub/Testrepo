"""FastAPI application: image upload -> job -> status -> 3D preview -> GLB/OBJ download.

Secrets live only in this process (see config.py). The browser never receives a
token; it only receives booleans like ``configured`` / ``reachable``.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import json

from .config import APP_ROOT, settings
from .jobs import JobStore
from .providers.base import GenerationOptions
from .providers.registry import build_providers, resolve

WEB_DIR = APP_ROOT / "web"
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}

app = FastAPI(title="InstantMesh image-to-3D", version="1.0.0")
store = JobStore(settings)


def _sniff_image(data: bytes) -> str | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "provider": settings.provider, "config": settings.public_summary()}


@app.get("/api/providers")
def providers(probe: bool | None = None) -> dict:
    """Report every provider's configuration and (optionally) its reachability.

    This is the endpoint that makes sandbox network restrictions visible instead
    of silently failing at generation time.
    """
    do_probe = settings.probe_network if probe is None else probe
    out = []
    for name, provider in build_providers(settings).items():
        info = provider.describe()
        info["active"] = name == settings.provider
        if do_probe:
            result = provider.probe()
            info["reachable"] = result.reachable
            info["probe_detail"] = result.detail
            info["probe_latency_ms"] = result.latency_ms
        out.append(info)
    return {"active": settings.provider, "providers": out}


@app.post("/api/jobs")
async def create_job(
    image: UploadFile = File(...),
    provider: str | None = Form(None),
    seed: int = Form(42),
    steps: int = Form(75),
    remove_background: bool = Form(True),
    export_texmap: bool = Form(False),
    export_video: bool = Form(False),
) -> JSONResponse:
    data = await image.read()
    if not data:
        raise HTTPException(400, "empty upload")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, f"image exceeds {settings.max_upload_bytes} bytes")
    mime = _sniff_image(data)
    if mime not in ALLOWED_MIME:
        raise HTTPException(415, "only PNG, JPEG or WebP images are accepted")
    if not 1 <= steps <= 150:
        raise HTTPException(422, "steps must be between 1 and 150")

    try:
        selected = resolve(settings, provider)
    except KeyError as exc:
        raise HTTPException(400, str(exc)) from exc

    options = GenerationOptions(
        seed=seed,
        steps=steps,
        remove_background=remove_background,
        export_texmap=export_texmap,
        export_video=export_video,
    )
    job = store.create(data, image.filename or "upload.png", options, selected)
    return JSONResponse(job.to_dict(), status_code=202)


@app.post("/api/import")
async def import_mesh(
    files: List[UploadFile] = File(...),
    metrics: str | None = Form(None),
    origin_note: str | None = Form(None),
):
    """Accept a mesh produced elsewhere (GLB, or OBJ + MTL + texture) for preview/download.

    The GLB is structurally validated here before it is accepted, so a truncated or
    corrupt file is rejected with a reason instead of being shown as a broken viewer.
    Imported jobs are stamped origin='external_import'; they are never reported as
    inference performed by this app.
    """
    blobs: dict[str, tuple[str, bytes]] = {}
    for f in files:
        name = f.filename or "upload.bin"
        data = await f.read()
        if not data:
            continue
        if len(data) > settings.max_upload_bytes * 4:
            raise HTTPException(413, f"{name} is too large")
        blobs[name.lower()] = (name, data)

    glb = next(((n, d) for k, (n, d) in blobs.items() if k.endswith(".glb")), None)
    obj = next(((n, d) for k, (n, d) in blobs.items() if k.endswith(".obj")), None)
    if not glb and not obj:
        raise HTTPException(415, "provide a .glb, or an .obj (optionally with .mtl and texture images)")

    meta: dict = {"import": {"note": origin_note or "mesh produced outside this app"}}
    if metrics:
        try:
            meta["reported_metrics"] = json.loads(metrics)
        except json.JSONDecodeError as exc:
            raise HTTPException(422, f"metrics is not valid JSON: {exc}") from exc

    if glb:
        from tools.verify_mesh import Glb

        tmp = settings.storage_dir / "_incoming.glb"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(glb[1])
        try:
            parsed = Glb(tmp)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(422, f"GLB failed structural validation: {exc}") from exc
        finally:
            tmp.unlink(missing_ok=True)
        if parsed.problems:
            raise HTTPException(422, f"GLB failed structural validation: {'; '.join(parsed.problems)}")
        summary = parsed.summary()
        summary.pop("images", None)
        meta["glb"] = summary

    artifacts: dict[str, tuple[str, bytes]] = {}
    for name, data in blobs.values():
        low = name.lower()
        if low.endswith(".glb"):
            artifacts["glb"] = (name, data)
        elif low.endswith(".obj"):
            artifacts["obj"] = (name, data)
        elif low.endswith((".mtl", ".png", ".jpg", ".jpeg", ".webp", ".bin")):
            # kept as an extra download so a textured OBJ stays usable
            artifacts[f"extra_{len(artifacts)}"] = (name, data)

    job = store.create_import(artifacts, meta)
    return JSONResponse(job.to_dict(), status_code=201)


@app.get("/api/jobs")
def list_jobs() -> dict:
    return {"jobs": [job.to_dict() for job in store.list()[:50]]}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, "unknown job")
    return job.to_dict()


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str) -> dict:
    return {"deleted": store.delete(job_id)}


@app.get("/api/jobs/{job_id}/download/{kind}")
def download(job_id: str, kind: str):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, "unknown job")
    path = job.files.get(kind)
    if not path or not Path(path).exists():
        raise HTTPException(404, f"artifact '{kind}' not available")
    path = Path(path)
    if job.simulated:
        filename = f"SIMULATED_NOT_AI_{job.id}.{path.suffix.lstrip('.')}"
    else:
        filename = f"instantmesh_{job.id}.{path.suffix.lstrip('.')}"
    return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream", filename=filename)


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


def main() -> None:
    import uvicorn

    store.cleanup()
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
