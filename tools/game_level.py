#!/usr/bin/env python3
"""Turn the villa GLB into a playable level: collision grid, spawn, objectives.

The visual model is already packed into VPK1 for the renderer (`tools/villa_pack.py`).
A game also needs to know **where you can walk**, and the honest way to get that is to
derive it from the geometry that will be drawn, not to hand-author boxes that drift out of
sync with the art.

    python tools/game_level.py villa_v2/villa_v2_lite.glb -o android/game/app/src/main/assets/level.bin

Output (LVL1, little endian):

    header 32 B : magic 'LVL1', version, cols, rows, cell_m, origin_x, origin_z, spawn(3),
                  objectives_count
    ground     : cols*rows float32      walkable surface height (Y-up)
    blocked    : cols*rows uint8        1 = cannot stand here
    objectives : n * (float32 x, float32 y, float32 z, float32 radius)

Rules, all measured from the mesh AABBs:
  * a surface is walkable if its top is between -0.6 m and +0.55 m above the local ground
    (so the terrace step, the driveway and the lawn all read as ground);
  * anything whose AABB crosses the body band (0.55 m .. 1.85 m above ground) blocks the
    cell - walls, glazing, hedges, tree trunks, planters, furniture;
  * the roof is excluded (it is 3 m up and the player cannot reach it), but everything at
    ground level, including planting, is included, so trees are solid.
"""
import argparse
import json
import math
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from villa_pack import Glb  # reuse the battle-tested GLB reader  # noqa: E402

MAGIC = b"LVL1"
VERSION = 1
HEADER = 56


def erode(mask, k):
    """True L-inf erosion by k cells.

    Each shift must read the ORIGINAL mask: `mask &= shift(mask)` inside the loop shrinks
    the result by every offset in turn, which quietly erases the whole garden (it did, and
    the objectives fell back to the raw reachable set without anyone noticing).
    """
    out = mask.copy()
    rows_, cols_ = mask.shape
    for dr in range(-k, k + 1):
        for dc in range(-k, k + 1):
            sh = np.zeros_like(mask)
            src = mask[max(0, dr):rows_ + min(0, dr), max(0, dc):cols_ + min(0, dc)]
            sh[max(0, -dr):max(0, -dr) + src.shape[0],
               max(0, -dc):max(0, -dc) + src.shape[1]] = src
            out &= sh
    return out


def node_world(g, nodes, roots):
    """Flatten the glTF scene graph into world matrices (Y-up, as in the file)."""
    world = {}
    stack = [(r, np.eye(4)) for r in roots]
    while stack:
        ni, pm = stack.pop()
        nd = nodes[ni]
        if "matrix" in nd:
            local = np.asarray(nd["matrix"], dtype=np.float64).reshape(4, 4).T
        else:
            t = nd.get("translation", [0, 0, 0])
            q = nd.get("rotation", [0, 0, 0, 1])
            s = nd.get("scale", [1, 1, 1])
            x, y, z, w = q
            r = np.array([
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
            ])
            r = r @ np.diag(s)
            local = np.eye(4)
            local[:3, :3] = r
            local[:3, 3] = t
        wm = pm @ local
        world[ni] = wm
        for c in nd.get("children", []):
            stack.append((c, wm))
    return world


