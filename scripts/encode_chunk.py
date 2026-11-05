"""Encode ten validated native frames once; assembly later stream-copies them.
This keeps Actions artifact storage small without duplicating/interpolating frames
or applying a second lossy encode. Final delivery is the same CRF-17 H.264 stream.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
from PIL import Image
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output'
ap=argparse.ArgumentParser(); ap.add_argument('--chunk',type=int,required=True); ap.add_argument('--crf',type=int,default=17); a=ap.parse_args()
start=a.chunk*10+1; end=start+9
for f in range(start,end+1):
    with Image.open(OUT/'frames'/f'alpine_{f:04d}.png') as im:
        if im.size!=(1920,1080): raise RuntimeError(f'Invalid frame {f}: {im.size}')
        im.verify()
folder=OUT/'segments'; folder.mkdir(exist_ok=True)
video=folder/f'segment_{a.chunk:03d}.mp4'; ff=imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ff,'-hide_banner','-y','-framerate','24','-start_number',str(start),'-i',str(OUT/'frames'/'alpine_%04d.png'),'-frames:v','10','-c:v','libx264','-preset','slow','-crf',str(a.crf),'-threads','4','-pix_fmt','yuv420p','-video_track_timescale','24000','-movflags','+faststart','-an',str(video)],check=True)
r=imageio_ffmpeg.read_frames(str(video),pix_fmt='rgb24'); metadata=next(r); count=sum(1 for _ in r)
if count!=10 or tuple(metadata['size'])!=(1920,1080): raise RuntimeError('Chunk decode failed')
sidecar=json.loads((OUT/'frames'/f'alpine_{start:04d}.render.json').read_text())
manifest={'chunk':a.chunk,'start':start,'end':end,'source_frames_verified':10,'decoded_frames':count,'size':[1920,1080],'fps':24,'crf':a.crf,'scene_sha256':sidecar['scene_sha256'],'samples_max':sidecar['samples'],'sha256':hashlib.sha256(video.read_bytes()).hexdigest()}
video.with_suffix('.json').write_text(json.dumps(manifest,indent=2)); print(json.dumps(manifest))
