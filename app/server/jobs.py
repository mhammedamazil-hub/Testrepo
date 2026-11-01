"""Job store + worker pool.

In-process and deliberately small: an honest reference implementation. For
multi-replica production, swap ``JobStore`` for Redis/RQ or a queue service; the
HTTP contract does not change.
"""
from __future__ import annotations

import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import Settings
from .providers.base import GenerationOptions, ImageTo3DProvider, ProviderError, ProviderUnavailable

ARTIFACTS = {
    "glb": "glb_path",
    "obj": "obj_path",
    "multiview": "multiview_path",
    "video": "video_path",
}


@dataclass
class Job:
    id: str
    provider: str
    filename: str
    created_at: float
    options: GenerationOptions
    status: str = "queued"  # queued | running | succeeded | failed
    stage: str = "queued"
    progress: int = 0
    message: str = "Queued"
    simulated: bool = False
    error: Optional[str] = None
    error_kind: Optional[str] = None
    files: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    duration_s: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "message": self.message,
            "simulated": self.simulated,
            "error": self.error,
            "error_kind": self.error_kind,
            "created_at": self.created_at,
            "duration_s": self.duration_s,
            "source_filename": self.filename,
            "options": self.options.__dict__,
            "files": {
                kind: f"/api/jobs/{self.id}/download/{kind}" for kind in self.files if self.files.get(kind)
            },
            "metadata": self.metadata,
        }


class JobStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=max(1, settings.max_concurrent_jobs))
        settings.storage_dir.mkdir(parents=True, exist_ok=True)

    # -- lifecycle ----------------------------------------------------
    def create(self, image_bytes: bytes, filename: str, options: GenerationOptions, provider: ImageTo3DProvider) -> Job:
        job_id = uuid.uuid4().hex[:16]
        job_dir = self.settings.storage_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(filename).suffix.lower() or ".png"
        (job_dir / f"input{suffix}").write_bytes(image_bytes)

        job = Job(
            id=job_id,
            provider=provider.name,
            filename=filename,
            created_at=time.time(),
            options=options,
        )
        with self._lock:
            self._jobs[job_id] = job
        self._pool.submit(self._run, job, job_dir / f"input{suffix}", job_dir)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def delete(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.pop(job_id, None)
        if job:
            shutil.rmtree(self.settings.storage_dir / job_id, ignore_errors=True)
        return job is not None

    def cleanup(self) -> int:
        cutoff = time.time() - self.settings.job_ttl_hours * 3600
        removed = 0
        for job in self.list():
            if job.created_at < cutoff and job.status in {"succeeded", "failed"}:
                if self.delete(job.id):
                    removed += 1
        return removed

    # -- worker -------------------------------------------------------
    def _run(self, job: Job, image_path: Path, job_dir: Path) -> None:
        from .providers.registry import resolve

        started = time.time()

        def progress(stage: str, pct: int, message: str) -> None:
            job.stage = stage
            job.progress = max(0, min(100, pct))
            job.message = message
            job.status = "running"

        try:
            provider = resolve(self.settings, job.provider)
            job.status = "running"
            job.message = f"Using provider: {provider.label}"
            job.simulated = not provider.real_inference
            result = provider.generate(image_path, job.options, job_dir, progress)
            job.simulated = result.simulated
            job.files = {
                kind: str(getattr(result, attr))
                for kind, attr in ARTIFACTS.items()
                if getattr(result, attr)
            }
            job.metadata = result.metadata or {}
            job.status = "succeeded"
            job.stage = "done"
            job.progress = 100
            job.message = (
                "Simulation finished (not AI output)"
                if result.simulated
                else "Mesh generated successfully"
            )
        except ProviderUnavailable as exc:
            job.status = "failed"
            job.error_kind = "provider_unavailable"
            job.error = str(exc)
            job.message = "Provider unavailable"
        except ProviderError as exc:
            job.status = "failed"
            job.error_kind = "inference_failed"
            job.error = str(exc)
            job.message = "Inference failed"
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error_kind = "internal_error"
            job.error = f"{type(exc).__name__}: {exc}"
            job.message = "Internal error"
        finally:
            job.duration_s = round(time.time() - started, 2)
