"""Independent full decode, unique-frame check and Blender-file provenance gate."""
import hashlib,json
from pathlib import Path
import imageio_ffmpeg
import numpy as np
from PIL import Image
from project_config import FPS,FRAME_COUNT,WIDTH,HEIGHT,SECONDS,REVISION
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output'
r=imageio_ffmpeg.read_frames(str(OUT/'Alpine_Mirror_1080p_20s.mp4'),pix_fmt='rgb24');meta=next(r)
count=0;hashes=set();changes=[];previous=None;review=OUT/'review';review.mkdir(exist_ok=True)
for count,data in enumerate(r,1):
    if len(data)!=WIDTH*HEIGHT*3:raise RuntimeError('Decoded buffer has wrong dimensions')
    hashes.add(hashlib.sha256(data).digest());a=np.frombuffer(data,dtype=np.uint8).reshape(HEIGHT,WIDTH,3);sample=a[::12,::12].astype(np.float32)
    if previous is not None:changes.append(float(np.abs(sample-previous).mean()))
    previous=sample
    if count in [1,FRAME_COUNT//2,FRAME_COUNT]:Image.fromarray(a).save(review/f'final_check_{count:04d}.jpg',quality=93)
if count!=FRAME_COUNT or len(hashes)!=FRAME_COUNT:raise RuntimeError(f'Expected {FRAME_COUNT} unique frames, got {count} / {len(hashes)}')
if tuple(meta['size'])!=(WIDTH,HEIGHT) or abs(meta['fps']-FPS)>.001 or abs(meta['duration']-SECONDS)>.03:raise RuntimeError(f'Bad movie metadata: {meta}')
expected=json.loads((OUT/'delivery_validation.json').read_text());digest=hashlib.sha256((OUT/'Alpine_Mirror.blend').read_bytes()).hexdigest()
if digest!=expected['scene_sha256']:raise RuntimeError('Delivered scene hash does not match rendered scene')
report={'status':'PASS','revision':REVISION,'decoded_frames':count,'unique_decoded_frame_hashes':len(hashes),'dimensions':meta['size'],'fps':meta['fps'],'duration_seconds':meta['duration'],'scene_hash_matches':True,'mean_sampled_frame_difference_8bit':float(np.mean(changes)),'max_sampled_frame_difference_8bit':float(np.max(changes)),'notes':'Native full-HD 60 fps, no repeated full-frame images; artistic realism requires separate review.'}
(OUT/'independent_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
