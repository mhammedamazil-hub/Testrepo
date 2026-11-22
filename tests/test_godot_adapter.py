"""Tests for the Godot adapter (file generation, no Godot binary required)."""

import json
import os
import shutil
import tempfile
import unittest

from universal_engine.adapters.godot import (
    GodotAdapter,
    _escape_godot_string,
    _variant,
    build_godot_adapter,
)
from universal_engine.cli import (
    _player_gdscript,
    _game_manager_gdscript,
    _collectible_gdscript,
    _write_main_scene,
)


class TestGodotHelpers(unittest.TestCase):
    def test_escape_godot_string(self):
        self.assertEqual(_escape_godot_string('hello"world'), 'hello\\"world')
        self.assertEqual(_escape_godot_string("a\\b"), "a\\\\b")

    def test_variant_bool(self):
        self.assertEqual(_variant(True), "true")
        self.assertEqual(_variant(False), "false")

    def test_variant_int(self):
        self.assertEqual(_variant(42), "42")

    def test_variant_float(self):
        self.assertTrue(_variant(3.5).endswith("3.5") or _variant(3.5) == "3.5")
        self.assertIn(".", _variant(1.0))

    def test_variant_string(self):
        self.assertEqual(_variant("hello"), '"hello"')

    def test_variant_list(self):
        self.assertEqual(_variant([1, 2, 3]), "[1, 2, 3]")

    def test_adapter_not_available_without_godot(self):
        adapter = GodotAdapter()
        self.assertFalse(adapter.available)
        self.assertIsNone(adapter.godot_path)

    def test_adapter_capabilities(self):
        adapter = GodotAdapter()
        caps = adapter.capabilities()
        self.assertEqual(caps["name"], "godot")
        self.assertEqual(caps["status"], "PLANNED")
        self.assertFalse(caps["available"])
        self.assertGreater(len(caps["operations"]), 0)
        self.assertIn("project_create", caps["operations"])
        self.assertIn("game_run", caps["operations"])

    def test_build_godot_adapter(self):
        adapter = build_godot_adapter()
        self.assertIsInstance(adapter, GodotAdapter)


class TestGodotProjectCreation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.adapter = GodotAdapter()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_project_create(self):
        root = os.path.join(self.tmp, "godot_proj")
        result = self.adapter.project_create(root, name="TestGame")
        self.assertTrue(result["ok"], result.get("error"))
        self.assertTrue(os.path.isfile(os.path.join(root, "project.godot")))
        self.assertTrue(os.path.isfile(os.path.join(root, "scenes", "Main.tscn")))
        self.assertTrue(os.path.isdir(os.path.join(root, "scripts")))
        self.assertTrue(os.path.isdir(os.path.join(root, "assets")))
        self.assertTrue(os.path.isdir(os.path.join(root, "builds")))

        # Verify project.godot content
        pg = os.path.join(root, "project.godot")
        with open(pg) as f:
            content = f.read()
        self.assertIn('name="TestGame"', content)
        self.assertIn('run/main_scene="res://scenes/Main.tscn"', content)

    def test_project_create_idempotent(self):
        root = os.path.join(self.tmp, "godot_proj2")
        r1 = self.adapter.project_create(root, name="TestGame")
        self.assertTrue(r1["ok"])
        r2 = self.adapter.project_create(root, name="TestGame")
        # Should still succeed (mkdir exist_ok=True, overwrite project.godot)
        self.assertTrue(r2["ok"])


