"""Unit tests for the provider layer. Run: python3 -m pytest app/tests -q  (or unittest)

These tests never touch the network and never claim to prove model quality:
they verify the plumbing (artifact classification, provider resolution, GLB
validity of the mock output, and honest labelling of simulated results).
"""
from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.server.config import Settings
from app.server.providers.base import GenerationOptions, ProgressFn
from app.server.providers.mock import MockProvider
from app.server.providers.registry import build_providers, resolve
from app.server.providers.replicate import _glb_or_obj


class TestMockProvider(unittest.TestCase):
    def test_produces_valid_glb_and_obj(self):
        provider = MockProvider()
        with tempfile.TemporaryDirectory() as tmp:
            events: list[tuple[str, int, str]] = []
            result = provider.generate(
                Path(__file__), GenerationOptions(), Path(tmp), lambda s, p, m: events.append((s, p, m))
            )
            self.assertTrue(result.simulated, "mock output must always be flagged simulated")
            self.assertIsNotNone(result.glb_path)

            raw = result.glb_path.read_bytes()
            magic, version, total = struct.unpack("<4sII", raw[:12])
            self.assertEqual(magic, b"glTF")
            self.assertEqual(version, 2)
            self.assertEqual(total, len(raw), "GLB header length must match file size")
            json_len, json_type = struct.unpack("<I4s", raw[12:20])
            self.assertEqual(json_type, b"JSON")
            gltf = json.loads(raw[20 : 20 + json_len])
            self.assertEqual(gltf["asset"]["version"], "2.0")
            self.assertIn("SIMULATED", gltf["nodes"][0]["name"])

            self.assertTrue(result.obj_path.exists())
            self.assertIn("SIMULATED", result.obj_path.read_text().splitlines()[0])
            self.assertEqual(events[-1][1], 100, "progress must reach 100%")

    def test_reports_not_real_inference(self):
        self.assertFalse(MockProvider().real_inference)


class TestRegistry(unittest.TestCase):
    def test_all_providers_present(self):
        providers = build_providers(Settings())
        self.assertEqual(set(providers), {"mock", "hf_space", "replicate", "local_gpu"})
        self.assertFalse(providers["mock"].real_inference)
        for name in ("hf_space", "replicate", "local_gpu"):
            self.assertTrue(providers[name].real_inference, f"{name} must be a real provider")

    def test_resolve_and_unknown(self):
        settings = Settings()
        self.assertEqual(resolve(settings, "mock").name, "mock")
        with self.assertRaises(KeyError):
            resolve(settings, "does-not-exist")

    def test_replicate_needs_token(self):
        providers = build_providers(Settings())
        providers["replicate"].token = None
        self.assertFalse(providers["replicate"].is_configured())
        providers["replicate"].token = "dummy"
        self.assertTrue(providers["replicate"].is_configured())


class TestArtifactSniffing(unittest.TestCase):
    def test_detects_formats_by_magic_bytes(self):
        self.assertEqual(_glb_or_obj(b"glTF\x02\x00\x00\x00"), "glb")
        self.assertEqual(_glb_or_obj(b"v 1.0 0.0 0.0\nv 0.0 1.0 0.0\n"), "obj")
        self.assertEqual(_glb_or_obj(b"# exported\nv 0 0 0\n"), "obj")
        self.assertEqual(_glb_or_obj(b"\x89PNG\r\n\x1a\n...."), "png")
        self.assertEqual(_glb_or_obj(b"\x00\x00\x00\x20ftypisom"), "mp4")
        self.assertIsNone(_glb_or_obj(b"random junk"))


class TestSettings(unittest.TestCase):
    def test_public_summary_never_leaks_secrets(self):
        settings = Settings()
        settings.hf_token = "hf_SECRET"
        settings.replicate_token = "r8_SECRET"
        blob = json.dumps(settings.public_summary())
        self.assertNotIn("hf_SECRET", blob)
        self.assertNotIn("r8_SECRET", blob)
        self.assertIn('"hf_token_present": true', blob)


if __name__ == "__main__":
    unittest.main(verbosity=2)
