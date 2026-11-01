"""Tests for the photo-carving pipeline (tools/carve_car.py, tools/carve_finish.py).

These are cheap checks that fail loudly if the pipeline regresses:

* the studio background model really does reject the backdrop,
* mask calibration returns a plausible pixels-per-metre figure,
* the delivered GLBs are watertight, correctly sized and textured,
* the renderer samples glTF UVs with a top-left origin (a V flip here silently
  mirrors every texture, which is exactly the bug this asserts against).

The heavy carve itself is not run in tests - it is minutes of CPU work. Its
output is verified from the committed artefacts instead.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools import carve_car as cc  # noqa: E402

SRC = ROOT / "carve_src"


@pytest.mark.skipif(not (SRC / "0_0_front.png").exists(), reason="turnaround sheet not present")
def test_background_model_rejects_studio_backdrop():
    rgb, mask = cc.segment_view(SRC / "0_0_front.png")
    h, w = mask.shape
    # corners are pure backdrop and must never be solid
    assert not mask[:8, :8].any()
    assert not mask[:8, -8:].any()
    assert mask.any()


@pytest.mark.skipif(not (SRC / "0_0_front.png").exists(), reason="turnaround sheet not present")
def test_calibration_is_physically_plausible():
    rgb, mask = cc.segment_view(SRC / "0_0_front.png")
    axis = cc.symmetry_axis(rgb, *cc.bbox(mask)[1::2])
    # the mirror plane must land near the middle of the car, not at an edge
    c0, _, c1, _ = cc.bbox(mask)
    assert c0 + 0.25 * (c1 - c0) < axis < c0 + 0.95 * (c1 - c0)


@pytest.mark.parametrize("tier,faces,tex", [("refined_carve", 45_000, 2048),
                                            ("refined_carve_high", 160_000, 4096)])
def test_delivered_glb_is_a_valid_car(tier, faces, tex):
    glb = ROOT / tier / "model_textured.glb"
    if not glb.exists():
        pytest.skip(f"{tier} not built")
    import trimesh
    mesh = trimesh.load(glb, force="mesh")
    assert abs(len(mesh.faces) - faces) < 0.05 * faces
    assert mesh.visual.uv is not None
    assert mesh.visual.material.baseColorTexture.size == (tex, tex)
    # real BMW M5 F90 dimensions, to the millimetre after the exact fit
    assert np.allclose(mesh.extents, [4.976, 2.126, 1.473], atol=0.005)
    metrics = json.loads((ROOT / tier / "carve_metrics.json").read_text())
    assert metrics["watertight"] is True
    assert metrics["winding_consistent"] is True
    assert max(abs(v) for v in metrics["real_world_error_pct"].values()) < 0.1


def test_renderer_samples_gltf_uvs_top_left():
    """glTF puts UV (0,0) at the top-left texel; flipping V mirrors every texture."""
    from tools import render_mesh as R
    tex = np.zeros((4, 4, 3))
    tex[0, :, :] = [1.0, 0.0, 0.0]      # top row red
    col = R.sample_texture(tex, np.array([[0.5, 0.02]]))    # near v=0 -> top row
    assert col[0, 0] > 0.9 and col[0, 1] < 0.1


def test_print_stl_matches_the_mesh_in_millimetres():
    stl = ROOT / "refined_carve" / "print_mm.stl"
    if not stl.exists():
        pytest.skip("print STL not built")
    import trimesh
    m = trimesh.load(stl)
    assert np.allclose(m.extents, [4976, 2126, 1473], atol=5)
    assert m.is_watertight
