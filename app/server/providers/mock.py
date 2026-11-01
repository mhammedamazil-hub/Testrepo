"""Mock provider: exercises the full pipeline WITHOUT any AI inference.

It emits a procedurally generated cube (valid GLB + OBJ) and a placeholder PNG,
and every artifact is tagged ``simulated=True``. This exists purely so that
upload -> job -> progress -> 3D preview -> download can be tested
deterministically and offline. It is never a substitute for real generation and
the UI labels it loudly.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

from .base import GenerationOptions, GenerationResult, ImageTo3DProvider, ProgressFn


def _png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    r, g, b = rgb
    row = b"\x00" + bytes((r, g, b)) * width
    raw = row * height
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


_VERTICES = [
    (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
    (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
]
_INDICES = [
    0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7,
    0, 1, 5, 0, 5, 4, 3, 7, 6, 3, 6, 2,
    0, 4, 7, 0, 7, 3, 1, 2, 6, 1, 6, 5,
]


def _write_glb(path: Path) -> None:
    positions = b"".join(struct.pack("<3f", *v) for v in _VERTICES)
    indices = b"".join(struct.pack("<H", i) for i in _INDICES)
    while len(indices) % 4:
        indices += b"\x00"
    binary = positions + indices

    gltf = {
        "asset": {"version": "2.0", "generator": "arena-sandbox mock provider (SIMULATED)"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "SIMULATED_NOT_AI"}],
        "meshes": [
            {
                "name": "SIMULATED_NOT_AI",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0},
                        "indices": 1,
                        "material": 0,
                        "mode": 4,
                    }
                ],
            }
        ],
        "materials": [
            {
                "name": "placeholder",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.85, 0.25, 0.25, 1.0],
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.7,
                },
            }
        ],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(positions), "target": 34962},
            {"buffer": 0, "byteOffset": len(positions), "byteLength": len(indices), "target": 34963},
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": len(_VERTICES),
                "type": "VEC3",
                "min": [-1.0, -1.0, -1.0],
                "max": [1.0, 1.0, 1.0],
            },
            {"bufferView": 1, "componentType": 5123, "count": len(_INDICES), "type": "SCALAR"},
        ],
    }

    import json

    json_chunk = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_chunk) % 4:
        json_chunk += b" "

    total = 12 + 8 + len(json_chunk) + 8 + len(binary)
    with path.open("wb") as fh:
        fh.write(struct.pack("<4sII", b"glTF", 2, total))
        fh.write(struct.pack("<I4s", len(json_chunk), b"JSON"))
        fh.write(json_chunk)
        fh.write(struct.pack("<I4s", len(binary), b"BIN\x00"))
        fh.write(binary)


def _write_obj(path: Path) -> None:
    lines = ["# SIMULATED placeholder - not AI output"]
    for v in _VERTICES:
        lines.append("v {} {} {}".format(*v))
    for i in range(0, len(_INDICES), 3):
        a, b, c = _INDICES[i], _INDICES[i + 1], _INDICES[i + 2]
        lines.append(f"f {a + 1} {b + 1} {c + 1}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class MockProvider(ImageTo3DProvider):
    name = "mock"
    label = "Mock / simulation (no AI inference)"
    real_inference = False
    required_env: tuple[str, ...] = ()

    def probe(self):
        from .base import ProbeResult

        return ProbeResult(reachable=True, detail="local, always available")

    def generate(
        self,
        image_path: Path,
        options: GenerationOptions,
        workdir: Path,
        progress: ProgressFn,
    ) -> GenerationResult:
        import time

        progress("upload", 5, "Mock: received image " + image_path.name)
        time.sleep(0.2)
        progress("preprocess", 20, "Mock: skipping background removal")
        time.sleep(0.2)
        progress("multiview", 45, "Mock: pretending to run Zero123++ (no GPU)")
        time.sleep(0.2)
        progress("reconstruct", 75, "Mock: pretending to run the LRM mesh decoder")
        time.sleep(0.2)

        glb = workdir / "SIMULATED_NOT_AI.glb"
        obj = workdir / "SIMULATED_NOT_AI.obj"
        mv = workdir / "SIMULATED_multiview.png"
        _write_glb(glb)
        _write_obj(obj)
        mv.write_bytes(_png(320, 213, (45, 55, 72)))

        progress("export", 100, "Mock: wrote placeholder cube (simulated)")
        return GenerationResult(
            glb_path=glb,
            obj_path=obj,
            multiview_path=mv,
            simulated=True,
            metadata={"note": "Procedural cube from the mock provider. Not AI output."},
        )
