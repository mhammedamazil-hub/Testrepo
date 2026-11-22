"""Blender addon installation test (requires bpy).
Only runs when bpy is available (inside Blender).
"""
import sys
import os

_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_blender_addon_path = os.path.join(_repo_root, 'blender-addon')
for p in (_repo_root, _blender_addon_path):
    if p not in sys.path:
        sys.path.insert(0, p)


def main():
    try:
        import bpy
    except ImportError:
        print('SKIP: bpy not available (not running inside Blender)')
        return

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


if __name__ == '__main__':
    main()