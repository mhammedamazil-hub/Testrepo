"""Provider abstraction.

Every backend that can turn one image into one real mesh implements
``ImageTo3DProvider``. The HTTP layer and the frontend know nothing about any
specific vendor, so swapping providers never touches the UI.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

ProgressFn = Callable[[str, int, str], None]
"""progress(stage, percent, human_message)"""


class ProviderError(RuntimeError):
    """Inference failed for a reason we want the user to see."""


class ProviderUnavailable(ProviderError):
    """Provider is not configured, or the network cannot reach it."""


class NotImplementedProvider(ProviderUnavailable):
    """Provider exists in code but has no working backend yet."""


@dataclass
class GenerationOptions:
    seed: int = 42
    steps: int = 75
    remove_background: bool = True
    export_texmap: bool = False
    export_video: bool = False


@dataclass
class GenerationResult:
    """Paths to artifacts produced by a provider.

    ``simulated`` is True only for the mock provider. The UI refuses to present
    a simulated result as AI output.
    """

    glb_path: Optional[Path] = None
    obj_path: Optional[Path] = None
    multiview_path: Optional[Path] = None
    video_path: Optional[Path] = None
    simulated: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class ProbeResult:
    reachable: bool
    detail: str
    latency_ms: Optional[int] = None


class ImageTo3DProvider(abc.ABC):
    name: str = "base"
    label: str = "Base provider"
    #: True when the provider produces a real mesh from a real model.
    real_inference: bool = True
    #: Env vars this provider needs (names only, never values).
    required_env: tuple[str, ...] = ()

    def is_configured(self) -> bool:
        return True

    def probe(self) -> ProbeResult:
        return ProbeResult(reachable=True, detail="no probe implemented")

    @abc.abstractmethod
    def generate(
        self,
        image_path: Path,
        options: GenerationOptions,
        workdir: Path,
        progress: ProgressFn,
    ) -> GenerationResult:
        """Run image-to-3D. Must raise ProviderError on failure."""

    def describe(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "real_inference": self.real_inference,
            "configured": self.is_configured(),
            "required_env": list(self.required_env),
        }
