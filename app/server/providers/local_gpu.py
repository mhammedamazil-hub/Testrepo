"""Provider: the official InstantMesh repository running on a local NVIDIA GPU.

This drives ``integrations/local_gpu/instantmesh_generate.py`` (shipped with this
repo), which reuses the official model code from
``src.models.lrm_mesh.InstantMesh`` / ``src.utils.mesh_util.save_glb`` and writes
both a GLB and an OBJ. The official ``run.py`` CLI only writes OBJ, which is why
we wrap it instead of shelling out to ``run.py`` directly.

Preconditions, verified from the repo (not guessed):
  * PyTorch >= 2.1.0, CUDA >= 12.1, xformers, nvdiffrast (compiled from source)
  * ~7.3 GB of weights pulled from the Hub on first run
  * a CUDA GPU; the official code hard-codes ``torch.device('cuda')``
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
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

SCRIPT = Path(__file__).resolve().parents[3] / "integrations" / "local_gpu" / "instantmesh_generate.py"


class LocalGpuProvider(ImageTo3DProvider):
    name = "local_gpu"
    label = "Local NVIDIA GPU (official InstantMesh repo)"
    real_inference = True
    required_env = ("CUDA GPU", "LOCAL_GPU_REPO")

    def __init__(self, python: str, repo: str, config: str):
        self.python = python
        self.repo = Path(repo)
        self.config = config

    def is_configured(self) -> bool:
        return self.repo.exists() and (self.repo / "src" / "models" / "lrm_mesh.py").exists()

    def probe(self) -> ProbeResult:
        if not self.is_configured():
            return ProbeResult(False, f"InstantMesh repo not found at {self.repo}")
        try:
            out = subprocess.run(
                [self.python, "-c", "import torch;print(int(torch.cuda.is_available()))"],
                capture_output=True,
                text=True,
                timeout=90,
            )
            ok = out.stdout.strip().endswith("1")
            if not ok:
                return ProbeResult(False, f"torch present but no CUDA device (stderr={out.stderr.strip()[:200]})")
            return ProbeResult(True, "torch sees a CUDA device")
        except FileNotFoundError:
            return ProbeResult(False, f"python interpreter not found: {self.python}")
        except Exception as exc:  # noqa: BLE001
            return ProbeResult(False, f"probe failed: {exc}")

    def generate(
        self,
        image_path: Path,
        options: GenerationOptions,
        workdir: Path,
        progress: ProgressFn,
    ) -> GenerationResult:
        if not self.is_configured():
            raise ProviderUnavailable(
                f"InstantMesh repo not found at {self.repo}; set LOCAL_GPU_REPO to a clone of "
                "github.com/TencentARC/InstantMesh"
            )
        if not SCRIPT.exists():
            raise ProviderUnavailable(f"wrapper script missing: {SCRIPT}")

        cmd = [
            self.python,
            str(SCRIPT),
            "--config", self.config,
            "--image", str(image_path),
            "--out", str(workdir),
            "--seed", str(options.seed),
            "--steps", str(options.steps),
        ]
        if not options.remove_background:
            cmd.append("--no-rembg")
        if options.export_texmap:
            cmd.append("--export-texmap")

        env = dict(os.environ, PYTHONUNBUFFERED="1")
        progress("launch", 5, "Starting InstantMesh on the local GPU")
        proc = subprocess.Popen(
            cmd, cwd=str(self.repo), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        tail: list[str] = []
        assert proc.stdout is not None
        for line in proc.stdout:
            tail.append(line.rstrip())
            tail = tail[-40:]
            m = re.search(r"STAGE:(\w+):(\d+):(.*)", line)
            if m:
                progress(m.group(1), int(m.group(2)), m.group(3).strip())
        code = proc.wait()
        if code != 0:
            raise ProviderError("InstantMesh exited with code {}:\n{}".format(code, "\n".join(tail[-15:])))

        manifest = workdir / "manifest.json"
        if not manifest.exists():
            raise ProviderError("InstantMesh finished but produced no manifest.json")
        data = json.loads(manifest.read_text())
        result = GenerationResult(metadata={"provider": self.name, **data.get("metadata", {})})
        for kind, key in (("glb", "glb_path"), ("obj", "obj_path"), ("multiview", "multiview_path"), ("video", "video_path")):
            value = data.get(key)
            if value and Path(value).exists():
                dest = workdir / f"instantmesh.{kind if kind != 'multiview' else 'png'}"
                shutil.copyfile(value, dest)
                setattr(result, f"{kind}_path", dest)
        progress("export", 100, "Local GPU job finished")
        return result
