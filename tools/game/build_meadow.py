"""Deterministic ground-conforming grass positions, not a replacement terrain texture."""
from pathlib import Path
import json,struct,hashlib,math,random
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
def build():
 source=ROOT/'engine/public/world/track/terrain.glb';raw=source.read_bytes();size=struct.unpack_from('<I',raw,12)[0];j=json.loads(raw[20:20+size]);blob=raw[28+size:]
 def array(index):
  a=j['accessors'][index];v=j['bufferViews'][a['bufferView']];return np.frombuffer(blob,dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']],count=a['count']*(3 if a['type']=='VEC3' else 1),offset=v.get('byteOffset',0)+a.get('byteOffset',0))
 mesh=next(m for m in j['meshes'] if 'Ground' in m['name'])['primitives'][0];verts=array(mesh['attributes']['POSITION']).reshape(-1,3);tri=verts[array(mesh['indices']).reshape(-1,3)]
 cells={}
 for i,t in enumerate(tri):
  lo=np.floor(t[:,[0,2]].min(0)/16).astype(int);hi=np.floor(t[:,[0,2]].max(0)/16).astype(int)
  for x in range(lo[0],hi[0]+1):
   for z in range(lo[1],hi[1]+1):cells.setdefault((x,z),[]).append(i)
 def height(x,z):
  for index in cells.get((math.floor(x/16),math.floor(z/16)),[]):
   a,b,c=tri[index];den=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
   if abs(den)<1e-9:continue
   u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/den;v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/den
   if u>=-1e-5 and v>=-1e-5 and u+v<=1.00001:return float(u*a[1]+v*b[1]+(1-u-v)*c[1])
 route=json.loads((source.parent/'route.json').read_text())['points'];arr=np.array(route);starts=arr[:,[0,2]];delta=np.roll(starts,-1,axis=0)-starts;length2=np.sum(delta*delta,axis=1);rng=random.Random(41024);placements=[]
 for i,p in enumerate(route):
  b=route[(i+1)%len(route)];dx=b[0]-p[0];dz=b[2]-p[2];length=math.hypot(dx,dz)
  for side in [-1,1]:
   for k in range(12):
    offset=side*rng.uniform(7.5,25);along=rng.uniform(0,length);x=p[0]-dz/length*offset+dx/length*along;z=p[2]+dx/length*offset+dz/length*along;projection=np.clip(np.sum((np.array([x,z])-starts)*delta,axis=1)/length2,0,1);nearest=np.min(np.sum((np.array([x,z])-starts-projection[:,None]*delta)**2,axis=1))
    if nearest<6.8**2:continue
    y=height(x,z)
    if y is not None and y>.25 and y<p[1]+9:placements.append([round(x,3),round(y-.015,3),round(z,3),round(rng.uniform(.8,1.35),3),round(rng.random()*math.tau,3)])
 folder=ROOT/'engine/public/world/meadow';folder.mkdir(exist_ok=True);target=folder/'grass.json';target.write_text(json.dumps(placements,separators=(',',':'))+'\n')
 record={'seed':41024,'plants':len(placements),'geometry':'Original procedural tapered blade clumps, instanced spatially. Existing CC0 photographic grass retained separately.','placement':'Barycentric height against custom graded terrain, route corridor 7.5–25m, lake excluded.','terrain_sha256':hashlib.sha256(raw).hexdigest(),'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest()};(folder/'provenance.json').write_text(json.dumps(record,indent=2)+'\n');print(record)
if __name__=='__main__':build()
