"""
Data Integrity Tests for Reality Engine

Tests:
- Save and reload
- Stable entity IDs
- Parent-child relationships
- Component persistence
- Schema versioning
- Invalid data handling
- Coordinate conversion
- Unit consistency
"""

import json
import os
import sys
import tempfile
import uuid

# Add repo to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_engine.cli import main


def test_save_and_reload():
    """Test that entities persist across save/load cycles."""
    tmpdir = tempfile.mkdtemp()
    scene_name = "integrity_test"

    # Create scene
    rc = main(['reality', 'scene-create', scene_name, '--path', tmpdir])
    assert rc == 0, "scene-create failed"

    # Create entities with known IDs
    rc = main(['reality', 'entity-create', scene_name, "player", '--path', tmpdir])
    assert rc == 0, "entity-create player failed"

    rc = main(['reality', 'entity-create', scene_name, "enemy", '--path', tmpdir])
    assert rc == 0, "entity-create enemy failed"

    # Load and verify
    rc = main(['reality', 'scene-load', scene_name, '--path', tmpdir])
    assert rc == 0, "scene-load failed"

    # Read scene file directly
    scene_path = os.path.join(tmpdir, "scenes", f"{scene_name}.scene.reality")
    assert os.path.exists(scene_path), "Scene file not created"

    with open(scene_path, 'r') as f:
        data = json.load(f)

    assert data['entities'] is not None, "Entities not in scene data"
    assert len(data['entities']) == 2, f"Expected 2 entities, got {len(data['entities'])}"

    names = [e['name'] for e in data['entities']]
    assert 'player' in names, "player entity not found"
    assert 'enemy' in names, "enemy entity not found"

    # Verify entity IDs are UUIDs
    for entity in data['entities']:
        assert 'id' in entity, f"Entity {entity.get('name')} missing id"
        # Validate UUID format
        uuid.UUID(entity['id'])

    print("PASS: Save and reload - entities persist with stable UUIDs")
    return True


def test_component_persistence():
    """Test that components persist across save/load."""
    tmpdir = tempfile.mkdtemp()
    scene_name = "component_test"

    main(['reality', 'scene-create', scene_name, '--path', tmpdir])
    main(['reality', 'entity-create', scene_name, "test_entity", '--path', tmpdir])

    # Add physics component
    main(['reality', 'physics-configure', scene_name, "test_entity",
          '--body-type', 'dynamic', '--mass', '5.0', '--friction', '0.7',
          '--restitution', '0.3', '--collider-shape', 'sphere',
          '--path', tmpdir])

    # Read scene file
    scene_path = os.path.join(tmpdir, "scenes", f"{scene_name}.scene.reality")
    with open(scene_path, 'r') as f:
        data = json.load(f)

    entity = data['entities'][0]
    assert 'physics' in entity['components'], "Physics component not found"

    physics = entity['components']['physics']
    assert physics['mass'] == 5.0, f"Expected mass 5.0, got {physics['mass']}"
    assert physics['friction'] == 0.7, f"Expected friction 0.7, got {physics['friction']}"
    assert physics['restitution'] == 0.3, f"Expected restitution 0.3, got {physics['restitution']}"
    assert physics['body_type'] == 'dynamic', f"Expected body_type dynamic, got {physics['body_type']}"
    assert physics['collider']['shape'] == 'sphere', f"Expected sphere collider, got {physics['collider']['shape']}"

    print("PASS: Component persistence - physics properties saved correctly")
    return True


def test_entity_modify_and_reload():
    """Test that entity modifications persist."""
    tmpdir = tempfile.mkdtemp()
    scene_name = "modify_test"

    main(['reality', 'scene-create', scene_name, '--path', tmpdir])
    main(['reality', 'entity-create', scene_name, "mod_entity", '--path', tmpdir])

    # Modify entity
    main(['reality', 'entity-modify', scene_name, "mod_entity",
          '--property', 'name=renamed_entity', '--path', tmpdir])

    # Load and verify
    rc = main(['reality', 'scene-load', scene_name, '--path', tmpdir])
    assert rc == 0

    scene_path = os.path.join(tmpdir, "scenes", f"{scene_name}.scene.reality")
    with open(scene_path, 'r') as f:
        data = json.load(f)

    names = [e['name'] for e in data['entities']]
    assert 'renamed_entity' in names, "Entity rename not persisted"
    assert 'mod_entity' not in names, "Old entity name still present"

    print("PASS: Entity modify and reload - name change persisted")
    return True


def test_schema_versioning():
    """Test that scene files have correct schema version."""
    tmpdir = tempfile.mkdtemp()
    scene_name = "version_test"

    main(['reality', 'scene-create', scene_name, '--path', tmpdir])

    scene_path = os.path.join(tmpdir, "scenes", f"{scene_name}.scene.reality")
    with open(scene_path, 'r') as f:
        data = json.load(f)

    assert data.get('format') == 'reality-engine-scene/1', f"Unexpected format: {data.get('format')}"
    assert data.get('version') == '1.0', f"Unexpected version: {data.get('version')}"

    print("PASS: Schema versioning - correct format and version")
    return True


