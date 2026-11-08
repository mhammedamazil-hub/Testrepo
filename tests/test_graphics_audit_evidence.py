"""Validate stored proof consistency, not the current machine's graphics speed.

Re-run the actual tools to test graphics execution. These tests need no GPU,
Blender or ModernGL, and must not silently promote export to engine validation.
"""
import hashlib
import json
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/research-assets'


class GraphicsEvidenceTest(unittest.TestCase):
    def test_software_graphics_evidence_is_explicitly_cpu_only(self):
        proof = json.loads((ASSETS/'software-opengl-proof.json').read_text())
        self.assertEqual(proof['status'], 'SOFTWARE_OPENGL_AND_COMPUTE_PROOF_PASS')
        self.assertIn('llvmpipe', proof['renderer'])
        self.assertGreaterEqual(proof['version_code'], 430)
        self.assertFalse(proof['gpu_hardware_added'])
        self.assertEqual(proof['execution_device'], 'CPU')
        self.assertEqual(proof['compute_shader_values_verified'], 256)
        self.assertEqual(hashlib.sha256((ASSETS/'software-opengl-proof.png').read_bytes()).hexdigest(),
                         proof['image_sha256'])

    def test_asset_manifest_and_baked_texture_dimensions(self):
        directory = ASSETS/'game-ready-wall'
        proof = json.loads((directory/'proof.json').read_text())
        for filename, metadata in proof['files'].items():
            content = (directory/filename).read_bytes()
            self.assertEqual(len(content), metadata['bytes'])
            self.assertEqual(hashlib.sha256(content).hexdigest(), metadata['sha256'])
        for filename in ['wall_basecolor.png','wall_normal.png']:
            image = (directory/filename).read_bytes()
            self.assertEqual(image[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack_from('>II', image, 16), (512,512))

    def test_glb_contains_portable_materials_and_geometry(self):
        raw = (ASSETS/'game-ready-wall/wall.glb').read_bytes()
        magic, version, length = struct.unpack_from('<4sII',raw)
        self.assertEqual((magic,version,length), (b'glTF',2,len(raw)))
        json_length, chunk_type = struct.unpack_from('<I4s',raw,12)
        self.assertEqual(chunk_type,b'JSON')
        data = json.loads(raw[20:20+json_length])
        material = data['materials'][0]
        self.assertIn('baseColorTexture',material['pbrMetallicRoughness'])
        self.assertIn('normalTexture',material)
        self.assertEqual(len(data['images']),2)
        self.assertTrue(all('bufferView' in item for item in data['images']))
        for mesh in data['meshes']:
            for primitive in mesh['primitives']:
                self.assertTrue({'POSITION','NORMAL','TEXCOORD_0','TANGENT'} <= primitive['attributes'].keys())

    def test_limitations_and_eevee_evidence_are_not_overstated(self):
        directory = ASSETS/'game-ready-wall'
        proof = json.loads((directory/'proof.json').read_text())
        self.assertFalse(proof['godot_import_tested'])
        self.assertFalse(proof['unity_import_tested'])
        self.assertFalse(proof['integration_stability_proven'])
        self.assertIn('SIGSEGV',proof['native_bpy_finalization'])
        self.assertIn('WORKAROUND',proof['status'])
        eevee = proof['eevee_software_render']
        self.assertFalse(eevee['realtime_gameplay_tested'])
        self.assertIn('llvmpipe',eevee['renderer'])
        self.assertEqual(hashlib.sha256((directory/'eevee-software-proof.png').read_bytes()).hexdigest(),
                         eevee['image_sha256'])


if __name__ == '__main__':
    unittest.main()
