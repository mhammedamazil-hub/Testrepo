"""Acquire bounded CC0 astrophotography, with verified original hash/provenance."""
import hashlib,io,json,urllib.request
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'AlpineAfterDark/0.2 (small CC0 asset research)'})
 with urllib.request.urlopen(req,timeout=120) as r:return r.read(12_000_001)
info=json.loads(get('https://api.polyhaven.com/info/satara_night'))
files=json.loads(get('https://api.polyhaven.com/files/satara_night'));entry=files['tonemapped'];data=get(entry['url'])
assert len(data)==entry['size'] and hashlib.md5(data).hexdigest()==entry['md5']
im=Image.open(io.BytesIO(data)).convert('RGB');im=im.resize((4096,2048),Image.Resampling.LANCZOS)
# Keep the actual photographic stars and Milky Way; do not insert village/ground
# backplates into Alpine. Feather only the lower hemisphere into a dark nadir.
pixels=im.load()
for y in range(1004,2048):
 fade=max(0.,min(1.,(1060-y)/56))
 for x in range(4096):
  c=pixels[x,y];pixels[x,y]=tuple(round(c[i]*fade+(3,6,13)[i]*(1-fade)) for i in range(3))
out=ROOT/'engine/public/world/night';out.mkdir(parents=True,exist_ok=True)
p=out/'milky-way.jpg';im.save(p,quality=92,optimize=True)
record={'asset':'Satara Night','author':'Greg Zaal','source':'https://polyhaven.com/a/satara_night','license':'CC0-1.0','credit':'Powered by Poly Haven','source_url':entry['url'],'source_md5':entry['md5'],'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'output_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'output_bytes':p.stat().st_size,'dimensions':[4096,2048],'modifications':'Resized photographic tonemapped sky; lower hemisphere feathered to dark navy to remove village/ground backplates. Stars and Milky Way remain real photography. Artistic long-exposure sky, not an astronomy simulation.','official_info':info}
(out/'provenance.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
