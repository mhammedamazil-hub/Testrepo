"""Isolated bpy realism pass: curved vehicle, native spruce, roadside assets,
metre-scale detail maps and a static reflection panorama of the actual terrain.
Does not change the original cinematic or first-pass asset manifest.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'game/assets'


def build():
    import bpy
    import numpy as np
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from PIL import Image, ImageFilter
    source = ROOT/'output/Alpine_Mirror.blend'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    rng = np.random.default_rng(61027)

    def material(name, color, rough=.8, metal=0):
        mat=bpy.data.materials.new(name);mat.use_nodes=True
        bsdf=mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value=(*color,1)
        bsdf.inputs['Roughness'].default_value=rough
        bsdf.inputs['Metallic'].default_value=metal
        return mat

    def select(objects):
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects: obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]

    def mesh(name, verts, faces, mat, smooth=False):
        data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
        data.materials.append(mat)
        for p in data.polygons:p.use_smooth=smooth
        return obj

    def cube(name, loc, scale, mat, bevel=.02):
        bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
        obj=bpy.context.object;obj.name=name;obj.dimensions=scale
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        obj.data.materials.append(mat)
        if bevel:
            mod=obj.modifiers.new('Stamped edge radius','BEVEL');mod.width=bevel;mod.segments=3
            bpy.ops.object.modifier_apply(modifier=mod.name)
            mod=obj.modifiers.new('Panel normals','WEIGHTED_NORMAL')
            bpy.ops.object.modifier_apply(modifier=mod.name)
        return obj

    def line(name, points, radius, mat):
        curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D'
        curve.bevel_depth=radius;curve.bevel_resolution=2
        spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
        for p,co in zip(spline.points,points):p.co=(*co,1)
        obj=bpy.data.objects.new(name,curve);scene.collection.objects.link(obj)
        curve.materials.append(mat)
        select([obj]);bpy.ops.object.convert(target='MESH')
        return bpy.context.object

    def export(name, objects):
        for obj in objects:
            if obj.type=='MESH':
                select([obj]);mod=obj.modifiers.new('Export triangles','TRIANGULATE')
                bpy.ops.object.modifier_apply(modifier=mod.name)
        select(objects)
        bpy.ops.export_scene.gltf(filepath=str(OUT/name),export_format='GLB',use_selection=True,export_tangents=True)
        return sum(len(o.data.polygons) for o in objects if o.type=='MESH')

    # Neutral, tileable multi-scale surface data, with explicitly non-color normals.
    noise=np.zeros((512,512),dtype=np.float32)
    for size,weight in [(8,.27),(32,.23),(128,.23),(512,.27)]:
        layer=Image.fromarray(rng.integers(0,256,(size,size),dtype=np.uint8))
        noise+=np.asarray(layer.resize((512,512),Image.Resampling.BICUBIC),dtype=np.float32)/255*weight
    # Enforce periodic borders for repeatable world-space sampling.
    noise[-1,:]=noise[0,:];noise[:,-1]=noise[:,0]
    color=np.stack([noise*.67+.19,noise*.64+.20,noise*.53+.17],axis=-1)
    Image.fromarray(np.uint8(np.clip(color,0,1)*255)).save(OUT/'ground_detail.png')
    dx=(np.roll(noise,-1,1)-np.roll(noise,1,1))*1.6
    dy=(np.roll(noise,-1,0)-np.roll(noise,1,0))*1.6
    normals=np.stack([-dx,-dy,np.ones_like(dx)],axis=-1)
    normals/=np.linalg.norm(normals,axis=-1,keepdims=True)
    Image.fromarray(np.uint8((normals*.5+.5)*255)).save(OUT/'ground_detail_normal.png')

    paint=material('Touring_Deep_Petrol_Metallic',(.055,.17,.205),.24,.64)
    paint.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=.35
    rubber=material('Tire_Rubber',(.014,.018,.019),.9)
    trim=material('Satin_Trim',(.025,.031,.033),.45)
    glass=material('Tinted_Glass',(.018,.037,.045),.115,0)
    alloy=material('Machined_Alloy',(.42,.45,.46),.23,.86)
    lamp=material('Headlamp_Lens',(.72,.79,.82),.16)
    tail=material('Tail_Light_Lens',(.42,.012,.009),.23)
    parts=[]
    # Watertight loft with real wheel-arch cutouts rather than stacked boxes.
    sections=[(-2.16,.72,.84),(-2.0,.87,1.01),(-1.5,.93,1.08),(-.7,.94,1.09),(.45,.94,1.03),(1.3,.91,.97),(1.97,.84,.85),(2.15,.70,.76)]
    verts=[]
    for y,w,z in sections:
        profile=[(0,.40),(.82*w,.42),(w,.58),(w,.81*z),(.94*w,z),(.64*w,z+.035),(0,z+.04)]
        profile+= [(-x,h) for x,h in reversed(profile[1:-1])]
        verts.extend((x,y,h) for x,h in profile)
    n=len(verts)//len(sections)
    faces=[tuple(reversed(range(n))),tuple((len(sections)-1)*n+k for k in range(n))]
    faces.extend((i*n+k,i*n+(k+1)%n,(i+1)*n+(k+1)%n,(i+1)*n+k) for i in range(len(sections)-1) for k in range(n))
    shell=mesh('Touring_Body',verts,faces,paint,True)
    select([shell]);mod=shell.modifiers.new('Pressed panel rounding','BEVEL');mod.width=.045;mod.segments=3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for y in [-1.35,1.35]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=40,radius=.445,depth=3,location=(0,y,.39),rotation=(0,math.pi/2,0))
        cutter=bpy.context.object
        select([shell]);mod=shell.modifiers.new('Wheel arch','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
        bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    parts.append(shell)
    cabin=[(-.84,-1.72,1.04),(.84,-1.72,1.04),(.83,.96,1.02),(-.83,.96,1.02),
           (-.65,-1.20,1.56),(.65,-1.20,1.56),(.65,.32,1.56),(-.65,.32,1.56)]
    parts.append(mesh('Cabin_Frame',cabin,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],paint))
    parts.append(mesh('Windshield',[(-.765,.95,1.09),(.765,.95,1.09),(.608,.333,1.515),(-.608,.333,1.515)],[(0,1,2,3)],glass))
    parts.append(mesh('Rear_Glass',[(.768,-1.725,1.12),(-.768,-1.725,1.12),(-.604,-1.21,1.515),(.604,-1.21,1.515)],[(0,1,2,3)],glass))
    for x in [-1,1]:
        for label,ys in [('Rear',(-1.59,-.42,-1.14,-.42)),('Front',(-.34,.83,-.34,.27))]:
            a,b,c,d=ys
            parts.append(mesh(label+'_Side_Window',[(x*.843,a,1.13),(x*.843,b,1.10),(x*.656,d,1.515),(x*.656,c,1.515)],[(0,1,2,3)],glass))
        parts.append(cube('Sill',(x*.91,0,.48),(.055,2.0,.11),trim))
        parts.append(cube('Mirror',(x*1.04,.48,1.16),(.22,.29,.14),paint,.055))
        parts.append(cube('Mirror_Lens',(x*1.045,.325,1.16),(.16,.012,.09),alloy,.01))
        for y in [-.80,.30]:parts.append(cube('Door_Handle',(x*.94,y,1.005),(.025,.17,.035),alloy,.01))
        parts.append(line('Door_Panel_Gap',[(x*.945,-.37,.53),(x*.949,-.37,.84),(x*.89,-.37,1.055)],.006,trim))
        parts.append(line('Roof_Rail',[(x*.61,-1.05,1.61),(x*.61,.20,1.61)],.019,alloy))
        parts.append(cube('Headlamp_Housing',(x*.55,2.09,.80),(.47,.07,.13),trim,.035))
        parts.append(cube('LED_Strip',(x*.55,2.132,.82),(.40,.014,.026),lamp,.01))
        parts.append(cube('Tail_Lamp',(x*.57,-2.079,.88),(.38,.055,.095),tail,.025))
    parts.append(cube('Front_Intake',(0,2.115,.60),(.78,.04,.14),trim,.04))
    parts.append(cube('Rear_Bumper',(0,-2.12,.55),(1.5,.10,.12),trim,.04))
    parts.append(cube('Rear_Number_Plate',(0,-2.173,.77),(.40,.012,.09),alloy,.005))
    for y in [-1.35,1.35]:
        for x in [-.91,.91]:
            group=[]
            bpy.ops.mesh.primitive_torus_add(major_segments=40,minor_segments=10,major_radius=.285,minor_radius=.095,location=(x,y,.39),rotation=(0,math.pi/2,0))
            tire=bpy.context.object;tire.data.materials.append(rubber);group.append(tire)
            for p in tire.data.polygons:p.use_smooth=True
            bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.225,depth=.19,location=(x,y,.39),rotation=(0,math.pi/2,0))
            rim=bpy.context.object;rim.data.materials.append(trim);group.append(rim)
            for angle in range(5):
                a=angle*math.tau/5
                spoke=cube('Spoke',(x+math.copysign(.106,x),y+math.sin(a)*.115,.39+math.cos(a)*.115),(.025,.035,.22),alloy,.009)
                spoke.rotation_euler.x=-a;group.append(spoke)
            bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.063,depth=.235,location=(x,y,.39),rotation=(0,math.pi/2,0))
            hub=bpy.context.object;hub.data.materials.append(alloy);group.append(hub)
            select(group);bpy.ops.object.join();wheel=bpy.context.object
            wheel.name='Wheel_'+('F' if y>0 else 'R')+('L' if x<0 else 'R')
            scene.cursor.location=(x,y,.39);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
            parts.append(wheel)
    # One body mesh with material surfaces, plus four wheel pivots. Do not turn
    # every trim component into another runtime draw/scene-node submission.
    wheels=[o for o in parts if o.name.startswith('Wheel_')]
    panels=[o for o in parts if o not in wheels]
    select(panels);bpy.ops.object.join();body=bpy.context.object;body.name='Touring_Body'
    vehicle_triangles=export('touring_car.glb',[body,*wheels])
    for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)

    # Bake a genuine needle shoot into a transparent atlas. Branch cards keep
    # fine silhouettes without the opaque diamond clumps of the first LOD.
    shootmats=[material('ShootBake'+str(i),c,.82) for i,c in enumerate([(.04,.10,.038),(.075,.16,.055),(.11,.20,.07)])]
    nv=[];nf=[];ni=[]
    localrng=np.random.default_rng(706)
    for step in range(1,9):
        c=Vector((step/9,0,-step/90))
        for sign in [-1,1]:
            end=c+Vector((.10,.29*(1-step/13)*sign,.015))
            axis=(end-c).normalized();u=Vector((0,0,1));v=axis.cross(u)
            for tuft in range(7):
                center=c.lerp(end,(tuft+.5)/7)
                for q in range(18):
                    angle=q*2.399963+float(localrng.uniform(-.2,.2))
                    direction=(axis*.35+u*math.cos(angle)+v*math.sin(angle)).normalized()
                    length=float(localrng.uniform(.047,.105));width=.0065
                    tangent=direction.cross(axis).normalized()
                    k=len(nv)
                    nv.extend([tuple(center-tangent*width),tuple(center+direction*length),tuple(center+tangent*width)])
                    nf.append((k,k+1,k+2));ni.append(int(localrng.integers(0,3)))
    shoot=mesh('Needle_Shoot_Capture',nv,nf,shootmats[0],True)
    for mat in shootmats[1:]:shoot.data.materials.append(mat)
    for poly,mi in zip(shoot.data.polygons,ni):poly.material_index=mi
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16
    scene.cycles.max_bounces=2;scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.world=bpy.data.worlds.new('Shoot Capture');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.7,.8,.9,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
    bpy.ops.object.light_add(type='SUN');light=bpy.context.object;light.rotation_euler=(.35,-.4,-.5);light.data.energy=1.8
    bpy.ops.object.camera_add(location=(.57,0,3));capture=bpy.context.object
    capture.data.type='ORTHO';capture.data.ortho_scale=1.35;scene.camera=capture
    scene.render.resolution_x=512;scene.render.resolution_y=256;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.view_settings.view_transform='Standard'
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.render.filepath=str(OUT/'spruce_shoot.png');bpy.ops.render.render(write_still=True)
    with Image.open(OUT/'spruce_shoot.png') as proof:assert proof.getchannel('A').getbbox() is not None
    for obj in [shoot,light,capture]:bpy.data.objects.remove(obj,do_unlink=True)
    bark=material('Spruce_Bark_LOD',(.15,.085,.04),.94)
    leaves=material('Spruce_Needle_Cards',(.12,.2,.07),.9)
    image=bpy.data.images.load(str(OUT/'spruce_shoot.png'))
    tex=leaves.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
    leaves.node_tree.links.new(tex.outputs['Color'],leaves.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    leaves.node_tree.links.new(tex.outputs['Alpha'],leaves.node_tree.nodes['Principled BSDF'].inputs['Alpha'])
    leaves.surface_render_method='DITHERED'
    tree_parts=[]
    bpy.ops.mesh.primitive_cone_add(vertices=8,radius1=.015,radius2=.001,depth=1,location=(0,0,.5))
    trunk=bpy.context.object;trunk.data.materials.append(bark);tree_parts.append(trunk)
    cv=[];cf=[]
    for branch in range(64):
        z=.12+branch/64*.86;angle=branch*2.399963+float(localrng.uniform(-.2,.2))
        direction=Vector((math.cos(angle),math.sin(angle),-.10)).normalized()
        side=Vector((-math.sin(angle),math.cos(angle),0))
        length=.245*(1-z)**.8*float(localrng.uniform(.82,1.17))
        root=Vector((0,0,z))
        for roll in [0,math.pi/3,2*math.pi/3]:
            across=side*math.cos(roll)+Vector((0,0,math.sin(roll)))
            width=length*.35;k=len(cv)
            cv.extend([tuple(root-across*width),tuple(root+direction*length-across*width),tuple(root+direction*length+across*width),tuple(root+across*width)])
            cf.append((k,k+1,k+2,k+3))
    cards=mesh('Spatial_Needle_Shoots',cv,cf,leaves)
    uv=cards.data.uv_layers.new(name='UVMap')
    for poly in cards.data.polygons:
        for li,coord in zip(poly.loop_indices,[(0,0),(1,0),(1,1),(0,1)]):uv.data[li].uv=coord
    tree_parts.append(cards)
    select(tree_parts);bpy.ops.object.join();tree=bpy.context.object;tree.name='Roadside_Spruce'
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    tree_triangles=export('spruce_near.glb',[tree]);bpy.data.objects.remove(tree,do_unlink=True)

    rockmat=material('Weathered_Granite',(.31,.32,.29),.96)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1)
    rock=bpy.context.object;rock.name='Granite'
    for vertex in rock.data.vertices:
        vertex.co*=float(rng.uniform(.80,1.13));vertex.co.z*=.62
    rock.data.materials.append(rockmat)
    rock_triangles=export('granite.glb',[rock]);bpy.data.objects.remove(rock,do_unlink=True)
    grassmat=material('Alpine_Grass',(.19,.24,.085),.98)
    vertices=[];faces=[]
    for blade in range(15):
        a=float(rng.uniform(0,math.tau));x,y=rng.uniform(-.17,.17,2);h=float(rng.uniform(.16,.46));w=.014
        lean=np.array([math.sin(a),math.cos(a)])*.1
        k=len(vertices)
        vertices.extend([(x-w,y,0),(x+w,y,0),(x+w*.6+lean[0]*.5,y+lean[1]*.5,h*.55),(x-w*.6+lean[0]*.5,y+lean[1]*.5,h*.55),(x+lean[0],y+lean[1],h)])
        faces.extend([(k,k+1,k+2,k+3),(k+3,k+2,k+4)])
    grass=mesh('Meadow_Tuft',vertices,faces,grassmat,True)
    grass_triangles=export('meadow_tuft.glb',[grass]);bpy.data.objects.remove(grass,do_unlink=True)

    bpy.ops.import_scene.gltf(filepath=str(OUT/'terrain.glb'))
    ground=next(o for o in bpy.data.objects if o.type=='MESH' and 'Alpine_Ground' in o.name)
    bvh=BVHTree.FromObject(ground,bpy.context.evaluated_depsgraph_get())
    data=json.loads((OUT/'world_data.json').read_text());route=np.array(data['route'])
    placements={'grass':[],'rocks':[]}
    for i,p in enumerate(route):
        tangent=route[(i+1)%len(route)]-route[(i-1)%len(route)]
        side=np.array([-tangent[2],0,tangent[0]]);side/=np.linalg.norm(side)
        for j in range(7):
            offset=float(rng.uniform(4.1,11.5))*(-1 if j%2 else 1)
            position=p+side*offset
            x,y=float(position[0]),float(-position[2])
            hit,normal,_,_=bvh.ray_cast(Vector((x,y,150)),Vector((0,0,-1)),300)
            if hit is None or hit.z<.25:continue
            entry=[round(x,3),round(hit.z-.04,3),round(-y,3),round(float(rng.uniform(.7,1.4)),3),round(float(rng.uniform(0,math.tau)),3)]
            placements['grass'].append(entry)
            if j==0 and i%2==0:
                entry=entry.copy();entry[3]=round(float(rng.uniform(.3,.85)),3);entry[1]-=.12
                placements['rocks'].append(entry)
    (OUT/'world_data_detail.json').write_text(json.dumps(placements,separators=(',',':'))+'\n')
    # Static, viewpoint-dependent approximation: capture the actual game terrain
    # and photographic sky from lake centre, NOT a claim of real-time reflection.
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12
    scene.cycles.max_bounces=2;scene.render.threads_mode='FIXED';scene.render.threads=2
    world=bpy.data.worlds.new('Alpine Reflection Capture');world.use_nodes=True;scene.world=world
    nodes=world.node_tree.nodes;links=world.node_tree.links
    env=nodes.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(OUT/'sky.jpg'))
    links.new(env.outputs['Color'],nodes['Background'].inputs['Color']);nodes['Background'].inputs['Strength'].default_value=.8
    bpy.ops.object.light_add(type='SUN');sun=bpy.context.object;sun.rotation_euler=(.65,-.25,-.55);sun.data.energy=2
    bpy.ops.object.camera_add(location=(0,135,1.5),rotation=(math.pi/2,0,0))
    camera=bpy.context.object;camera.data.type='PANO'
    if hasattr(camera.data,'panorama_type'):camera.data.panorama_type='EQUIRECTANGULAR'
    else:camera.data.cycles.panorama_type='EQUIRECTANGULAR'
    scene.camera=camera
    scene.render.resolution_x=1024;scene.render.resolution_y=512;scene.render.resolution_percentage=100
    scene.render.film_transparent=False;scene.view_settings.view_transform='AgX'
    scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=91
    scene.render.filepath=str(OUT/'lake_reflection.jpg')
    bpy.ops.render.render(write_still=True)
    names=['touring_car.glb','spruce_near.glb','spruce_shoot.png','granite.glb','meadow_tuft.glb','ground_detail.png','ground_detail_normal.png','world_data_detail.json','lake_reflection.jpg']
    report={'source_blend_sha256':source_hash,'vehicle_triangles':vehicle_triangles,'near_spruce_triangles':tree_triangles,'granite_triangles':rock_triangles,'tuft_triangles':grass_triangles,
            'placements':{k:len(v) for k,v in placements.items()},'reflection':'Static Cycles CPU panorama of actual game terrain at lake centre; not real-time or viewpoint-correct everywhere',
            'files':{name:{'bytes':(OUT/name).stat().st_size,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()} for name in names}}
    assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
    (OUT/'detail_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    if '--worker' in sys.argv:
        build();sys.stdout.flush();sys.stderr.flush();os._exit(0)
    else:
        sys.path.insert(0,str(ROOT/'tools'))
        from audit_software_graphics import software_environment
        env=software_environment();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='2')
        subprocess.run([sys.executable,__file__,'--worker'],env=env,check=True)
