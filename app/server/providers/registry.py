"""Provider registry: instantiate every known provider without side effects."""
from __future__ import annotations

from .base import ImageTo3DProvider
from .hf_space import HfSpaceProvider
from .local_gpu import LocalGpuProvider
from .mock import MockProvider
from .replicate import ReplicateProvider


def build_providers(settings) -> dict[str, ImageTo3DProvider]:
    return {
        "mock": MockProvider(),
        "hf_space": HfSpaceProvider(settings.hf_space_id, settings.hf_token, settings.hf_timeout_s),
        "replicate": ReplicateProvider(settings.replicate_model, settings.replicate_token, settings.replicate_timeout_s),
        "local_gpu": LocalGpuProvider(settings.local_gpu_python, settings.local_gpu_repo, settings.local_gpu_config),
    }


def resolve(settings, name: str | None = None) -> ImageTo3DProvider:
    providers = build_providers(settings)
    key = (name or settings.provider or "mock").strip().lower()
    if key not in providers:
        raise KeyError(f"unknown provider '{key}'; known: {sorted(providers)}")
    return providers[key]
