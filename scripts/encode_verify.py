"""Validate all 480 full-HD PNGs, encode H.264, then independently inspect output."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from PIL import Image
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output'
ap=argparse.ArgumentParser(); ap.add_argument('--crf',type=int,default=17); ap.add_argument('--segments',action='store_true'); a=ap.parse_args()
ff=imageio_ffmpeg.get_ffmpeg_exe(); video=OUT/'Alpine_Mirror_1080p_20s.mp4'
scene_hashes=set()
if a.segments:
    paths=[]
    for chunk in range(48):
        path=OUT/'segments'/f'segment_{chunk:03d}.mp4'
        manifest=json.loads(path.with_suffix('.json').read_text())
        assert manifest['chunk']==chunk and manifest['start']==chunk*10+1 and manifest['end']==chunk*10+10
        assert manifest['source_frames_verified']==10 and manifest['decoded_frames']==10
        assert manifest['size']==[1920,1080] and manifest['fps']==24
        assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['sha256']
        scene_hashes.add(manifest['scene_sha256']); paths.append(path)
    if len(scene_hashes)!=1: raise RuntimeError('Segments came from different scene versions')
    expected_scene=hashlib.sha256((OUT/'Alpine_Mirror.blend').read_bytes()).hexdigest()
    if expected_scene not in scene_hashes: raise RuntimeError('Segments do not match delivered Blender file')
    listing=OUT/'concat_segments.txt'
    listing.write_text(''.join("file '"+str(p)+"'\n" for p in paths))
    cmd=[ff,'-hide_banner','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-video_track_timescale','24000','-movflags','+faststart',str(video)]
else:
    frames=OUT/'frames'
    for f in range(1,481):
        path=frames/f'alpine_{f:04d}.png'
        if not path.is_file(): raise RuntimeError(f'Missing frame {f}')
        with Image.open(path) as im:
            if im.size!=(1920,1080): raise RuntimeError(f'Wrong resolution at frame {f}: {im.size}')
            im.verify()
    cmd=[ff,'-hide_banner','-y','-framerate','24','-start_number','1','-i',str(frames/'alpine_%04d.png'),'-frames:v','480','-c:v','libx264','-preset','slow','-crf',str(a.crf),'-pix_fmt','yuv420p','-movflags','+faststart','-an',str(video)]
subprocess.run(cmd,check=True)
# Decode the complete movie, not just its container metadata.
reader=imageio_ffmpeg.read_frames(str(video),pix_fmt='rgb24'); meta=next(reader); count=0
for data in reader:
    count+=1
    if len(data)!=1920*1080*3: raise RuntimeError('Decoded frame size mismatch')
if count!=480 or tuple(meta['size'])!=(1920,1080) or abs(meta['fps']-24)>.001 or abs(meta['duration']-20)>.05: raise RuntimeError(f'Movie validation failed: {meta}, count {count}')
report={'status':'TECHNICAL_PASS','file':video.name,'native_frames':480,'decoded_frames':count,'width':1920,'height':1080,'fps':24,'duration_seconds':meta['duration'],'codec':meta.get('codec'),'bytes':video.stat().st_size,'audio':'none requested; silent','interpolated_or_duplicated_frames':False,'assembly':'verified segments, stream-copy without second lossy encode' if a.segments else 'PNG sequence encode','scene_sha256':next(iter(scene_hashes)) if scene_hashes else None,'visual_approval':'Separate artistic review required; technical pass is not a photorealism certification.'}
(OUT/'delivery_validation.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
