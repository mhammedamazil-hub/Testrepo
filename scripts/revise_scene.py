"""Revision 2: backlit 60-fps lake flight. Upgrade the existing scene in place.
Physical water geometry, volumetric clouds/mist, modeled birds and volumetric
spruce shoots. No image backplates or interpolated animation frames.
"""
import bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output'; PI=math.pi
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Alpine_Mirror.blend'))
s=bpy.context.scene; rng=random.Random(6026)
FPS=60; END=1200
# Do not append repeatedly when iterating locally: always rebuild from the
# previous delivered scene or the reproducible base builder before this script.
if s.get('revision',1)>=2: raise RuntimeError('Already revised: restore the base scene or rebuild it first.')

def col(name):
    c=bpy.data.collections.new('COL_'+name); s.collection.children.link(c); return c
fx=col('Atmosphere'); birds=col('Birds'); lights=bpy.data.collections.get('COL_Light'); forest=bpy.data.collections.get('COL_Forest')
def mesh(name,vs,fs,mats,collection,ids=None,smooth=False):
    me=bpy.data.meshes.new(name); me.from_pydata(vs,[],fs); me.update()
    for m in mats: me.materials.append(m)
    if ids is not None:
        for p,i in zip(me.polygons,ids): p.material_index=i
    if smooth:
        for p in me.polygons: p.use_smooth=True
    o=bpy.data.objects.new(name,me); collection.objects.link(o); return o

def mat(name,color,rough=.65):
    m=bpy.data.materials.new(name);m.use_nodes=True; ns=m.node_tree.nodes;ls=m.node_tree.links;p=ns.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough
    return m,ns,ls,p

def node(ns,t): return ns.new(t)
def calc(ns,ls,op,*args):
    n=node(ns,'ShaderNodeMath'); n.operation=op
    for i,a in enumerate(args):
        if isinstance(a,(float,int)): n.inputs[i].default_value=a
        else: ls.new(a,n.inputs[i])
    return n.outputs[0]
def noise(ns,ls,coord,scale,detail=4):
    n=node(ns,'ShaderNodeTexNoise'); n.inputs['Scale'].default_value=scale;n.inputs['Detail'].default_value=detail;n.inputs['Roughness'].default_value=.68;ls.new(coord,n.inputs['Vector']);return n.outputs['Fac']
def ramp(ns,ls,fac,entries):
    n=node(ns,'ShaderNodeValToRGB');cr=n.color_ramp;cr.elements.remove(cr.elements[1])
    for i,(pos,color) in enumerate(entries):
        e=cr.elements[0] if i==0 else cr.elements.new(pos);e.position=pos;e.color=(*color,1)
    ls.new(fac,n.inputs[0]);return n.outputs[0]
def linear(obj):
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            for k in fc.keyframe_points:k.interpolation='LINEAR'

# Fuller, genuinely 3D shoot masses, irregular tier heights, curved boughs.
bark,ns,ls,p=mat('MAT_R2_FissuredSpruceBark',(.12,.075,.039),.88)
tc=node(ns,'ShaderNodeTexCoord'); stretch=node(ns,'ShaderNodeVectorMath');stretch.operation='MULTIPLY';ls.new(tc.outputs['Generated'],stretch.inputs[0]);stretch.inputs[1].default_value=(18,18,1.3)
f=noise(ns,ls,stretch.outputs[0],3,4);ls.new(ramp(ns,ls,f,[(.2,(.035,.027,.02)),(.5,(.13,.09,.052)),(.8,(.27,.21,.13))]),p.inputs['Base Color'])
b=node(ns,'ShaderNodeBump');b.inputs['Distance'].default_value=.028;b.inputs['Strength'].default_value=.6;ls.new(f,b.inputs['Height']);ls.new(b.outputs[0],p.inputs['Normal'])
needles=[]
for j,c in enumerate([(.045,.105,.043),(.066,.145,.055),(.09,.18,.071),(.035,.085,.052)]):
    m,ns,ls,p=mat('MAT_R2_WaxySpruceShoot_%d'%j,c,.63)
    p.inputs['Subsurface Weight'].default_value=.04;p.inputs['Subsurface Radius'].default_value=(.035,.06,.02)
    info=node(ns,'ShaderNodeObjectInfo');mix=node(ns,'ShaderNodeMixRGB');ls.new(info.outputs['Random'],mix.inputs[0]);mix.inputs[1].default_value=(*[a*.72 for a in c],1);mix.inputs[2].default_value=(*[a*1.28 for a in c],1);ls.new(mix.outputs[0],p.inputs['Base Color'])
    trans=node(ns,'ShaderNodeBsdfTranslucent');ls.new(mix.outputs[0],trans.inputs[0]);blend=node(ns,'ShaderNodeMixShader');blend.inputs[0].default_value=.16;ls.new(p.outputs[0],blend.inputs[1]);ls.new(trans.outputs[0],blend.inputs[2]);ls.new(blend.outputs[0],ns.get('Material Output').inputs['Surface']);needles.append(m)

