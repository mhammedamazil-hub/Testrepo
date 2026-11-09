"""Compile the user's CC-BY Roadster with real bpy; keep source bytes unchanged."""
import json,hashlib,math,os,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def build():
 import bpy
 from mathutils import Matrix,Vector
 source=ROOT/'roadster_lite.glb';before=hashlib.sha256(source.read_bytes()).hexdigest()
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source))
 meshes=[o for o in bpy.data.objects if o.type=='MESH']
 points=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
 lows=[min(p[i] for p in points) for i in range(3)];highs=[max(p[i] for p in points) for i in range(3)]
 keys=[('FL','Ft.L'),('FR','Ft.R'),('RL','Bk.L'),('RR','Bk.R')]
 pivots={k:bpy.data.objects['TR.DEF-Wheel.'+n].matrix_world.translation.copy() for k,n in keys}
 cx=sum(v.x for v in pivots.values())/4;cy=sum(v.y for v in pivots.values())/4
 normalize=Matrix.Rotation(math.pi,4,'Z')@Matrix.Translation(Vector((-cx,-cy,-lows[2])))
 owners={};groups={};radii={}
 for obj in meshes:
  lineage=[];p=obj
  while p:lineage.append(p.name);p=p.parent
  label='Body'
  for k,n in keys:
   if any(x=='TR.DEF-Wheel.'+n for x in lineage):label='Spin_'+k
   if any(x=='TR.DEF-WheelBrake.'+n for x in lineage):label='Caliper_'+k
  owners[obj.name]=label;groups.setdefault(label,[]).append(obj)
 for k,n in keys:
  ps=[o.matrix_world@Vector(c) for o in groups['Spin_'+k] for c in o.bound_box]
  radii[k]=(max(p.z for p in ps)-min(p.z for p in ps))/2
 for im in bpy.data.images:
  w,h=im.size
  if max(w,h)>1024:im.scale(round(w*1024/max(w,h)),round(h*1024/max(w,h)))
 for mat in bpy.data.materials:
  bsdf=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  if not bsdf:continue
  if mat.name=='car_main_paint':
   bsdf.inputs['Coat Weight'].default_value=.55;bsdf.inputs['Coat Roughness'].default_value=.16
   bsdf.inputs['Roughness'].default_value=.24
  if mat.name in ['headlights_main','headlights_AHO']:
   bsdf.inputs['Emission Color'].default_value=(.72,.86,1,1);bsdf.inputs['Emission Strength'].default_value=3
  if mat.name in ['Glass_rear_lights_main','Glass_rear_lights_DHO']:
   bsdf.inputs['Emission Color'].default_value=(1,.008,.002,1);bsdf.inputs['Emission Strength'].default_value=2
 # Bake parent transforms before joining; preserve real UV/material assignments.
 for obj in meshes:
  m=normalize@obj.matrix_world;obj.parent=None;obj.matrix_world=Matrix.Identity(4);obj.data.transform(m)
 outputs=[]
 for label,items in groups.items():
  bpy.ops.object.select_all(action='DESELECT')
  for obj in items:obj.select_set(True)
  bpy.context.view_layer.objects.active=items[0];bpy.ops.object.join();obj=bpy.context.object
  obj.name='Roadster_'+label
  if len(obj.data.polygons)>12000:
   mod=obj.modifiers.new('Bounded gameplay geometry','DECIMATE');mod.ratio=.65
   bpy.ops.object.modifier_apply(modifier=mod.name)
  if label!='Body':
   center=normalize@pivots[label.split('_')[1]];obj.data.transform(Matrix.Translation(-center));obj.location=center
  outputs.append(obj)
 bpy.ops.object.select_all(action='DESELECT')
 for obj in outputs:obj.select_set(True)
 folder=ROOT/'engine/public/world/roadster';folder.mkdir(parents=True,exist_ok=True)
 target=folder/'roadster.glb'
 bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_tangents=True,export_image_format='JPEG',export_jpeg_quality=92)
 wheels=[]
 for k,n in keys:
  v=normalize@pivots[k]
  wheels.append({'name':k,'center':[v.x,v.z,-v.y],'radius':radii[k]})
 manifest={'title':'Tesla Roadster 2020','author':'metarex.4d','source':'https://sketchfab.com/3d-models/tesla-roadster-2020-1fbf29e297bd4a17ac39a00a378441d8','license':'CC-BY-4.0','license_url':'https://creativecommons.org/licenses/by/4.0/','source_sha256':before,'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source_bytes':source.stat().st_size,'output_bytes':target.stat().st_size,'compiler':'Blender bpy '+bpy.app.version_string,'triangles':sum(len(p.vertices)-2 for o in outputs for p in o.data.polygons),'dimensions_m':[highs[0]-lows[0],highs[2]-lows[2],highs[1]-lows[1]],'wheels':wheels,'modifications':'Normalized original supplied model units as metres; front aligned to -Z; ground-centred; merged body/rotating wheels/calipers separately; bounded decimation on large meshes; textures capped at 1024; clearcoat and lamp emission. Dimensions/wheel centres are MODEL measurements, not certified Tesla drawings.','original_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==before}
 (folder/'model.json').write_text(json.dumps(manifest,indent=2)+'\n')
 # Importable physics geometry contract, also travels in the standalone app.
 (ROOT/'engine/roadster-model.json').write_text(json.dumps(manifest,indent=2)+'\n')
 spec=ROOT/'engine/level.json';j=json.loads(spec.read_text());j['assets']['vehicle']='roadster/roadster.glb';spec.write_text(json.dumps(j,indent=2)+'\n')
 print(json.dumps(manifest,indent=2),flush=True)
if __name__=='__main__':
 if '--worker' in sys.argv:build();sys.stdout.flush();sys.stderr.flush();os._exit(0)
 else:
  sys.path.insert(0,str(ROOT/'tools'));from audit_software_graphics import software_environment
  env=software_environment();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='2')
  subprocess.run([sys.executable,__file__,'--worker'],env=env,check=True)
