"""Blender 4.3 authoring pass: modular graded terrain + craggy alpine skyline.
No generated reference image is used as a game texture. Original route/colliders
stay independent. Run node terrain-input preparation, then this file with bpy.
"""
from pathlib import Path
import math,json,hashlib,subprocess
import bpy
import numpy as np
from PIL import Image
from mathutils import noise,Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'engine/public/world/mountain';OUT.mkdir(exist_ok=True)
subprocess.run(['node',str(ROOT/'engine/tests/build-mountain-input.js')],check=True,cwd=ROOT)
data=json.loads((ROOT/'.cache/mountain/input.json').read_text());n=data['segments'];vertices=data['vertices']
bpy.ops.wm.read_factory_settings(use_empty=True)
geo=bpy.data.collections.new('COL_Geo');bpy.context.scene.collection.children.link(geo)
refs=bpy.data.collections.new('COL_Reference');bpy.context.scene.collection.children.link(refs)
mat=bpy.data.materials.new('MAT_Alpine_VertexLayers');mat.use_nodes=True
nodes=mat.node_tree.nodes;attr=nodes.new('ShaderNodeVertexColor');attr.layer_name='Color';bsdf=nodes.get('Principled BSDF');bsdf.inputs['Roughness'].default_value=.94;mat.node_tree.links.new(attr.outputs['Color'],bsdf.inputs['Base Color'])
report=[]
def mesh(name,points,faces,base=False):
 m=bpy.data.meshes.new(name);m.from_pydata([(x,-z,y) for x,y,z in points],[],faces);m.update();o=bpy.data.objects.new(name,m);geo.objects.link(o);m.materials.append(mat)
 colour=m.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='POINT')
 for i,p in enumerate(points):
  normal=m.vertices[i].normal;slope=1-abs(normal.z);h=p[1];t=max(0,min(1,(slope-.12)*2.6));v=noise.noise(Vector((p[0]*.011,p[2]*.011,h*.006)),noise_basis='PERLIN_ORIGINAL')
  grass=(.16+v*.025,.205+v*.028,.135+v*.02);rock=(.61+v*.07,.625+v*.065,.63+v*.06);snow=max(0,min(1,(h-1550)/450))*(1-min(1,slope*2))
  c=tuple(((grass[k]*(1-t)+rock[k]*t) if base else rock[k])*(1-snow)+(.79,.83,.85)[k]*snow for k in range(3));colour.data[i].color=(*c,1)
 for polygon in m.polygons:polygon.use_smooth=True
 # UVs in world metres; runtime uses triplanar layers rather than stretched UVs.
 uv=m.uv_layers.new(name='UVMap')
 for polygon in m.polygons:
  for loop in polygon.loop_indices:
   p=points[m.loops[loop].vertex_index];uv.data[loop].uv=(p[0]/12,p[2]/12)
 report.append({'name':name,'triangles':sum(len(f)-2 for f in faces),'vertices':len(points)});return o
