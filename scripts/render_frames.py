"""Resumable native Cycles frame rendering, CPU only; never duplicates/interpolates frames."""
import argparse, hashlib, json, os, time
from pathlib import Path
import bpy
from project_config import FPS, FRAME_COUNT
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output'
ap=argparse.ArgumentParser(); ap.add_argument('--start',type=int,default=1); ap.add_argument('--end',type=int,default=FRAME_COUNT)
ap.add_argument('--samples',type=int,default=128); ap.add_argument('--threads',type=int,default=min(4,os.cpu_count() or 2))
ap.add_argument('--noise',type=float,default=.03); ap.add_argument('--min-samples',type=int,default=24)
ap.add_argument('--percent',type=int,default=100); ap.add_argument('--only',default=''); ap.add_argument('--still',action='store_true')
a=ap.parse_args()
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Alpine_Mirror.blend'))
s=bpy.context.scene
if s.render.fps!=FPS or s.frame_end!=FRAME_COUNT or s.get('revision')!=2: raise RuntimeError('Wrong scene revision/fps/frame count')
s.render.engine='CYCLES'; s.cycles.device='CPU'; s.cycles.samples=a.samples
s.cycles.use_adaptive_sampling=True; s.cycles.adaptive_threshold=a.noise; s.cycles.adaptive_min_samples=min(a.samples,a.min_samples)
s.cycles.use_denoising=True; s.cycles.denoiser='OPENIMAGEDENOISE'
s.render.resolution_percentage=a.percent; s.render.threads_mode='FIXED'; s.render.threads=a.threads
s.render.use_persistent_data=True
frames=[int(f) for f in a.only.split(',')] if a.only else list(range(a.start,a.end+1))
folder=OUT/('review' if a.only else 'frames'); folder.mkdir(exist_ok=True,parents=True)
statusfile=OUT/f'status_{a.start:04d}_{a.end:04d}.json'
width=int(1920*a.percent/100); height=int(1080*a.percent/100)
fingerprint={'scene_sha256':hashlib.sha256((OUT/'Alpine_Mirror.blend').read_bytes()).hexdigest(),'samples':a.samples,'percent':a.percent,'renderer':bpy.app.version_string,'noise':a.noise,'min_samples':min(a.samples,a.min_samples)}
started=time.time(); times=[]; completed=[]
for f in frames:
    path=OUT/'Alpine_Mirror_1080p.png' if a.still else folder/f'alpine_{f:04d}.png'
    valid=False
    sidecar=path.with_suffix('.render.json')
    if path.exists() and sidecar.exists():
        try:
            with Image.open(path) as im: valid=im.size==(width,height) and json.loads(sidecar.read_text())=={**fingerprint,'frame':f}; im.verify()
        except Exception: valid=False
    if not valid:
        print(f'RENDER START frame={f} samples={a.samples} size={width}x{height}',flush=True)
        s.frame_set(f); temp=path.with_name('rendering_'+path.name); s.render.filepath=str(temp)
        now=time.time(); bpy.ops.render.render(write_still=True); temp.replace(path); sidecar.write_text(json.dumps({**fingerprint,'frame':f},indent=2)); times.append(time.time()-now)
    completed.append(f)
    status={'state':'rendering','completed':len(completed),'total':len(frames),'last_frame':f,'elapsed_seconds':time.time()-started,'mean_frame_seconds':sum(times)/len(times) if times else 0,'samples_max':a.samples,'native_resolution':[width,height],'cpu_threads':a.threads}
    statusfile.write_text(json.dumps(status,indent=2)); print('PROGRESS '+json.dumps(status),flush=True)
status['state']='complete'; statusfile.write_text(json.dumps(status,indent=2))
print('CHUNK COMPLETE',flush=True)
