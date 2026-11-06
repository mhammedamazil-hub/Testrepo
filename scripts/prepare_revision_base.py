"""Restore the exact delivered revision-1 geometry, without changing branches.
The immutable source blob comes from this repository's existing history. This
makes upgrades reproducible even after a newer .blend has been delivered.
"""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output';OUT.mkdir(exist_ok=True)
BASE_COMMIT='d95ac748d7cd08a5f359501323048047a0c2433e'
EXPECTED_SHA256='dc2f96a21f2ddf89c3e70a878b7bf2cdc5615617ae609b80e0fa968b433060ac'
path=OUT/'Alpine_Mirror.blend'
with path.open('wb') as f:subprocess.run(['git','show',f'{BASE_COMMIT}:output/Alpine_Mirror.blend'],cwd=ROOT,stdout=f,check=True)
actual=hashlib.sha256(path.read_bytes()).hexdigest()
if actual!=EXPECTED_SHA256:raise RuntimeError('Base scene hash mismatch')
(OUT/'base_provenance.json').write_text(json.dumps({'commit':BASE_COMMIT,'sha256':actual,'purpose':'Revision 1 geometry preserved for an in-place revision 2 upgrade'},indent=2))
print('Original delivered geometry restored and SHA-256 verified.')
