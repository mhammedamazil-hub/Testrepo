"""
Reality Engine Studio - Blender Addon
=====================================

A Blender addon providing 8 panels for Reality Engine development:
1. Project Panel - project creation and management
2. Scene Panel - scene creation and management
3. Entity Panel - entity creation and inspection
4. Component Panel - component add/remove
5. Physics Panel - physics configuration and simulation
6. Runtime Panel - runtime launch/inspect/stop
7. Export Panel - scene export
8. Diagnostics Panel - engine diagnostics

Designed to work both with Blender (bpy) available and in headless/CI environments
where bpy is not installed.
"""

bl_info = {
    "name": "Reality Engine Studio",
    "author": "Reality Engine Team",
    "version": (0, 1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Reality Engine",
    "description": "Reality Engine Studio - 8-panel Blender addon for game development",
    "category": "Game Development",
}

import sys
import os

# Add the parent directory to path so we can import universal_engine
_addon_dir = os.path.dirname(__file__)
_repo_root = os.path.abspath(os.path.join(_addon_dir, "..", "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Try to import bpy; if unavailable (headless/CI), we still register stub classes
try:
    import bpy
    from bpy.props import StringProperty, IntProperty, BoolProperty, FloatProperty, EnumProperty
    from bpy.types import Panel, Operator, PropertyGroup
    _BPY_AVAILABLE = True
except ImportError:
    _BPY_AVAILABLE = False

    # Stub classes for headless environments
    class bpy:
        class types:
            class Panel:
                bl_idname = ""
                bl_label = ""
                bl_space_type = ""
                bl_region_type = ""
                bl_category = ""

                @classmethod
                def register(cls):
                    pass

                @classmethod
                def unregister(cls):
                    pass

                def draw(self, context):
                    pass

            class Operator:
                bl_idname = ""
                bl_label = ""

                @classmethod
                def register(cls):
                    pass

                @classmethod
                def unregister(cls):
                    pass

                def execute(self, context):
                    pass

        class props:
            @staticmethod
            def StringProperty(**kwargs):
                return ""

            @staticmethod
            def IntProperty(**kwargs):
                return 0

            @staticmethod
            def BoolProperty(**kwargs):
                return False

            @staticmethod
            def FloatProperty(**kwargs):
                return 0.0

            @staticmethod
            def EnumProperty(**kwargs):
                return ""

    class Panel:
        bl_idname = ""
        bl_label = ""
        bl_space_type = ""
        bl_region_type = ""
        bl_category = ""

        @classmethod
        def register(cls):
            pass

        @classmethod
        def unregister(cls):
            pass

        def draw(self, context):
            pass

    class Operator:
        bl_idname = ""
        bl_label = ""

        @classmethod
        def register(cls):
            pass

        @classmethod
        def unregister(cls):
            pass

        def execute(self, context):
            pass

    class PropertyGroup:
        pass


# Module-level property exports (for use when bpy is unavailable)
StringProperty = bpy.props.StringProperty
IntProperty = bpy.props.IntProperty
BoolProperty = bpy.props.BoolProperty
FloatProperty = bpy.props.FloatProperty
EnumProperty = bpy.props.EnumProperty

# Import panel modules
from . import panels

# Register all panel classes
_classes = []

if _BPY_AVAILABLE:
    from .panels import register_all as _register_all, unregister_all as _unregister_all
else:
    # In headless mode, panels module still provides stub classes
    from .panels import register_all as _register_all, unregister_all as _unregister_all


def register():
    """Register all Reality Engine Studio addon classes."""
    _register_all()


def unregister():
    """Unregister all Reality Engine Studio addon classes."""
    _unregister_all()


if __name__ == "__main__":
    register()
