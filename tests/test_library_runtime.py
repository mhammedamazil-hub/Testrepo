"""Guard licensed library packaging and the actual second-runtime contract."""
import hashlib,json,struct,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'game/assets/library'
def glb(path):
 data=path.read_bytes();size=struct.unpack_from('<I',data,12)[0];return json.loads(data[20:20+size])
class LibraryRuntimeTest(unittest.TestCase):
 def test_compiled_library_matches_recorded_hashes(self):
  manifest=json.loads((LIB/'manifest.json').read_text())
  self.assertEqual(manifest['license'],'CC0-1.0')
  for name,record in manifest['files'].items():
   data=(LIB/name).read_bytes();self.assertEqual(len(data),record['bytes']);self.assertEqual(hashlib.sha256(data).hexdigest(),record['sha256'])
 def test_actual_selected_grass_and_budgeted_pine_geometry(self):
  for name,triangles in [('grass',79),('pine',412)]:
   j=glb(LIB/(name+'.glb'));count=sum(j['accessors'][p['indices']]['count']//3 for m in j['meshes'] for p in m['primitives']);self.assertEqual(count,triangles)
 def test_pine_atlas_opaque_wood_islands_are_excluded(self):
  image=Image.open(LIB/'pine_twig_rgba.png');self.assertEqual(image.size,(211,421))
  alpha=list(image.getchannel('A').get_flattened_data());coverage=sum(a>128 for a in alpha)/len(alpha)
  self.assertGreater(coverage,.1);self.assertLess(coverage,.4)
 def test_bpy_scene_contract_protects_cinematic_and_native_size(self):
  level=json.loads((ROOT/'engine/level.json').read_text());self.assertEqual(level['source_blend_sha256'],'ef72c7f780af86dd6b89a07ae13aab9970d485ed782e835c19061c57b343dfc3');self.assertIn('bpy',level['compiler']);self.assertEqual(level['viewport'],[1920,1080]);self.assertEqual(level['physics_hz'],60)
 def test_chosen_runtime_licenses_are_preserved(self):
  text=(ROOT/'engine/THIRD_PARTY_NOTICES.txt').read_text();self.assertIn('Three.js (MIT)',text);self.assertIn('Rapier (Apache-2.0)',text);self.assertIn('postprocessing (Zlib)',text);self.assertIn('Permission is granted',text)
 def test_both_editions_receive_real_library_models(self):
  source=(ROOT/'game/code/main.gd').read_text();self.assertIn('res://assets/library/pine.glb',source);self.assertIn('res://assets/library/grass.glb',source)
  source=(ROOT/'engine/src/world.js').read_text();self.assertIn('new Water(',source);self.assertIn('this.addCollider(mesh)',source);self.assertIn('material.depthWrite=true',source)
 def test_native_mirror_prevents_water_recursion(self):
  source=(ROOT/'game/code/lake_effects.gd').read_text();self.assertIn('SubViewport.UPDATE_ALWAYS',source);self.assertIn('mirror.cull_mask = 1',source);self.assertIn('lake.layers = 2',source)
