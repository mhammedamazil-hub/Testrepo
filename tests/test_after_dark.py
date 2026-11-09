"""Source, compiled model, sky rights and crawler-card regression guards."""
import hashlib,json,struct,unittest
from pathlib import Path
from html.parser import HTMLParser
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
class Metadata(HTMLParser):
 def __init__(self):super().__init__();self.tags={}
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='meta':self.tags[a.get('property',a.get('name',''))]=a.get('content','')
class AfterDarkTest(unittest.TestCase):
 def test_original_user_model_is_unchanged_and_attributed(self):
  meta=json.loads((ROOT/'engine/roadster-model.json').read_text());self.assertEqual(meta['source_sha256'],hashlib.sha256((ROOT/'roadster_lite.glb').read_bytes()).hexdigest());self.assertEqual(meta['author'],'metarex.4d');self.assertEqual(meta['license'],'CC-BY-4.0');self.assertTrue(meta['original_unchanged'])
 def test_compiled_model_has_four_wheels_and_correct_binary_hash(self):
  meta=json.loads((ROOT/'engine/roadster-model.json').read_text());path=ROOT/'engine/public/world/roadster/roadster.glb';data=path.read_bytes();self.assertEqual(hashlib.sha256(data).hexdigest(),meta['output_sha256']);j=json.loads(data[20:20+struct.unpack_from('<I',data,12)[0]]);names=[x.get('name') for x in j['nodes']]
  for key in ['FL','FR','RL','RR']:self.assertIn('Roadster_Spin_'+key,names)
  self.assertEqual(len(meta['wheels']),4);self.assertLess(meta['triangles'],270000)
 def test_level_uses_the_supplied_roadster_derivative(self):
  level=json.loads((ROOT/'engine/level.json').read_text());self.assertEqual(level['assets']['vehicle'],'roadster/roadster.glb');self.assertIn("'vehicle':'roadster/roadster.glb'",(ROOT/'tools/game/prepare_library_assets.py').read_text())
 def test_actual_photographic_milky_way_hash_and_license(self):
  folder=ROOT/'engine/public/world/night';meta=json.loads((folder/'provenance.json').read_text());self.assertEqual(meta['author'],'Greg Zaal');self.assertEqual(meta['license'],'CC0-1.0');self.assertEqual(hashlib.sha256((folder/'milky-way.jpg').read_bytes()).hexdigest(),meta['output_sha256']);self.assertEqual(Image.open(folder/'milky-way.jpg').size,(4096,2048))
 def test_raw_html_exposes_absolute_crawler_tags(self):
  parser=Metadata();parser.feed((ROOT/'engine/index.html').read_text());m=parser.tags;self.assertIn('Alpine: After Dark',m['og:title']);self.assertEqual(m['og:image'],'https://mhammedamazil-hub.github.io/Testrepo/social/after-dark-beyond-v4.jpg');self.assertEqual(m['og:image:width'],'1200');self.assertEqual(m['og:image:height'],'630');self.assertEqual(m['twitter:card'],'summary_large_image');self.assertTrue(m['og:url'].endswith('/Testrepo/'))
 def test_preview_is_real_capture_size_and_web_sized(self):
  path=ROOT/'engine/public/social/after-dark-beyond-v4.jpg';self.assertEqual(Image.open(path).size,(1200,630));self.assertLess(path.stat().st_size,1000000);record=json.loads((ROOT/'docs/game/beyond-road-v4/social-preview.json').read_text());self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),record['image_sha256']);self.assertEqual(hashlib.sha256((ROOT/record['source']).read_bytes()).hexdigest(),record['source_sha256'])
 def test_dynamic_chassis_has_no_kinematic_drive_assignments(self):
  source=(ROOT/'engine/src/physics.js').read_text();self.assertIn('RigidBodyDesc.dynamic()',source);self.assertIn('createVehicleController',source);step=source[source.index(' step(dt,'):];self.assertNotIn('setNextKinematicRotation',step);self.assertNotIn('this.car.setTranslation',step);self.assertNotIn('this.car.setLinvel',step);self.assertIn('longitudinalLimit',step)
 def test_physics_claims_are_honestly_labelled(self):
  source=(ROOT/'engine/src/vehicle-spec.js').read_text();self.assertIn('engineering estimates',source);self.assertIn('mass:2200',source);self.assertIn('not published Tesla measurements',source)
