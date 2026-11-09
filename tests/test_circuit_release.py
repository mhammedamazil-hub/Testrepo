"""Custom-only circuit packaging and provenance. Actual ray/drive tests live in engine/tests."""
import hashlib,json,math,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CircuitReleaseTest(unittest.TestCase):
 def test_closed_resampled_route_has_no_large_seam_or_abrupt_steps(self):
  track=json.loads((ROOT/'engine/public/world/track/route.json').read_text());points=track['points'];self.assertEqual(len(points),640);self.assertEqual(track['width'],10);self.assertEqual(track['gates'],[160,320,480,0])
  lengths=[math.dist(p,points[(i+1)%len(points)]) for i,p in enumerate(points)];self.assertGreater(min(lengths),1);self.assertLess(max(lengths),1.7);self.assertLess(max(abs(points[(i+1)%640][1]-p[1]) for i,p in enumerate(points)),.25)
 def test_custom_terrain_derivative_is_hashed_original_is_unchanged(self):
  folder=ROOT/'engine/public/world/track';meta=json.loads((folder/'provenance.json').read_text());source=(ROOT/meta['source']).read_bytes();target=(folder/'terrain.glb').read_bytes();self.assertEqual(hashlib.sha256(source).hexdigest(),meta['source_sha256']);self.assertEqual(meta['source_sha256'],'df54e53ec2fb2c840014d50366df7eb424286d25c6bec03ac26dbb25c896ccca');self.assertEqual(hashlib.sha256(target).hexdigest(),meta['output_sha256']);self.assertGreater(meta['graded_vertices'],0);self.assertEqual(target[:4],b'glTF');self.assertEqual(struct.unpack_from('<I',target,8)[0],len(target))
 def test_runtime_and_compiler_use_corrected_terrain_and_gates(self):
  level=json.loads((ROOT/'engine/level.json').read_text());self.assertEqual(level['assets']['terrain'],'track/terrain.glb');self.assertEqual(level['checkpoints'],[160,320,480,0]);compiler=(ROOT/'tools/game/prepare_library_assets.py').read_text();self.assertIn("'terrain':'track/terrain.glb'",compiler);self.assertIn("'checkpoints':[160,320,480,0]",compiler)
 def test_real_solver_completed_an_entire_lap_without_losing_contact(self):
  result=json.loads((ROOT/'docs/game/circuit-v3/solver-lap.json').read_text());self.assertTrue(result['passed']);self.assertEqual(result['laps'],1);self.assertEqual(result['min_wheel_contacts'],4);self.assertLess(result['max_centerline_distance_m'],1)
 def test_both_modes_real_pedals_and_accessible_settings_exist(self):
  html=(ROOT/'engine/index.html').read_text()
  for name in ['steering-wheel','steering-arrows','gas-pedal','brake-pedal','reverse-gear','setting-wheel','setting-arrows','setting-assist','setting-quality','map-car','route-hint']:self.assertIn('id="'+name+'"',html)
  self.assertIn('aria-label="Accelerator"',html);self.assertIn('aria-label="Brake"',html)
