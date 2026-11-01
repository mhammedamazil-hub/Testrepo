#!/usr/bin/env python3
"""Drive the official InstantMesh HF Space from CI (or anywhere with open egress).

Why this exists: GitHub-hosted standard runners have no GPU, and GPU runners are
paid-only. But runners DO have open internet egress, so they can call the free
ZeroGPU Space and bring the resulting mesh back as an artifact.

Contract notes (verified 2026-11-01, see SANDBOX_INSTANTMESH_AUDIT.md §11.2):
  * /make3d takes NO parameters because the multi-view grid lives in a gr.State.
  * That State is session-scoped, so every call MUST be made on the SAME Client.
  * Passing the state explicitly raises IndexError; a fresh client gets AppError.

Outputs a metrics.json plus the mesh files into --out.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

SPACE = os.environ.get("HF_SPACE_ID", "TencentARC/InstantMesh")
TOKEN = os.environ.get("HF_TOKEN") or None


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def probe(url: str, timeout: int = 20) -> dict:
    import time as _t

    started = _t.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "instantmesh-ci/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(1024)
            return {"url": url, "status": resp.status, "ms": int((_t.time() - started) * 1000)}
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "error": f"{type(exc).__name__}: {exc}",
                "ms": int((_t.time() - started) * 1000)}


def first_file(value):
    """Gradio returns str | dict(path=..) | list/tuple of those. Normalise to a Path."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            found = first_file(item)
            if found:
                return found
        return None
    if isinstance(value, dict):
        value = value.get("path") or value.get("url")
    if isinstance(value, str):
        p = Path(value)
        if p.exists():
            return p
    return None


def sniff(path: Path) -> str:
    head = path.read_bytes()[:16]
    if head[:4] == b"glTF":
        return "glb"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if head[:3] == b"\xff\xd8\xff":
        return "jpg"
    if head[:2] in (b"v ", b"# ") or path.suffix.lower() == ".obj":
        return "obj"
    if head[4:8] == b"ftyp":
        return "mp4"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if path.suffix.lower() == ".mtl":
        return "mtl"
    return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="input photograph")
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--steps", type=int, default=75)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-rembg", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    image = Path(args.image).resolve()
    if not image.exists():
        log(f"FATAL: input image not found: {image}")
        return 2

    metrics: dict = {
        "driver": "tools/hfspace_inference.py",
        "space": SPACE,
        "authenticated": bool(TOKEN),
        "input_image": image.name,
        "input_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "steps": args.steps,
        "seed": args.seed,
        "probes": [
            probe("https://huggingface.co"),
            probe("https://tencentarc-instantmesh.hf.space/config"),
            probe("https://api.replicate.com/v1/models"),
        ],
    }
    log("egress probes: " + json.dumps(metrics["probes"]))

    from gradio_client import Client, handle_file

    log(f"connecting to {SPACE} (authenticated={bool(TOKEN)})")
    try:
        client = Client(SPACE, hf_token=TOKEN, verbose=False)
    except Exception as exc:  # noqa: BLE001
        metrics["fatal"] = f"Client init failed: {type(exc).__name__}: {exc}"
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
        return 3

    t_all = time.time()
    stage_times: dict[str, float] = {}

    # ---- stage 1: preprocess ----
    t0 = time.time()
    try:
        proc = client.predict(handle_file(str(image)), not args.no_rembg, api_name="/preprocess")
    except Exception as exc:  # noqa: BLE001
        metrics["fatal"] = f"/preprocess failed: {type(exc).__name__}: {exc}"
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
        return 4
    stage_times["preprocess_s"] = round(time.time() - t0, 1)
    proc_path = first_file(proc)
    log(f"preprocess -> {proc_path} ({stage_times['preprocess_s']}s)")

    # ---- stage 2: multi-view diffusion (same client = same session) ----
    t0 = time.time()
    try:
        mvs = client.predict(handle_file(str(proc_path or image)), args.steps, args.seed,
                             api_name="/generate_mvs")
    except Exception as exc:  # noqa: BLE001
        metrics["fatal"] = f"/generate_mvs failed: {type(exc).__name__}: {exc}"
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
        return 5
    stage_times["generate_mvs_s"] = round(time.time() - t0, 1)
    mv_path = first_file(mvs)
    log(f"generate_mvs -> {mv_path} ({stage_times['generate_mvs_s']}s)")

    # ---- stage 3: reconstruction (consumes the server-side gr.State) ----
    t0 = time.time()
    try:
        mesh = client.predict(api_name="/make3d")
    except Exception as exc:  # noqa: BLE001
        metrics["fatal"] = (
            f"/make3d failed: {type(exc).__name__}: {exc}. "
            "Most likely cause: the gr.State was not populated in this session "
            "(session expired, or a different client was used)."
        )
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
        return 6
    stage_times["make3d_s"] = round(time.time() - t0, 1)
    log(f"make3d -> {mesh} ({stage_times['make3d_s']}s)")

    metrics["stage_times"] = stage_times
    metrics["total_s"] = round(time.time() - t_all, 1)

    # ---- collect artefacts ----
    candidates = []
    for item in (mesh if isinstance(mesh, (list, tuple)) else [mesh]):
        p = first_file(item)
        if p:
            candidates.append(p)
    if mv_path:
        candidates.append(mv_path)
    if proc_path:
        candidates.append(proc_path)

    saved = []
    used: set[str] = set()
    for src in candidates:
        kind = sniff(src)
        if src == proc_path:
            stem = "processed_input"
        elif src == mv_path:
            stem = "multiview"
        elif kind in ("glb", "obj", "mtl"):
            stem = "instantmesh"
        else:
            stem = "artifact"
        name = f"{stem}.{kind if kind != 'unknown' else src.suffix.lstrip('.') or 'bin'}"
        if name in used:                      # never overwrite: keep both
            name = f"{stem}_{len(used)}.{kind if kind != 'unknown' else 'bin'}"
        used.add(name)
        dest = out / name
        dest.write_bytes(src.read_bytes())
        saved.append({"kind": kind, "file": dest.name, "bytes": dest.stat().st_size,
                      "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()})
        log(f"collected {dest.name} ({dest.stat().st_size} bytes, detected {kind})")

    metrics["artifacts"] = saved
    has_mesh = any(a["kind"] in ("glb", "obj") for a in saved)
    metrics["success"] = has_mesh
    if not has_mesh:
        metrics["fatal"] = "Space returned no GLB/OBJ (raw output: {})".format(str(mesh)[:400])

    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    log("SUCCESS" if has_mesh else "FAILED: no mesh artefact")
    return 0 if has_mesh else 7


if __name__ == "__main__":
    sys.exit(main())
