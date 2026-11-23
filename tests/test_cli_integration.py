"""CLI integration tests — tests actual CLI command behavior."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from universal_engine.cli import main


def run_cli(*args, json_mode=True):
    """Run the CLI as a subprocess and return (exit_code, parsed_json_or_text)."""
    argv = list(args)
    if json_mode and "--json" not in argv:
        argv.insert(0, "--json")
    proc = subprocess.run(
        [sys.executable, "-m", "universal_engine"] + argv,
        capture_output=True, text=True, timeout=30,
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError:
        return proc.returncode, proc.stdout


class TestCliProject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_version(self):
        code, data = run_cli("version")
        self.assertEqual(code, 0)
        self.assertEqual(data["code"], "OK")
        self.assertEqual(data["data"]["name"], "universal-engine")

    def test_project_create_inspect_validate(self):
        proj = os.path.join(self.tmp, "CliGame")
        code, data = run_cli("project", "create", "CliGame", "--path", self.tmp)
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        # When --path is given, root = path, so file is at self.tmp/universal-engine.json
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "universal-engine.json")))

        code, data = run_cli("project", "inspect", "--path", self.tmp)
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["name"], "CliGame")

        code, data = run_cli("project", "validate", "--path", self.tmp)
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertTrue(data["data"]["valid"])

    def test_project_create_duplicate(self):
        run_cli("project", "create", "DupGame", "--path", self.tmp)
        code, data = run_cli("project", "create", "DupGame", "--path", self.tmp)
        self.assertEqual(code, 1)
        self.assertFalse(data["ok"])
        self.assertEqual(data["code"], "PROJECT_EXISTS")


class TestCliScene(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.proj = os.path.join(self.tmp, "SceneGame")
        run_cli("project", "create", "SceneGame", "--path", self.proj)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scene_create_inspect(self):
        code, data = run_cli("scene", "create", "Level1", "--path", self.proj)
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["objects"], 3)

        code, data = run_cli("scene", "inspect", "Level1", "--path", self.proj)
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["object_count"], 3)

    def test_scene_inspect_not_found(self):
        code, data = run_cli("scene", "inspect", "Nope", "--path", self.proj)
        self.assertEqual(code, 1)
        self.assertFalse(data["ok"])
        self.assertEqual(data["code"], "SCENE_NOT_FOUND")


class TestCliAdapters(unittest.TestCase):
    def test_adapters_list(self):
        code, data = run_cli("adapters")
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        adapters = data["data"]["adapters"]
        names = [a["name"] for a in adapters]
        self.assertIn("blender", names)
        self.assertIn("godot", names)
        godot = [a for a in adapters if a["name"] == "godot"][0]
        self.assertFalse(godot["available"])


class TestCliGameCreate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_game_create(self):
        proj = os.path.join(self.tmp, "PlayGame")
        code, data = run_cli("game", "create", "PlayGame", "--path", self.tmp)
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["game"], "PlayGame")
        # When --path is given, root = self.tmp, so files are at self.tmp/
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "project.godot")))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "scenes", "Main.tscn")))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "scripts", "Player.gd")))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "scripts", "GameManager.gd")))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "scripts", "Collectible.gd")))


class TestCliNodeScript(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.proj = os.path.join(self.tmp, "NodeGame")
        run_cli("game", "create", "NodeGame", "--path", self.proj)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_node_create_modify(self):
        code, data = run_cli("node", "create", "Main", "Marker3D", "SpawnPoint",
                             "--path", self.proj, "--parent", "World",
                             "--property", "position=1,2,3")
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])

        code, data = run_cli("node", "modify", "Main", "SpawnPoint",
                             "--path", self.proj, "--property", "position=4,5,6")
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])

    def test_script_create(self):
        code, data = run_cli("script", "create", "MyScript",
                             "--path", self.proj, "--extends", "Node3D")
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertTrue(os.path.isfile(os.path.join(self.proj, "scripts", "MyScript.gd")))


class TestCliAssetPhysics(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.proj = os.path.join(self.tmp, "AssetGame")
        run_cli("game", "create", "AssetGame", "--path", self.proj)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_asset_import(self):
        # Create dummy glb
        asset = os.path.join(self.tmp, "model.glb")
        with open(asset, "wb") as f:
            f.write(b"glTF")
        code, data = run_cli("asset", "import", asset, "--path", self.proj)
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["format"], "glb")

    def test_asset_inspect(self):
        asset = os.path.join(self.tmp, "model.glb")
        with open(asset, "wb") as f:
            f.write(b"glTF")
        code, data = run_cli("asset", "inspect", asset)
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])

    def test_physics_configure(self):
        code, data = run_cli("physics", "configure", "Main", "Rock",
                             "--path", self.proj, "--type", "RigidBody3D",
                             "--shape", "box", "--size", "2,2,2",
                             "--mass", "5.0", "--friction", "0.7")
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["body"], "Rock")
        self.assertEqual(data["data"]["mass"], 5.0)


class TestCliGameRunNoGodot(unittest.TestCase):
    """Game run without Godot binary should report BACKEND_UNAVAILABLE."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.proj = os.path.join(self.tmp, "RunGame")
        run_cli("game", "create", "RunGame", "--path", self.proj)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_game_run_no_godot(self):
        code, data = run_cli("game", "run", "--path", self.proj, "--headless")
        self.assertEqual(code, 1)
        self.assertFalse(data["ok"])
        self.assertEqual(data["code"], "BACKEND_UNAVAILABLE")

    def test_game_test_no_godot(self):
        code, data = run_cli("game", "test", "--path", self.proj, "--headless")
        self.assertEqual(code, 1)
        self.assertFalse(data["ok"])
        self.assertEqual(data["code"], "BACKEND_UNAVAILABLE")

    def test_preview_capture_no_godot(self):
        code, data = run_cli("preview", "capture", "Main", "/tmp/out.png",
                             "--path", self.proj)
        self.assertEqual(code, 1)
        self.assertFalse(data["ok"])
        self.assertEqual(data["code"], "BACKEND_UNAVAILABLE")


class TestCliBuildNoGodot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.proj = os.path.join(self.tmp, "BuildGame")
        run_cli("game", "create", "BuildGame", "--path", self.proj)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_no_godot(self):
        code, data = run_cli("build", "--path", self.proj, "--output", "builds",
                             "--platform", "linux")
        self.assertEqual(code, 1)
        self.assertFalse(data["ok"])
        self.assertEqual(data["code"], "BACKEND_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