def boxes(g):
    """(name, aabb_min, aabb_max) in world space, Y-up."""
    js = g.js
    nodes = js["nodes"]
    roots = js["scenes"][js.get("scene", 0)]["nodes"]
    world = node_world(g, nodes, roots)
    out = []
    for ni, wm in world.items():
        nd = nodes[ni]
        if "mesh" not in nd:
            continue
        lo = np.array([1e30] * 3)
        hi = np.array([-1e30] * 3)
        for prim in js["meshes"][nd["mesh"]]["primitives"]:
            acc = js["accessors"][prim["attributes"]["POSITION"]]
            if "min" not in acc:
                continue
            a = np.asarray(acc["min"], dtype=np.float64)
            b = np.asarray(acc["max"], dtype=np.float64)
            # transform the 8 corners, not just the min/max
            corners = np.array([[a[0] if i & 1 else b[0],
                                 a[1] if i & 2 else b[1],
                                 a[2] if i & 4 else b[2]] for i in range(8)])
            w = corners @ wm[:3, :3].T + wm[:3, 3]
            lo = np.minimum(lo, w.min(0))
            hi = np.maximum(hi, w.max(0))
        if np.isfinite(lo).all():
            out.append((nd.get("name", ""), lo, hi))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("glb")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--cell", type=float, default=0.30, help="grid cell size in metres")
    ap.add_argument("--margin", type=float, default=3.0)
    ap.add_argument("--objectives", type=int, default=8)
    ap.add_argument("--map", default=None, help="write a top-down PNG of the grid")
    ap.add_argument("--json-out", default=None)
    ns = ap.parse_args()

    g = Glb(ns.glb)
    bs = boxes(g)
    print("objects:", len(bs), flush=True)

    all_lo = np.min([b[1] for b in bs], axis=0)
    all_hi = np.max([b[2] for b in bs], axis=0)
    # Y-up: x = east, y = up, z = north(=Blender -y). Grid over x/z, height in y.
    x0 = math.floor(all_lo[0] - ns.margin)
    z0 = math.floor(all_lo[2] - ns.margin)
    x1 = math.ceil(all_hi[0] + ns.margin)
    z1 = math.ceil(all_hi[2] + ns.margin)
    cols = int(math.ceil((x1 - x0) / ns.cell))
    rows = int(math.ceil((z1 - z0) / ns.cell))
    print(f"level {x1-x0:.0f} x {z1-z0:.0f} m -> {cols} x {rows} cells @ {ns.cell} m",
          flush=True)

    # ---- 1. rasterise TRIANGLES, not object AABBs.
    ground = np.full((rows, cols), -9.0, dtype=np.float32)
    modeled = np.zeros((rows, cols), dtype=bool)
    body_block = np.zeros((rows, cols), dtype=bool)
    # An object-level AABB is hopeless here: the walls of one elevation are a single joined
    # mesh, so its box covers the whole house and the interior becomes solid rock (that is
    # exactly what the first map showed). Walking on triangles gives thin walls, real
    # doorways and correct terrace steps.
    CARD_MATS = ("spray_", "leaf_card", "grass_blade", "palm_frond")
    js = g.js
    nodes = js["nodes"]
    roots = js["scenes"][js.get("scene", 0)]["nodes"]
    world = node_world(g, nodes, roots)
    mat_names = [m.get("name", "") for m in js.get("materials", [])]

    def cell_of(x, z):
        return (int((z - z0) / ns.cell), int((x - x0) / ns.cell))

    trees = 0
    tree_radii = []
    tris_ground = tris_wall = 0
    names_block = {}

    for ni, wm in world.items():
        nd = nodes[ni]
        if "mesh" not in nd:
            continue
        name = nd.get("name", "")
        is_tree = name.startswith(("tree_", "cypress", "olive_", "palm_"))
        is_shrub = name.startswith("shrub_")
        for prim in js["meshes"][nd["mesh"]]["primitives"]:
            mname = mat_names[prim["material"]] if prim.get("material") is not None and \
                prim["material"] < len(mat_names) else ""
            if any(mname.startswith(c) for c in CARD_MATS):
                continue                       # foliage cards: handled as a trunk below
            pos = g.accessor(prim["attributes"]["POSITION"]).astype(np.float64)
            if "indices" in prim:
                idx = g.accessor(prim["indices"])[:, 0].astype(np.int64)
            else:
                idx = np.arange(len(pos), dtype=np.int64)
            P = pos @ wm[:3, :3].T + wm[:3, 3]
            T = P[idx.reshape(-1, 3)]          # (n, 3, 3)
            if not len(T):
                continue
            ymin = T[:, :, 1].min(1)
            ymax = T[:, :, 1].max(1)
            # triangle normal y (for "is this a floor" decisions)
            e1 = T[:, 1] - T[:, 0]
            e2 = T[:, 2] - T[:, 0]
            cn = np.cross(e1, e2)
            nl = np.linalg.norm(cn, axis=1)
            ny = np.where(nl > 1e-9, np.abs(cn[:, 1]) / np.maximum(nl, 1e-9), 0.0)
            floor = (ny > 0.72) & (ymax <= 0.65) & (ymax > -3.0)
            wall = (~floor) & (ymax > 0.55) & (ymin < 1.95) & (ymin < 2.6)
            for sel, kind in ((floor, "g"), (wall, "w")):
                for t in T[sel]:
                    a, b, c = t
                    xa = min(a[0], b[0], c[0]); xb = max(a[0], b[0], c[0])
                    za = min(a[2], b[2], c[2]); zb = max(a[2], b[2], c[2])
                    r0, c0_ = cell_of(xa, za); r1, c1_ = cell_of(xb, zb)
                    r0 = max(0, r0); c0_ = max(0, c0_)
                    r1 = min(rows - 1, r1); c1_ = min(cols - 1, c1_)
                    if r1 < r0 or c1_ < c0_:
                        continue
                    # barycentric test on the 2D projection, one cell padded
                    pad = 1
                    rr = np.arange(max(0, r0 - pad), min(rows, r1 + pad + 1))
                    cc = np.arange(max(0, c0_ - pad), min(cols, c1_ + pad + 1))
                    if not len(rr) or not len(cc):
                        continue
                    gz = z0 + (rr + 0.5) * ns.cell
                    gx = x0 + (cc + 0.5) * ns.cell
                    GX, GZ = np.meshgrid(gx, gz)
                    d1 = ((b[0] - a[0]) * (GZ - a[2]) - (b[2] - a[2]) * (GX - a[0]))
                    d2 = ((c[0] - b[0]) * (GZ - b[2]) - (c[2] - b[2]) * (GX - b[0]))
                    d3 = ((a[0] - c[0]) * (GZ - c[2]) - (a[2] - c[2]) * (GX - c[0]))
                    inside = ((d1 >= -1e-9) & (d2 >= -1e-9) & (d3 >= -1e-9)) | \
                             ((d1 <= 1e-9) & (d2 <= 1e-9) & (d3 <= 1e-9))
                    if not inside.any():
                        continue
                    sl = (rr[:, None], cc[None, :])
                    if kind == "g":
                        # interpolate the plane height at those cells
                        det = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
                        if abs(det) < 1e-12:
                            continue
                        l1 = ((b[2] - c[2]) * (GX - c[0]) + (c[0] - b[0]) * (GZ - c[2])) / det
                        l2 = ((c[2] - a[2]) * (GX - c[0]) + (a[0] - c[0]) * (GZ - c[2])) / det
                        l3 = 1.0 - l1 - l2
                        h = l1 * a[1] + l2 * b[1] + l3 * c[1]
                        cur = ground[sl]
                        upd = inside & (h > cur)
                        if upd.any():
                            gsub = ground[sl]
                            gsub[upd] = h[upd]
                            ground[sl] = gsub
                            modeled[sl] |= upd
                        tris_ground += 1
                    else:
                        blk = body_block[sl]
                        blk |= inside
                        body_block[sl] = blk
                        tris_wall += 1
        if "pool_water" in name or "pool_basin" in name:
            # water is not a floor. Without this the player walks across the pool surface and
            # the reflections are hidden under their feet.
            for prim in js["meshes"][nd["mesh"]]["primitives"]:
                acc = js["accessors"][prim["attributes"]["POSITION"]]
                if "min" not in acc:
                    continue
                a = np.asarray(acc["min"]); b = np.asarray(acc["max"])
                corners = np.array([[a[0] if i & 1 else b[0], a[1] if i & 2 else b[1],
                                     a[2] if i & 4 else b[2]] for i in range(8)])
                w = corners @ wm[:3, :3].T + wm[:3, 3]
                lo, hi = w.min(0), w.max(0)
                rr0, cc0 = cell_of(lo[0], lo[2]); rr1, cc1 = cell_of(hi[0], hi[2])
                body_block[max(0, rr0):min(rows, rr1 + 1),
                           max(0, cc0):min(cols, cc1 + 1)] = True
            continue
        if is_tree:
            lo, hi = None, None
            for prim in js["meshes"][nd["mesh"]]["primitives"]:
                acc = js["accessors"][prim["attributes"]["POSITION"]]
                if "min" not in acc:
                    continue
                a = np.asarray(acc["min"]); b = np.asarray(acc["max"])
                corners = np.array([[a[0] if i & 1 else b[0], a[1] if i & 2 else b[1],
                                     a[2] if i & 4 else b[2]] for i in range(8)])
                w = corners @ wm[:3, :3].T + wm[:3, 3]
                lo = w.min(0) if lo is None else np.minimum(lo, w.min(0))
                hi = w.max(0) if hi is None else np.maximum(hi, w.max(0))
            if lo is not None:
                cx, cz = 0.5 * (lo[0] + hi[0]), 0.5 * (lo[2] + hi[2])
                rr, cc = cell_of(cx, cz)
                # A tree is not a 0.55 m post. The trunk is, but the canopy around it is 2-3 m
                # of leaf cards, and blocking only the trunk let the player walk in until the
                # leaves were across the whole screen - the v9 screenshot. Block the canopy's
                # own footprint, kept a little tighter than the cards so you can still walk
                # under the edge of a tree, and clamped so one palm cannot wall off the lawn.
                canopy_r = 0.5 * max(hi[0] - lo[0], hi[2] - lo[2])
                block_r = max(0.62, min(canopy_r * 0.62, 2.2))
                k = max(1, int(round(block_r / ns.cell)))
                body_block[max(0, rr - k):min(rows, rr + k + 1),
                           max(0, cc - k):min(cols, cc + k + 1)] = True
                trees += 1
                tree_radii.append(round(block_r, 2))
        if is_shrub:
            for prim in js["meshes"][nd["mesh"]]["primitives"]:
                acc = js["accessors"][prim["attributes"]["POSITION"]]
                if "min" not in acc:
                    continue
                a = np.asarray(acc["min"]); b = np.asarray(acc["max"])
                corners = np.array([[a[0] if i & 1 else b[0], a[1] if i & 2 else b[1],
                                     a[2] if i & 4 else b[2]] for i in range(8)])
                w = corners @ wm[:3, :3].T + wm[:3, 3]
                lo, hi = w.min(0), w.max(0)
                if hi[1] - lo[1] < 0.35:
                    continue
                rr0, cc0 = cell_of(lo[0], lo[2]); rr1, cc1 = cell_of(hi[0], hi[2])
                body_block[max(0, rr0):min(rows, rr1 + 1),
                           max(0, cc0):min(cols, cc1 + 1)] = True

    ground[ground < -8.5] = 0.0
    # Outside the modelled ground there is nothing to walk on: a featureless plane is not a
    # level, and it also dragged the objectives out to the horizon (seen on the map).
    # erode the walkable area by ~1 m so the player never stands on the very edge of the
    # modelled ground (it looks like the world ends, because it does)
    inside_m = erode(modeled, max(1, int(round(1.0 / ns.cell))))
    blocked_outside = ~inside_m
    blocked = body_block | blocked_outside

    # ---- 2. spawn: a clear cell on the lawn south of the terrace, facing the house
    #      (Y-up: south = -z, so the camera looks towards +z)
    def free(r, c):
        return 0 <= r < rows and 0 <= c < cols and not blocked[r, c]

    # The player is a 0.68 m wide body (game_core.h tests 8 rim points at 0.34 m), so a cell
    # is only walkable if its whole 3x3 neighbourhood is. Without this the level claimed
    # corridors were reachable that the body could not fit through, and the host walk stall
    # at the first hedge gap proved it.
    body_free = erode(~blocked, 1)
    print("body-width walkable cells:", int(body_free.sum()), "of", int((~blocked).sum()), "free")

    spawn_xy = None
    for cand in ((11.8, -14.0), (11.8, -16.0), (0.0, -14.0), (11.8, -20.0), (5.0, -12.0)):
        r, c = cell_of(*cand)
        if body_free[r, c] and body_free[r, c - 1] and body_free[r, c + 1]:
            spawn_xy = (x0 + (c + 0.5) * ns.cell, z0 + (r + 0.5) * ns.cell)
            break
    if spawn_xy is None:
        raise SystemExit("no clear spawn cell found")

    # ---- 3. reachability flood fill from the spawn (4-neighbour, no diagonals)
    def flood(passable, start):
        out = np.zeros_like(passable)
        st = [start]
        out[start] = True
        while st:
            r, c = st.pop()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < rows and 0 <= cc < cols and passable[rr, cc] and not out[rr, cc]:
                    out[rr, cc] = True
                    st.append((rr, cc))
        return out

    r0, c0 = cell_of(*spawn_xy)
    reach = flood(body_free, (r0, c0))

    # Verify with the *exact* runtime test: 8 rim samples at BODY_R against the walkable
    # cells (game_core.h). body_free already leaves a cell of clearance, so this should pass
    # almost everywhere; anything that still fails is dropped once. Note the trap here:
    # "keep eroding until the property holds" can never terminate - repeatedly eroding a
    # bounded region always ends in the empty set (it tried, and shrank the garden to 4 k of
    # 46 k cells before the objectives ran out of room).
    BODY_R = 0.26
    bad = []
    ys_, xs_ = np.nonzero(reach)
    for r, c in zip(ys_, xs_):
        cx = x0 + (c + 0.5) * ns.cell
        cz = z0 + (r + 0.5) * ns.cell
        for i in range(8):
            a = i * (math.pi / 4.0)
            cc_ = int((cx + math.cos(a) * BODY_R - x0) / ns.cell)
            rr_ = int((cz + math.sin(a) * BODY_R - z0) / ns.cell)
            if not (0 <= rr_ < rows and 0 <= cc_ < cols) or not reach[rr_, cc_]:
                bad.append((r, c))
                break
    print("cells failing the %.2f m rim test:" % BODY_R, len(bad), flush=True)
    for (r, c) in bad:
        reach[r, c] = False
    if bad:
        reach = flood(reach, (r0, c0))
    print("reachable cells:", int(reach.sum()), "of", int(body_free.sum()), "body-free",
          flush=True)
    if not reach[r0, c0]:
        ys_, xs_ = np.nonzero(reach)
        d2_ = (ys_ - r0) ** 2 + (xs_ - c0) ** 2
        k = int(np.argmin(d2_))
        r0, c0 = int(ys_[k]), int(xs_[k])
        spawn_xy = (x0 + (c0 + 0.5) * ns.cell, z0 + (r0 + 0.5) * ns.cell)
        print("spawn moved to the nearest walkable cell:", [round(v, 2) for v in spawn_xy])

    # ---- 4. objectives: spread out, on reachable cells, near landmarks if possible
    # keep objectives away from the boundary so they do not sit on the edge of the world
    inset = erode(reach, max(1, int(round(3.0 / ns.cell))))     # off the world edge
    inset = erode(inset, max(1, int(round(0.6 / ns.cell))))      # a body's width from walls
    print("objective candidate cells:", int(inset.sum()), "of", int(reach.sum()), "reachable")
    if inset.sum() < 500:
        print("WARNING: clearance erosion left too little; objectives relaxed to plain reach")
        inset = reach
    ys, xs = np.nonzero(inset)
    pts = np.stack([x0 + (xs + 0.5) * ns.cell, z0 + (ys + 0.5) * ns.cell], axis=1)
    # farthest-point sampling from the spawn: maximises the ground the player must cover
    chosen = []
    seeds = pts.copy()
    min_sep = 14.0
    d2 = ((seeds[:, 0] - spawn_xy[0]) ** 2 + (seeds[:, 1] - spawn_xy[1]) ** 2)
    for _ in range(ns.objectives * 3):
        if len(chosen) >= ns.objectives:
            break
        i = int(np.argmax(d2))
        if d2[i] < min_sep ** 2:
            break                     # no room left for another well-separated objective
        chosen.append(seeds[i])
        d = ((seeds[:, 0] - seeds[i, 0]) ** 2 + (seeds[:, 1] - seeds[i, 1]) ** 2)
        d2 = np.minimum(d2, d)
    obj = []
    for (ox, oz) in chosen:
        rr, cc = cell_of(ox, oz)
        gy = float(ground[rr, cc]) + 1.05
        obj.append((float(ox), gy, float(oz), 0.75))
    obj.sort(key=lambda t: (t[2], t[0]))

    # ---- 5. write
    hdr = MAGIC + struct.pack("<7I", VERSION, cols, rows, len(obj), 0, 0, 0) + \
        struct.pack("<6f", ns.cell, x0, z0, spawn_xy[0], float(ground[r0, c0]), spawn_xy[1])
    assert len(hdr) == HEADER, len(hdr)

    walkable = reach.astype(np.uint8)
    out = bytearray()
    out += hdr
    out += ground.astype("<f4").tobytes()
    out += walkable.tobytes()
    for (x, y, z, rad) in obj:
        out += struct.pack("<4f", x, y, z, rad)
    os.makedirs(os.path.dirname(os.path.abspath(ns.out)), exist_ok=True)
    with open(ns.out, "wb") as f:
        f.write(out)

    info = {
        "glb": ns.glb, "cells": [cols, rows], "cell_m": ns.cell,
        "extent_m": [round(x1 - x0, 1), round(z1 - z0, 1)],
        "spawn": [round(spawn_xy[0], 2), round(float(ground[r0, c0]), 2), round(spawn_xy[1], 2)],
        "objectives": [[round(x, 2), round(y, 2), round(z, 2)] for (x, y, z, _r) in obj],
        "reachable_cells": int(reach.sum()), "free_cells": int((~blocked).sum()),
        "blocked_cells": int(blocked.sum()),
        "bytes": len(out),
        "top_blockers": sorted(names_block.items(), key=lambda kv: -kv[1])[:10],
        "trees_as_trunks": trees, "tri_ground": tris_ground, "tri_wall": tris_wall,
    }
    print(json.dumps(info, indent=1), flush=True)

    # ---- 6. BFS distance check: every objective must be reachable and take real effort
    from collections import deque
    dist = np.full((rows, cols), -1, dtype=np.int32)
    dist[r0, c0] = 0
    q = deque([(r0, c0)])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < rows and 0 <= cc < cols and not blocked[rr, cc] and dist[rr, cc] < 0:
                dist[rr, cc] = dist[r, c] + 1
                q.append((rr, cc))
    worst = 0
    for (x, y, z, _r) in obj:
        rr, cc = cell_of(x, z)
        if dist[rr, cc] < 0:
            raise SystemExit(f"objective at {x:.1f},{z:.1f} is NOT reachable")
        worst = max(worst, int(dist[rr, cc]))
    info["worst_objective_m"] = round(worst * ns.cell, 1)
    if tree_radii:
        import statistics
        print(f"tree colliders: {len(tree_radii)} trees, canopy radius "
              f"{min(tree_radii):.2f}-{max(tree_radii):.2f} m (median "
              f"{statistics.median(tree_radii):.2f} m) - v9 blocked 0.55 m and let the player "
              f"stand inside the leaves")
    print(f"PLAYABLE: all {len(obj)} objectives reachable, farthest {info['worst_objective_m']} m "
          f"of walking", flush=True)

    # ---- 7. a top-down map is the cheapest way for a human to audit the level
    if ns.map:
        from PIL import Image
        img = np.zeros((rows, cols, 3), dtype=np.uint8)
        img[..., 0] = (ground + 2) * 30
        img[blocked] = (40, 40, 46)
        img[reach] = (26, 60, 90)
        for (x, y, z, _r) in obj:
            rr, cc = cell_of(x, z)
            img[max(0, rr - 2):rr + 3, max(0, cc - 2):cc + 3] = (240, 190, 60)
        img[max(0, r0 - 2):r0 + 3, max(0, c0 - 2):c0 + 3] = (90, 220, 120)
        Image.fromarray(np.flipud(img)).resize((cols * 4, rows * 4), Image.NEAREST).save(ns.map)
        print("map ->", ns.map, flush=True)

    if ns.json_out:
        json.dump(info, open(ns.json_out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