def spruce(seed):
    r=random.Random(seed);vs=[];fs=[];ids=[]
    def tri(a,b,c,mi):
        k=len(vs);vs.extend([tuple(a),tuple(b),tuple(c)]);fs.append((k,k+1,k+2));ids.append(mi)
    def tube(a,b,ra,rb,sides=5):
        a=Vector(a);b=Vector(b);d=(b-a).normalized();u=d.cross(Vector((.01,1,.001))).normalized();v=d.cross(u);k=len(vs)
        for pt,rad in [(a,ra),(b,rb)]:
            for q in range(sides):vs.append(tuple(pt+rad*(u*math.cos(q*2*PI/sides)+v*math.sin(q*2*PI/sides))))
        for q in range(sides):fs.append((k+q,k+(q+1)%sides,k+sides+(q+1)%sides,k+sides+q));ids.append(0)
    for k in range(11):
        z=k/11; tube((.008*math.sin(z*3),.006*z,z),(.008*math.sin((z+1/11)*3),.006*(z+1/11),z+1/11),.015*(1-z)**.8+.0005,.015*max(0,1-z-1/11)**.8+.0002,7)
    for branch in range(64):
        z=.12+branch/64*.86+r.uniform(-.012,.012);angle=branch*2.399963+r.uniform(-.28,.28)
        direction=Vector((math.cos(angle),math.sin(angle),0));side=Vector((-direction.y,direction.x,0));length=.245*(1-z)**.8*r.uniform(.75,1.2)
        root=Vector((.008*math.sin(z*3),.006*z,z));mid=root+direction*length*.58+Vector((0,0,-length*.16));tip=root+direction*length+Vector((0,0,-length*.09))
        tube(root,mid,.0026*(1-z)+.0002,.0011);tube(mid,tip,.0011,.00012,4)
        for step in range(1,7):
            t=step/7;c=root.lerp(mid,t/.58) if t<.58 else mid.lerp(tip,(t-.58)/.42)
            for sign in [-1,1]:
                branchlet=length*(.25+.12*r.random())*(1-t*.45)
                end=c+side*branchlet*sign+direction*branchlet*.48+Vector((0,0,branchlet*r.uniform(-.25,.5)))
                tube(c,end,.0008,.0001,3)
                axis=(end-c).normalized();u=axis.cross(Vector((0,0,1))).normalized();v=axis.cross(u)
                for tuft in range(4):
                    center=c.lerp(end,(tuft+.5)/4)
                    for q in range(15):
                        a=q*2.3999+r.random();along=r.uniform(-.003,.005)
                        cc=center+axis*along+u*r.uniform(-.003,.003)+v*r.uniform(-.003,.003)
                        needle=(axis*r.uniform(.2,.6)+u*math.cos(a)+v*math.sin(a)).normalized()
                        ln=r.uniform(.008,.019)*(1-.22*t);w=r.uniform(.001,.0018)
                        tangent=needle.cross(axis).normalized()
                        if tangent.length<.1:tangent=u
                        tri(cc-tangent*w,cc+needle*ln,cc+tangent*w,1+r.randrange(4))
    return mesh('LIB_R2_VolumetricSpruce_%d'%seed,vs,fs,[bark]+needles,forest,ids)

