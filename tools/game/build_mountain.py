"""Blender 4.3 authoring pass: modular graded terrain + craggy alpine skyline.
No generated reference image is used as a game texture. Original route/colliders
stay independent. Run node terrain-input preparation, then this file with bpy.
"""
from pathlib import Path
import math,json,hashlib,subprocess
import bpy
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
  grass=(.16+v*.025,.205+v*.028,.135+v*.02);rock=(.30+v*.09,.30+v*.085,.285+v*.08);snow=max(0,min(1,(h-1050)/350))*(1-min(1,slope*2))
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
def outer(a,t):
 dx,dz=math.cos(a),math.sin(a);edge=1200/max(abs(dx),abs(dz));r=edge-2+t*4602;x,z=dx*r,dz*r
 k=a/(math.pi*2)*256;lo=math.floor(k)%256;u=k-math.floor(k);boundary=data['boundary'][lo]*(1-u)+data['boundary'][(lo+1)%256]*u
 ridge=.48+.24*math.sin(5*a+.7)+.17*math.sin(11*a+2)+.1*math.sin(19*a)
 profile=max(0,math.exp(-((t-.34)/.24)**2)-math.exp(-(.34/.24)**2)*(1-t));detail=noise.ridged_multi_fractal(Vector((x*.0017,z*.0017,.42)),.9,2.1,4,1,2)
 h=boundary*(1-t)+profile*(750+ridge*1250)+detail*210*min(1,t*8)+t*70-5*(1-t)
 return x,h,z
for sector in range(16):
 for lod,(angular,radial) in enumerate(((24,24),(12,12),(6,6))):
  points=[outer((sector+i/angular)/16*math.pi*2,j/radial) for j in range(radial+1) for i in range(angular+1)]
  mesh(f'Massif_{sector}_LOD{lod}',points,[tuple(reversed(face)) for face in faces_grid(angular+1,radial+1)])
# Explicit metre-scale reference stays outside export.
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,.85));scale=bpy.context.object;scale.name='REF_Human_1m70';scale.dimensions=(.45,.3,1.7)
for collection in list(scale.users_collection):collection.objects.unlink(scale)
refs.objects.link(scale);scale.hide_render=True
for o in bpy.context.selected_objects:o.select_set(False)
for o in geo.objects:o.select_set(True)
bpy.context.view_layer.objects.active=next(iter(geo.objects))
output=OUT/'alpine-massif.glb';bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,export_yup=True,export_normals=True)
source=ROOT/'game/assets/mountain/alpine-mountain.blend';source.parent.mkdir(exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(source))
manifest={'author':'Original procedural environment, repository authoring script','tool':'Blender '+bpy.app.version_string,'units':'metres','map_collision':'Unchanged JS graded terrain/road/rails; this GLB is render-only','lod':'64 terrain tiles, 16 skyline sectors, each with three levels; tile boundary vertices locked. Camera-distance/frustum switches at runtime.','boundary_max_gap_metres':max(abs(outer(i/256*math.pi*2,0)[1]-data['boundary'][i]) for i in range(256)),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'meshes':report}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('BLENDER_MOUNTAIN_EXPORTED',manifest['bytes'],len(report),'meshes',flush=True)
