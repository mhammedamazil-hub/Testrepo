"""Provider: Replicate-hosted InstantMesh (Cog model), JSON HTTP API.

Verified 2026-11-01: ``aryamansital/instant_mesh`` is live and exposes
``image_path, remove_background, export_video, export_texmap, sample_steps, seed``
and returns files (multiview png, video, obj, glb). Replicate's own page quotes
~$0.14 per run on A100-80GB (~103 s typical).

``camenduru/instantmesh`` (linked from the official README) is **404 now** — do
not build against it.

Billing is per second of active GPU time, so this provider reports the runtime it
observed in ``metadata`` to keep cost reporting honest.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import time
import urllib.error
import urllib.request
from pathlib import Path

from .base import (
    GenerationOptions,
    GenerationResult,
    ImageTo3DProvider,
    ProbeResult,
    ProgressFn,
    ProviderError,
    ProviderUnavailable,
)

API = "https://api.replicate.com/v1"
GLB_MAGIC = b"glTF"


def _glb_or_obj(raw: bytes) -> str | None:
    head = raw[:4]
    if head == GLB_MAGIC:
        return "glb"
    stripped = raw.lstrip()[:2]
    if stripped in (b"v ", b"# ", b"mt"):
        return "obj"
    if raw[:3] == b"\xff\xd8\xff" or raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if raw[4:8] == b"ftyp":
        return "mp4"
    return None


class ReplicateProvider(ImageTo3DProvider):
    name = "replicate"
    label = "Replicate (hosted InstantMesh Cog model)"
    real_inference = True
    required_env = ("REPLICATE_API_TOKEN",)

    def __init__(self, model: str, token: str | None, timeout_s: int = 900):
        self.model = model
        self.token = token
        self.timeout_s = timeout_s

    def is_configured(self) -> bool:
        return bool(self.token)

    def _request(self, url: str, payload: dict | None = None, method: str = "GET") -> dict:
        data = None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "instantmesh-app/1.0",
        }
        if payload is not None:
            data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())

    def probe(self) -> ProbeResult:
        started = time.time()
        try:
            req = urllib.request.Request(f"{API}/models/{self.model}", headers={"User-Agent": "instantmesh-app/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())
            return ProbeResult(
                True,
                f"model {body.get('owner')}/{body.get('name')} reachable (latest version {body.get('latest_version', {}).get('id', '?')[:12]})",
                int((time.time() - started) * 1000),
            )
        except Exception as exc:  # noqa: BLE001
            return ProbeResult(False, f"unreachable: {type(exc).__name__}: {exc}")

    def generate(
        self,
        image_path: Path,
        options: GenerationOptions,
        workdir: Path,
        progress: ProgressFn,
    ) -> GenerationResult:
        if not self.token:
            raise ProviderUnavailable("REPLICATE_API_TOKEN is not set")

        raw = image_path.read_bytes()
        mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
        payload = {
            "input": {
                "image_path": f"data:{mime};base64,{base64.b64encode(raw).decode()}",
                "remove_background": options.remove_background,
                "export_video": options.export_video,
                "export_texmap": options.export_texmap,
                "sample_steps": options.steps,
                "seed": options.seed,
            }
        }

        progress("submit", 5, f"Submitting to Replicate ({self.model})")
        try:
            pred = self._request(f"{API}/models/{self.model}/predictions", payload, method="POST")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:400]
            raise ProviderError(f"Replicate rejected the request ({exc.code}): {detail}") from exc
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailable(f"cannot reach Replicate: {exc}") from exc

        started = time.time()
        status = pred.get("status")
        while status not in {"succeeded", "failed", "canceled"}:
            if time.time() - started > self.timeout_s:
                raise ProviderError(f"Replicate prediction timed out after {self.timeout_s}s")
            elapsed = int(time.time() - started)
            progress("waiting", min(35 + elapsed // 2, 85), f"Replicate status={status} ({elapsed}s)")
            time.sleep(3)
            pred = self._request(pred["urls"]["get"])

        if pred.get("status") != "succeeded":
            raise ProviderError(f"Replicate prediction {pred.get('status')}: {pred.get('error')}")

        runtime = round(time.time() - started, 1)
        progress("download", 88, f"Prediction finished in {runtime}s, downloading artifacts")

        urls = pred.get("output")
        if isinstance(urls, dict):
            urls = [v for v in urls.values() if isinstance(v, str)]
        if isinstance(urls, str):
            urls = [urls]
        if not urls:
            raise ProviderError(f"Replicate returned no output: {pred.get('output')!r}")

        result = GenerationResult(
            metadata={"provider": self.name, "model": self.model, "prediction_id": pred.get("id"), "runtime_s": runtime}
        )
        for url in urls:
            with urllib.request.urlopen(url, timeout=120) as resp:
                body = resp.read()
            kind = _glb_or_obj(body)
            if kind == "glb":
                result.glb_path = workdir / "instantmesh.glb"
                result.glb_path.write_bytes(body)
            elif kind == "obj":
                result.obj_path = workdir / "instantmesh.obj"
                result.obj_path.write_bytes(body)
            elif kind == "png":
                result.multiview_path = workdir / "multiview.png"
                result.multiview_path.write_bytes(body)
            elif kind == "mp4":
                result.video_path = workdir / "preview.mp4"
                result.video_path.write_bytes(body)

        if not result.glb_path and not result.obj_path:
            raise ProviderError("Replicate output contained no GLB/OBJ mesh")
        progress("export", 100, "Replicate artifacts downloaded")
        return result

    def describe(self) -> dict:
        info = super().describe()
        info.update({"model": self.model, "notes": "per-second GPU billing; ~$0.14/run at A100 for this model"})
        return info
