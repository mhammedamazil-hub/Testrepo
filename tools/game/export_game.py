"""Import and export the actual Godot project; fail on script/parse errors."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--godot',default=str(ROOT/'.cache/godot/Godot_v4.4.1-stable_linux.x86_64'))
args=parser.parse_args()
engine=Path(args.godot).resolve()
if not engine.is_file():raise SystemExit('Godot executable not found; see game/README.md')
web=ROOT/'.exports/web';web.mkdir(parents=True,exist_ok=True)

def run(arguments):
    result=subprocess.run([str(engine),'--headless','--path',str(ROOT/'game'),*arguments],
                          text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(result.stdout)
    if result.returncode or any(marker in result.stdout for marker in ['SCRIPT ERROR','Parse Error','Failed to load script','Failed to export']):
        raise SystemExit('Godot import/export failed; inspect output above')
run(['--editor','--import'])
run(['--export-release','Web',str(web/'index.html')])
import shutil
for filename in ['GODOT_LICENSE.txt','GODOT_COPYRIGHT.txt']:
    shutil.copyfile(ROOT/'game/licenses'/filename,web/filename)
if (ROOT/'game/CREDITS.md').exists():
    shutil.copyfile(ROOT/'game/CREDITS.md',web/'CREDITS.md')
for suffix in ['html','js','pck','wasm']:
    assert (web/('index.'+suffix)).stat().st_size>100,'Missing export component: '+suffix
for suffix in ['js','pck','wasm']:
    path=web/('index.'+suffix)
    with path.open('rb') as src,gzip.open(str(path)+'.gz','wb',compresslevel=9) as dst:
        import shutil
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
print('Web export and downloadable archive ready:',ROOT/'.exports/Alpine_Mirror_Web.zip')
