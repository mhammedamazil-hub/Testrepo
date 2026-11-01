"""Provider: the official TencentARC/InstantMesh Gradio Space, called over its
Gradio API (``gradio_api``), which runs on ZeroGPU.

Verified contract (probed 2026-11-01 from ``/gradio_api/info``):

    /check_input_image (image)
    /preprocess        (image, do_remove_background) -> processed image
    /generate_mvs      (processed image, sample_steps, sample_seed) -> multiview grid
    /make3d            () -> (OBJ FileData, GLB FileData)

Note the asymmetry: ``/make3d`` declares **no parameters** because the official
UI passes a ``gr.State`` object (the generated multiview image) between steps.
The state is stored server-side keyed by the Gradio session hash, so the three
calls must be made on the *same* ``gradio_client.Client`` instance (which keeps
one session hash). If the Space ever drops that state, this provider fails loudly
rather than silently returning something wrong.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .base import (
    GenerationOptions,
    GenerationResult,
    ImageTo3DProvider,
    ProbeResult,
    ProgressFn,
    ProviderError,
    ProviderUnavailable,
)


def _first_file(value: Any) -> Path | None:
    """Gradio returns filepaths as str, dict(path=...), or a tuple of those."""
    if isinstance(value, (list, tuple)):
        for item in value:
            found = _first_file(item)
            if found:
                return found
        return None
    if isinstance(value, dict):
        value = value.get("path") or value.get("url")
    if isinstance(value, str) and ("/" in value or "\\" in value) and Path(value).exists():
        return Path(value)
    return None


class HfSpaceProvider(ImageTo3DProvider):
    name = "hf_space"
    label = "Official HF Space (TencentARC/InstantMesh, ZeroGPU)"
    real_inference = True
    required_env = ("gradio_client (pip)",)

    def __init__(self, space_id: str, token: str | None, timeout_s: int = 900):
        self.space_id = space_id
        self.token = token
        self.timeout_s = timeout_s

    # -- availability -------------------------------------------------
    def is_configured(self) -> bool:
        try:
            import gradio_client  # noqa: F401
        except Exception:
            return False
        return True

    def probe(self) -> ProbeResult:
        import time
        import urllib.request

        url = f"https://{self.space_id.replace('/', '-').lower().replace('_', '-')}.hf.space/config"
        started = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "instantmesh-app/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp.read(2048)
            return ProbeResult(True, f"space config reachable ({url})", int((time.time() - started) * 1000))
        except Exception as exc:  # noqa: BLE001
            return ProbeResult(False, f"unreachable: {type(exc).__name__}: {exc}")

    def _client(self):
        try:
            from gradio_client import Client
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailable(
                "gradio_client is not installed. `pip install gradio_client` to use this provider."
            ) from exc
        try:
            return Client(self.space_id, hf_token=self.token, verbose=False)
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailable(f"cannot connect to HF Space {self.space_id}: {exc}") from exc

    # -- inference ----------------------------------------------------
    def generate(
        self,
        image_path: Path,
        options: GenerationOptions,
        workdir: Path,
        progress: ProgressFn,
    ) -> GenerationResult:
        from gradio_client import handle_file

        progress("connect", 5, f"Connecting to {self.space_id}")
        client = self._client()

        try:
            progress("preprocess", 15, "Space: background removal + framing")
            processed = client.predict(
                handle_file(str(image_path)),
                options.remove_background,
                api_name="/preprocess",
            )
            processed_path = _first_file(processed)
            if processed_path is None:
                raise ProviderError(f"/preprocess returned no file: {processed!r}")

            progress("multiview", 35, f"Space: Zero123++ sampling ({options.steps} steps, seed {options.seed})")
            mvs = client.predict(
                handle_file(str(processed_path)),
                options.steps,
                options.seed,
                api_name="/generate_mvs",
            )
            mv_path = _first_file(mvs)

            progress("reconstruct", 70, "Space: LRM + FlexiCubes mesh extraction")
            mesh = client.predict(api_name="/make3d")
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"HF Space inference failed: {type(exc).__name__}: {exc}") from exc

        files = [p for p in (_first_file(item) for item in (mesh if isinstance(mesh, (list, tuple)) else [mesh])) if p]
        if not files:
            raise ProviderError(f"/make3d returned no mesh file: {mesh!r}")

        result = GenerationResult(metadata={"provider": self.name, "space": self.space_id})
        for f in files:
            suffix = f.suffix.lower()
            dest = workdir / f"instantmesh{suffix}"
            shutil.copyfile(f, dest)
            if suffix == ".glb":
                result.glb_path = dest
            elif suffix == ".obj":
                result.obj_path = dest
        if mv_path:
            result.multiview_path = workdir / "multiview.png"
            shutil.copyfile(mv_path, result.multiview_path)
        if not result.glb_path and not result.obj_path:
            raise ProviderError(f"/make3d produced only unexpected files: {[f.name for f in files]}")

        progress("export", 100, "Space: mesh downloaded")
        return result

    def describe(self) -> dict:
        info = super().describe()
        info.update(
            {
                "space_id": self.space_id,
                "authenticated": bool(self.token),
                "notes": (
                    "Anonymous ZeroGPU quota is ~2 GPU-min/day; an HF token raises it to the "
                    "account quota (~5 min/day free, resets 24h after first use)."
                ),
            }
        )
        return info
