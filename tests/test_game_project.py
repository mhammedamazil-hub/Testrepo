"""Source/evidence integrity checks. Actual engine checks live under game/tests.

These tests do not execute a renderer and cannot certify 60 FPS.
"""
import hashlib
import json
import math
from pathlib import Path
import struct
import unittest

ROOT=Path(__file__).resolve().parents[1]
GAME=ROOT/'game'


def glb_json(path):
    raw=path.read_bytes()
    magic,version,length=struct.unpack_from('<4sII',raw)
    if (magic,version,length)!=(b'glTF',2,len(raw)):
        raise AssertionError('Invalid GLB header: '+str(path))
    count,kind=struct.unpack_from('<I4s',raw,12)
    if kind!=b'JSON':raise AssertionError('Missing GLB JSON')
    return json.loads(raw[20:20+count])


class GameProjectTest(unittest.TestCase):
    def test_original_scene_and_authored_asset_hashes(self):
        manifest=json.loads((GAME/'assets/asset_manifest.json').read_text())
        self.assertEqual(hashlib.sha256((ROOT/manifest['source']).read_bytes()).hexdigest(),manifest['source_sha256'])
        self.assertEqual(manifest['terrain_triangles'],61400)
        for name,metadata in manifest['files'].items():
            content=(GAME/'assets'/name).read_bytes()
            self.assertEqual(len(content),metadata['bytes'],name)
            self.assertEqual(hashlib.sha256(content).hexdigest(),metadata['sha256'],name)

    def test_native_heightfield_route_and_forest_data(self):
        data=json.loads((GAME/'assets/world_data.json').read_text())
        self.assertEqual(len(data['route']),160)
        self.assertGreater(len(data['forest']),1000)
        self.assertTrue(all(len(p)==3 and all(math.isfinite(v) for v in p) for p in data['route']))
        segments=[math.dist(p,data['route'][(i+1)%160]) for i,p in enumerate(data['route'])]
        self.assertLess(max(segments),15)
        self.assertGreater(sum(segments),900)
        self.assertLess(sum(segments),1100)

    def test_real_gltf_geometry_skin_and_animation(self):
        terrain=glb_json(GAME/'assets/terrain.glb')
        self.assertEqual(len(terrain['meshes']),2)
        self.assertTrue(all('normalTexture' in m for m in terrain['materials']))
        hiker=glb_json(GAME/'assets/hiker.glb')
        self.assertEqual(len(hiker['skins'][0]['joints']),11)
        clips={item['name'] for item in hiker['animations']}
        self.assertTrue({'Idle','Walk'}<=clips)
        car=glb_json(GAME/'assets/vehicle.glb')
        self.assertTrue({'Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR'}<=set(item.get('name','') for item in car['nodes']))

    def test_tree_impostor_is_not_empty(self):
        from PIL import Image
        with Image.open(GAME/'assets/spruce_impostor.png') as image:
            self.assertEqual(image.size,(512,1024))
            self.assertEqual(image.mode,'RGBA')
            self.assertIsNotNone(image.getchannel('A').getbbox())
            self.assertGreater(image.getchannel('A').getextrema()[1],200)

    def test_native_resolution_is_not_a_claim_of_achieved_fps(self):
        settings=(GAME/'project.godot').read_text()
        for expected in ['viewport_width=1920','viewport_height=1080','window/stretch/mode="viewport"','"gl_compatibility"']:
            self.assertIn(expected,settings)
        proof=json.loads((ROOT/'docs/game/browser-validation.json').read_text())
        self.assertTrue(proof['target_1080p_verified'])
        self.assertEqual(proof['target_60fps_verified'],bool(proof['final']['fps']>=60 and 0<proof['final']['p95_frame_ms']<=16.67))
        self.assertGreater(proof['final']['frame_samples'],0)
        self.assertEqual(proof['final']['render_scale'],1)
        self.assertIn('SwiftShader',proof['gpu']['renderer'])

    def test_actual_engine_and_rendered_gameplay_evidence(self):
        physics=json.loads((ROOT/'docs/game/headless-validation.json').read_text())
        self.assertEqual(physics['status'],'HEADLESS_GAMEPLAY_PASS')
        self.assertEqual(len(physics['checks']),14)
        self.assertTrue(all(item['passed'] for item in physics['checks']))
        self.assertFalse(physics['rendered'])
        web=json.loads((ROOT/'docs/game/browser-validation.json').read_text())
        self.assertEqual(web['status'],'BROWSER_GAMEPLAY_PASS')
        self.assertGreater(web['distance_driven_meters'],3)
        self.assertTrue(web['driving']['driving'])
        self.assertFalse(web['after']['driving'])
        self.assertEqual(web['console_errors'],[])


if __name__=='__main__':unittest.main()
