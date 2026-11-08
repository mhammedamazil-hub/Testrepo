"""Fetch bounded CC0 Poly Haven inputs on a free GitHub runner.

Sandbox networking cannot access the asset CDN. This records API metadata,
upstream integrity digests and actual downloaded hashes, never runtime hotlinks.
A separate authoring step optimizes only selected inputs for mobile use.
"""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.cache/library-transport'
OUT.mkdir(parents=True,exist_ok=True)
HEADERS={'User-Agent':'Alpine-Mirror-research/1.0 (Powered by Poly Haven)'}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=120) as response:
        return response.read()

def save(asset,channel,item):
    name=asset+'__'+channel+'__'+item['url'].split('/')[-1]
    if item.get('size',0)>8_000_000:return None
    data=get(item['url'])
    if item.get('md5') and hashlib.md5(data).hexdigest()!=item['md5']:raise RuntimeError('Upstream digest mismatch '+name)
    (OUT/name).write_bytes(data)
    return {'file':name,'url':item['url'],'bytes':len(data),'md5':item.get('md5'),'sha256':hashlib.sha256(data).hexdigest()}

catalog={}
for asset in ['leafy_grass','pine_bark','pine_tree_01','grass_medium_01']:
    info=json.loads(get('https://api.polyhaven.com/info/'+asset))
    files=json.loads(get('https://api.polyhaven.com/files/'+asset))
    (OUT/(asset+'__api.json')).write_text(json.dumps(files,indent=2)+'\n')
    record={'info':info,'source':'https://polyhaven.com/a/'+asset,'license':'CC0-1.0','formats':list(files),'downloads':[]}
    if asset in ['leafy_grass','pine_bark']:
        for key in ['Diffuse','nor_gl','Rough','rough','arm']:
            item=files.get(key,{}).get('1k',{}).get('jpg')
            if item:
                entry=save(asset,key,item)
                if entry:record['downloads'].append(entry)
    else:
        model=files.get('gltf',{}).get('1k',{}).get('gltf',{})
        record['gltf_1k']=model
        if model.get('url') and model.get('size',0)<4_000_000:
            data=get(model['url']);gltf=json.loads(data)
            (OUT/(asset+'.gltf')).write_bytes(data)
            record['model_meshes']=[{'name':mesh.get('name'),'triangles':sum(gltf['accessors'][p['indices']]['count']//3 for p in mesh['primitives'] if 'indices' in p)} for mesh in gltf.get('meshes',[])]
            record['model_nodes']=gltf.get('nodes',[])
            # Preserve photographic foliage inputs, not a huge cinematic mesh.
            for name,item in model.get('include',{}).items():
                lower=name.lower()
                if any(t in lower for t in ['twig','grass']) and any(t in lower for t in ['diff','mask','nor_gl','arm']) and lower.endswith(('.jpg','.png')):
                    entry=save(asset,'atlas',item)
                    if entry:record['downloads'].append(entry)
                if lower.endswith('.bin') and item.get('size',1e9)<12_000_000:
                    entry=save(asset,'geometry',item)
                    if entry:record['downloads'].append(entry)
    catalog[asset]=record
report=ROOT/'docs/research/library-catalog.json'
report.parent.mkdir(parents=True,exist_ok=True)
report.write_text(json.dumps(catalog,indent=2)+'\n')
print(json.dumps({a:{'formats':r['formats'],'meshes':r.get('model_meshes'),'downloads':[(e['file'],e['bytes']) for e in r['downloads']]} for a,r in catalog.items()},indent=2))
