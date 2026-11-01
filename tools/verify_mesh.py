#!/usr/bin/env python3
"""Independent mesh verifier — stdlib only, no GPU, no numpy, no browser.

Purpose: prove that a GLB/OBJ produced elsewhere is a *real, loadable* 3D asset.
Two modes:

    python tools/verify_mesh.py inspect  model.glb
    python tools/verify_mesh.py render   model.glb --out renders/ --frames 6

`inspect` parses the container byte-by-byte (glTF 2.0 spec), checks every
bufferView stays inside the BIN chunk, counts geometry, and reports whether the
mesh carries per-vertex colours (COLOR_0) or a UV-mapped texture
(TEXCOORD_0 + material.baseColorTexture + embedded image).

`render` re-implements just enough of the pipeline (transform, perspective
projection, triangle rasterisation with a z-buffer, texture sampling from an
embedded PNG) to write real shaded turntable PNGs. Those PNGs are the evidence:
if the sandbox renders the mesh from four angles, a 3D viewer can open it.

This deliberately does NOT try to be a general renderer. It supports the subset
InstantMesh/trimesh emit: indexed triangles, POSITION, optional COLOR_0,
optional TEXCOORD_0 with a PNG texture, optional baseColorFactor.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import zlib
from pathlib import Path

# --------------------------------------------------------------------------- PNG

def _png_write(path: Path, width: int, height: int, rgb: bytearray) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    stride = width * 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        + chunk(b"IEND", b"")
    )


def png_decode(data: bytes):
    """Decode 8-bit non-interlaced PNG. Returns (width, height, channels, bytearray)."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, w, h, depth, ctype, interlace = 8, bytearray(), 0, 0, 8, 2, 0
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
    if depth != 8 or interlace != 0:
        raise ValueError(f"unsupported PNG (depth={depth}, interlace={interlace})")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(bytes(idat))

    stride = w * channels
    out = bytearray(h * stride)
    prev = bytearray(stride)
    src = 0
    for y in range(h):
        ftype = raw[src]
        src += 1
        line = bytearray(raw[src:src + stride])
        src += stride
        bpp = channels
        if ftype == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return w, h, channels, out


# --------------------------------------------------------------------------- GLB

COMPONENTS = {
    5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
    5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4),
}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


