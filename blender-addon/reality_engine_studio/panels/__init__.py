"""
Reality Engine Studio - Panels package
"""

from .project_panel import (
    RES_PT_project_panel,
    RES_OT_project_create,
)
from .scene_panel import (
    RES_PT_scene_panel,
    RES_OT_scene_create,
    RES_OT_scene_load,
)
from .entity_panel import (
    RES_PT_entity_panel,
    RES_OT_entity_create,
    RES_OT_entity_inspect,
    RES_OT_entity_modify,
)
from .component_panel import (
    RES_PT_component_panel,
    RES_OT_component_add,
    RES_OT_component_remove,
)
from .physics_panel import (
    RES_PT_physics_panel,
    RES_OT_physics_configure,
    RES_OT_physics_simulate,
)
from .runtime_panel import (
    RES_PT_runtime_panel,
    RES_OT_runtime_launch,
    RES_OT_runtime_status,
    RES_OT_runtime_inspect,
    RES_OT_runtime_stop,
)
from .export_panel import (
    RES_PT_export_panel,
    RES_OT_scene_export,
)
from .diagnostics_panel import (
    RES_PT_diagnostics_panel,
    RES_OT_engine_diagnostics,
)

# All classes to register/unregister
_classes = [
    RES_PT_project_panel,
    RES_OT_project_create,
    RES_PT_scene_panel,
    RES_OT_scene_create,
    RES_OT_scene_load,
    RES_PT_entity_panel,
    RES_OT_entity_create,
    RES_OT_entity_inspect,
    RES_OT_entity_modify,
    RES_PT_component_panel,
    RES_OT_component_add,
    RES_OT_component_remove,
    RES_PT_physics_panel,
    RES_OT_physics_configure,
    RES_OT_physics_simulate,
    RES_PT_runtime_panel,
    RES_OT_runtime_launch,
    RES_OT_runtime_status,
    RES_OT_runtime_inspect,
    RES_OT_runtime_stop,
    RES_PT_export_panel,
    RES_OT_scene_export,
    RES_PT_diagnostics_panel,
    RES_OT_engine_diagnostics,
]


def register():
    """Register all panel classes."""
    try:
        import bpy
        for cls in _classes:
            bpy.utils.register_class(cls)
    except ImportError:
        for cls in _classes:
            cls.register()


def unregister():
    """Unregister all panel classes."""
    try:
        import bpy
        for cls in reversed(_classes):
            bpy.utils.unregister_class(cls)
    except ImportError:
        for cls in reversed(_classes):
            cls.unregister()


register_all = register
unregister_all = unregister
