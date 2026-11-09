"""Grade only the custom terrain derivative below the road; never edit cinematic/shared GLB."""
from pathlib import Path
import hashlib,json,struct
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
def build():
 source=ROOT/'game/assets/terrain.glb';data=bytearray(source.read_bytes());size=struct.unpack_from('<I',data,12)[0];gltf=json.loads(data[20:20+size]);base=28+size
 route=np.array(json.loads((ROOT/'engine/public/world/track/route.json').read_text())['points'])
 changed=0
 for mesh in gltf['meshes']:
  if 'Ground' not in mesh.get('name',''):continue
  for primitive in mesh['primitives']:
   a=gltf['accessors'][primitive['attributes']['POSITION']];v=gltf['bufferViews'][a['bufferView']]
   assert v.get('byteStride',12)==12
   positions=np.frombuffer(data,dtype='<f4',count=a['count']*3,offset=base+v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,3)
   for start in range(0,len(positions),512):
    p=positions[start:start+512];delta=p[:,None,[0,2]]-route[None,:,[0,2]];dist=np.sum(delta*delta,axis=2);nearest=dist.argmin(axis=1);d=np.sqrt(dist[np.arange(len(p)),nearest]);blend=np.clip((30-d)/10,0,1);target=route[nearest,1]-.65
    mask=(d<30)&(p[:,1]>target);changed+=int(mask.sum());p[mask,1]=p[mask,1]*(1-blend[mask])+target[mask]*blend[mask]
   a['min']=positions.min(axis=0).tolist();a['max']=positions.max(axis=0).tolist()
 # Accessor bounds must describe the edited vertex buffer, so rebuild the JSON chunk.
 text=json.dumps(gltf,separators=(',',':')).encode();text+=b' '*((-len(text))%4);binary=bytes(data[base:]);out=struct.pack('<III',0x46546c67,2,28+len(text)+len(binary))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(binary),0x004e4942)+binary
 target=ROOT/'engine/public/world/track/terrain.glb';target.write_bytes(out)
 meta={'source':'game/assets/terrain.glb','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(out).hexdigest(),'graded_vertices':changed,'modifications':'Only custom derivative: grade terrain below road in a 20m corridor, blend to original terrain over next 10m. Recomputed runtime vertex normals. Original cinematic/shared terrain untouched.'}
 (target.parent/'provenance.json').write_text(json.dumps(meta,indent=2)+'\n');print(meta)
if __name__=='__main__':build()