class Glb:
    def __init__(self, path: Path):
        raw = path.read_bytes()
        if len(raw) < 20:
            raise ValueError("file too small to be a GLB")
        magic, version, total = struct.unpack("<4sII", raw[:12])
        if magic != b"glTF":
            raise ValueError(f"bad magic {magic!r} (expected b'glTF')")
        if version != 2:
            raise ValueError(f"unsupported glTF version {version}")
        if total != len(raw):
            raise ValueError(f"header length {total} != file size {len(raw)}")
        self.file_size = len(raw)
        self.json = None
        self.bin = b""
        pos = 12
        while pos + 8 <= len(raw):
            (clen,) = struct.unpack("<I", raw[pos:pos + 4])
            ctype = raw[pos + 4:pos + 8]
            body = raw[pos + 8:pos + 8 + clen]
            if ctype[:4] == b"JSON":
                self.json = json.loads(body.decode("utf-8"))
            elif ctype[:4] == b"BIN\x00":
                self.bin = body
            pos += 8 + clen + ((4 - clen % 4) % 4 if clen % 4 else 0)
        if self.json is None:
            raise ValueError("GLB has no JSON chunk")
        self.problems: list[str] = []
        self._validate()

    def _validate(self) -> None:
        g = self.json
        if not str(g.get("asset", {}).get("version", "")).startswith("2"):
            self.problems.append("asset.version is not 2.x")
        for i, bv in enumerate(g.get("bufferViews", [])):
            off = bv.get("byteOffset", 0)
            ln = bv.get("byteLength", 0)
            if off + ln > len(self.bin):
                self.problems.append(f"bufferView[{i}] overruns BIN chunk ({off}+{ln} > {len(self.bin)})")
        for i, acc in enumerate(g.get("accessors", [])):
            if "bufferView" not in acc:
                continue
            bv = g["bufferViews"][acc["bufferView"]]
            csize = COMPONENTS[acc["componentType"]][1]
            need = acc["count"] * NCOMP[acc["type"]] * csize
            if need > bv["byteLength"]:
                self.problems.append(f"accessor[{i}] needs {need} bytes but bufferView has {bv['byteLength']}")

    def read_accessor(self, index: int):
        acc = self.json["accessors"][index]
        bv = self.json["bufferViews"][acc["bufferView"]]
        fmt, csize = COMPONENTS[acc["componentType"]]
        n = NCOMP[acc["type"]]
        base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = bv.get("byteStride") or n * csize
        count = acc["count"]
        unpack = struct.Struct("<" + fmt * n).unpack_from
        if stride == n * csize:
            flat = struct.unpack_from("<" + fmt * (n * count), self.bin, base)
            return [flat[i * n:(i + 1) * n] for i in range(count)]
        return [unpack(self.bin, base + i * stride) for i in range(count)]

    def images_decoded(self) -> list[dict]:
        out = []
        for i, img in enumerate(self.json.get("images", [])):
            data = None
            if "bufferView" in img:
                bv = self.json["bufferViews"][img["bufferView"]]
                off = bv.get("byteOffset", 0)
                data = self.bin[off:off + bv["byteLength"]]
            elif str(img.get("uri", "")).startswith("data:"):
                import base64
                data = base64.b64decode(img["uri"].split(",", 1)[1])
            if data is None:
                continue
            try:
                w, h, ch, px = png_decode(data)
                out.append({"index": i, "mime": img.get("mimeType"), "width": w, "height": h,
                            "channels": ch, "pixels": px, "bytes": len(data)})
            except Exception as exc:  # noqa: BLE001
                out.append({"index": i, "mime": img.get("mimeType"), "bytes": len(data), "error": str(exc)})
        return out

    def summary(self) -> dict:
        g = self.json
        prims = [p for m in g.get("meshes", []) for p in m.get("primitives", [])]
        attrs = sorted({a for p in prims for a in p.get("attributes", {})})
        triangles = 0
        positions = 0
        for p in prims:
            pos_idx = p["attributes"].get("POSITION")
            if pos_idx is not None:
                positions += g["accessors"][pos_idx]["count"]
            if "indices" in p:
                triangles += g["accessors"][p["indices"]]["count"] // 3
            elif pos_idx is not None:
                triangles += g["accessors"][pos_idx]["count"] // 3
        mats = g.get("materials", [])
        has_tex = any("baseColorTexture" in m.get("pbrMetallicRoughness", {}) for m in mats)
        images = self.images_decoded()
        return {
            "container": "GLB",
            "file_size_bytes": self.file_size,
            "generator": g.get("asset", {}).get("generator"),
            "nodes": len(g.get("nodes", [])),
            "meshes": len(g.get("meshes", [])),
            "primitives": len(prims),
            "materials": len(mats),
            "textures": len(g.get("textures", [])),
            "images": [
                {k: im[k] for k in ("index", "mime", "width", "height", "bytes") if k in im} for im in images
            ],
            "attributes": attrs,
            "vertices": positions,
            "triangles": triangles,
            "uv_mapped": "TEXCOORD_0" in attrs and has_tex,
            "vertex_colored": "COLOR_0" in attrs,
            "problems": self.problems,
        }

    # -- geometry for the renderer ------------------------------------
    def primitives(self):
        g = self.json
        images = {im["index"]: im for im in self.images_decoded()}
        for mesh in g.get("meshes", []):
            for prim in mesh.get("primitives", []):
                if prim.get("mode", 4) != 4:
                    continue  # triangles only
                pos = self.read_accessor(prim["attributes"]["POSITION"])
                if "indices" in prim:
                    idx = [v[0] for v in self.read_accessor(prim["indices"])]
                else:
                    idx = list(range(len(pos)))
                colors = None
                if "COLOR_0" in prim["attributes"]:
                    acc = g["accessors"][prim["attributes"]["COLOR_0"]]
                    colors = self.read_accessor(prim["attributes"]["COLOR_0"])
                    if acc["componentType"] in (5121, 5123):
                        scale = 255.0 if acc["componentType"] == 5121 else 65535.0
                        colors = [tuple(c / scale for c in row) for row in colors]
                uvs = None
                if "TEXCOORD_0" in prim["attributes"]:
                    acc = g["accessors"][prim["attributes"]["TEXCOORD_0"]]
                    uvs = self.read_accessor(prim["attributes"]["TEXCOORD_0"])
                    if acc["componentType"] == 5123:
                        uvs = [tuple(v / 65535.0 for v in row) for row in uvs]
                base = [1.0, 1.0, 1.0, 1.0]
                tex = None
                if "material" in prim:
                    mat = g["materials"][prim["material"]]
                    base = mat.get("pbrMetallicRoughness", {}).get("baseColorFactor", base)
                    bct = mat.get("pbrMetallicRoughness", {}).get("baseColorTexture")
                    if bct is not None:
                        tdef = g["textures"][bct["index"]]
                        image = images.get(tdef.get("source"))
                        if image and "pixels" in image:
                            tex = image
                yield {"pos": pos, "idx": idx, "colors": colors, "uvs": uvs, "base": base, "tex": tex}