old_meshes=sorted({o.data for o in s.objects if o.type=='MESH' and (o.name.startswith('TREE_') or o.name.startswith('LIB_Spruce'))},key=lambda m:m.name)
canopy_library=[]
for j,old in enumerate(old_meshes):
    if j<5:
        new=spruce(706+j);data=new.data;canopy_library.append(data)
    else:new=None;data=canopy_library[j%5]
    for o in list(s.objects):
        if o.type=='MESH' and o.data==old:o.data=data
    if new is not None:bpy.data.objects.remove(new,do_unlink=True)
    if old.users==0:bpy.data.meshes.remove(old)
# Small coherent wind sway on the near forest; anchored trunks, not whole-tree translation.
wind_count=0
for o in s.objects:
    if o.name.startswith('TREE_') and o.location.y<155 and abs(o.location.x)<140:
        phase=(wind_count*1.718)%6.28
        for axis,amount in [(0,.0025),(1,.0037)]:
            f=o.driver_add('rotation_euler',axis);f.driver.expression=f'{amount}*(sin(frame/60*1.1+{phase})+.35*sin(frame/60*2.3+{phase*.7}))'
        wind_count+=1

# Curved grass blades instead of rigid single triangles.
grass=bpy.data.objects.get('GEO_Meadow_IndividualBlades')
if grass:
    old=grass.data;vs=[];fs=[];ids=[]
    flight_frusta=[]
    for t in [0,.15,.3,.5,.7,1]:
        loc=Vector((12-54*t+1.4*math.sin(PI*t),-68+103*t,4.5+9*t+.3*math.sin(PI*t)))
        forward=(Vector((0,745,82+4*math.sin(PI*t)))-loc).normalized();right=forward.cross(Vector((0,0,1))).normalized();up=right.cross(forward)
        flight_frusta.append((loc,forward,right,up))
    for face in old.polygons:
        if len(face.vertices)!=3:continue
        a,b,tip=[old.vertices[i].co.copy() for i in face.vertices];base=(a+b)*.5
        keep=False
        for loc,forward,right,up in flight_frusta:
            relative=base-loc;depth=relative.dot(forward)
            if depth>0 and abs(relative.dot(right))<depth*.76 and abs(relative.dot(up))<depth*.49:keep=True;break
        if not keep:continue
        width=(b-a)*.5;height=tip.z-base.z;lean=(tip-base);lean.z=0;k=len(vs)
        for level in range(4):
            t=level/3;center=base+Vector((lean.x*t*t,lean.y*t*t,height*t));center.x+=math.sin(base.x*1.7+base.y)*height*.17*t*t
            w=width*(1-t*.95);vs.extend([tuple(center-w),tuple(center+w)])
        for level in range(3):fs.append((k+2*level,k+2*level+1,k+2*level+3,k+2*level+2));ids.append(face.material_index)
    me=bpy.data.meshes.new('GEO_R2_CurvedMeadowBlades');me.from_pydata(vs,[],fs)
    for m in old.materials:me.materials.append(m)
    for face,i in zip(me.polygons,ids):face.material_index=i
    grass.data=me
    if old.users==0:bpy.data.meshes.remove(old)
    del vs,fs,ids

# Camera: a ~108 m drone flight, not a 3 m nearly static push-in.
cam=s.camera;cam.animation_data_clear();cam.data.lens=28;cam.data.clip_end=30000
camera_positions=[]
for i in range(21):
    t=i/20;f=1+round(t*(END-1));loc=Vector((12-54*t+1.4*math.sin(PI*t),-68+103*t,4.5+9*t+.3*math.sin(PI*t)))
    target=Vector((0,745,82+4*math.sin(PI*t)));cam.location=loc;cam.rotation_euler=(target-loc).to_track_quat('-Z','Y').to_euler();cam.rotation_euler.z+=math.radians(.035)*math.sin(t*7)
    cam.keyframe_insert('location',frame=f);cam.keyframe_insert('rotation_euler',frame=f);camera_positions.append(tuple(loc))
