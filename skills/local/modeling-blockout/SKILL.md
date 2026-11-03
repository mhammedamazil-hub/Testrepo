---
name: modeling-blockout
description: Spec-driven blockout from primitives with real millimetre dimensions, drift and envelope checks. Enforces the professional rule that proportions are settled before detail.
license: MIT
metadata:
  requires: bpy
---

# Modeling Blockout

The 19-step professional workflow starts with *proportion, then form, then detail*. This
skill builds the proportion stage as data - a JSON spec of boxes, cylinders and prisms
with real dimensions - and then proves the result matches the spec.

## When to use
- Starting any hard-surface, architectural or product asset.
- When you need a "grey box" to check silhouette against a reference before committing.
- When a spec lives in a drawing: type the dimensions once, generate the blockout.

## Procedure
1. Write a spec (JSON list of parts: `name`, `type`, `size` in mm, `at`, optional
   `taper`, `bevel`, `rotation`).
2. Run `blockout.py --spec spec.json`. It reports each part's measured dimensions, the
   **drift** (measured minus requested, per axis) and the **envelope** of the whole asset.
3. Fix drift before continuing. Drift means a bevel, a taper or a rotation is eating the
   dimensions - that is a modelling bug, not a rounding error.
4. Compare the envelope to the reference (`reference-analysis`), then commit to detail.

## CLI
```
.venv/bin/python tools/bpy_run.py skills/local/modeling-blockout/scripts/blockout.py --     --spec /tmp/blockout.json --save /tmp/blockout.blend --tolerance 0.02
```

## Spec format
```json
{"parts": [
  {"name": "Hull", "type": "box", "size": [4500, 1900, 1400], "at": [0, 0, 700]},
  {"name": "Cabin", "type": "box", "size": [2400, 1600, 500], "at": [0, 100, 1600],
   "taper": 0.85, "bevel": 40}
]}
```

## Verification done
Test spec `[4.5, 1.9, 1.42]` -> measured envelope `[4.5, 1.9, 1.42]`, drift `[0, 0, 0]`,
`BLOCKOUT OK`.

## Limits (honest)
- `taper` deliberately shrinks the top face, so the drift check excludes tapered axes -
  the reported dimension is the base, not the mean.
- Bevel changes dimensions by the bevel width per edge; the drift check reports it, it
  does not silently compensate.
- Boxes and cylinders only. Curved/biomorphic forms belong in `modeling-automotive` or
  hand modelling.
