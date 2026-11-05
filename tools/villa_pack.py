#!/usr/bin/env python3
"""Pack the villa GLB into VPK1 - a flat, GPU-ready binary for the Android viewer.

Why this exists
---------------
The exported GLB is 52 MB and 723 meshes: a browser glTF viewer needs a real glTF parser
(JSON + 723 node matrices + 1019 sub-meshes + 110 separate images) and that is both slow to
load and slow to draw on a cheap tablet. Geometry is 36 MB of the file - textures are only
15 MB - so shrinking textures alone does not help.

This tool rewrites the *content* of the GLB into a format a 300-line C++ renderer can draw:

  * nodes flattened: every primitive baked into world space (no scene graph in the app);
  * merged per material, then split into chunks of <= 65 535 vertices so the app can use
    16-bit indices everywhere (works on GLES2 hardware without OES_element_index_uint);
  * positions quantised to uint16 inside each chunk's bounding box (6 bytes, not 12);
  * normals quantised to int8 (4 bytes, not 12);
  * textures kept as the original JPEG bytes, embedded in the same file;
  * one file, one memory read, no JSON parsing at runtime.

    python tools/villa_pack.py villa_v2/villa_v2_lite.glb -o android/viewer/app/src/main/assets/model.vpk

Format (little endian) is documented in `android/viewer/app/src/main/cpp/vpk.h`.
"""
import argparse
import json
import os
import struct
import time

vpk_subdiv = True
vpk_fix_normals = True
import sys

import numpy as np

MAGIC = b"VPK1"
VERSION = 1
HEADER_SIZE = 84
DRAW_SIZE = 100
CHUNK = 65535

COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
        5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


class Glb:
    def __init__(self, path):
        raw = open(path, "rb").read()
        magic, ver, length = struct.unpack_from("<III", raw, 0)
        if magic != 0x46546C67:
            raise SystemExit("not a GLB: %s" % path)
        off, self.bin = 12, b""
        while off < length:
            clen, ctype = struct.unpack_from("<II", raw, off)
            body = raw[off + 8:off + 8 + clen]
            if ctype == 0x4E4F534A:
                self.js = json.loads(body.decode("utf-8"))
            elif ctype == 0x004E4942:
                self.bin = body
            off += 8 + clen + ((4 - clen % 4) % 4 if clen % 4 else 0)

    def accessor(self, idx):
        """Return an (count, ncomp) float/int array. Handles strides + sparse-free data."""
        acc = self.js["accessors"][idx]
        fmt, size = COMP[acc["componentType"]]
        n = NCOMP[acc["type"]]
        count = acc["count"]
        dt = np.dtype(fmt)
        if "bufferView" not in acc:
            return np.zeros((count, n), dtype=dt)
        bv = self.js["bufferViews"][acc["bufferView"]]
        base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = bv.get("byteStride") or (size * n)
        if stride == size * n:
            arr = np.frombuffer(self.bin, dtype=dt, count=count * n, offset=base)
            return arr.reshape(count, n)
        out = np.empty((count, n), dtype=dt)
        for i in range(count):
            out[i] = np.frombuffer(self.bin, dtype=dt, count=n, offset=base + i * stride)
        return out


def quat_mat(t, r, s):
    x, y, z, w = r
    m = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=np.float64)
    m = m @ np.diag(np.asarray(s, dtype=np.float64))
    out = np.eye(4)
    out[:3, :3] = m
    out[:3, 3] = t
    return out


def node_local(nd):
    if "matrix" in nd:
        return np.asarray(nd["matrix"], dtype=np.float64).reshape(4, 4).T  # column-major
    return quat_mat(nd.get("translation", [0, 0, 0]),
                    nd.get("rotation", [0, 0, 0, 1]),
                    nd.get("scale", [1, 1, 1]))


LAYOUT = None