def faces_grid(w,h):return [(z*w+x,(z+1)*w+x,(z+1)*w+x+1,z*w+x+1) for z in range(h-1) for x in range(w-1)]
# Tiles share exact edge positions at all three LODs. 300 m is the spatial unit.
# Lock a 32-sample boundary ring on every level, preventing open T-junctions.
for z in range(8):
 for x in range(8):
  for lod,step in enumerate((1,2,4)):
   points=[];lookup={};faces=[]
   def add(ix,iz):
    key=(ix,iz)
    if key not in lookup:
     idx=((z*32+iz)*(n+1)+x*32+ix)*3;lookup[key]=len(points);points.append(vertices[idx:idx+3])
    return lookup[key]
   for iz in range(0,32,step):
    for ix in range(0,32,step):
     ring=[(ix,iz),(ix,iz+step),(ix+step,iz+step),(ix+step,iz)]
     # boundary subdivisions are triangulated through a cell centre
     if step>1 and (ix==0 or iz==0 or ix+step==32 or iz+step==32):
      coords=[]
      for j,(a,b) in enumerate(ring):
       c,d=ring[(j+1)%4];edge=(a==c and a in (0,32)) or (b==d and b in (0,32));count=step if edge else 1
       for k in range(count):coords.append((a+(c-a)*k//count,b+(d-b)*k//count))
      centre=add(ix+step//2,iz+step//2)
      for j,p in enumerate(coords):faces.append((add(*p),add(*coords[(j+1)%len(coords)]),centre))
     else:faces.append(tuple(add(*p) for p in ring))
   mesh(f'Terrain_{x}_{z}_LOD{lod}',points,faces,True)
# Low-cost distant ring: no fully detailed distant world, just readable silhouettes.
# Seven distinct massifs, with open valley exits instead of a continuous dome.
PEAKS=[(-1900,-2300,2050,1050,850),(-350,-3200,2380,1250,1000),(1600,-2700,1900,1050,800),(2900,-600,1420,850,1100),(2200,2300,980,1300,1000),(-2300,2400,1120,1100,1000),(-3100,0,1640,1000,1350)]
PEAKS=[(x*1.35,z*1.35,h*.82,sx*1.2,sz*1.2) for x,z,h,sx,sz in PEAKS]
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def geology(x,z):
 warp_x=noise.noise(Vector((x*.00065,z*.00065,3.7)))*210;warp_z=noise.noise(Vector((x*.00065,z*.00065,8.2)))*210
 values=[]
 for px,pz,height,sx,sz in PEAKS:
  d=math.hypot((x+warp_x-px)/sx,(z+warp_z-pz)/sz)
  # Talus apron supports an eroded limestone crown: not a smooth cone.
  apron=height*.30*max(0,1-d*.62)**1.5
  flutes=noise.noise(Vector((x*.005,z*.005,px*.001)))*.10
  crown=height*.70*smooth(1.03,.48,d+flutes)
  values.append(apron+crown)
 mass=max(values);envelope=min(1,mass/350)
 ridged=noise.ridged_multi_fractal(Vector((x*.0028,z*.0028,.77)),1.05,2.15,5,1,2)
 gullies=noise.noise(Vector((x*.012,z*.012,4.6)))
 mass=mass*(.75+ridged*.18)+gullies*30*envelope
 # Broad bedding shelves, varied by location. Never periodic shader stripes.
 step=90+noise.noise(Vector((x*.001,z*.001,2.4)))*24
 fraction=(mass/step)%1;terraced=(math.floor(mass/step)+smooth(.12,.8,fraction))*step
 return max(0,mass*.65+terraced*.35)
def outer(a,t):
 dx,dz=math.cos(a),math.sin(a);edge=1200/max(abs(dx),abs(dz));r=edge-2+t*4602;x,z=dx*r,dz*r
 k=a/(math.pi*2)*256;lo=math.floor(k)%256;u=k-math.floor(k);boundary=data['boundary'][lo]*(1-u)+data['boundary'][(lo+1)%256]*u
 blend=smooth(0,.12,t);h=(boundary-5)*(1-blend)+(geology(x,z)+25)*blend
 return x,h,z
for sector in range(16):
 for lod,(angular,radial) in enumerate(((40,48),(20,24),(10,12))):
  points=[outer((sector+i/angular)/16*math.pi*2,j/radial) for j in range(radial+1) for i in range(angular+1)]
  mesh(f'Massif_{sector}_LOD{lod}',points,[tuple(reversed(face)) for face in faces_grid(angular+1,radial+1)])
# Adapt licensed PBR source maps. Preserve originals + MIT notice in source.
source_pbr=ROOT/'game/assets/mountain/pbr-original';size=(1024,1024)
albedo=np.array(Image.open(source_pbr/'rock_albedo.jpg').convert('RGB').resize(size,Image.Resampling.LANCZOS),dtype=np.float32)/255
occlusion=np.array(Image.open(source_pbr/'rock_ao.jpg').convert('L').resize(size,Image.Resampling.LANCZOS),dtype=np.float32)/255
height=np.array(Image.open(source_pbr/'rock_depth.jpg').convert('L').resize(size,Image.Resampling.LANCZOS),dtype=np.float32)/255
pixels=np.empty((1024,1024,4),np.uint8);pixels[:,:,:3]=np.clip(albedo*(.65+.35*occlusion[:,:,None])*255,0,255);pixels[:,:,3]=np.clip(height*255,0,255)
Image.fromarray(pixels,'RGBA').save(OUT/'limestone-pbr.png',optimize=True)
# Explicit metre-scale reference stays outside export.
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,.85));scale=bpy.context.object;scale.name='REF_Human_1m70';scale.dimensions=(.45,.3,1.7)
for collection in list(scale.users_collection):collection.objects.unlink(scale)
refs.objects.link(scale);scale.hide_render=True
for o in bpy.context.selected_objects:o.select_set(False)
for o in geo.objects:o.select_set(True)
bpy.context.view_layer.objects.active=next(iter(geo.objects))
output=OUT/'alpine-massif.glb';bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,export_yup=True,export_normals=True)
source=ROOT/'game/assets/mountain/alpine-mountain.blend';source.parent.mkdir(exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(source))
manifest={'terrain_source_sha256':hashlib.sha256((ROOT/'engine/src/online/map.js').read_bytes()).hexdigest(),'author':'Original procedural environment, repository authoring script','tool':'Blender '+bpy.app.version_string,'units':'metres','map_collision':'Shared graded ground and road/rails retained; distant massif GLB is render-only','lod':'64 terrain tiles, 16 skyline sectors, each with three levels; tile boundary vertices locked. Camera-distance/frustum switches at runtime.','boundary_max_gap_metres':max(abs(outer(i/256*math.pi*2,0)[1]-data['boundary'][i]) for i in range(256)),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'meshes':report}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('BLENDER_MOUNTAIN_EXPORTED',manifest['bytes'],len(report),'meshes',flush=True)