class TestGodotSceneGeneration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.adapter = GodotAdapter()
        self.adapter.project_create(self.tmp, name="TestGame")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scene_create_basic(self):
        result = self.adapter.scene_create(self.tmp, "Level1", nodes=[
            {"type": "Node3D", "name": "Root"},
            {"type": "Camera3D", "name": "Camera", "parent": "Root"},
        ])
        self.assertTrue(result["ok"], result.get("error"))
        scene_path = os.path.join(self.tmp, "scenes", "Level1.tscn")
        self.assertTrue(os.path.isfile(scene_path))

        with open(scene_path) as f:
            content = f.read()
        self.assertIn('[gd_scene', content)
        self.assertIn('[node name="Root" type="Node3D"]', content)
        self.assertIn('[node name="Camera" type="Camera3D" parent="Root"]', content)

    def test_scene_inspect(self):
        self.adapter.scene_create(self.tmp, "Level1", nodes=[
            {"type": "Node3D", "name": "Root"},
            {"type": "Camera3D", "name": "Camera", "parent": "Root"},
        ])
        result = self.adapter.scene_inspect(self.tmp, "Level1")
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["data"]["scene"], "Level1")
        self.assertEqual(result["data"]["node_count"], 2)
        names = [n["name"] for n in result["data"]["nodes"]]
        self.assertIn("Root", names)
        self.assertIn("Camera", names)

    def test_scene_inspect_not_found(self):
        result = self.adapter.scene_inspect(self.tmp, "Nonexistent")
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "SCENE_NOT_FOUND")

    def test_node_create(self):
        self.adapter.scene_create(self.tmp, "Level1", nodes=[
            {"type": "Node3D", "name": "Root"},
        ])
        result = self.adapter.node_create(
            self.tmp, "Level1", "CharacterBody3D", "Player",
            parent="Root", properties={"position": [0, 2, 0]},
        )
        self.assertTrue(result["ok"], result.get("error"))

        # Verify node was added
        result2 = self.adapter.scene_inspect(self.tmp, "Level1")
        names = [n["name"] for n in result2["data"]["nodes"]]
        self.assertIn("Player", names)

    def test_node_modify(self):
        self.adapter.scene_create(self.tmp, "Level1", nodes=[
            {"type": "Node3D", "name": "Root"},
        ])
        self.adapter.node_create(
            self.tmp, "Level1", "CharacterBody3D", "Player",
            parent="Root", properties={"position": [0, 2, 0]},
        )
        result = self.adapter.node_modify(
            self.tmp, "Level1", "Player",
            properties={"position": [0, 5, 0], "scale": [2, 2, 2]},
        )
        self.assertTrue(result["ok"], result.get("error"))

    def test_script_create(self):
        result = self.adapter.script_create(self.tmp, "Player", extends="CharacterBody3D")
        self.assertTrue(result["ok"], result.get("error"))
        script_path = os.path.join(self.tmp, "scripts", "Player.gd")
        self.assertTrue(os.path.isfile(script_path))
        with open(script_path) as f:
            content = f.read()
        self.assertIn("extends CharacterBody3D", content)
        self.assertIn("func _ready", content)

    def test_asset_import(self):
        # Create a dummy asset file
        asset_path = os.path.join(self.tmp, "test_model.glb")
        with open(asset_path, "wb") as f:
            f.write(b"\x00\x00\x00\x00glTF")

        result = self.adapter.asset_import(self.tmp, asset_path)
        self.assertTrue(result["ok"], result.get("error"))
        dest = os.path.join(self.tmp, "assets", "test_model.glb")
        self.assertTrue(os.path.isfile(dest))
        self.assertEqual(result["data"]["format"], "glb")