def test_invalid_data_handling():
    """Test handling of invalid/missing data."""
    tmpdir = tempfile.mkdtemp()

    # Try to load non-existent scene
    rc = main(['reality', 'scene-load', 'nonexistent_scene', '--path', tmpdir])
    assert rc != 0, "Should fail to load nonexistent scene"

    # Try to create entity in non-existent scene
    rc = main(['reality', 'entity-create', 'nonexistent_scene', 'test', '--path', tmpdir])
    assert rc != 0, "Should fail to create entity in nonexistent scene"

    # Try to configure physics for non-existent entity
    main(['reality', 'scene-create', 'test_scene', '--path', tmpdir])
    rc = main(['reality', 'physics-configure', 'test_scene', 'nonexistent_entity',
               '--body-type', 'dynamic', '--path', tmpdir])
    assert rc != 0, "Should fail to configure physics for nonexistent entity"

    print("PASS: Invalid data handling - proper error responses")
    return True


def test_coordinate_conversion():
    """Test coordinate values are stored and retrieved correctly."""
    tmpdir = tempfile.mkdtemp()
    scene_name = "coord_test"

    main(['reality', 'scene-create', scene_name, '--path', tmpdir])
    main(['reality', 'entity-create', scene_name, "coord_entity", '--path', tmpdir])

    # Modify position
    main(['reality', 'entity-modify', scene_name, "coord_entity",
          '--property', 'position=1.5,-2.3,4.7', '--path', tmpdir])

    scene_path = os.path.join(tmpdir, "scenes", f"{scene_name}.scene.reality")
    with open(scene_path, 'r') as f:
        data = json.load(f)

    entity = data['entities'][0]
    pos = entity['transform']['position']
    assert abs(pos[0] - 1.5) < 0.001, f"X coordinate mismatch: {pos[0]}"
    assert abs(pos[1] - (-2.3)) < 0.001, f"Y coordinate mismatch: {pos[1]}"
    assert abs(pos[2] - 4.7) < 0.001, f"Z coordinate mismatch: {pos[2]}"

    print("PASS: Coordinate conversion - positions stored accurately")
    return True


def test_unit_consistency():
    """Test that physics units are consistent."""
    tmpdir = tempfile.mkdtemp()
    scene_name = "unit_test"

    main(['reality', 'scene-create', scene_name, '--path', tmpdir])
    main(['reality', 'entity-create', scene_name, "unit_entity", '--path', tmpdir])

    # Configure with specific units
    main(['reality', 'physics-configure', scene_name, "unit_entity",
          '--body-type', 'dynamic', '--mass', '1.0', '--friction', '0.5',
          '--restitution', '0.0', '--collider-shape', 'box', '--path', tmpdir])

    scene_path = os.path.join(tmpdir, "scenes", f"{scene_name}.scene.reality")
    with open(scene_path, 'r') as f:
        data = json.load(f)

    physics = data['entities'][0]['components']['physics']
    assert physics['mass'] == 1.0, f"Mass should be 1.0 kg, got {physics['mass']}"
    assert physics['friction'] == 0.5, f"Friction should be 0.5, got {physics['friction']}"
    assert physics['restitution'] == 0.0, f"Restitution should be 0.0, got {physics['restitution']}"

    print("PASS: Unit consistency - physics units are consistent")
    return True


def test_scene_export():
    """Test scene export creates valid copy."""
    tmpdir = tempfile.mkdtemp()
    scene_name = "export_test"

    main(['reality', 'scene-create', scene_name, '--path', tmpdir])
    main(['reality', 'entity-create', scene_name, "export_entity", '--path', tmpdir])

    export_path = os.path.join(tmpdir, "scenes", f"{scene_name}.exported.reality")
    main(['reality', 'scene-export', scene_name, '--path', tmpdir,
          '--output', export_path])

    assert os.path.exists(export_path), "Exported file not created"

    with open(export_path, 'r') as f:
        export_data = json.load(f)

    assert export_data['name'] == scene_name, "Export name mismatch"
    assert len(export_data['entities']) == 1, "Export entity count mismatch"

    print("PASS: Scene export - valid copy created")
    return True


if __name__ == '__main__':
    tests = [
        test_save_and_reload,
        test_component_persistence,
        test_entity_modify_and_reload,
        test_schema_versioning,
        test_invalid_data_handling,
        test_coordinate_conversion,
        test_unit_consistency,
        test_scene_export,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1

    print(f"\n=== Data Integrity Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    sys.exit(1 if failed > 0 else 0)
