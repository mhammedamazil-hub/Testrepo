"""Flight scope, grass provenance and unchanged-graphics optimization guards."""
import hashlib,json,math,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class BeyondRoadTest(unittest.TestCase):
 def test_meadow_hash_count_and_graded_terrain_provenance(self):
  folder=ROOT/'engine/public/world/meadow';meta=json.loads((folder/'provenance.json').read_text());data=(folder/'grass.json').read_bytes();points=json.loads(data);self.assertEqual(len(points),meta['plants']);self.assertGreater(len(points),10000);self.assertEqual(hashlib.sha256(data).hexdigest(),meta['output_sha256']);self.assertEqual(hashlib.sha256((ROOT/'engine/public/world/track/terrain.glb').read_bytes()).hexdigest(),meta['terrain_sha256']);self.assertTrue(all(p[1]>.2 for p in points))
 def test_grass_cannot_hide_or_block_the_driving_corridor(self):
  grass=json.loads((ROOT/'engine/public/world/meadow/grass.json').read_text());route=json.loads((ROOT/'engine/public/world/track/route.json').read_text())['points']
  for p in grass[::97]:
   best=1e9
   for i,a in enumerate(route):
    b=route[(i+1)%len(route)];dx=b[0]-a[0];dz=b[2]-a[2];t=max(0,min(1,((p[0]-a[0])*dx+(p[2]-a[2])*dz)/(dx*dx+dz*dz)));best=min(best,math.hypot(p[0]-a[0]-t*dx,p[2]-a[2]-t*dz))
   self.assertGreater(best,6.7)
 def test_existing_graphics_budgets_and_photographic_assets_are_retained(self):
  main=(ROOT/'engine/src/main.js').read_text();world=(ROOT/'engine/src/world.js').read_text();self.assertIn("this.quality='full'",main);self.assertIn('full:1920*1080,balanced:1280*720,performance:960*540',main);self.assertIn('this.sun.shadow.mapSize.set(1024,1024)',world);self.assertIn('light.shadow.mapSize.set(512,512)',world);self.assertIn('textureWidth:512,textureHeight:512',world);self.assertIn("this.instances(grass.scene,this.scatter.grass,35,70,'grass')",world)
 def test_inactive_effect_is_disabled_not_just_invisibly_blended(self):
  source=(ROOT/'engine/src/main.js').read_text();self.assertIn('this.effects.enabled=enabled;this.clearEffects.enabled=!enabled',source);self.assertIn('preserveDrawingBuffer:false',source);self.assertIn('await this.renderer.compileAsync',source);self.assertIn('now-this.lastTelemetry>250',source);self.assertIn('now-this.lastHUD>50',source)
 def test_flight_is_labelled_fictional_and_never_assigns_body_motion(self):
  html=(ROOT/'engine/index.html').read_text();self.assertIn('FICTIONAL THRUSTER MODE',html);self.assertIn('FICTIONAL FLIGHT',html);source=(ROOT/'engine/src/flight.js').read_text();self.assertIn('addForce',source);self.assertIn('addTorque',source)
  for direct in ['setTranslation','setLinvel','setRotation','setAngvel']:self.assertNotIn(direct,source)
 def test_lobby_actions_and_independent_flight_touch_inputs_are_real(self):
  source=(ROOT/'engine/index.html').read_text()
  for name in ['lobby-garage','lobby-settings','lobby-training','launch-drive','launch-flight','flight-toggle','land-control','boost-control','performance-summary']:self.assertIn('id="'+name+'"',source)
  for action in ['lift','descend','boost']:self.assertIn('data-hold="'+action+'"',source)
