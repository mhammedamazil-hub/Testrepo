"""Use real bpy to package the selected CC0 library assets and scene contract.
The 17-million-triangle/949MB pine is intentionally NOT imported: its real
photographic twig and bark maps are applied to the budgeted 3D branch-card LOD.
The grass geometry is an actual Poly Haven mesh, not a renamed primitive.
"""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CACHE=ROOT/'.cache/library-transport'
OUT=ROOT/'game/assets/library'

def build():
 import bpy
 from PIL import Image,ImageChops,ImageDraw
 from mathutils import Vector
 OUT.mkdir(parents=True,exist_ok=True)
 catalog=json.loads((ROOT/'docs/research/library-catalog.json').read_text())
 for record in catalog.values():
  for item in record['downloads']:
   p=CACHE/item['file']
   assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],p
 def image_for(asset,key):
  return next(CACHE/e['file'] for e in catalog[asset]['downloads'] if ('__'+key+'__') in e['file'])
 # Atlas download order is not a naming contract; select actual diffuse by name.
 def named(asset,word):return next(CACHE/e['file'] for e in catalog[asset]['downloads'] if word in e['file'])
 for asset,prefix in [('pine_tree_01','pine_twig'),('grass_medium_01','grass_blades')]:
  color=Image.open(named(asset,'diff_1k')).convert('RGBA')
  alpha=Image.open(named(asset,'alpha_1k')).convert('L').resize(color.size)
  if asset=='pine_tree_01':
   # The source is a mixed UV atlas: opaque cone/wood islands MUST NOT be
   # stretched over foliage cards. Isolate the actual upper-left needle twig.
   island=Image.new('L',color.size,0)
   ImageDraw.Draw(island).polygon([(25,35),(210,35),(230,80),(235,150),(230,255),(212,335),(190,389),(168,450),(116,450),(80,435),(40,415),(25,350)],fill=255)
   alpha=ImageChops.multiply(alpha,island)
  color.putalpha(alpha)
  if asset=='pine_tree_01':color=color.crop((25,35,236,456))
  color.save(OUT/(prefix+'_rgba.png'))
 for asset,prefix in [('leafy_grass','ground'),('pine_bark','bark')]:
  for key,channel in [('Diffuse','diff'),('nor_gl','normal'),('arm','arm')]:
   shutil.copyfile(image_for(asset,key),OUT/(prefix+'_'+channel+'.jpg'))
 # Create a local complete glTF package from the verified transport.
 folder=ROOT/'.cache/library-grass-package';(folder/'textures').mkdir(parents=True,exist_ok=True)
 shutil.copyfile(CACHE/'grass_medium_01.gltf',folder/'grass.gltf')
 for entry in catalog['grass_medium_01']['downloads']:
  name=entry['url'].split('/')[-1]
  if name.endswith('.bin'):shutil.copyfile(CACHE/entry['file'],folder/name)
  elif '__atlas__' in entry['file']:shutil.copyfile(CACHE/entry['file'],folder/'textures'/name)
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.gltf(filepath=str(folder/'grass.gltf'))
 grass=next(o for o in bpy.data.objects if 'tiny_a_LOD0' in o.name and o.type=='MESH')
 grass.location=(0,0,0);bpy.context.view_layer.update()
 grass.scale*=.42/max(grass.dimensions.z,.01);bpy.context.view_layer.update()
 grass.location.z-=min((grass.matrix_world@Vector(p)).z for p in grass.bound_box)
 bpy.ops.object.select_all(action='DESELECT');grass.select_set(True);bpy.context.view_layer.objects.active=grass
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 for mat in grass.data.materials:
  nodes=mat.node_tree.nodes;links=mat.node_tree.links
  bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
  tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(OUT/'grass_blades_rgba.png'))
  links.new(tex.outputs['Color'],bsdf.inputs['Base Color']);links.new(tex.outputs['Alpha'],bsdf.inputs['Alpha'])
 grass.name='PolyHaven_Grass_Tiny_A'
 bpy.ops.export_scene.gltf(filepath=str(OUT/'grass.glb'),export_format='GLB',use_selection=True,export_tangents=True)
 grass_tris=sum(len(p.vertices)-2 for p in grass.data.polygons)
 for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
 bpy.ops.import_scene.gltf(filepath=str(ROOT/'game/assets/spruce_near.glb'))
 tree=next(o for o in bpy.data.objects if o.type=='MESH')
 def surface(mat,diff,normal=None,alpha=False):
  nodes=mat.node_tree.nodes;links=mat.node_tree.links
  bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
  tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(OUT/diff),check_existing=True)
  links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
  if alpha:links.new(tex.outputs['Alpha'],bsdf.inputs['Alpha'])
  if normal:
   texn=nodes.new('ShaderNodeTexImage');texn.image=bpy.data.images.load(str(OUT/normal),check_existing=True);texn.image.colorspace_settings.name='Non-Color'
   convert=nodes.new('ShaderNodeNormalMap');links.new(texn.outputs['Color'],convert.inputs['Color']);links.new(convert.outputs['Normal'],bsdf.inputs['Normal'])
  bsdf.inputs['Roughness'].default_value=.9
 surface(tree.data.materials[0],'bark_diff.jpg','bark_normal.jpg')
 for mat in list(tree.data.materials)[1:]:surface(mat,'pine_twig_rgba.png',alpha=True)
 # Repeat bark in metre-scale vertical units, rather than stretching 2m over 16m.
 for polygon in tree.data.polygons:
  if polygon.material_index==0:
   for li in polygon.loop_indices:tree.data.uv_layers.active.data[li].uv.y*=8
 tree.name='Library_Pine_Branch_LOD'
 bpy.ops.object.select_all(action='DESELECT');tree.select_set(True);bpy.context.view_layer.objects.active=tree
 bpy.ops.export_scene.gltf(filepath=str(OUT/'pine.glb'),export_format='GLB',use_selection=True,export_tangents=True)
 tree_tris=sum(len(p.vertices)-2 for p in tree.data.polygons)
 report={'library':'Poly Haven','credit':'Powered by Poly Haven','license':'CC0-1.0','license_scope':'Poly Haven source inputs; original Alpine scaffold and game code retain repository terms','grass_source':'grass_medium_01 / tiny_a_LOD0','grass_triangles':grass_tris,'pine_source':'pine_tree_01 photographic twig maps + pine_bark; adapted branch-card geometry, not the 17M-triangle source tree','pine_triangles':tree_tris,'pine_atlas_adaptation':'isolated upper-left photographic needle island, crop [25,35,236,456]; opaque cone/wood islands excluded','sources':{k:{'url':r['source'],'authors':r['info'].get('authors',{})} for k,r in catalog.items()},'files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in OUT.iterdir() if p.is_file() and p.name in {'pine_twig_rgba.png','grass_blades_rgba.png','ground_diff.jpg','ground_normal.jpg','ground_arm.jpg','bark_diff.jpg','bark_normal.jpg','bark_arm.jpg','grass.glb','pine.glb'}}}
 (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
 # A bpy-produced level/resource contract consumed by the custom framework.
 spec={'schema':'alpine.level.v1','compiler':'Blender bpy '+bpy.app.version_string,'source_blend_sha256':hashlib.sha256((ROOT/'output/Alpine_Mirror.blend').read_bytes()).hexdigest(),'name':'Alpine Mirror','viewport':[1920,1080],'physics_hz':60,'lake':{'position':[0,0,-135],'size':[320,460]},'sun':[20,285,-800],'checkpoints':[160,320,480,0],'assets':{'terrain':'track/terrain.glb','road':'road.glb','vehicle':'roadster/roadster.glb','character':'hiker.glb','pine':'library/pine.glb','grass':'library/grass.glb','rocks':'granite.glb'}}
 (ROOT/'engine/level.json').write_text(json.dumps(spec,indent=2)+'\n')
 print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
 if '--worker' in sys.argv:build();sys.stdout.flush();sys.stderr.flush();os._exit(0)
 else:
  sys.path.insert(0,str(ROOT/'tools'));from audit_software_graphics import software_environment
  env=software_environment();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='2')
  subprocess.run([sys.executable,__file__,'--worker'],env=env,check=True)
