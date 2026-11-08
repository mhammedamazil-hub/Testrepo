"""Import/export the real Godot game into a fresh staging directory.

Reject script errors and incomplete exports. Swap the live preview only after
all files are ready; a failed build never destroys the previous playable build.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--godot',default=str(ROOT/'.cache/godot/Godot_v4.4.1-stable_linux.x86_64'))
args=parser.parse_args()
engine=Path(args.godot).resolve()
if not engine.is_file():raise SystemExit('Godot executable not found; see game/README.md')
web=ROOT/'.exports/web-staging'
if web.exists():shutil.rmtree(web)
web.mkdir(parents=True)

def run(arguments):
    result=subprocess.run([str(engine),'--headless','--path',str(ROOT/'game'),*arguments],
                          text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(result.stdout)
    if result.returncode or any(marker in result.stdout for marker in ['SCRIPT ERROR','Parse Error','Failed to load script','Failed to export']):
        raise SystemExit('Godot import/export failed; previous playable export is unchanged')

run(['--editor','--import'])
run(['--export-release','Web',str(web/'index.html')])
for filename in ['GODOT_LICENSE.txt','GODOT_COPYRIGHT.txt']:
    shutil.copyfile(ROOT/'game/licenses'/filename,web/filename)
shutil.copyfile(ROOT/'game/CREDITS.md',web/'CREDITS.md')
(web/'PLAY.txt').write_text('''ALPINE MIRROR - LAKESIDE ESCAPE

This is an actual Godot Web game. Serve this extracted folder over HTTP(S).
Do not double-click index.html using file://: browser security blocks its files.

One free local option, if Python 3 is installed:
  Open a terminal in this extracted folder.
  Run: python3 -m http.server 8080
  Open http://localhost:8080 in a WebGL 2-capable desktop browser.
  Stop the server with Ctrl+C when finished.

Controls: WASD/arrows move or drive; E enters/exits the car; Space jumps/brakes;
Shift runs; mouse orbits after clicking; Escape pauses/releases cursor;
R recovers; F fullscreen; F2 enhanced shadows; F8 resets frame-time samples;
Q rear view; M mute. Touch controls are not implemented.

Native 1920x1080 is verified. 60 FPS is a target, NOT a certified result.
The sandbox CPU software-rendering test did not achieve 60 FPS.
Actual speed depends on the graphics device and browser running this build.

This is a playable prototype, not a complete GTA-scale or photoreal game.
Credits and engine licenses are included in this folder.
''')
for suffix in ['html','js','pck','wasm']:
    if (web/('index.'+suffix)).stat().st_size<=100:raise SystemExit('Incomplete export: '+suffix)
for filename,magic in [('index.wasm',b'\x00asm'),('index.pck',b'GDPC')]:
    with (web/filename).open('rb') as binary:
        if binary.read(4)!=magic:raise SystemExit('Invalid runtime header: '+filename)
if '$GODOT_' in (web/'index.html').read_text():raise SystemExit('Unexpanded HTML template tokens')
for suffix in ['js','pck','wasm']:
    path=web/('index.'+suffix)
    with path.open('rb') as src,gzip.open(str(path)+'.gz','wb',compresslevel=9) as dst:
        shutil.copyfileobj(src,dst)
report={'engine':subprocess.check_output([str(engine),'--headless','--version'],text=True).strip(),
        'export':'Actual Godot single-threaded Web release, GL Compatibility',
        'native_resolution_target':[1920,1080],'fps_target':60,
        'performance_verified':False,
        'files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                 for p in web.iterdir() if p.is_file() and p.suffix!='.gz'}}
(ROOT/'.exports/web-export.json').write_text(json.dumps(report,indent=2)+'\n')
with zipfile.ZipFile(ROOT/'.exports/Alpine_Mirror_Web.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for p in web.iterdir():
        if p.is_file() and p.suffix!='.gz':archive.write(p,p.name)
with zipfile.ZipFile(ROOT/'.exports/Alpine_Mirror_Web.zip') as archive:
    if archive.testzip() is not None:raise SystemExit('Export archive CRC validation failed')
final=ROOT/'.exports/web'
previous=ROOT/'.exports/web-previous'
if previous.exists():shutil.rmtree(previous)
if final.exists():final.rename(previous)
web.rename(final)
if previous.exists():shutil.rmtree(previous)
print('Validated Web export and downloadable archive ready:',ROOT/'.exports/Alpine_Mirror_Web.zip')
