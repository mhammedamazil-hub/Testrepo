"""Unit tests for the platform core (pure Python — no Blender/Godot required).

Run with: python -m unittest discover -s tests -v
"""

import json
import os
import tempfile
import unittest

from universal_engine import PLANNED, UNAVAILABLE
from universal_engine.adapters import BlenderAdapter, GodotAdapter
from universal_engine.core import (
    ObjectDef,
    Project,
    Scene,
    Transform,
    error_result,
    ok_result,
)


class TestResultShapes(unittest.TestCase):
    def test_ok_result(self):
        r = ok_result(data={"x": 1})
        self.assertTrue(r["ok"])
        self.assertEqual(r["code"], "OK")
        self.assertEqual(r["data"], {"x": 1})
        self.assertIsNone(r["error"])

    def test_error_result(self):
        r = error_result("E1", "something broke")
        self.assertFalse(r["ok"])
        self.assertEqual(r["code"], "E1")
        self.assertEqual(r["error"]["code"], "E1")
        self.assertEqual(r["error"]["message"], "something broke")


class TestTransform(unittest.TestCase):
    def test_defaults(self):
        t = Transform()
        self.assertEqual(t.position, [0.0, 0.0, 0.0])
        self.assertEqual(t.rotation, [0.0, 0.0, 0.0])
        self.assertEqual(t.scale, [1.0, 1.0, 1.0])


class TestScene(unittest.TestCase):
    def test_add_and_find(self):
        scene = Scene(name="Test")
        scene.add_object(ObjectDef(id="o1", name="Cube", type="Mesh"))
        self.assertEqual(scene.find_object("o1").name, "Cube")
        self.assertIsNone(scene.find_object("nope"))

    def test_find_by_name(self):
        scene = Scene(name="Test")
        scene.add_object(ObjectDef(id="o1", name="Cube", type="Mesh"))
        scene.add_object(ObjectDef(id="o2", name="Player", type="CharacterBody3D"))
        self.assertEqual(scene.find_object_by_name("Cube").id, "o1")
        self.assertEqual(scene.find_object_by_name("Player").id, "o2")
        self.assertIsNone(scene.find_object_by_name("Nope"))

    def test_serialization_roundtrip(self):
        scene = Scene(name="Roundtrip")
        scene.add_object(
            ObjectDef(id="o1", name="Light", type="Light", transform=Transform(position=[1, 2, 3]))
        )
        restored = Scene.from_dict(scene.to_dict())
        self.assertEqual(restored.name, "Roundtrip")
        obj = restored.find_object("o1")
        self.assertIsNotNone(obj)
        self.assertEqual(obj.transform.position, [1.0, 2.0, 3.0])


class TestProject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "mygame")

    def test_create_and_structure(self):
        project = Project(self.root, name="mygame")
        self.assertFalse(project.exists)
        result = project.create()
        self.assertTrue(result["ok"])
        self.assertTrue(project.exists)
        self.assertTrue(os.path.isfile(project.descriptor_path))
        for d in ("scenes", "assets", "scripts", "builds"):
            self.assertTrue(os.path.isdir(os.path.join(project.root, d)))
        desc = project.descriptor()
        self.assertEqual(desc["name"], "mygame")
        self.assertEqual(desc["root"], self.root)

    def test_create_idempotent_error(self):
        project = Project(self.root, name="dup")
        self.assertTrue(project.create()["ok"])
        result = project.create()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "PROJECT_EXISTS")

    def test_validate(self):
        project = Project(self.root, name="val")
        project.create()
        result = project.validate()
        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["valid"])
        self.assertEqual(result["data"]["issues"], [])


class TestSceneFileIO(unittest.TestCase):
    def test_create_and_inspect_roundtrip(self):
        tmp = tempfile.mkdtemp()
        project = Project(tmp, name="proj")
        project.create()
        scene = Scene(name="Level1")
        scene.add_object(ObjectDef(id="cam-1", name="Camera", type="Camera"))
        path = project.scene_path("Level1")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(scene.to_dict(), f)

        self.assertIn("Level1.scene.json", project.list_scenes())
        with open(path, "r", encoding="utf-8") as f:
            restored = Scene.from_dict(json.load(f))
        self.assertEqual(len(restored.objects), 1)


class TestAdapters(unittest.TestCase):
    def test_blender_adapter_unavailable(self):
        adapter = BlenderAdapter()
        self.assertFalse(adapter.available)
        self.assertEqual(adapter.status, UNAVAILABLE)
        caps = adapter.capabilities()
        self.assertEqual(caps["available"], False)
        self.assertGreater(len(caps["operations"]), 0)

    def test_godot_adapter_planned(self):
        adapter = GodotAdapter()
        self.assertFalse(adapter.available)
        self.assertEqual(adapter.status, PLANNED)
        caps = adapter.capabilities()
        self.assertEqual(caps["available"], False)
        self.assertGreater(len(caps["operations"]), 0)


if __name__ == "__main__":
    unittest.main()
