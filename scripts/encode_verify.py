"""Validate all 480 full-HD PNGs, encode H.264, then independently inspect output."""
import argparse, json, subprocess, sys
from pathlib import Path
from PIL import Image
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output'
ap=argparse.ArgumentParser(); ap.add_argument('--crf',type=int,default=17); a=ap.parse_args()
frames=OUT/'frames'
for f in range(1,481):
    p=frames/f'alpine_{f:04d}.png'
    if not p.is_file(): raise RuntimeError(f'Missing frame {f}')
    with Image.open(p) as im:
        if im.size!=(1920,1080): raise RuntimeError(f'Wrong resolution at frame {f}: {im.size}')
        im.verify()
ff=imageio_ffmpeg.get_ffmpeg_exe(); video=OUT/'Alpine_Mirror_1080p_20s.mp4'
cmd=[ff,'-hide_banner','-y','-framerate','24','-start_number','1','-i',str(frames/'alpine_%04d.png'),'-frames:v','480','-c:v','libx264','-preset','slow','-crf',str(a.crf),'-pix_fmt','yuv420p','-movflags','+faststart','-an',str(video)]
subprocess.run(cmd,check=True)
# Decode the complete movie, not just its container metadata.
reader=imageio_ffmpeg.read_frames(str(video),pix_fmt='rgb24'); meta=next(reader); count=0
for data in reader:
    count+=1
    if len(data)!=1920*1080*3: raise RuntimeError('Decoded frame size mismatch')
if count!=480 or tuple(meta['size'])!=(1920,1080) or abs(meta['fps']-24)>.001 or abs(meta['duration']-20)>.05: raise RuntimeError(f'Movie validation failed: {meta}, count {count}')
report={'status':'TECHNICAL_PASS','file':video.name,'native_frames':480,'decoded_frames':count,'width':1920,'height':1080,'fps':24,'duration_seconds':meta['duration'],'codec':meta.get('codec'),'bytes':video.stat().st_size,'audio':'none requested; silent','interpolated_or_duplicated_frames':False,'visual_approval':'Separate artistic review required; technical pass is not a photorealism certification.'}
(OUT/'delivery_validation.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