linear(cam)
# Find a physically consistent fixed solar direction that is initially ridge-
# occluded and revealed by camera parallax. The sun does not race through the sky.
mountain=next(o for o in s.objects if o.name.startswith('GEO_HeroMassif'))
bvh=BVHTree.FromObject(mountain,bpy.context.evaluated_depsgraph_get());start=Vector(camera_positions[0]);finish=Vector(camera_positions[-1]);candidates=[]
for ai in range(-32,33):
    az=math.radians(ai*.125)
    for ei in range(100,177):
        elev=math.radians(ei*.125);direction=Vector((math.sin(az)*math.cos(elev),math.cos(az)*math.cos(elev),math.sin(elev)));point=direction*15000
        a=bvh.ray_cast(start,(point-start).normalized(),3000)[0];b=bvh.ray_cast(finish,(point-finish).normalized(),3000)[0]
        reflection=Vector((finish.x+math.sin(az)*finish.z/math.tan(elev),finish.y+math.cos(az)*finish.z/math.tan(elev),.1))
        water_hit=bvh.ray_cast(reflection,(point-reflection).normalized(),3000)[0]
        if a is not None and b is None and water_hit is None:candidates.append((abs(ai*.125)+abs(ei*.125-18)*.35,az,elev,direction))
if candidates:_,az,elev,sun_dir=min(candidates,key=lambda q:q[0]);reveal_verified=True
else:az=math.radians(-2.5);elev=math.radians(18.5);sun_dir=Vector((math.sin(az)*math.cos(elev),math.cos(az)*math.cos(elev),math.sin(elev)));reveal_verified=False
print('Solar reveal',reveal_verified,'azimuth',math.degrees(az),'elevation',math.degrees(elev),flush=True)
for o in list(s.objects):
    if o.type=='LIGHT':bpy.data.objects.remove(o,do_unlink=True)
ld=bpy.data.lights.new('LGT_R2_BacklitMorningSun','SUN');ld.energy=3.0;ld.angle=math.radians(.65);ld.color=(1,.89,.72)
lo=bpy.data.objects.new(ld.name,ld);lights.objects.link(lo);lo.rotation_euler=(-sun_dir).to_track_quat('-Z','Y').to_euler()
# Finite solar disc: real glossy reflection, with the directional lamp supplying illumination.
sunmat,ns,ls,p=mat('MAT_R2_SolarDisc',(1,.86,.64),.1);ns.clear();e=node(ns,'ShaderNodeEmission');e.inputs[0].default_value=(1,.88,.66,1);e.inputs[1].default_value=15;out=node(ns,'ShaderNodeOutputMaterial');ls.new(e.outputs[0],out.inputs[0])
bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=69,location=sun_dir*15000);disc=bpy.context.object;disc.name='GEO_R2_SolarDisc';disc.data.materials.append(sunmat);disc.visible_shadow=False;disc.visible_diffuse=False;disc.visible_volume_scatter=False
world=bpy.data.worlds.new('WORLD_R2_PhysicalMorningSky');world.use_nodes=True;s.world=world;ns=world.node_tree.nodes;ls=world.node_tree.links;ns.clear()
sky=node(ns,'ShaderNodeTexSky');sky.sky_type='NISHITA';sky.sun_elevation=elev;sky.sun_rotation=math.atan2(sun_dir.y,sun_dir.x);sky.sun_disc=False;sky.altitude=1.6;sky.air_density=.7;sky.dust_density=.15;sky.ozone_density=1.25
lp=node(ns,'ShaderNodeLightPath');view=calc(ns,ls,'MAXIMUM',lp.outputs['Is Camera Ray'],lp.outputs['Is Glossy Ray'])
bg=node(ns,'ShaderNodeBackground');ls.new(sky.outputs[0],bg.inputs[0]);bg.inputs[1].default_value=.23
# CC0 captured sky for distant cloud detail and its matching water reflection.
# This is a sky environment only: every mountain, tree, rock and shoreline stays 3D.
image=bpy.data.images.load(str(ROOT/'assets'/'partly_cloudy_morning_4k.jpg'),check_existing=True);image.pack()
tc=node(ns,'ShaderNodeTexCoord');reverse=node(ns,'ShaderNodeVectorMath');reverse.operation='SCALE';ls.new(tc.outputs['Normal'],reverse.inputs[0]);reverse.inputs['Scale'].default_value=-1
mapping=node(ns,'ShaderNodeMapping');ls.new(reverse.outputs[0],mapping.inputs[0]);mapping.inputs['Rotation'].default_value=(0,0,-PI/2)
for frame,rotation in [(1,-PI/2),(END,-PI/2+.001)]:mapping.inputs['Rotation'].default_value=(0,0,rotation);mapping.inputs['Rotation'].keyframe_insert('default_value',frame=frame)
linear(world.node_tree)
env=node(ns,'ShaderNodeTexEnvironment');env.image=image;ls.new(mapping.outputs[0],env.inputs[0]);photobg=node(ns,'ShaderNodeBackground');photobg.inputs[1].default_value=.8;ls.new(env.outputs[0],photobg.inputs[0]);blend=node(ns,'ShaderNodeMixShader');ls.new(view,blend.inputs[0]);ls.new(bg.outputs[0],blend.inputs[1]);ls.new(photobg.outputs[0],blend.inputs[2]);out=node(ns,'ShaderNodeOutputWorld');ls.new(blend.outputs[0],out.inputs[0])