class TestPlayableGameGeneration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_player_gdscript(self):
        script = _player_gdscript()
        self.assertIn("extends CharacterBody3D", script)
        self.assertIn("func _physics_process", script)
        self.assertIn("move_and_slide", script)
        self.assertIn("jump_velocity", script)

    def test_game_manager_gdscript(self):
        script = _game_manager_gdscript()
        self.assertIn("extends Node3D", script)
        self.assertIn("func _on_collectible_collected", script)
        self.assertIn("func _on_restart_button_pressed", script)
        self.assertIn("get_tree().reload_current_scene", script)
        self.assertIn("UI/ScoreLabel", script)

    def test_collectible_gdscript(self):
        script = _collectible_gdscript()
        self.assertIn("extends Area3D", script)
        self.assertIn("body_entered.connect", script)
        self.assertIn("queue_free()", script)

    def test_write_main_scene(self):
        proj = os.path.join(self.tmp, "Game")
        _write_main_scene(proj)
        scene_path = os.path.join(proj, "scenes", "Main.tscn")
        self.assertTrue(os.path.isfile(scene_path))
        with open(scene_path) as f:
            content = f.read()
        # Valid Godot .tscn structure
        self.assertIn("[gd_scene", content)
        self.assertIn("load_steps=", content)
        self.assertIn("format=3", content)
        self.assertIn('[ext_resource path="res://scripts/Player.gd"', content)
        self.assertIn('[ext_resource path="res://scripts/GameManager.gd"', content)
        self.assertIn('[ext_resource path="res://scripts/Collectible.gd"', content)
        # Sub-resources at top level
        self.assertIn('[sub_resource type="BoxShape3D" id=1]', content)
        self.assertIn('[sub_resource type="CapsuleShape3D" id=2]', content)
        # Nodes with full parent paths
        self.assertIn('[node name="Ground" type="StaticBody3D" parent="World"]', content)
        self.assertIn('[node name="Player" type="CharacterBody3D" parent="World"]', content)
        self.assertIn('[node name="Camera" type="Camera3D" parent="World/Player"]', content)
        self.assertIn('[node name="GameManager" type="Node3D" parent="World"]', content)
        # UI nodes
        self.assertIn('[node name="ScoreLabel" type="Label" parent="World/UI"]', content)
        self.assertIn('[node name="RestartButton" type="Button" parent="World/UI"]', content)
        # Collectibles
        self.assertIn("Collectible0", content)
        self.assertIn("Collectible4", content)
        # Player in "player" group
        self.assertIn('groups = ["player"]', content)

    def test_game_create_end_to_end(self):
        from universal_engine.adapters.godot import build_godot_adapter
        adapter = build_godot_adapter()
        root = os.path.join(self.tmp, "MyGame")

        # Replicate game_create steps
        presult = adapter.project_create(root, name="MyGame")
        self.assertTrue(presult["ok"], presult.get("error"))

        nodes = [
            {"type": "Node3D", "name": "World"},
            {"type": "Node3D", "name": "Ground", "parent": "World"},
            {"type": "Node3D", "name": "Player", "parent": "World"},
            {"type": "Node3D", "name": "Camera", "parent": "Player"},
            {"type": "Node3D", "name": "Light", "parent": "World"},
            {"type": "Node3D", "name": "Collectibles", "parent": "World"},
            {"type": "Node3D", "name": "GameManager", "parent": "World"},
            {"type": "CanvasLayer", "name": "UI", "parent": "World"},
        ]
        sresult = adapter.scene_create(root, "Main", nodes=nodes)
        self.assertTrue(sresult["ok"], sresult.get("error"))

        adapter.script_create(root, "Player", extends="CharacterBody3D", code=_player_gdscript())
        adapter.script_create(root, "GameManager", extends="Node3D", code=_game_manager_gdscript())
        adapter.script_create(root, "Collectible", extends="Area3D", code=_collectible_gdscript())
        _write_main_scene(root)

        # Verify all files exist
        self.assertTrue(os.path.isfile(os.path.join(root, "project.godot")))
        self.assertTrue(os.path.isfile(os.path.join(root, "scenes", "Main.tscn")))
        self.assertTrue(os.path.isfile(os.path.join(root, "scripts", "Player.gd")))
        self.assertTrue(os.path.isfile(os.path.join(root, "scripts", "GameManager.gd")))
        self.assertTrue(os.path.isfile(os.path.join(root, "scripts", "Collectible.gd")))

    def test_godot_unavailable_for_runtime(self):
        adapter = GodotAdapter()
        self.assertFalse(adapter.available)
        result = adapter.game_run(self.tmp)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "BACKEND_UNAVAILABLE")

        result = adapter.game_test(self.tmp)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "BACKEND_UNAVAILABLE")

        result = adapter.preview_capture(self.tmp, "Main", "/tmp/out.png")
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "BACKEND_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
