"""Isolated codec smoke test. Synthetic test colors are NEVER delivery footage."""
import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
class EncodingSmokeTest(unittest.TestCase):
    def test_full_hd_chunk_concat_and_decode(self):
        with tempfile.TemporaryDirectory(prefix='alpine-codec-test-') as tmp:
            root=Path(tmp); scripts=root/'scripts'; out=root/'output'; frames=out/'frames'
            scripts.mkdir(); frames.mkdir(parents=True)
            for name in ['encode_chunk.py','encode_verify.py','project_config.py']:
                shutil.copy(ROOT/'scripts'/name,scripts/name)
            import hashlib
            blend=out/'Alpine_Mirror.blend'; blend.write_bytes(b'ISOLATED SYNTHETIC CODEC TEST, NOT A BLENDER DELIVERABLE')
            digest=hashlib.sha256(blend.read_bytes()).hexdigest()
            for i in range(1,26):
                Image.new('RGB',(1920,1080),(i*12,34,56)).save(frames/f'alpine_{i:04d}.png')
                (frames/f'alpine_{i:04d}.render.json').write_text(json.dumps({'scene_sha256':digest,'samples':64,'percent':100,'frame':i}))
            p=subprocess.run([sys.executable,str(scripts/'encode_chunk.py'),'--chunk','0'],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr[-3000:])
            segment=out/'segments'/'segment_000.mp4'; original=json.loads(segment.with_suffix('.json').read_text())
            # Repeated synthetic test chunks exercise concat timestamp math only.
            for c in range(1,48):
                target=segment.with_name(f'segment_{c:03d}.mp4'); shutil.copy(segment,target)
                target.with_suffix('.json').write_text(json.dumps({**original,'chunk':c,'start':c*25+1,'end':c*25+25}))
            p=subprocess.run([sys.executable,str(scripts/'encode_verify.py'),'--segments'],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr[-3000:])
            report=json.loads((out/'delivery_validation.json').read_text())
            self.assertEqual(report['decoded_frames'],1200)
            self.assertEqual(report['duration_seconds'],20.)
            self.assertEqual(report['scene_sha256'],digest)
    def test_missing_frames_rejected(self):
        with tempfile.TemporaryDirectory(prefix='alpine-missing-test-') as tmp:
            root=Path(tmp); (root/'scripts').mkdir(); (root/'output').mkdir()
            shutil.copy(ROOT/'scripts'/'encode_verify.py',root/'scripts'/'encode_verify.py')
            shutil.copy(ROOT/'scripts'/'project_config.py',root/'scripts'/'project_config.py')
            p=subprocess.run([sys.executable,str(root/'scripts'/'encode_verify.py')],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertIn('Missing frame 1',p.stderr)

if __name__=='__main__': unittest.main()