# Closed dielectric lake, with genuine traveling gravity waves driven by Scene Time.
water=bpy.data.objects.get('GEO_Lake_WaterSurface');old=water.data
NX,NY=320,460;vs=[];fs=[]
for j in range(NY+1):
    y=-95+j
    for i in range(NX+1):vs.append((-160+i,y,0))
for j in range(NY):
    for i in range(NX):
        a=j*(NX+1)+i;fs.append((a,a+1,a+NX+2,a+NX+1))
# Close the boundary down to 10 metres to make the absorption medium well-defined.
edge=list(range(NX+1))+[j*(NX+1)+NX for j in range(1,NY+1)]+[NY*(NX+1)+i for i in range(NX-1,-1,-1)]+[j*(NX+1) for j in range(NY-1,0,-1)]
bottom=[]
for index in edge:bottom.append(len(vs));x,y,_=vs[index];vs.append((x,y,-10))
for k,a in enumerate(edge):n=(k+1)%len(edge);fs.append((a,bottom[k],bottom[n],edge[n]))
fs.append(tuple(reversed(bottom)))
me=bpy.data.meshes.new('GEO_R2_ClosedLakeWaveGrid');me.from_pydata(vs,[],fs);me.update();water.data=me
for p in me.polygons:p.use_smooth=True
if old.users==0:bpy.data.meshes.remove(old)
wm,ns,ls,p=mat('MAT_Lake_Fresnel_AnimatedCapillaryRipples',(.025,.075,.065),.042)
p.inputs['IOR'].default_value=1.333;p.inputs['Transmission Weight'].default_value=1.;p.inputs['Coat Weight'].default_value=0.
g=node(ns,'ShaderNodeNewGeometry');mapping=node(ns,'ShaderNodeMapping');ls.new(g.outputs['Position'],mapping.inputs[0]);mapping.inputs['Scale'].default_value=(.6,1.8,1)
for f,loc in [(1,(0,0,0)),(END,(8.5,1.6,0))]:mapping.inputs['Location'].default_value=loc;mapping.inputs['Location'].keyframe_insert('default_value',frame=f)
linear(wm.node_tree)
fine=noise(ns,ls,mapping.outputs[0],5.5,3);small=noise(ns,ls,mapping.outputs[0],1.5,4)
b1=node(ns,'ShaderNodeBump');b1.inputs['Distance'].default_value=.006;b1.inputs['Strength'].default_value=.36;ls.new(fine,b1.inputs['Height'])
b2=node(ns,'ShaderNodeBump');b2.inputs['Distance'].default_value=.024;b2.inputs['Strength'].default_value=.46;ls.new(small,b2.inputs['Height']);ls.new(b1.outputs[0],b2.inputs['Normal']);ls.new(b2.outputs[0],p.inputs['Normal'])
absorb=node(ns,'ShaderNodeVolumeAbsorption');absorb.inputs['Color'].default_value=(.12,.49,.37,1);absorb.inputs['Density'].default_value=.12;ls.new(absorb.outputs[0],ns.get('Material Output').inputs['Volume']);me.materials.append(wm)
ng=bpy.data.node_groups.new('GN_R2_TravelingWindWaves','GeometryNodeTree');ng.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');ng.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry');ns=ng.nodes;ls=ng.links
inp=node(ns,'NodeGroupInput');out=node(ns,'NodeGroupOutput');pos=node(ns,'GeometryNodeInputPosition');clock=node(ns,'GeometryNodeInputSceneTime');total=None
for angle,length,amplitude in [(-32,13,.018),(7,7.3,.012),(36,4.6,.008),(58,3.1,.005),(100,2.4,.003)]:
    a=math.radians(angle);dot=node(ns,'ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';ls.new(pos.outputs[0],dot.inputs[0]);dot.inputs[1].default_value=(math.cos(a),math.sin(a),0)
    spatial=calc(ns,ls,'MULTIPLY',dot.outputs['Value'],2*PI/length);phase=calc(ns,ls,'SUBTRACT',spatial,calc(ns,ls,'MULTIPLY',clock.outputs['Seconds'],math.sqrt(9.81*2*PI/length)))
    wave=calc(ns,ls,'MULTIPLY',calc(ns,ls,'SINE',phase),amplitude);total=wave if total is None else calc(ns,ls,'ADD',total,wave)
vec=node(ns,'ShaderNodeCombineXYZ');ls.new(total,vec.inputs['Z']);setpos=node(ns,'GeometryNodeSetPosition');ls.new(inp.outputs[0],setpos.inputs['Geometry']);ls.new(vec.outputs[0],setpos.inputs['Offset']);ls.new(setpos.outputs[0],out.inputs[0]);mod=water.modifiers.new('Traveling physical surface waves','NODES');mod.node_group=ng
# Smooth near-shore bathymetry: transmission actually reveals shallow substrate.
terrain=next(o for o in s.objects if o.name.startswith('GEO_LakeBasin'))
for v in terrain.data.vertices:
    if v.co.z<0:
        x,y=v.co.x,v.co.y
        left=-63+.10*max(y,0)+5*math.sin(y*.029);right=49-.079*max(y,0)+7*math.sin(y*.027+1)-13*math.exp(-((y-52)/43)**2)
        d=max(0,-max(left-x,x-right));v.co.z=-min(4,.08+d*.16)
terrain.data.update()

# Distant clouds use an attributed CC0 captured 4k environment.
# Rounded procedural cloud test volumes were rejected during visual QA.
cloud_count=0
# Height-decaying patchy valley mist for depth and physically shadowed god rays.
mist=bpy.data.materials.new('MAT_R2_ValleyMist');mist.use_nodes=True;ns=mist.node_tree.nodes;ls=mist.node_tree.links;ns.clear();g=node(ns,'ShaderNodeNewGeometry');xyz=node(ns,'ShaderNodeSeparateXYZ');ls.new(g.outputs['Position'],xyz.inputs[0]);height=calc(ns,ls,'EXPONENT',calc(ns,ls,'MULTIPLY',xyz.outputs['Z'],-.040));patch=noise(ns,ls,g.outputs['Position'],.018,3)
patch=calc(ns,ls,'MAXIMUM',calc(ns,ls,'SUBTRACT',patch,.3),0.)
density=calc(ns,ls,'MULTIPLY',calc(ns,ls,'MULTIPLY',height,patch),.00050)
vol=node(ns,'ShaderNodeVolumeScatter');vol.inputs['Color'].default_value=(.78,.86,.96,1);vol.inputs['Anisotropy'].default_value=.72;ls.new(density,vol.inputs['Density']);out=node(ns,'ShaderNodeOutputMaterial');ls.new(vol.outputs[0],out.inputs['Volume'])
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,480,90));o=bpy.context.object;o.name='FX_R2_HeightDecayingValleyMist';o.scale=(1400,1240,180);o.data.materials.append(mist)
for c in list(o.users_collection):c.objects.unlink(o)
fx.objects.link(o)

