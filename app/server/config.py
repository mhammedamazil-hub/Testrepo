"""Runtime configuration. Every secret comes from the server-side environment.

Nothing in this module is ever shipped to the browser except the *booleans*
exposed by /api/providers (e.g. "is this provider configured?").
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    # Which provider to use for real inference: mock | hf_space | replicate | local_gpu
    provider: str = field(default_factory=lambda: os.environ.get("IM_PROVIDER", "mock").strip().lower())

    # ---- Provider: official Hugging Face Space (Gradio API, ZeroGPU) ----
    hf_space_id: str = field(default_factory=lambda: os.environ.get("HF_SPACE_ID", "TencentARC/InstantMesh"))
    hf_token: str | None = field(default_factory=lambda: os.environ.get("HF_TOKEN") or None)
    hf_timeout_s: int = field(default_factory=lambda: _env_int("HF_TIMEOUT_S", 900))

    # ---- Provider: Replicate (hosted InstantMesh, Cog model) ----
    replicate_token: str | None = field(default_factory=lambda: os.environ.get("REPLICATE_API_TOKEN") or None)
    replicate_model: str = field(
        default_factory=lambda: os.environ.get("REPLICATE_MODEL", "aryamansital/instant_mesh")
    )
    replicate_timeout_s: int = field(default_factory=lambda: _env_int("REPLICATE_TIMEOUT_S", 900))

    # ---- Provider: local GPU running the official repo ----
    local_gpu_python: str = field(default_factory=lambda: os.environ.get("LOCAL_GPU_PYTHON", "python"))
    local_gpu_repo: str = field(
        default_factory=lambda: os.environ.get("LOCAL_GPU_REPO", str(REPO_ROOT / "vendor" / "InstantMesh"))
    )
    local_gpu_config: str = field(
        default_factory=lambda: os.environ.get("LOCAL_GPU_CONFIG", "configs/instant-mesh-large.yaml")
    )

    # ---- Server ----
    host: str = field(default_factory=lambda: os.environ.get("IM_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: _env_int("IM_PORT", 8000))
    storage_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("IM_STORAGE_DIR", str(APP_ROOT / "storage")))
    )
    max_upload_bytes: int = field(default_factory=lambda: _env_int("IM_MAX_UPLOAD_BYTES", 12 * 1024 * 1024))
    job_ttl_hours: int = field(default_factory=lambda: _env_int("IM_JOB_TTL_HOURS", 24))
    max_concurrent_jobs: int = field(default_factory=lambda: _env_int("IM_MAX_CONCURRENT_JOBS", 2))
    # Probe provider hosts on /api/providers (useful to prove egress restrictions).
    probe_network: bool = field(default_factory=lambda: _env_bool("IM_PROBE_NETWORK", True))

    def public_summary(self) -> dict:
        """Safe-to-expose view of config. Never includes tokens."""
        return {
            "provider": self.provider,
            "hf_space_id": self.hf_space_id,
            "hf_token_present": bool(self.hf_token),
            "replicate_model": self.replicate_model,
            "replicate_token_present": bool(self.replicate_token),
            "local_gpu_repo": self.local_gpu_repo,
            "local_gpu_config": self.local_gpu_config,
            "max_upload_bytes": self.max_upload_bytes,
        }


settings = Settings()