def fix_normals(p, n, uv, idx, weld=1e-3, angle_cos=0.75):
    """Recompute normals per face and split vertices on hard edges.

    The villa's slabs are boxes whose eight corner vertices are shared between the top, the
    bottom and the four sides, so their vertex normals average to something pointing sideways
    or straight down. Shading a 70 m lawn with a downward normal makes it read as a dark wall
    - which is exactly what the first 1080p frame showed, and why the baked sun looked absent
    on the ground. It also poisons any attempt to bake occlusion per vertex.

    This welds by (position, normal): vertices are merged only when they belong to faces that
    actually share a normal, so hard edges stay hard and curved surfaces stay smooth.
    """
    tri = idx.reshape(-1, 3)
    a, b, c = p[tri[:, 0]], p[tri[:, 1]], p[tri[:, 2]]
    fn = np.cross(b - a, c - a)
    ln = np.linalg.norm(fn, axis=1, keepdims=True)
    fn = np.divide(fn, ln, out=np.zeros_like(fn), where=ln > 1e-12)

    # accumulate per (vertex, face) so a face never blends with a neighbour it disagrees with
    P, N, UV, I = [], [], [], []
    key_to_id = {}
    qp = np.round(p / weld).astype(np.int64)
    qn = np.round(fn / 0.05).astype(np.int64)
    for t in range(len(tri)):
        for k in range(3):
            vi = int(tri[t, k])
            key = (int(qp[vi, 0]), int(qp[vi, 1]), int(qp[vi, 2]),
                   int(qn[t, 0]), int(qn[t, 1]), int(qn[t, 2]))
            nid = key_to_id.get(key)
            if nid is None:
                nid = len(P)
                key_to_id[key] = nid
                P.append(p[vi])
                N.append(fn[t])
                UV.append(uv[vi])
            I.append(nid)
    return np.array(P, dtype=np.float32), np.array(N, dtype=np.float32), \
        np.array(UV, dtype=np.float32), np.array(I, dtype=np.uint32)


def subdivide_big(p, n, uv, idx, max_edge=2.5, max_depth=4):
    """Split large triangles into a finer grid.

    A 70 x 70 m lawn slab is four vertices. Per-vertex sun visibility and AO cannot describe
    a tree's shadow on that, and the shadow simply is not there - the lawn renders uniformly
    lit while the trees above it cast nothing. Subdividing only the big facets (a few hundred
    triangles in this scene) gives the bake somewhere to put the pattern, for ~30 k extra
    vertices out of 1.1 M.
    """
    tris = idx.reshape(-1, 3)
    P, Nn, UV = list(p), list(n), list(uv)
    out = [tris]

    def edge_len(a, b):
        return float(np.linalg.norm(a - b))

    for depth in range(max_depth):
        new_tris = []
        extra_p, extra_n, extra_uv = [], [], []
        nxt = len(P)

        def midpoint(i, j):
            nonlocal nxt
            m = 0.5 * (P[i] + P[j])
            P.append(m)
            Nn.append(0.5 * (Nn[i] + Nn[j]))
            UV.append(0.5 * (UV[i] + UV[j]))
            nxt += 1
            return nxt - 1

        changed = False
        for t in np.concatenate(out) if len(out) > 1 else out[0]:
            a, b, c = P[t[0]], P[t[1]], P[t[2]]
            if max(edge_len(a, b), edge_len(b, c), edge_len(c, a)) <= max_edge:
                new_tris.append([int(t[0]), int(t[1]), int(t[2])])
                continue
            changed = True
            ab = midpoint(t[0], t[1])
            bc = midpoint(t[1], t[2])
            ca = midpoint(t[2], t[0])
            i0, i1, i2 = int(t[0]), int(t[1]), int(t[2])
            for tri in ((i0, ab, ca), (ab, i1, bc), (ca, bc, i2), (ab, bc, ca)):
                new_tris.append(list(tri))
        out = [np.array(new_tris, dtype=np.uint32)]
        if not changed:
            break
    return (np.array(P), np.array(Nn), np.array(UV), out[0].reshape(-1))


