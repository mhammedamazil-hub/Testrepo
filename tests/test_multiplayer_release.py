"""Static-host deployment, derivative provenance and multiplayer scope guards."""
from pathlib import Path
import hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
class MultiplayerReleaseTest(unittest.TestCase):
 def test_separate_pages_entry_and_live_link(self):
  html=(ROOT/'engine/multiplayer.html').read_text();main=(ROOT/'engine/index.html').read_text();config=(ROOT/'engine/vite.config.js').read_text()
  self.assertIn('href="multiplayer.html"',main);self.assertIn('multiplayer.html',config)
  for key in ['guest-name','colours','quality','create-room','join-room','invite-link','ready','start-race','chat-message','nitro','recover','standings','results-list']:self.assertIn('id="'+key+'"',html)
 def test_low_asset_is_separate_attributed_and_unchanged_source(self):
  folder=ROOT/'engine/public/world/grand-prix';meta=json.loads((folder/'low-car-provenance.json').read_text());self.assertEqual(meta['license'],'CC-BY-4.0');self.assertEqual(meta['author'],'metarex.4d');self.assertEqual(meta['source_sha256'],hashlib.sha256((ROOT/'engine/public/world/roadster/roadster.glb').read_bytes()).hexdigest());self.assertEqual(meta['output_sha256'],hashlib.sha256((folder/'roadster-low.glb').read_bytes()).hexdigest());self.assertLess(meta['triangles'],65000);self.assertLess(meta['bytes'],4500000)
 def test_public_discovery_and_development_proxy_are_explicit(self):
  net=(ROOT/'engine/src/online/network.js').read_text();config=(ROOT/'engine/vite.config.js').read_text();self.assertIn("host:'0.peerjs.com'",net);self.assertIn("location.hostname",net);self.assertIn("VITE_PEER_HOST",net);self.assertIn("ws:true",config);self.assertNotIn("host:'localhost'",net)
 def test_no_airborne_multiplayer_or_host_override_from_guest(self):
  main=(ROOT/'engine/src/online/main.js').read_text();session=(ROOT/'engine/src/online/race-session.js').read_text();net=(ROOT/'engine/src/online/network.js').read_text()
  self.assertIn('this.physics.flight.engage=()=>false',main);self.assertIn('input.groundBoost=',main);self.assertIn('id!==this.hostId',session);self.assertNotIn("m.type==='start'",net);self.assertIn('this.session.recover(id)',net);self.assertIn('p.penalty+=3',session)
 def test_chat_is_text_only_and_bounded(self):
  main=(ROOT/'engine/src/online/main.js').read_text();protocol=(ROOT/'engine/src/online/protocol.js').read_text();self.assertIn('document.createTextNode(event.text.slice(0,160))',main);self.assertIn('children.length>35',main);self.assertIn('8192',protocol);self.assertIn('MAX_PLAYERS=6',protocol);self.assertNotIn('.innerHTML=',main)
 def test_low_balanced_high_presets_are_user_choices(self):
  source=(ROOT/'engine/src/online/quality.js').read_text();self.assertIn('800*450',source);self.assertIn('1280*720',source);self.assertIn('1920*1080',source);self.assertIn('shadows:false',source);self.assertIn("car:'roadster/roadster.glb'",source)
