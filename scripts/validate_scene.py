"""Revision-2 technical gate. Artistic approval still requires image review."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from project_config import FPS,FRAME_COUNT
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Alpine_Mirror.blend'));s=bpy.context.scene
checks={
 'revision_2':s.get('revision')==2,
 'native_full_hd':(s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage)==(1920,1080,100),
 'twenty_seconds_at_60fps':(s.frame_start,s.frame_end,s.render.fps)==(1,FRAME_COUNT,FPS),
 'cycles_cpu':s.render.engine=='CYCLES' and s.cycles.device=='CPU',
 'denoising':s.cycles.use_denoising,
 'agx':s.view_settings.view_transform=='AgX',
 'actual_mountain_geometry':any(o.type=='MESH' and o.name.startswith('GEO_HeroMassif') and len(o.data.polygons)>100000 for o in s.objects),
 'forest_instances':sum(o.name.startswith('TREE_') for o in s.objects)>2500,
 'volumetric_tree_canopies':any(m.name.startswith('LIB_R2_VolumetricSpruce') for m in bpy.data.meshes),
 'wind_sway':sum(o.name.startswith('TREE_') and o.animation_data is not None for o in s.objects)>30,
 'packed_photographic_sky':any(n.type=='TEX_ENVIRONMENT' and n.image is not None and n.image.packed_file is not None for n in s.world.node_tree.nodes),
 'dramatic_mist_banks':sum(o.name.startswith('FX_R2_DramaticMistBank') for o in s.objects)==3,
 'finite_valley_mist':bpy.data.objects.get('FX_R2_HeightDecayingValleyMist') is not None,
 'seven_animated_birds':sum(o.name.startswith('BIRD_R2_Flock') and o.animation_data is not None for o in s.objects)==7,
 'no_photo_backplates':all(n.type!='TEX_IMAGE' for m in bpy.data.materials if m.use_nodes for n in m.node_tree.nodes),
 'no_missing_assets':not any(i.filepath and not i.packed_file for i in bpy.data.images),
 'camera_reveals_fixed_sun':bool(s.get('solar_reveal_verified')),
 'sunlit_water_at_end':bool(s.get('solar_water_glint_verified')),
 'raytraced_backlight':bpy.data.objects.get('LGT_R2_BacklitMorningSun') is not None,
 'motion_blur':s.render.use_motion_blur,
}
water=bpy.data.objects.get('GEO_Lake_WaterSurface');checks['geometric_water_waves']=water is not None and any(m.type=='NODES' and 'Traveling' in m.name for m in water.modifiers)
m=water.data.materials[0];p=m.node_tree.nodes.get('Principled BSDF')
checks['physical_water_ior']=abs(p.inputs['IOR'].default_value-1.333)<.001 and p.inputs['Transmission Weight'].default_value>.9
checks['water_absorption']=any(n.type=='VOLUME_ABSORPTION' for n in m.node_tree.nodes)
checks['animated_capillary_waves']=m.node_tree.animation_data is not None
positions=[]
for f in [1,600,1200]:s.frame_set(f);positions.append(tuple(s.camera.location))
checks['substantial_drone_flight']=(Vector(positions[-1])-Vector(positions[0])).length>100
checks['rising_drone']=positions[-1][2]-positions[0][2]>8
report={'technical_status':'PASS' if all(checks.values()) else 'FAIL','revision':2,'checks':checks,'camera_positions':positions,'objects':len(s.objects),'unique_polygons':sum(len(m.polygons) for m in bpy.data.meshes),'visual_status':'NOT_CERTIFIED until first/mid/last and motion tests are reviewed','blender':bpy.app.version_string}
(OUT/'scene_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if not all(checks.values()):raise SystemExit(1)