def bake_occlusion(tris_world, verts, normals, cell=0.35, tris_canopy=None):
    """Per-vertex sun visibility and ambient occlusion, from the geometry itself.

    GLES2 forward rendering has no shadow maps and no SSAO, so the light has to be *baked*:
    the villa and the garden are static, the sun is static, and the only thing that moves is
    the player. That is exactly the case baking solves well.

    The bake builds a sparse voxel occupancy grid from every triangle, then marches each
    vertex towards the sun (one cone, sampled with jitter for a soft penumbra) and into eight
    hemisphere directions for contact occlusion. Everything is numpy and chunked, so 1.1 M
    vertices are a couple of seconds, not hours.

    `tris_world` is an (n,3,3) array of solid world-space triangles; `tris_canopy` are the
    alpha-tested foliage cards. Foliage is NOT solid: a leaf card in a voxel grid is a wall,
    and since the lawn is dotted with grass clumps that made 80 % of the garden read as
    shadowed. Canopy geometry is kept in its own grid and attenuates the sun by a fixed
    soft weight, which gives real dappled tree shade instead of a black carpet.
    """
    lo = np.minimum(tris_world.reshape(-1, 3).min(0), verts.min(0)) - 1.0
    hi = np.maximum(tris_world.reshape(-1, 3).max(0), verts.max(0)) + 1.0
    dims = np.ceil((hi - lo) / cell).astype(int) + 1
    print(f"  occlusion grid {dims[0]}x{dims[1]}x{dims[2]} @ {cell} m", flush=True)
    occ = np.zeros(int(dims[0] * dims[1] * dims[2]), dtype=bool)
    canopy = np.zeros(int(dims[0] * dims[1] * dims[2]), dtype=bool)

    def vox(p):
        i = np.floor((p - lo) / cell).astype(np.int64)
        ok = np.all((i >= 0) & (i < dims), axis=1)
        i = np.clip(i, 0, dims - 1)
        return (i[:, 0] * dims[1] + i[:, 1]) * dims[2] + i[:, 2], ok

    def fill(grid, tris):
        if len(tris) == 0:
            return
        e = np.linalg.norm(tris - np.roll(tris, 1, axis=1), axis=2)
        big = e.max(1) > 1.2
        small = tris[~big]
        if len(small):
            a, b, c = small[:, 0], small[:, 1], small[:, 2]
            pts = np.concatenate([a, b, c, (a + b) * 0.5, (b + c) * 0.5, (c + a) * 0.5,
                                  (a + b + c) / 3.0])
            idx, ok = vox(pts)
            grid[idx[ok]] = True
        for t in tris[big]:
            m = max(np.linalg.norm(t[0] - t[1]), np.linalg.norm(t[1] - t[2]),
                    np.linalg.norm(t[2] - t[0]))
            n = int(np.clip(np.ceil(m / 0.30), 2, 90))
            for i in range(n + 1):
                for j in range(n + 1 - i):
                    u = i / n
                    w = j / n
                    p = t[0] * (1 - u - w) + t[1] * u + t[2] * w
                    idx, ok = vox(p[None, :])
                    if ok[0]:
                        grid[idx[0]] = True

    fill(occ, tris_world)
    fill(canopy, tris_canopy if tris_canopy is not None else np.zeros((0, 3, 3)))

    print(f"  occupied voxels: solid {int(occ.sum())}, canopy {int(canopy.sum())}", flush=True)

    def march(orig, dirs, steps, max_t):
        """(solid hit, number of canopy samples hit) for every (vertex, direction)."""
        nv, nd = orig.shape[0], dirs.shape[0]
        hit = np.zeros((nv, nd), dtype=bool)
        soft = np.zeros((nv, nd), dtype=np.int16)
        for t in steps:
            if t > max_t:
                break
            p = orig[:, None, :] + dirs[None, :, :] * t
            idx, ok = vox(p.reshape(-1, 3))
            # a sample outside the grid is empty sky, NOT the nearest boundary voxel.
            # Clamping here made every upward ray "hit" the top layer of the grid, so the
            # first bake reported 98 % of the garden in shadow and silently wasted 90 s.
            idx = idx.reshape(nv, nd)
            ok = ok.reshape(nv, nd)
            hit |= ok & occ[idx]
            soft += (ok & canopy[idx] & ~occ[idx]).astype(np.int16)
        return hit, soft

    # --- sun: 22 deg up, raking. Sample three jittered directions for a soft edge.
    el, az = np.radians(30.0), np.radians(236.0)   # must match game_sun()
    sun = np.array([np.sin(az) * np.cos(el), np.sin(el), -np.cos(az) * np.cos(el)])
    rng = np.random.default_rng(7)
    jitter = sun[None, :] + rng.normal(0, 0.035, (3, 3))
    jitter /= np.linalg.norm(jitter, axis=1, keepdims=True)
    sun_steps = np.array([0.35 * (k ** 1.25) for k in range(1, 34)])
    vis = np.zeros(len(verts), dtype=np.float32)
    for chunk0 in range(0, len(verts), 40000):
        sl = slice(chunk0, min(chunk0 + 40000, len(verts)))
        v = verts[sl]
        # Bias the ray origin along the LIGHT, not just the normal. Vanity case that broke the
        # first two bakes: the lawn slab's 70 m long side faces have horizontal normals, so a
        # normal-only offset put their origin at ground level, every ray hit the floor and the
        # garden rendered uniformly shadowed. Biasing along the ray direction always escapes
        # the surface, whatever its orientation.
        o = v + normals[sl] * (cell * 0.5) + jitter.mean(0)[None, :] * (cell * 1.8)
        hard, soft = march(o, jitter, sun_steps + 1.0, 30.0)
        # one leaf sample dims the sun, several leaves (a canopy) block most of it
        transmit = 1.0 - 0.22 * np.minimum(soft, 4).astype(np.float32) / 2.0
        vis[sl] = ((1.0 - hard.astype(np.float32)) * np.clip(transmit, 0.45, 1.0)).mean(1)
    # --- ambient: eight slanted directions, short range
    ao_dirs = []
    for k in range(8):
        a = k * np.pi / 4.0
        t = np.radians(38.0)
        ao_dirs.append([np.cos(a) * np.cos(t), np.sin(t), np.sin(a) * np.cos(t)])
    ao_dirs = np.array(ao_dirs)
    ao_steps = np.array([0.30, 0.65, 1.05, 1.55, 2.15, 2.85, 3.6, 4.5])
    occ_a = np.zeros(len(verts), dtype=np.float32)
    for chunk0 in range(0, len(verts), 40000):
        sl = slice(chunk0, min(chunk0 + 40000, len(verts)))
        v = verts[sl]
        o = v + normals[sl] * (cell * 0.5) + ao_dirs.mean(0)[None, :] * (cell * 1.8)
        hard, soft = march(o, ao_dirs, ao_steps + 0.8, 4.5)
        open_a = (1.0 - hard.astype(np.float32)) * np.clip(1.0 - 0.2 * soft, 0.4, 1.0)
        occ_a[sl] = open_a.mean(1)
    # keep a floor so nothing goes pitch black, and lift the curve a little
    ao = np.clip(occ_a, 0.12, 1.0) ** 0.75
    return ao.astype(np.float32), np.clip(vis, 0.0, 1.0).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("glb")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--json-out", default=None, help="dump pack stats for the docs/tests")
    ap.add_argument("--no-ao", action="store_true", help="skip the occlusion bake (fast)")
    ap.add_argument("--keep-normals", action="store_true",
                    help="keep the GLB's vertex normals (they average slab corners to "
                         "sideways/downward and light the lawn like a wall)")
    ap.add_argument("--no-subdiv", action="store_true",
                    help="do not subdivide large facets (faster, but shadows on the lawn "
                         "disappear - the slab only has four vertices)")
    ns = ap.parse_args()
    global vpk_subdiv
    vpk_subdiv = not ns.no_subdiv
    global vpk_fix_normals
    vpk_fix_normals = not ns.keep_normals

    g = Glb(ns.glb)
    js = g.js
    nodes = js["nodes"]
    roots = js["scenes"][js.get("scene", 0)]["nodes"]

    # ---- flatten the scene graph into world matrices, per (node, mesh)
    world = {}
    stack = [(r, np.eye(4)) for r in roots]
    while stack:
        ni, pm = stack.pop()
        wm = pm @ node_local(nodes[ni])
        world[ni] = wm
        for c in nodes[ni].get("children", []):
            stack.append((c, wm))

    mats = js.get("materials", [])
    tex_src = {}          # image index -> texture id
    tex_bytes = {}        # texture id -> bytes
    tex_mime = {}

    # ---- group primitives by material, baking transforms
    groups = {}           # material index -> dict of lists
    all_tris = []         # world-space triangles (solid), for the occlusion bake
    canopy_tris = []      # alpha-tested foliage cards: soft occluders, not walls
    stats = {"prims": 0, "skipped_modes": 0, "missing_uv": 0, "tris": 0}
    # Framing box: the building envelope only. A raw bbox would frame a 92 m garden
    # because the tree canopies are part of the scene.
    BUILDING = ("wall", "plinth", "pier", "glass", "soffit", "par_", "roof", "door_",
                "canopy", "entry", "chimney", "IW")
    fit_lo = np.array([1e30] * 3)
    fit_hi = np.array([-1e30] * 3)
    scene_lo = np.array([1e30] * 3)
    scene_hi = np.array([-1e30] * 3)

    for ni, wm in world.items():
        nd = nodes[ni]
        if "mesh" not in nd:
            continue
        # Backdrops must not drive the camera framing: the ridges are 700 m away and the
        # lawn slabs are 150 m, so a raw scene bbox would frame a field, not a house.
        nm = nd.get("name", "").lower()
        is_backdrop = any(k in nm for k in ("ridge", "lawn", "ground", "field"))
        mesh = js["meshes"][nd["mesh"]]
        for prim in mesh["primitives"]:
            if prim.get("mode", 4) != 4:
                stats["skipped_modes"] += 1
                continue
            stats["prims"] += 1
            pos = g.accessor(prim["attributes"]["POSITION"]).astype(np.float64)
            nrm = g.accessor(prim["attributes"]["NORMAL"]).astype(np.float64) \
                if "NORMAL" in prim["attributes"] else np.zeros_like(pos)
            if "TEXCOORD_0" in prim["attributes"]:
                uv = g.accessor(prim["attributes"]["TEXCOORD_0"]).astype(np.float32)
            else:
                uv = np.zeros((len(pos), 2), dtype=np.float32)
                stats["missing_uv"] += 1
            idx = g.accessor(prim["indices"])[:, 0].astype(np.uint32) \
                if "indices" in prim else np.arange(len(pos), dtype=np.uint32)

            R = wm[:3, :3]
            nmat = np.linalg.inv(R).T if abs(np.linalg.det(R)) > 1e-12 else R
            p = pos @ R.T + wm[:3, 3]
            n = nrm @ nmat.T
            ln = np.linalg.norm(n, axis=1, keepdims=True)
            n = np.divide(n, ln, out=np.zeros_like(n), where=ln > 1e-9)

            # large facets (lawn, drive, terrace, roof slabs) get subdivided so the baked
            # sun/AO has somewhere to live
            _e = np.linalg.norm(p[idx.reshape(-1, 3)] - np.roll(p[idx.reshape(-1, 3)], 1, axis=1),
                                axis=2).max() if len(idx) else 0.0
            if _e > 2.5 and vpk_subdiv and len(idx) // 3 < 4000:
                p, n, uv, idx = subdivide_big(p, n, uv, idx.astype(np.uint32))
                stats["subdiv_tris"] = stats.get("subdiv_tris", 0) + len(idx) // 3
            lo, hi = p.min(0), p.max(0)
            scene_lo = np.minimum(scene_lo, lo)
            scene_hi = np.maximum(scene_hi, hi)
            if nm.startswith(BUILDING):
                fit_lo = np.minimum(fit_lo, lo)
                fit_hi = np.maximum(fit_hi, hi)

            mi = prim.get("material", -1)
            grp = groups.setdefault(mi, {"p": [], "n": [], "uv": [], "i": [], "base": 0})
            grp["p"].append(p.astype(np.float32))
            _cut = False
            if prim.get("material") is not None and prim["material"] < len(mats):
                _m = mats[prim["material"]]
                _cut = _m.get("alphaMode") in ("MASK", "BLEND") or \
                    "leaf" in _m.get("name", "").lower() or \
                    "grass" in _m.get("name", "").lower() or \
                    "frond" in _m.get("name", "").lower()
            (canopy_tris if _cut else all_tris).append(p[idx.reshape(-1, 3)])
            grp["n"].append(n.astype(np.float32))
            grp["uv"].append(uv)
            grp["i"].append(idx + grp["base"])
            grp["base"] += len(p)
            stats["tris"] += len(idx) // 3

    # ---- materials -> textures
    def material_info(mi):
        if mi < 0 or mi >= len(mats):
            return (np.array([0.75, 0.75, 0.75, 1.0]), 0xFFFF, False, 0.5,
                    np.zeros(3))
        m = mats[mi]
        pbr = m.get("pbrMetallicRoughness", {})
        base = np.array(pbr.get("baseColorFactor", [1, 1, 1, 1]), dtype=np.float64)
        tid = 0xFFFF
        bct = pbr.get("baseColorTexture")
        if bct is not None:
            src = js["textures"][bct["index"]].get("source")
            if src is not None:
                if src not in tex_src:
                    im = js["images"][src]
                    bv = js["bufferViews"][im["bufferView"]]
                    off = bv.get("byteOffset", 0)
                    data = g.bin[off:off + bv["byteLength"]]
                    tid = len(tex_src)
                    tex_src[src] = tid
                    tex_bytes[tid] = data
                    tex_mime[tid] = im.get("mimeType", "image/jpeg")
                tid = tex_src[src]
        cutout = m.get("alphaMode") in ("MASK", "BLEND")
        cutoff = float(m.get("alphaCutoff", 0.5)) if cutout else 0.0
        emis = np.array(m.get("emissiveFactor", [0, 0, 0]), dtype=np.float64)
        # Glass: glTF transmission cannot be done on GLES2. A transmissive surface drawn
        # opaque renders as a white panel (which is exactly what the first preview showed),
        # so it is drawn last, alpha-blended, with a dark cool tint - a window reads as
        # glazing because it is darker than the wall, not because it is see-through.
        name = m.get("name", "").lower()
        trans = float(m.get("extensions", {})
                       .get("KHR_materials_transmission", {}).get("transmissionFactor", 0.0))
        glass = trans > 0.05 or "glass" in name
        # Water is a separate pass on the device: animated normals, sky reflection, sun
        # glints. The villa already contains a plunge pool (materials pool_tile /
        # water_ripple), so nothing has to be modelled - it only has to be shaded properly.
        water = (not glass) and ("water" in name or "ripple" in name)
        return (base, tid, bool(m.get("doubleSided", False)), cutoff, emis, glass, water)

    # ---- build chunks (<= CHUNK verts) and quantise
    draws = []
    chunks = []          # (draw_dict, vertex_bytes, index_bytes) - kept together on purpose
    for mi, grp in sorted(groups.items(), key=lambda kv: str(kv[0])):
        base, tid, two_sided, cutoff, emis, glass, water = material_info(mi)
        P = np.concatenate(grp["p"]); N = np.concatenate(grp["n"])
        UV = np.concatenate(grp["uv"]); I = np.concatenate(grp["i"])
        if vpk_fix_normals:
            P, N, UV, I = fix_normals(P, N, UV, I)
        # split triangles into chunks whose vertex span fits in uint16
        start = 0
        ntri = len(I) // 3
        while start < ntri:
            vids = {}
            tri_sel = []
            stop = start
            while stop < ntri:
                tri = I[stop * 3:stop * 3 + 3]
                new = [v for v in tri if v not in vids]
                if len(vids) + len(new) > CHUNK:
                    break
                for v in new:
                    vids[v] = len(vids)
                tri_sel.append([vids[v] for v in tri])
                stop += 1
            if stop == start:                    # degenerate / single oversized tri
                stop = start + 1
                vids = {int(v): k for k, v in enumerate(I[start * 3:start * 3 + 3])}
                tri_sel = [[vids[int(v)] for v in I[start * 3:start * 3 + 3]]]
            order = np.array(sorted(vids, key=lambda k: vids[k]), dtype=np.int64)
            vp = P[order]; vn = N[order]; vuv = UV[order]
            lo = vp.min(0); ext = np.maximum(vp.max(0) - lo, 1e-6)
            posq = np.clip(np.round((vp - lo) / ext * 65535.0), 0, 65535).astype(np.uint16)
            nrmq = np.clip(np.round(vn * 127.0), -127, 127).astype(np.int8)
            pad = np.zeros((len(order), 1), dtype=np.int8)
            # `pad` is not padding any more: it carries the baked ambient occlusion and sun
            # visibility as two normalised bytes. Keeping them in the existing 2 bytes holds
            # the 20-byte stride, which is what the drivers are happiest with.
            chunk = np.zeros(len(order), dtype=[("p", "<u2", 3), ("ao", "u1", 2),
                                                ("n", "i1", 4), ("uv", "<f4", 2)])
            chunk["p"] = posq
            chunk["n"] = np.concatenate([nrmq, pad], axis=1)
            chunk["uv"] = vuv
            tri = np.array(tri_sel, dtype=np.uint16)
            dr = ({
                "vert_offset": 0, "index_offset": 0,   # filled in below
                "vertex_count": len(order), "index_count": tri.size,
                "pos_min": lo.astype(np.float32), "pos_scale": ext.astype(np.float32),
                "tex": tid, "two_sided": two_sided, "cutout": cutoff > 0, "glass": glass,
                "water": water,
                "base": base.astype(np.float32), "cutoff": float(cutoff), "wids": order,
                "emissive": emis.astype(np.float32),
            })
            draws.append(dr)
            chunks.append((dr, chunk, tri, vp.astype(np.float32), vn.astype(np.float32)))
            start = stop

    # ---- draw order matters for a blended viewer: opaque first, cutout foliage next,
    # then glass. Depth writes are off for the blended passes on the device. The chunk
    # payload is sorted WITH its draw record - sorting the records alone silently
    # mismatched offsets to vertices (it scrambled the model once).
    for i, c in enumerate(chunks):
        c[0]["_idx"] = i
    key = lambda c: (2 if c[0]["glass"] else (1 if c[0]["cutout"] else 0))
    chunks.sort(key=key)
    draws = [c[0] for c in chunks]

    # ---- bake sun visibility + AO into the vertex attribute (uv2.x, uv2.y), then write
    ao_stat = {}
    ao_uv = {}
    if not ns.no_ao:
        verts = np.concatenate([c[3] for c in chunks])
        norms = np.concatenate([c[4] for c in chunks])
        tris = np.concatenate(all_tris) if all_tris else np.zeros((0, 3, 3))
        canopy = np.concatenate(canopy_tris) if canopy_tris else None
        print(f"baking occlusion for {len(verts)} vertices from {len(tris)} triangles",
              flush=True)
        t0 = time.time()
        ao, sun = bake_occlusion(tris, verts, norms, tris_canopy=canopy)
        # distribute the per-vertex values into each chunk's vertex order
        ao_uv = {}
        for dr, _vb, _ib, _vp, _vn in chunks:
            w = np.asarray(dr["wids"], dtype=np.int64)
            vals = np.stack([np.clip(ao[w] * 255, 0, 255), np.clip(sun[w] * 255, 0, 255)],
                            1).astype(np.uint8)
            ao_uv[dr["_idx"]] = vals
        ao_stat = {"ao_seconds": round(time.time() - t0, 1),
                   "ao_mean": round(float(ao.mean()), 3),
                   "sun_mean": round(float(sun.mean()), 3),
                   "sun_shadowed_fraction": round(float((sun < 0.6).mean()), 3),
                   "canopy_tris": int(len(canopy)) if canopy is not None else 0}

    # ---- lay the file out: header | draws | tex table | verts | indices | blob
    n_verts = sum(d["vertex_count"] for d in draws)
    n_idx = sum(d["index_count"] for d in draws)
    n_tex = len(tex_src)
    verts_off = HEADER_SIZE + DRAW_SIZE * len(draws) + 8 * n_tex
    idx_off = verts_off + 20 * n_verts
    blob_off = idx_off + 2 * n_idx

    blob = bytearray()
    tex_table = []
    for tid in range(n_tex):
        data = tex_bytes[tid]
        tex_table.append((blob_off + len(blob), len(data)))
        blob += data

    v_cursor = 0
    i_cursor = 0
    out_draws = bytearray()
    for d in draws:
        d["vert_offset"] = v_cursor
        d["index_offset"] = i_cursor
        v_cursor += d["vertex_count"]
        i_cursor += d["index_count"]
        # 4I + 10f + HH + 4f + f + 3f + 2f(pad) = 100 bytes, see vpk.h
        out_draws += struct.pack(
            "<4I10f2H4ff3f2f",
            d["index_offset"], d["index_count"], d["vert_offset"], d["vertex_count"],
            *[float(x) for x in d["pos_min"]], *[float(x) for x in d["pos_scale"]],
            0.0, 0.0, 0.0, 0.0,
            int(d["tex"]),
            (1 if d["cutout"] else 0) | (2 if d["two_sided"] else 0)
            | (4 if d["glass"] else 0) | (8 if d.get("water") else 0),
            *[float(x) for x in d["base"]], float(d["cutoff"]),
            *[float(x) for x in d["emissive"]],
            0.0, 0.0)

    if not np.isfinite(fit_lo).all() or (fit_lo > fit_hi).any():
        fit_lo, fit_hi = scene_lo, scene_hi
    # a little air around the building so the shot is not cropped to the walls
    fit_lo, fit_hi = fit_lo - 3.0, fit_hi + 3.0

    hdr = MAGIC + struct.pack(
        "<6I3f3f3f3f",
        VERSION, len(draws), n_tex, n_verts, n_idx, 0,
        *[float(x) for x in scene_lo], *[float(x) for x in scene_hi],
        *[float(x) for x in fit_lo], *[float(x) for x in fit_hi]) + b"\0" * 8
    assert len(hdr) == HEADER_SIZE, len(hdr)
    assert len(out_draws) == DRAW_SIZE * len(draws), len(out_draws)

    os.makedirs(os.path.dirname(os.path.abspath(ns.out)), exist_ok=True)
    with open(ns.out, "wb") as f:
        f.write(hdr)
        f.write(out_draws)
        for off, ln in tex_table:
            f.write(struct.pack("<2I", off, ln))
        for _dr, vb, _ib, _vp, _vn in chunks:
            vb["ao"] = ao_uv.get(_dr["_idx"], np.full((len(vb), 2), 255, np.uint8))
            f.write(vb.tobytes())
        for _dr, _vb, ib, _vp, _vn in chunks:
            f.write(ib)
        f.write(blob)

    size = os.path.getsize(ns.out)
    info = {
        "source": ns.glb, "source_mb": round(os.path.getsize(ns.glb) / 1e6, 2),
        "out": ns.out, "out_mb": round(size / 1e6, 2),
        "draws": len(draws), "textures": n_tex, "verts": n_verts, "tris": stats["tris"],
        "materials": len(groups),
        "glass_draws": sum(1 for d in draws if d["glass"]), "skipped_modes": stats["skipped_modes"],
        "prims_without_uv": stats["missing_uv"],
        "scene_min": [round(float(x), 3) for x in scene_lo],
        "scene_max": [round(float(x), 3) for x in scene_hi],
        "fit_min": [round(float(x), 3) for x in fit_lo],
        "fit_max": [round(float(x), 3) for x in fit_hi],
        "geometry_mb": round((20 * n_verts + 2 * n_idx) / 1e6, 2),
        "textures_mb": round(len(blob) / 1e6, 2),
        "water_draws": sum(1 for d in draws if d.get("water")),
    }
    info.update(ao_stat)
    print(json.dumps(info, indent=1))
    if ns.json_out:
        json.dump(info, open(ns.json_out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
