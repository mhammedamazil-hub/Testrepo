#!/usr/bin/env python3
"""Generate a known-good, UV-mapped, textured GLB to test the verifier itself.

This is a *fixture for testing the verifier*, not a 3D generator: it emits a
checkerboard-textured sphere. If `verify_mesh.py` renders the checkerboard
correctly, then its glTF parser, UV handling and PNG texture sampling all work —
so when a real InstantMesh GLB arrives, a failure means the mesh is bad, not the tool.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import zlib
from pathlib import Path


def checker_png(size: int, squares: int) -> bytes:
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = bytearray()
    cell = size // squares
    for y in range(size):
        raw.append(0)
        for x in range(size):
            on = ((x // cell) + (y // cell)) % 2 == 0
            raw += bytes((235, 235, 240) if on else (35, 60, 110))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + chunk(b"IEND", b""))


def sphere(seg: int, ring: int):
    verts, uvs, idx = [], [], []
    for i in range(ring + 1):
        v = i / ring
        theta = v * math.pi
        for j in range(seg + 1):
            u = j / seg
            phi = u * 2 * math.pi
            verts.append((math.sin(theta) * math.cos(phi), math.cos(theta), math.sin(theta) * math.sin(phi)))
            uvs.append((u, v))
    for i in range(ring):
        for j in range(seg):
            a = i * (seg + 1) + j
            b, c, d = a + seg + 1, a + 1, a + seg + 2
            idx += [a, b, c, c, b, d]
    return verts, uvs, idx


def build(path: Path, seg: int = 96, ring: int = 48) -> None:
    verts, uvs, idx = sphere(seg, ring)
    tex = checker_png(512, 8)

    pos_b = b"".join(struct.pack("<3f", *v) for v in verts)
    uv_b = b"".join(struct.pack("<2f", *t) for t in uvs)
    idx_b = b"".join(struct.pack("<I", i) for i in idx)
    while len(pos_b) % 4:
        pos_b += b"\x00"
    while len(uv_b) % 4:
        uv_b += b"\x00"
    while len(idx_b) % 4:
        idx_b += b"\x00"
    tex_off = len(pos_b) + len(uv_b) + len(idx_b)
    binary = pos_b + uv_b + idx_b + tex

    gltf = {
        "asset": {"version": "2.0", "generator": "make_test_mesh.py (verifier fixture, NOT AI)"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "VERIFIER_FIXTURE_TEXTURED_SPHERE"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "TEXCOORD_0": 1},
                                    "indices": 2, "material": 0, "mode": 4}]}],
        "materials": [{"name": "checkerboard",
                       "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "metallicFactor": 0.0,
                                                "roughnessFactor": 0.8}}],
        "textures": [{"sampler": 0, "source": 0}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}],
        "images": [{"bufferView": 3, "mimeType": "image/png"}],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_b), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_b), "byteLength": len(uv_b), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_b) + len(uv_b), "byteLength": len(idx_b), "target": 34963},
            {"buffer": 0, "byteOffset": tex_off, "byteLength": len(tex)},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(verts), "type": "VEC3",
             "min": [-1, -1, -1], "max": [1, 1, 1]},
            {"bufferView": 1, "componentType": 5126, "count": len(uvs), "type": "VEC2"},
            {"bufferView": 2, "componentType": 5125, "count": len(idx), "type": "SCALAR"},
        ],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    while len(js) % 4:
        js += b" "
    total = 12 + 8 + len(js) + 8 + len(binary)
    with path.open("wb") as fh:
        fh.write(struct.pack("<4sII", b"glTF", 2, total))
        fh.write(struct.pack("<I4s", len(js), b"JSON"))
        fh.write(js)
        fh.write(struct.pack("<I4s", len(binary), b"BIN\x00"))
        fh.write(binary)
    print(f"wrote {path} ({total} bytes, {len(idx)//3} triangles, embedded {len(tex)}-byte PNG texture)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tools/fixtures/textured_sphere.glb")
    ap.add_argument("--seg", type=int, default=96)
    ap.add_argument("--ring", type=int, default=48)
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    build(out, a.seg, a.ring)