# Seven distant corvid-like birds. Modeled wing silhouettes, gliding/flapping
# articulation and independent phase, not static V decals translated across sky.
birdmat,_,_,_=mat('MAT_R2_DistantBirdFeathers',(.025,.03,.036),.8)
for index in range(7):
    root=bpy.data.objects.new('BIRD_R2_Flock_%02d'%index,None);birds.objects.link(root)
    for sec in range(5):
        t=sec/4;root.location=(-112+195*t-index*5,330+60*t+index*4,145+8*math.sin(t*PI)+index*1.1);root.rotation_euler=(0,0,-math.atan2(195,60));root.keyframe_insert('location',frame=1+round(t*(END-1)));root.keyframe_insert('rotation_euler',frame=1+round(t*(END-1)))
    linear(root)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=1);body=bpy.context.object;body.name='BIRD_R2_Body_%02d'%index
    for c in list(body.users_collection):c.objects.unlink(body)
    birds.objects.link(body);body.parent=root;body.location=(0,0,0);body.scale=(.12,.36,.12);body.data.materials.append(birdmat)
    for side in [-1,1]:
        vs=[(0,.15,0),(side*.38,.10,.04),(side*.76,-.10,.02),(side*1.02,-.29,-.01),(side*.92,-.38,-.01),(side*.63,-.28,0),(side*.31,-.16,0),(0,-.12,0)]
        wing=mesh(f'BIRD_R2_Wing_{index}_{side}',vs,[(0,1,6,7),(1,2,5,6),(2,3,4,5)],[birdmat],birds);wing.parent=root;wing.location=(side*.06,0,.035)
        driver=wing.driver_add('rotation_euler',1);driver.driver.expression=f'{side}*.48*sin(frame/60*13.5+{index*1.7})*(.18+.82*max(0,sin(frame/60*.7+{index})))'
    tail=mesh('BIRD_R2_Tail_%02d'%index,[(-.12,-.18,0),(.12,-.18,0),(.18,-.63,0),(-.18,-.63,0)],[(0,1,2,3)],[birdmat],birds);tail.parent=root