# ------------------------------------------------------------------------ render

def _sample(tex: dict, u: float, v: float):
    w, h, ch, px = tex["width"], tex["height"], tex["channels"], tex["pixels"]
    x = min(w - 1, max(0, int(u * w)))
    y = min(h - 1, max(0, int((1.0 - v) * h)))  # glTF UV origin is top-left
    o = (y * w + x) * ch
    if ch >= 3:
        return px[o] / 255.0, px[o + 1] / 255.0, px[o + 2] / 255.0
    if ch == 1:
        g = px[o] / 255.0
        return g, g, g
    return 0.8, 0.8, 0.8


def render(glb: Glb, out_dir: Path, frames: int = 6, width: int = 320, height: int = 240,
           max_tris: int = 150_000) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    prims = list(glb.primitives())
    if not prims:
        raise ValueError("no triangle primitives to render")

    tris = []  # (xyz0, xyz1, xyz2, color, uv0, uv1, uv2, tex, base)
    for p in prims:
        pos, idx = p["pos"], p["idx"]
        for i in range(0, len(idx) - 2, 3):
            a, b, c = idx[i], idx[i + 1], idx[i + 2]
            if a >= len(pos) or b >= len(pos) or c >= len(pos):
                continue
            tris.append((
                pos[a], pos[b], pos[c],
                p["colors"][a] if p["colors"] else None,
                p["uvs"][a] if p["uvs"] else None,
                p["uvs"][b] if p["uvs"] else None,
                p["uvs"][c] if p["uvs"] else None,
                p["tex"], p["base"],
            ))
    if not tris:
        raise ValueError("no triangles after index expansion")
    original = len(tris)
    if len(tris) > max_tris:
        step = len(tris) // max_tris + 1
        tris = tris[::step]

    xs = [v[0] for t in tris for v in t[:3]]
    ys = [v[1] for t in tris for v in t[:3]]
    zs = [v[2] for t in tris for v in t[:3]]
    cx, cy, cz = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2
    extent = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) or 1.0
    scale = 2.0 / extent
    # radius of the bounding sphere around the normalised geometry
    radius = max(
        math.sqrt((v[0] - cx) ** 2 + (v[1] - cy) ** 2 + (v[2] - cz) ** 2)
        for t in tris[:20000] for v in t[:3]
    ) * scale or 1.0

    light = (0.35, 0.55, 0.75)
    ll = math.sqrt(sum(c * c for c in light))
    light = tuple(c / ll for c in light)
    written = []

    for f in range(frames):
        theta = 2 * math.pi * f / frames
        ct, st = math.cos(theta), math.sin(theta)
        buf = bytearray(b"\x12\x16\x1d" * (width * height))
        zbuf = [-1e9] * (width * height)
        fdist = 3.4
        # Fit the bounding sphere with ~15% margin so nothing is clipped.
        focal = 0.85 * (min(width, height) / 2.0) * fdist / radius
        # Slight elevation so the top of the object is visible, like a product shot.
        cp, sp = math.cos(math.radians(18.0)), math.sin(math.radians(18.0))

        for (p0, p1, p2, col, uv0, uv1, uv2, tex, base) in tris:
            pts = []
            ok = True
            for p in (p0, p1, p2):
                x = (p[0] - cx) * scale
                y = (p[1] - cy) * scale
                z = (p[2] - cz) * scale
                xr = x * ct + z * st
                zr = -x * st + z * ct
                yr = y * cp + zr * sp
                zr = -y * sp + zr * cp
                zc = zr + fdist
                if zc <= 0.05:
                    ok = False
                    break
                pts.append((width / 2 + focal * xr / zc, height / 2 - focal * yr / zc, zc))
            if not ok:
                continue

            ax, ay, az = pts[0]
            bx, by, bz = pts[1]
            gx, gy, gz = pts[2]
            area = (bx - ax) * (gy - ay) - (gx - ax) * (by - ay)
            if abs(area) < 1e-7:
                continue

            # face normal in view space for flat shading
            e1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
            e2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
            nx = e1[1] * e2[2] - e1[2] * e2[1]
            ny = e1[2] * e2[0] - e1[0] * e2[2]
            nz = e1[0] * e2[1] - e1[1] * e2[0]
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            nx, ny, nz = nx / nl, ny / nl, nz / nl
            nxr = nx * ct + nz * st
            nzr = -nx * st + nz * ct
            nyr = ny * cp + nzr * sp
            nzr = -ny * sp + nzr * cp
            lam = abs(nxr * light[0] + nyr * light[1] + nzr * light[2])
            shade = 0.22 + 0.78 * lam

            if tex is not None and uv0 is not None:
                um = (uv0[0] + uv1[0] + uv2[0]) / 3
                vm = (uv0[1] + uv1[1] + uv2[1]) / 3
                r, g, b = _sample(tex, um, vm)
            elif col is not None:
                r, g, b = col[0], col[1], col[2]
            else:
                r, g, b = base[0], base[1], base[2]

            minx = max(0, int(min(ax, bx, gx)))
            maxx = min(width - 1, int(max(ax, bx, gx)) + 1)
            miny = max(0, int(min(ay, by, gy)))
            maxy = min(height - 1, int(max(ay, by, gy)) + 1)
            if maxx < minx or maxy < miny:
                continue
            inv = 1.0 / area
            for py in range(miny, maxy + 1):
                row = py * width
                for px_ in range(minx, maxx + 1):
                    w0 = ((bx - ax) * (py + 0.5 - ay) - (px_ + 0.5 - ax) * (by - ay)) * inv
                    w1 = ((px_ + 0.5 - ax) * (gy - ay) - (gx - ax) * (py + 0.5 - ay)) * inv
                    w2 = 1.0 - w0 - w1
                    if w0 < -0.002 or w1 < -0.002 or w2 < -0.002:
                        continue
                    zc = w0 * az + w1 * bz + w2 * gz
                    depth = -zc
                    if depth <= zbuf[row + px_]:
                        continue
                    zbuf[row + px_] = depth
                    o = (row + px_) * 3
                    buf[o] = min(255, int(r * shade * 255))
                    buf[o + 1] = min(255, int(g * shade * 255))
                    buf[o + 2] = min(255, int(b * shade * 255))

        path = out_dir / f"render_{f:02d}.png"
        _png_write(path, width, height, buf)
        written.append(path)

    return written, {"triangles_total": original, "triangles_rendered": len(tris), "frames": frames}


