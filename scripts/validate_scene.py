"""Technical gate; deliberately does not claim artistic/photoreal approval."""
import bpy, json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Alpine_Mirror.blend'))
s=bpy.context.scene
checks={}
checks['native_full_hd']=(s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage)==(1920,1080,100)
checks['twenty_seconds_at_24fps']=(s.frame_start,s.frame_end,s.render.fps)==(1,480,24)
checks['cycles_cpu']=s.render.engine=='CYCLES' and s.cycles.device=='CPU'
checks['denoising']=s.cycles.use_denoising
checks['agx']=s.view_settings.view_transform=='AgX'
checks['real_3d_mountain']=any(o.type=='MESH' and o.name.startswith('GEO_HeroMassif') and len(o.data.polygons)>100000 for o in s.objects)
checks['forest_instances']=sum(o.name.startswith('TREE_') for o in s.objects)>2500
checks['no_external_image_projections']=all(n.type!='TEX_IMAGE' for m in bpy.data.materials if m.use_nodes for n in m.node_tree.nodes)
checks['no_missing_asset_dependencies']=not any(i.filepath and not i.packed_file for i in bpy.data.images)
checks['actual_water_surface']=bpy.data.objects.get('GEO_Lake_WaterSurface') is not None
m=bpy.data.materials.get('MAT_Lake_Fresnel_AnimatedCapillaryRipples'); p=m.node_tree.nodes.get('Principled BSDF')
checks['water_dielectric']=abs(p.inputs['IOR'].default_value-1.333)<.001 and p.inputs['Transmission Weight'].default_value>.5
checks['animated_ripples']=m.node_tree.animation_data is not None
positions=[]
for f in [1,240,480]:
    s.frame_set(f); positions.append(tuple(s.camera.location))
checks['real_camera_parallax']=(Vector(positions[-1])-Vector(positions[0])).length>1
checks['deep_focus_landscape']=not s.camera.data.dof.use_dof
checks['short_clip_safe']=s.camera.data.clip_end>=2000
report={'technical_status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'camera_positions':positions,'objects':len(s.objects),'unique_polygons':sum(len(m.polygons) for m in bpy.data.meshes),'visual_status':'NOT_CERTIFIED: consult preview and QA notes','blender':bpy.app.version_string}
(OUT/'scene_validation.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
if not all(checks.values()): raise SystemExit(1)
