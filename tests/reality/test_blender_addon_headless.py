"""Blender addon headless structural test (no bpy required)."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'blender-addon'))

from reality_engine_studio import bl_info
from reality_engine_studio.panels import _classes


def test_addon_structure():
    """Verify addon has 8 panels and 16 operators."""
    print(f'Addon name: {bl_info["name"]}')
    print(f'Addon version: {bl_info["version"]}')

    panel_count = sum(1 for c in _classes if c.__name__.startswith('RES_PT'))
    operator_count = sum(1 for c in _classes if c.__name__.startswith('RES_OT'))
    print(f'Panels: {panel_count}, Operators: {operator_count}')

    assert panel_count == 8, f'Expected 8 panels, got {panel_count}'
    assert operator_count == 16, f'Expected 16 operators, got {operator_count}'

    # Verify all expected panels exist
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
        found = any(c.__name__ == panel_id for c in _classes)
        assert found, f'Panel {panel_id} not found'
        print(f'  Panel {panel_id}: present')

    # Verify all expected operators exist
    expected_operators = [
        'RES_OT_project_create',
        'RES_OT_scene_create',
        'RES_OT_scene_load',
        'RES_OT_entity_create',
        'RES_OT_entity_inspect',
        'RES_OT_entity_modify',
        'RES_OT_component_add',
        'RES_OT_component_remove',
        'RES_OT_physics_configure',
        'RES_OT_physics_simulate',
        'RES_OT_runtime_launch',
        'RES_OT_runtime_status',
        'RES_OT_runtime_inspect',
        'RES_OT_runtime_stop',
        'RES_OT_scene_export',
        'RES_OT_engine_diagnostics',
    ]
    for op_id in expected_operators:
        found = any(c.__name__ == op_id for c in _classes)
        assert found, f'Operator {op_id} not found'
        print(f'  Operator {op_id}: present')

    print('PASS: Addon structure verified: 8 panels, 16 operators')


if __name__ == '__main__':
    test_addon_structure()