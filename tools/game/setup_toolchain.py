"""Restore the verified Godot/Linux + Web toolchain from temporary Git transport.

Linux x86-64 sandbox helper. Other platforms should install official Godot 4.4.1
and its export templates normally. No branch switch, system install or payment.
"""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[2]
if platform.system()!='Linux' or platform.machine()!='x86_64':
    raise SystemExit('This cache is Linux x86-64 only. Install official Godot 4.4.1 for your platform.')
metadata=json.loads((ROOT/'docs/GODOT_TOOLCHAIN_PROVENANCE.json').read_text())
commit=metadata['transport_commit']
cache=ROOT/'.cache/game-transport';cache.mkdir(parents=True,exist_ok=True)
try:
    subprocess.run(['git','cat-file','-e',commit+'^{commit}'],cwd=ROOT,check=True,stderr=subprocess.DEVNULL)
except subprocess.CalledProcessError:
    subprocess.run(['git','fetch','--depth','1','origin',commit],cwd=ROOT,check=True)
for name,digest in metadata['files'].items():
    path=cache/name
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        with path.open('wb') as stream:
            subprocess.run(['git','show',commit+':.cache/game-transport/'+name],cwd=ROOT,stdout=stream,check=True)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        raise SystemExit('Cached toolchain checksum mismatch: '+name)
engine_dir=ROOT/'.cache/godot';engine_dir.mkdir(exist_ok=True)
with zipfile.ZipFile(cache/'Godot_v4.4.1-stable_linux.x86_64.zip') as archive:
    # Official archive contains exactly the single engine executable.
    names=archive.namelist()
    if names!=['Godot_v4.4.1-stable_linux.x86_64']:raise SystemExit('Unexpected engine archive members')
    archive.extractall(engine_dir)
engine=engine_dir/names[0];engine.chmod(0o755)
templates=Path.home()/'.local/share/godot/export_templates/4.4.1.stable';templates.mkdir(parents=True,exist_ok=True)
import shutil
for name in ['web_nothreads_release.zip','web_nothreads_debug.zip']:
    shutil.copyfile(cache/name,templates/name)
print(subprocess.check_output([str(engine),'--headless','--version'],text=True).strip())
print('Official engine + single-thread Web templates installed; all transported SHA256 hashes verified.')
