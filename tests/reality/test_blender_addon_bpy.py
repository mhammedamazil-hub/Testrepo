"""Blender addon installation test (requires bpy)."""
import sys
import os

sys.path.append('blender-addon')

import bpy

try:
    from reality_engine_studio import register, unregister
    print('Addon imported successfully')

    # Register
    register()
    print('Addon registered successfully')

    # Check panels are registered
    expected_panels = [
        'RES_PT_project_panel',
        'RES_PT_scene_panel',
        'RES_PT_entity_panel',
        'RES_PT_component_panel',
        'RES_PT_physics_panel',
        'RES_PT_runtime_panel',
        'RES_PT_export_panel',
        'RES_PT_diagnostics_panel',
    ]
    for panel_id in expected_panels:
        if hasattr(bpy.types, panel_id):
            print(f'  Panel {panel_id}: registered')
        else:
            print(f'  Panel {panel_id}: NOT FOUND')

    # Unregister
    unregister()
    print('Addon unregistered successfully')

except Exception as e:
    print(f'Addon test failed: {e}')
    sys.exit(1)