# -------------------------------------------------------------------------- OBJ

def inspect_obj(path: Path) -> dict:
    v = f = vt = 0
    mtllib = []
    usemtl = set()
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("v "):
            v += 1
        elif line.startswith("vt "):
            vt += 1
        elif line.startswith("f "):
            f += 1
        elif line.startswith("mtllib "):
            mtllib.append(line.split(None, 1)[1].strip())
        elif line.startswith("usemtl "):
            usemtl.add(line.split(None, 1)[1].strip())
    return {
        "container": "OBJ",
        "file_size_bytes": path.stat().st_size,
        "vertices": v,
        "faces": f,
        "uvs": vt,
        "mtllib": mtllib,
        "usemtl": sorted(usemtl),
        "materials_present": [m for m in mtllib if (path.parent / m).exists()],
        "vertex_colored": "vt" == "" and False or (vt == 0 and f > 0),
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Verify a GLB/OBJ without a browser or GPU")
    ap.add_argument("mode", choices=["inspect", "render"])
    ap.add_argument("path")
    ap.add_argument("--out", default="renders")
    ap.add_argument("--frames", type=int, default=6)
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--height", type=int, default=240)
    args = ap.parse_args(argv)

    src = Path(args.path)
    if not src.exists():
        print(json.dumps({"error": f"no such file: {src}"}))
        return 2

    if src.suffix.lower() == ".obj":
        print(json.dumps(inspect_obj(src), indent=2))
        return 0

    try:
        glb = Glb(src)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc), "file": str(src)}))
        return 1

    summary = glb.summary()
    if args.mode == "inspect":
        summary["valid"] = not summary["problems"]
        print(json.dumps(summary, indent=2))
        return 0 if summary["valid"] else 1

    try:
        files, stats = render(glb, Path(args.out), args.frames, args.width, args.height)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": f"render failed: {exc}"}))
        return 1
    summary["renders"] = [str(f) for f in files]
    summary["render_stats"] = stats
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