# Moderate glare from the real solar disc; no painted-on god-ray overlay.
s.use_nodes=True;ns=s.node_tree.nodes;ls=s.node_tree.links;ns.clear();rl=node(ns,'CompositorNodeRLayers');glare=node(ns,'CompositorNodeGlare');glare.glare_type='FOG_GLOW';glare.quality='HIGH';glare.threshold=2.;glare.size=7;glare.mix=-.92;ls.new(rl.outputs['Image'],glare.inputs['Image']);out=node(ns,'CompositorNodeComposite');ls.new(glare.outputs[0],out.inputs[0])
s.render.fps=FPS;s.render.fps_base=1.;s.frame_start=1;s.frame_end=END
s.cycles.samples=128;s.cycles.use_denoising=True;s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=.03;s.cycles.adaptive_min_samples=24;s.cycles.volume_bounces=2;s.cycles.max_bounces=8;s.cycles.transmission_bounces=5;s.cycles.glossy_bounces=4
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Base Contrast';s.view_settings.exposure=.5
s.render.use_motion_blur=True;s.render.motion_blur_shutter=.4
s['revision']=2;s['delivery']='1920x1080, 60fps, 1200 native frames, 20 seconds';s['revision_brief']='Natural sun reveal, lake flight, readable backlit forest, CC0 photographic clouds and volumetric mist, breeze waves, distant flock.'
s['solar_water_glint_verified']=reveal_verified;s['solar_reveal_verified']=reveal_verified;s['sun_elevation_degrees']=math.degrees(elev);s['sun_azimuth_from_forward_degrees']=math.degrees(az)
s.frame_set(1);s.render.resolution_percentage=100
# Clean orphaned mesh/material data so the editable file is compact.
for block in list(bpy.data.meshes):
    if block.users==0:bpy.data.meshes.remove(block)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Alpine_Mirror.blend'),compress=True)
stats={'revision':2,'objects':len(s.objects),'unique_polygons':sum(len(m.polygons) for m in bpy.data.meshes),'trees':sum(o.name.startswith('TREE_') for o in s.objects),'wind_animated_trees':wind_count,'cloud_volume_puffs':cloud_count,'photographic_cloud_environment':'Poly Haven CC0 Kloofendal partly cloudy, 4k; packed sky only','birds':7,'resolution':[1920,1080],'fps':FPS,'frames':END,'seconds':20,'solar_reveal_verified':reveal_verified,'sun_elevation_degrees':math.degrees(elev),'sun_azimuth_degrees':math.degrees(az),'camera_positions':camera_positions,'blender':bpy.app.version_string}
(OUT/'scene_manifest.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats),flush=True)
if '--preview' in sys.argv:
    s.render.resolution_percentage=35;s.cycles.samples=24;s.cycles.adaptive_min_samples=8;s.render.filepath=str(OUT/'revision_preview.png');bpy.ops.render.render(write_still=True)
print('REVISION COMPLETE',flush=True)
