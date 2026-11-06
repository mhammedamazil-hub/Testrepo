"""Encode a native 60-fps segment from verified PNGs with two-pass H.264.
The first pass is analysis of original frames, not a lossy intermediate.
Assembly stream-copies the final segments, with no second lossy encode.
"""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from PIL import Image
import imageio_ffmpeg
from project_config import FPS,FRAME_COUNT,CHUNK_SIZE,WIDTH,HEIGHT
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output'
ap=argparse.ArgumentParser();ap.add_argument('--chunk',type=int,required=True);ap.add_argument('--bitrate',default='16M');a=ap.parse_args()
start=a.chunk*CHUNK_SIZE+1;end=min(FRAME_COUNT,start+CHUNK_SIZE-1);size=end-start+1
if not 0<=a.chunk or start>FRAME_COUNT:raise ValueError('Invalid chunk')
fingerprint=None
for f in range(start,end+1):
    path=OUT/'frames'/f'alpine_{f:04d}.png'
    with Image.open(path) as im:
        if im.size!=(WIDTH,HEIGHT):raise RuntimeError(f'Invalid frame {f}: {im.size}')
        im.verify()
    sidecar=json.loads(path.with_suffix('.render.json').read_text())
    if sidecar.get('frame')!=f or sidecar.get('percent')!=100:raise RuntimeError('Wrong frame/render scale sidecar')
    current={k:v for k,v in sidecar.items() if k!='frame'}
    if fingerprint is None:fingerprint=current
    elif fingerprint!=current:raise RuntimeError('Mixed scene versions/quality inside one chunk')
folder=OUT/'segments';folder.mkdir(exist_ok=True);video=folder/f'segment_{a.chunk:03d}.mp4';ff=imageio_ffmpeg.get_ffmpeg_exe()
base=[ff,'-hide_banner','-y','-framerate',str(FPS),'-start_number',str(start),'-i',str(OUT/'frames'/'alpine_%04d.png'),'-frames:v',str(size),'-c:v','libx264','-preset','slow','-b:v',a.bitrate,'-maxrate','18M','-bufsize','32M','-threads','4','-pix_fmt','yuv420p','-profile:v','high','-level:v','4.2','-refs','4','-an']
passlog=folder/f'pass_{a.chunk:03d}'
subprocess.run(base+['-pass','1','-passlogfile',str(passlog),'-f','null',os.devnull],check=True)
subprocess.run(base+['-pass','2','-passlogfile',str(passlog),'-video_track_timescale',str(FPS*1000),'-movflags','+faststart',str(video)],check=True)
for file in folder.glob(f'pass_{a.chunk:03d}*'):file.unlink()
r=imageio_ffmpeg.read_frames(str(video),pix_fmt='rgb24');metadata=next(r);count=sum(1 for _ in r)
if count!=size or tuple(metadata['size'])!=(WIDTH,HEIGHT) or abs(metadata['fps']-FPS)>.001:raise RuntimeError('Chunk decode failed')
manifest={'chunk':a.chunk,'start':start,'end':end,'source_frames_verified':size,'decoded_frames':count,'size':[WIDTH,HEIGHT],'fps':FPS,'rate_control':'two-pass H.264 from original PNGs','target_bitrate':a.bitrate,'scene_sha256':fingerprint['scene_sha256'],'samples_max':fingerprint['samples'],'sha256':hashlib.sha256(video.read_bytes()).hexdigest()}
video.with_suffix('.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest))
