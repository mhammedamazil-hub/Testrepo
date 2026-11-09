"""Finite-thruster source contracts and track/preset preservation."""
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ShortHopTest(unittest.TestCase):
 def test_finite_power_shared_fuel_and_ground_only_refill(self):
  s=(ROOT/'engine/src/flight.js').read_text()
  for value in ['poweredSeconds:6','manualSeconds:2.8','refillSeconds:20','minLaunchCharge:85','!this.grounded','if(grounded)this.energy','this.elapsed>=HOP.poweredSeconds','cost>this.energy','body.addForce','body.addTorque']:self.assertIn(value,s)
  self.assertNotIn('targetHeight-p.y',s)
  for method in ['setTranslation','setLinvel','setRotation','setAngvel']:self.assertNotIn(method,s)
 def test_duration_is_disclosed_as_game_setting_not_tesla_spec(self):
  html=(ROOT/'engine/index.html').read_text();research=(ROOT/'docs/research/short-hop-and-time-attack.md').read_text()
  for value in ['GAME SETTINGS','not official flight specifications','nothing refills in air','hard powered limit 6s']:self.assertIn(value,html)
  self.assertIn('https://www.tesla.com/roadster',research);self.assertIn('No official flight-duration figure',research)
 def test_track_art_retains_asphalt_and_collision_route(self):
  s=(ROOT/'engine/src/circuit-art.js').read_text();world=(ROOT/'engine/src/world.js').read_text()
  for value in ['kerbMaterial','circuitGrain','START / FINISH','reflectors','boardMat','mergeGeometries']:self.assertIn(value,s)
  self.assertIn('#include <map_fragment>',s);self.assertNotIn('createCollider',s)
  self.assertIn('makeStrip(this.track.width,0,0,roadMaterial,true)',world)
  route=json.loads((ROOT/'engine/public/world/track/route.json').read_text());self.assertEqual(route['width'],10);self.assertEqual(len(route['points']),640)
 def test_race_attempt_cannot_award_pb_for_hop_recovery_or_changed_assist(self):
  s=(ROOT/'engine/src/main.js').read_text()
  for value in ["this.trial.invalidate('THRUSTER HOP USED')","this.trial.invalidate('RECOVERY USED')","this.trial.invalidate('ASSIST CHANGED')",'this.trial.checkpoint','this.trial.finish','this.trial.countdown>0']:self.assertIn(value,s)
 def test_only_static_subtrees_are_frozen(self):
  s=(ROOT/'engine/src/world.js').read_text();freeze=(ROOT/'engine/src/static-scene.js').read_text()
  self.assertIn('matrixAutoUpdate=false',freeze);self.assertIn('matrixWorldAutoUpdate=false',freeze)
  self.assertIn('this.staticRoots.push(terrain.scene,road.scene)',s)
  for dynamic in ['this.car','this.person','this.sun','this.water']:self.assertNotIn('this.staticRoots.push('+dynamic+')',s)
  self.assertIn("mesh.name='DistantForest'",s);self.assertIn('mesh.frustumCulled=false',s)
