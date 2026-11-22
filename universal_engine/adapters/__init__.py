"""Platform adapters.

Each adapter wraps an external backend (Blender, Godot, physics, ...). Adapters
declare capabilities and availability; none is required for the platform core to
run.
"""

from universal_engine.adapters.blender import BlenderAdapter
from universal_engine.adapters.godot import GodotAdapter, build_godot_adapter

__all__ = ["BlenderAdapter", "GodotAdapter", "build_godot_adapter"]
