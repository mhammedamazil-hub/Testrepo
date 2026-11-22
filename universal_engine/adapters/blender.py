"""Blender adapter.

Blender is the central 3D authoring foundation. This adapter wraps bpy-based
headless Blender operations.

STATUS: UNAVAILABLE in this environment — Blender is not installed and cannot be
installed here (no root, no blender.org network access). The adapter provides
the interface and capability declarations only; no bpy operation can execute.
"""

from __future__ import annotations

from typing import Any, Dict

from universal_engine import UNAVAILABLE
from universal_engine.core import AdapterBase


class BlenderAdapter(AdapterBase):
    name = "blender"
    version = "0.0.0"
    status = UNAVAILABLE
    available = False

    def check_availability(self) -> bool:
        """Blender availability requires a real `bpy` / blender binary."""
        try:
            import bpy  # type: ignore  # noqa: F401
        except Exception:
            return False
        return True

    def capabilities(self) -> Dict[str, Any]:
        caps = super().capabilities()
        caps.update(
            {
                "reason": (
                    "Blender is not installed in this environment and cannot be "
                    "installed (no root access; blender.org not reachable). "
                    "bpy is not importable."
                ),
                "operations": [
                    "scene_create",
                    "object_create",
                    "mesh_generate",
                    "material_create",
                    "render",
                    "export_gltf",
                    "scene_inspect",
                    "screenshot_capture",
                ],
            }
        )
        return caps

    def headless_run(self, script: str) -> Dict[str, Any]:
        return {
            "ok": False,
            "code": "BACKEND_UNAVAILABLE",
            "error": "Blender is not installed in this environment.",
        }


def build_blender_adapter() -> BlenderAdapter:
    return BlenderAdapter()
