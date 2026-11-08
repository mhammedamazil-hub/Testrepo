"""Build optimized assets from the delivered Alpine .blend, without modifying it.

Requires the optional audit bpy environment and real Mesa OS dependencies.
Runs in an isolated authoring process. After validated writes, uses the explicitly
reported embedded-bpy cleanup workaround; this is NOT the gameplay runtime.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'game/assets'


def build():
    import bpy
    import numpy as np
    from mathutils import Vector
    from PIL import Image
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT/'output/Alpine_Mirror.blend'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    scene.frame_set(1)
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    bpy.context.preferences.filepaths.save_version = 0
    native = {}
    for name, nx, ny in [('GEO_HeroMassif_HydraulicErosion',900,630),
                         ('GEO_LakeBasin_ContinuousValleyBanks',520,460)]:
        obj = bpy.data.objects[name]
        coordinates = np.empty(len(obj.data.vertices)*3, dtype=np.float32)
        obj.data.vertices.foreach_get('co',coordinates)
        native[name] = (coordinates.reshape(ny+1,nx+1,3).copy(),obj.data.materials[0])
    original_trees = [(tuple(o.location),float(o.dimensions.z)) for o in bpy.data.objects
                      if o.name.startswith('TREE_') and -100<o.location.y<650 and abs(o.location.x)<380]
    spruce = bpy.data.objects.get('LIB_Spruce_100')
    assert spruce is not None
    for obj in list(bpy.data.objects):
        if obj != spruce:
            bpy.data.objects.remove(obj,do_unlink=True)
    for collection in list(spruce.users_collection):
        collection.objects.unlink(spruce)
    scene.collection.objects.link(spruce)
    spruce.hide_render = True
    spruce.hide_set(False)
    scene.world = bpy.data.worlds.new('Game_asset_bake_world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .7
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 8
    scene.cycles.max_bounces = 3
    scene.render.bake.margin = 12
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    scene.render.bake.use_pass_color = True

    def material(name,color,rough=.8,metal=0):
        m=bpy.data.materials.new(name);m.use_nodes=True
        p=m.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value=(*color,1)
        p.inputs['Roughness'].default_value=rough
        p.inputs['Metallic'].default_value=metal
        m.use_backface_culling=True
        return m

    def mesh(name,vertices,faces,mat):
        data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
        if mat:data.materials.append(mat)
        for p in data.polygons:p.use_smooth=True
        return obj

    def select(objects):
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]

    def export(name,objects,**options):
        for obj in objects:
            if obj.type=='MESH' and any(len(p.vertices)>4 for p in obj.data.polygons):
                select([obj])
                modifier=obj.modifiers.new('Export triangulation','TRIANGULATE')
                bpy.ops.object.modifier_apply(modifier=modifier.name)
        select(objects)
        bpy.ops.export_scene.gltf(filepath=str(OUT/name),export_format='GLB',
            use_selection=True,export_tangents=True,**options)

    def cube(name,location,dimensions,mat,bevel=.04):
        bpy.ops.mesh.primitive_cube_add(size=1,location=location)
        obj=bpy.context.object;obj.name=name;obj.dimensions=dimensions
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        if bevel:
            mod=obj.modifiers.new('Manufactured edge','BEVEL');mod.width=bevel;mod.segments=2
            bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.data.materials.append(mat)
        return obj

    def sphere(name,location,scale,mat):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,location=location)
        obj=bpy.context.object;obj.name=name;obj.scale=scale
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        obj.data.materials.append(mat)
        for p in obj.data.polygons:p.use_smooth=True
        return obj

    def join(objects,name):
        select(objects);bpy.ops.object.join();obj=bpy.context.object;obj.name=name
        return obj

    ground_source=native['GEO_LakeBasin_ContinuousValleyBanks'][0]
    def height(x,y):
        u=np.clip((x+650)/1300*520,0,519.9999);v=np.clip((y+65)/790*460,0,459.9999)
        i,j=int(u),int(v);u-=i;v-=j
        h=ground_source[j:j+2,i:i+2,2]
        return float((h[0,0]*(1-u)+h[0,1]*u)*(1-v)+(h[1,0]*(1-u)+h[1,1]*u)*v)
    def right(y):return 49-.079*max(y,0)+7*math.sin(y*.027+1)-13*math.exp(-((y-52)/43)**2)
    def left(y):return -63+.10*max(y,0)+5*math.sin(y*.029)
    controls=[(right(-25)+17,-25),(right(110)+17,110),(right(270)+17,270),(18,339),(-20,339),
              (left(270)-17,270),(left(100)-17,100),(left(-25)-17,-25),(-45,-52),(30,-52)]
    route=[]
    for i in range(len(controls)):
        a,b,c,d=[np.array(controls[(i+k)%len(controls)]) for k in (-1,0,1,2)]
        for j in range(16):
            t=j/16
            v=.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)
            route.append([float(v[0]),float(v[1]),height(*v)+.25])
    route=np.array(route)
    for unused in range(3):
        route[:,2]=(np.roll(route[:,2],1)+route[:,2]*2+np.roll(route[:,2],-1))/4
    route2=route[:,:2]
    terrain_objects=[]
    for source_name,step,name,resolution in [
        ('GEO_HeroMassif_HydraulicErosion',6,'Alpine_Massif',1024),
        ('GEO_LakeBasin_ContinuousValleyBanks',4,'Alpine_Ground',1024)]:
        full,original_mat=native[source_name]
        rows=list(range(0,len(full),step));cols=list(range(0,len(full[0]),step))
        if rows[-1]!=len(full)-1:rows.append(len(full)-1)
        if cols[-1]!=len(full[0])-1:cols.append(len(full[0])-1)
        grid=full[np.ix_(rows,cols)].copy()
        if name=='Alpine_Ground':
            for row in grid:
                for v in row:
                    ds=np.sum((route2-v[:2])**2,axis=1);k=int(np.argmin(ds));distance=math.sqrt(ds[k])
                    if distance<8:
                        blend=np.clip((8-distance)/3,0,1)
                        v[2]=v[2]*(1-blend)+(route[k,2]-.12)*blend
        w=len(cols);h=len(rows)
        faces=[(j*w+i,j*w+i+1,(j+1)*w+i+1,(j+1)*w+i)
               for j in range(h-1) for i in range(w-1)]
        obj=mesh(name,grid.reshape(-1,3).tolist(),faces,original_mat.copy())
        uv=obj.data.uv_layers.new(name='UVMap')
        x0,y0=full[0,0,:2];x1,y1=full[-1,-1,:2]
        for polygon in obj.data.polygons:
            for li in polygon.loop_indices:
                v=obj.data.vertices[obj.data.loops[li].vertex_index].co
                uv.data[li].uv=((v.x-x0)/(x1-x0),(v.y-y0)/(y1-y0))
        select([obj]);baked={}
        for channel,kind in [('albedo','DIFFUSE'),('normal','NORMAL')]:
            image=bpy.data.images.new(name+'_'+channel,width=resolution,height=resolution,alpha=False)
            if channel=='normal':image.colorspace_settings.name='Non-Color'
            node=obj.active_material.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
            obj.active_material.node_tree.nodes.active=node
            bpy.ops.object.bake(type=kind)
            image.filepath_raw=str(OUT/(name+'_'+channel+'.png'));image.file_format='PNG';image.save()
            baked[channel]=image
        mat=material('MAT_'+name,(1,1,1),.9)
        nodes,links=mat.node_tree.nodes,mat.node_tree.links;p=nodes.get('Principled BSDF')
        color=nodes.new('ShaderNodeTexImage');color.image=baked['albedo'];links.new(color.outputs['Color'],p.inputs['Base Color'])
        normal=nodes.new('ShaderNodeTexImage');normal.image=baked['normal']
        convert=nodes.new('ShaderNodeNormalMap');links.new(normal.outputs['Color'],convert.inputs['Color']);links.new(convert.outputs['Normal'],p.inputs['Normal'])
        obj.data.materials.clear();obj.data.materials.append(mat);terrain_objects.append(obj)
    export('terrain.glb',terrain_objects)

    asphalt=material('MAT_Asphalt',(.15,.16,.17),.93)
    rng=np.random.default_rng(841)
    grain=np.clip(rng.normal(83,9,(512,512,1)),40,120).astype(np.uint8)
    Image.fromarray(np.repeat(grain,3,axis=2)).save(OUT/'asphalt.png')
    image=bpy.data.images.load(str(OUT/'asphalt.png'))
    tex=asphalt.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
    asphalt.node_tree.links.new(tex.outputs['Color'],asphalt.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    roadv=[];roadfaces=[];lengths=[0.]
    normals=[]
    for i,p in enumerate(route):
        tangent=route[(i+1)%len(route),:2]-route[(i-1)%len(route),:2]
        side=np.array([-tangent[1],tangent[0]]);side/=np.linalg.norm(side);normals.append(side)
        for offset in (-3.65,3.65):roadv.append((p[0]+side[0]*offset,p[1]+side[1]*offset,p[2]))
        if i: lengths.append(lengths[-1]+float(np.linalg.norm(p-route[i-1])))
    for i in range(len(route)):
        n=(i+1)%len(route);roadfaces.append((2*i,2*n,2*n+1,2*i+1))
    road=mesh('Lakeside_Road',roadv,roadfaces,asphalt)
    uv=road.data.uv_layers.new(name='UVMap')
    for poly in road.data.polygons:
        i=poly.index
        for k,li in enumerate(poly.loop_indices):
            uv.data[li].uv=([(0,lengths[i]/5),(0,(lengths[i]+5)/5),(1,(lengths[i]+5)/5),(1,lengths[i]/5)])[k]
    paint=material('MAT_Road_Marking',(.83,.79,.60),.8)
    markv=[];markf=[]
    for i,p in enumerate(route):
        if i%2:continue
        n=(i+1)%len(route);a=route[i];b=route[n];s=normals[i]*.055
        start=len(markv);markv.extend([(a[0]-s[0],a[1]-s[1],a[2]+.025),(b[0]-s[0],b[1]-s[1],b[2]+.025),
                                      (b[0]+s[0],b[1]+s[1],b[2]+.025),(a[0]+s[0],a[1]+s[1],a[2]+.025)])
        markf.append(tuple(range(start,start+4)))
    marks=mesh('Center_Lines',markv,markf,paint)
    export('road.glb',[road,marks])

    # Capture a genuine original high-detail spruce as a cheap distant impostor.
    for obj in terrain_objects+[road,marks]:obj.hide_render=True
    spruce.hide_render=False;spruce.hide_viewport=False;spruce.location=(0,0,0)
    bpy.context.view_layer.update()
    current_height=spruce.dimensions.z
    spruce.scale*=16/current_height
    bpy.context.view_layer.update()
    bounds=[spruce.matrix_world@Vector(v) for v in spruce.bound_box]
    spruce.location.z-=min(v.z for v in bounds)
    bpy.context.view_layer.update()
    scene.use_nodes=False
    scene.render.use_compositing=False
    bpy.ops.object.light_add(type='SUN',location=(8,-8,20));sun=bpy.context.object
    sun.rotation_euler=(.4,-.5,-.4);sun.data.energy=2.2
    bpy.ops.object.camera_add(location=(0,-28,8));camera=bpy.context.object
    camera.rotation_euler=(math.pi/2,0,0);camera.data.type='ORTHO';camera.data.ortho_scale=17.2;scene.camera=camera
    scene.render.resolution_x=512;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.cycles.samples=16
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.render.filepath=str(OUT/'spruce_impostor.png')
    bpy.ops.render.render(write_still=True)
    with Image.open(OUT/'spruce_impostor.png') as proof_image:
        assert proof_image.getchannel('A').getbbox() is not None,'Tree impostor is empty'
    for obj in [spruce,sun,camera]:bpy.data.objects.remove(obj,do_unlink=True)

    # Original, non-branded vehicle. Geometry is authored in Blender, not runtime boxes.
    body_mat=material('MAT_Champagne_Paint',(.40,.35,.24),.25,.48)
    rubber=material('MAT_Rubber',(.018,.022,.025),.86)
    glass=material('MAT_Glass',(.025,.07,.085),.12,.42)
    alloy=material('MAT_Alloy',(.38,.42,.43),.24,.8)
    lamp=material('MAT_Lamp',(.84,.81,.65),.22)
    tail=material('MAT_Tail',(.48,.025,.012),.3)
    body=[cube('Body',(0,0,.72),(1.84,4.25,.58),body_mat,.16),
          cube('Hood',(0,1.15,1.02),(1.74,1.45,.21),body_mat,.08),
          cube('Roof',(0,-.27,1.57),(1.37,1.65,.10),body_mat,.07)]
    cabinverts=[(-.85,-1.35,1.0),(.85,-1.35,1.0),(.85,.72,1.0),(-.85,.72,1.0),
                (-.67,-1.05,1.53),(.67,-1.05,1.53),(.67,.38,1.53),(-.67,.38,1.53)]
    body.append(mesh('Cabin',cabinverts,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],glass))
    for x in [-.89,.89]:
        body.append(cube('Door_Trim',(x,-.15,.91),(.04,2.0,.06),rubber,.012))
        body.append(cube('Window_Pillar',(x*.83,-.25,1.32),(.04,.10,.5),body_mat,.01))
        body.append(cube('Mirror',(x*1.15,.42,1.18),(.22,.23,.12),body_mat,.035))
        body.append(cube('Headlight',(x*.70,2.13,.87),(.39,.035,.15),lamp,.02))
        body.append(cube('Taillight',(x*.70,-2.13,.86),(.35,.035,.14),tail,.02))
    body.append(cube('Grille',(0,2.135,.62),(.95,.04,.18),rubber,.02))
    body.append(cube('Rear_Bumper',(0,-2.13,.53),(1.58,.12,.12),rubber,.035))
    body_obj=join(body,'Vehicle_Body')
    wheels=[]
    for label,x,y in [('FL',-.94,1.32),('FR',.94,1.32),('RL',-.94,-1.30),('RR',.94,-1.30)]:
        parts=[]
        for name,radius,depth,mat in [('Tyre',.38,.24,rubber),('Rim',.245,.255,alloy)]:
            bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=radius,depth=depth,
                location=(x,y,.39),rotation=(0,math.pi/2,0))
            o=bpy.context.object;o.name=name;o.data.materials.append(mat);parts.append(o)
            mod=o.modifiers.new('Rounded tyre shoulder','BEVEL');mod.width=.025;mod.segments=2
            bpy.ops.object.modifier_apply(modifier=mod.name)
        wheel=join(parts,'Wheel_'+label)
        scene.cursor.location=(x,y,.39);select([wheel]);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        wheels.append(wheel)
    scene.cursor.location=(0,0,0)
    export('vehicle.glb',[body_obj]+wheels)

    # A small articulated hiking character, with real skeleton and Walk/Idle clips.
    jacket=material('MAT_Jacket',(.055,.16,.16),.86)
    trousers=material('MAT_Trousers',(.24,.21,.16),.95)
    skin=material('MAT_Skin',(.49,.28,.17),.82)
    boot=material('MAT_Boot',(.035,.028,.025),.9)
    hair=material('MAT_Hair',(.035,.023,.016),.95)
    bones={
        'Root':((0,0,.88),(0,0,1.04),None),'Spine':((0,0,1.04),(0,0,1.45),'Root'),
        'Head':((0,0,1.45),(0,0,1.80),'Spine'),
        'Arm_L':((-.27,0,1.40),(-.33,0,1.12),'Spine'),'Forearm_L':((-.33,0,1.12),(-.34,-.015,.89),'Arm_L'),
        'Arm_R':((.27,0,1.40),(.33,0,1.12),'Spine'),'Forearm_R':((.33,0,1.12),(.34,-.015,.89),'Arm_R'),
        'Leg_L':((-.115,0,.92),(-.115,0,.49),'Root'),'Shin_L':((-.115,0,.49),(-.115,0,.11),'Leg_L'),
        'Leg_R':((.115,0,.92),(.115,0,.49),'Root'),'Shin_R':((.115,0,.49),(.115,0,.11),'Leg_R')}
    parts=[]
    def weighted(obj,bone):
        group=obj.vertex_groups.new(name=bone);group.add(list(range(len(obj.data.vertices))),1,'REPLACE');parts.append(obj)
    weighted(cube('Torso',(0,0,1.225),(.45,.28,.47),jacket,.08),'Spine')
    weighted(cube('Hip',(0,0,.94),(.30,.25,.17),trousers,.045),'Root')
    weighted(cube('Backpack',(0,-.21,1.24),(.32,.19,.38),trousers,.07),'Spine')
    weighted(sphere('Head',(0,.015,1.665),(.128,.12,.16),skin),'Head')
    weighted(sphere('Hair',(0,-.008,1.745),(.131,.121,.09),hair),'Head')
    weighted(sphere('Nose',(0,.135,1.66),(.03,.035,.037),skin),'Head')
    for side,x in [('L',-.115),('R',.115)]:
        weighted(cube('UpperLeg'+side,(x,0,.71),(.16,.20,.42),trousers,.05),'Leg_'+side)
        weighted(cube('Shin'+side,(x,0,.30),(.135,.16,.38),trousers,.04),'Shin_'+side)
        weighted(cube('Boot'+side,(x,.045,.085),(.17,.29,.16),boot,.035),'Shin_'+side)
    for side,x in [('L',-.31),('R',.31)]:
        weighted(cube('UpperArm'+side,(x,0,1.27),(.15,.18,.29),jacket,.05),'Arm_'+side)
        weighted(cube('Forearm'+side,(x*1.07,0,1.02),(.12,.14,.23),jacket,.04),'Forearm_'+side)
        weighted(sphere('Hand'+side,(x*1.08,0,.87),(.065,.055,.08),skin),'Forearm_'+side)
    person=join(parts,'Hiker_Mesh')
    data=bpy.data.armatures.new('Hiker_Skeleton');rig=bpy.data.objects.new('Hiker',data);scene.collection.objects.link(rig)
    select([rig]);bpy.ops.object.mode_set(mode='EDIT')
    for name,(head,tail,parent) in bones.items():
        bone=data.edit_bones.new(name);bone.head=head;bone.tail=tail
        if parent:bone.parent=data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    mod=person.modifiers.new('Armature','ARMATURE');mod.object=rig;person.parent=rig
    scene.render.fps=30
    rig.animation_data_create()
    for clip in ['Idle','Walk']:
        action=bpy.data.actions.new(clip);rig.animation_data.action=action
        for frame in range(1,32,5):
            phase=(frame-1)/30*math.tau
            for name in bones:
                bone=rig.pose.bones[name];bone.rotation_mode='XYZ';bone.rotation_euler=(0,0,0)
                if clip=='Walk':
                    sign=-1 if name.endswith('_L') else 1
                    if name.startswith('Leg_'):bone.rotation_euler.x=math.sin(phase)*.52*sign
                    if name.startswith('Arm_'):bone.rotation_euler.x=-math.sin(phase)*.40*sign
                    if name.startswith('Shin_'):bone.rotation_euler.x=max(0,-math.sin(phase)*sign)*.65
                elif name=='Head':bone.rotation_euler.z=math.sin(phase)*.025
                bone.keyframe_insert('rotation_euler',frame=frame)
        action.use_fake_user=True
        track=rig.animation_data.nla_tracks.new();track.name=clip;track.strips.new(clip,1,action)
    rig.animation_data.action=None
    export('hiker.glb',[rig,person],export_animations=True,export_animation_mode='NLA_TRACKS')
    with Image.open(ROOT/'assets/partly_cloudy_morning_4k.jpg') as image:
        image.resize((2048,1024),Image.Resampling.LANCZOS).save(OUT/'sky.jpg',quality=88)
    positions=[]
    for (x,y,z),h in original_trees:
        if len(positions)>1550:break
        k=int(np.argmin(np.sum((route2-np.array([x,y]))**2,axis=1)))
        if float(np.linalg.norm(route2[k]-[x,y]))<10:continue
        if z<.2:continue
        positions.append([round(x,3),round(z,3),round(-y,3),round(h,3)])
    godot_route=[[round(p[0],4),round(p[2],4),round(-p[1],4)] for p in route]
    (OUT/'world_data.json').write_text(json.dumps({'route':godot_route,'forest':positions,
        'lake_bounds':[-160,160,-365,95],'source_blend_sha256':source_hash},separators=(',',':'))+'\n')
    report={'source':'output/Alpine_Mirror.blend','source_sha256':source_hash,
        'original_unique_polygons':2224092,'terrain_triangles':sum(len(o.data.polygons)*2 for o in terrain_objects),
        'terrain_method':'Retessellated native heightfields; preserves original eroded vertices sampled on fixed grids',
        'textures':'Cycles CPU-baked original mountain/ground albedo and tangent normals, 1024 square each',
        'forest':'Original native tree placements, filtered along new road; CPU-rendered original spruce impostor',
        'forest_instances':len(positions),'route_samples':len(route),'route_meters':round(lengths[-1],2),
        'vehicle':'Original Blender mesh; no brands; separate wheel origins',
        'character':'Original Blender mesh and 11-bone skeleton; exported Idle and Walk NLA clips',
        'shutdown_workaround':'Validated short-lived authoring process exits explicitly; native embedded-bpy finalization issue remains unresolved',
        'files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                 for p in OUT.iterdir() if p.is_file() and p.name in {'terrain.glb','road.glb','vehicle.glb','hiker.glb','sky.jpg','spruce_impostor.png','world_data.json','Alpine_Ground_albedo.png','Alpine_Ground_normal.png','Alpine_Massif_albedo.png','Alpine_Massif_normal.png','asphalt.png'}}}
    (OUT/'asset_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    assert all((OUT/f).stat().st_size>1000 for f in ['terrain.glb','road.glb','vehicle.glb','hiker.glb','spruce_impostor.png'])
    assert source_hash==hashlib.sha256(source.read_bytes()).hexdigest(),'Original production source changed!'
    print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2),flush=True)


if __name__=='__main__':
    if '--worker' in sys.argv:
        build()
        # See audit report: avoid unresolved native cleanup SIGSEGV only AFTER
        # successful output validation; this never catches or masks exceptions.
        sys.stdout.flush();sys.stderr.flush();os._exit(0)
    else:
        sys.path.insert(0,str(ROOT/'tools'))
        from audit_software_graphics import software_environment
        env=software_environment();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='2')
        subprocess.run([sys.executable,__file__,'--worker'],env=env,check=True)
