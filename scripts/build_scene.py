"""Deterministic, fully 3D alpine environment. Run with Python+bpy or Blender -b -P.
All dimensions in metres. No photograph is used as renderable geometry or texture.
"""
import bpy, math, random, argparse, sys, json, time
from pathlib import Path
from mathutils import Vector, noise
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from erosion import hydraulic_erosion

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)
random.seed(9417)
R = random
PI = math.pi
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.materials, bpy.data.meshes, bpy.data.curves, bpy.data.cameras):
    for block in list(datablocks):
        if block.users == 0: datablocks.remove(block)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
cols = {}
for name in ['Mountains', 'Terrain', 'Forest', 'Rocks', 'Groundcover', 'Water', 'Cameras', 'Light']:
    c = bpy.data.collections.new('COL_' + name); scene.collection.children.link(c); cols[name] = c

def move(obj, coll):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    cols[coll].objects.link(obj)
    return obj

def mesh(name, verts, faces, mats, coll, indices=None, smooth=False):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    for m in mats: me.materials.append(m)
    ob = bpy.data.objects.new(name, me); cols[coll].objects.link(ob)
    if indices is not None:
        for p, i in zip(me.polygons, indices): p.material_index = i
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return ob

def material(name, color, rough=.7):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=rough
    return m, m.node_tree.nodes, m.node_tree.links, p

def node(ns, kind, name=None):
    n=ns.new(kind)
    if name: n.label=name; n.name=name
    return n

def mathn(ns, ls, op, a, b=None):
    n=node(ns,'ShaderNodeMath'); n.operation=op
    for i,v in enumerate([a,b]):
        if v is None: continue
        if isinstance(v,(float,int)): n.inputs[i].default_value=v
        else: ls.new(v,n.inputs[i])
    return n.outputs[0]

def ntex(ns,ls,coord,scale,detail=4,rough=.7):
    n=node(ns,'ShaderNodeTexNoise'); n.inputs['Scale'].default_value=scale; n.inputs['Detail'].default_value=detail; n.inputs['Roughness'].default_value=rough
    ls.new(coord,n.inputs['Vector']); return n.outputs['Fac']

def ramp(ns,ls,fac,points):
    n=node(ns,'ShaderNodeValToRGB'); cr=n.color_ramp
    cr.elements.remove(cr.elements[1])
    for i,(pos,col) in enumerate(points):
        e=cr.elements[0] if i==0 else cr.elements.new(pos)
        e.position=pos; e.color=(*col,1)
    ls.new(fac,n.inputs[0]); return n.outputs['Color']

# Sedimentary limestone with nonuniform ledges, scree and altitude/slope snow.
rock,ns,ls,p=material('MAT_Limestone_Snow_SlopeAndAltitude',(.25,.27,.29))
g=node(ns,'ShaderNodeNewGeometry'); sep=node(ns,'ShaderNodeSeparateXYZ'); ls.new(g.outputs['Position'],sep.inputs[0])
fine=ntex(ns,ls,g.outputs['Position'],1.2,5)
coarse=ntex(ns,ls,g.outputs['Position'],.026,5)
strata=mathn(ns,ls,'ADD',mathn(ns,ls,'MULTIPLY',sep.outputs['Z'],.48),mathn(ns,ls,'MULTIPLY',coarse,7.))
strata=mathn(ns,ls,'SINE',strata)
stratacol=ramp(ns,ls,strata,[(0,(.17,.18,.19)),(.30,(.20,.205,.21)),(.7,(.25,.245,.23)),(1,(.29,.28,.26))])
weatherfac=mathn(ns,ls,'ADD',mathn(ns,ls,'MULTIPLY',coarse,.72),mathn(ns,ls,'MULTIPLY',fine,.28))
rockgrain=ramp(ns,ls,weatherfac,[(.2,(.045,.06,.075)),(.45,(.14,.145,.15)),(.7,(.29,.27,.23)),(.85,(.39,.36,.30))])
weather=node(ns,'ShaderNodeMixRGB'); weather.inputs[0].default_value=.77; ls.new(stratacol,weather.inputs[1]); ls.new(rockgrain,weather.inputs[2]); stratacol=weather.outputs[0]
normal=node(ns,'ShaderNodeSeparateXYZ'); ls.new(g.outputs['Normal'],normal.inputs[0])
# Snow gathers on ledges, and remains across steeper summit faces.
alt=mathn(ns,ls,'MULTIPLY',sep.outputs['Z'],.0054)
slope=mathn(ns,ls,'MULTIPLY',normal.outputs['Z'],.9)
snowfac=mathn(ns,ls,'ADD',alt,slope)
snowfac=mathn(ns,ls,'SUBTRACT',snowfac,mathn(ns,ls,'MULTIPLY',coarse,.60))
snowfac=ramp(ns,ls,snowfac,[(.97,(0,0,0)),(1.18,(1,1,1))])
mix=node(ns,'ShaderNodeMixRGB'); ls.new(snowfac,mix.inputs[0]); ls.new(stratacol,mix.inputs[1]); mix.inputs[2].default_value=(.79,.87,.94,1); ls.new(mix.outputs[0],p.inputs['Base Color'])
bump=node(ns,'ShaderNodeBump'); bump.inputs['Strength'].default_value=.65; bump.inputs['Distance'].default_value=.22; ls.new(fine,bump.inputs['Height'])
macro=node(ns,'ShaderNodeBump'); macro.inputs['Strength'].default_value=.72; macro.inputs['Distance'].default_value=3.2; ls.new(ntex(ns,ls,g.outputs['Position'],.18,5,.78),macro.inputs['Height']); ls.new(macro.outputs[0],bump.inputs['Normal']); ls.new(bump.outputs[0],p.inputs['Normal'])
p.inputs['Roughness'].default_value=.83

stone,ns,ls,p=material('MAT_Foreground_Gneiss_Quartz_Lichen',(.2,.23,.24),.79)
g=node(ns,'ShaderNodeNewGeometry'); f=ntex(ns,ls,g.outputs['Position'],3.8,5)
col=ramp(ns,ls,f,[(.18,(.035,.045,.055)),(.45,(.105,.13,.145)),(.60,(.23,.26,.28)),(.76,(.38,.39,.37))]); ls.new(col,p.inputs['Base Color'])
b=node(ns,'ShaderNodeBump'); b.inputs['Strength'].default_value=.7; b.inputs['Distance'].default_value=.13; ls.new(f,b.inputs['Height']); ls.new(b.outputs[0],p.inputs['Normal'])

ground,ns,ls,p=material('MAT_Alpine_Soil_Moss_Gravel',(.1,.13,.05),.95)
g=node(ns,'ShaderNodeNewGeometry'); f=ntex(ns,ls,g.outputs['Position'],.65,5)
col=ramp(ns,ls,f,[(.2,(.035,.045,.022)),(.42,(.09,.105,.042)),(.59,(.19,.20,.09)),(.75,(.29,.27,.19))]); ls.new(col,p.inputs['Base Color'])
b=node(ns,'ShaderNodeBump'); b.inputs['Distance'].default_value=.12; b.inputs['Strength'].default_value=.6; ls.new(ntex(ns,ls,g.outputs['Position'],18,3),b.inputs['Height']); ls.new(b.outputs[0],p.inputs['Normal'])

bark,ns,ls,p=material('MAT_Spruce_Bark',(.095,.064,.038),.92)
needle=[]
for i,c in enumerate([(.026,.067,.043),(.042,.092,.055),(.063,.12,.065),(.027,.053,.037)]):
    m,ns,ls,p=material('MAT_Spruce_Needles_%d'%i,c,.78)
    p.inputs['Subsurface Weight'].default_value=.025
    needle.append(m)
grassm=[]
for i,c in enumerate([(.09,.16,.035),(.16,.22,.062),(.25,.27,.10),(.095,.13,.045)]): grassm.append(material('MAT_Meadow_%d'%i,c,.87)[0])
flower=[material('MAT_Lupine_Violet',(.14,.10,.39),.6)[0],material('MAT_Lupine_Lavender',(.29,.25,.58),.6)[0],material('MAT_Flower_Cream',(.74,.7,.43),.65)[0]]
ice,ns,ls,p=material('MAT_Glacier_BlueIce',(.50,.67,.79),.58)
g=node(ns,'ShaderNodeNewGeometry'); f=ntex(ns,ls,g.outputs['Position'],.4,5); b=node(ns,'ShaderNodeBump'); b.inputs['Distance'].default_value=.8; b.inputs['Strength'].default_value=.55; ls.new(f,b.inputs['Height']); ls.new(b.outputs[0],p.inputs['Normal'])

# Multi-frequency relief. Grid meshes are triangulated for crag silhouettes.
def nz(x,y,s=1): return noise.noise_vector(Vector((x*s,y*s,3.17)))[0]
def fbm(x,y): return sum(nz(x,y,s)*a for s,a in [(.012,12),(.035,5),(.09,2),(.23,.65),(.7,.18)])
peaks=[(0,780,278,205,225),(-149,744,182,190,210),(155,820,198,190,230),(-315,870,168,220,240),(330,940,175,235,230),(40,1050,216,280,240)]
def mountainz(x,y):
    wx=x+nz(x,y,.015)*35; wy=y+nz(x+71,y,.017)*28
    vals=[]
    for px,py,h,rx,ry in peaks:
        # Angular metric generates faceted spurs instead of soft Gaussian hills.
        dx=(wx-px)/rx; dy=(wy-py)/ry
        dist=(abs(dx)**1.45+abs(dy)**1.45)**(1/1.45)
        angle=math.atan2(dy,dx)
        spur=1+.105*math.cos(angle*9+dist*4+nz(wx,wy,.012)*2)*min(1,dist*3)
        vals.append(h*max(0,1-dist)**.88*spur)
    h=max(vals)
    h+=fbm(x,y)*min(1,h/45)*1.8
    h+=nz(x+51,y,.055)*10*min(1,h/60)
    h+=noise.ridged_multi_fractal(Vector((x*.018,y*.018,2.7)),1.1,2.1,5,1.,2.)*18*min(1,h/60)-16*min(1,h/60)
    # weathered, narrow horizontal ledges
    h+=.12*math.sin(h*.9+nz(x,y,.06)*2.4)
    return max(3,h)

def grid(name,x0,x1,y0,y1,nx,ny,fun,mat,coll):
    verts=[]; faces=[]
    for j in range(ny+1):
        y=y0+(y1-y0)*j/ny
        for i in range(nx+1):
            x=x0+(x1-x0)*i/nx; verts.append((x,y,fun(x,y)))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i; b=a+1; c=a+nx+1; d=c+1
            if (i+j)%2: faces.extend([(a,b,c),(b,d,c)])
            else: faces.extend([(a,b,d),(a,d,c)])
    return mesh(name,verts,faces,[mat],coll,smooth=True)
print('Building mountain relief',flush=True)
# 360k simulated rainfall particles cut coherent drainage channels.
NX,NY=900,630
DX=1060/NX; DY=745/NY
heightfield=np.array([[mountainz(-530+i*DX,355+j*DY)/DX for i in range(NX+1)] for j in range(NY+1)],dtype=np.float64)
print('Hydraulic erosion: 140000 droplets, cliff-preserving blend',flush=True)
original_heightfield=heightfield.copy()
heightfield=(original_heightfield*.84+hydraulic_erosion(heightfield,drops=140000)*.16)*DX
np.save(OUT/'mountain_heightfield.npy',heightfield)
def eroded_height(x,y):
    u=max(0,min(NX-.0001,(x+530)/DX)); v=max(0,min(NY-.0001,(y-355)/DY))
    i=int(u); j=int(v); u-=i; v-=j
    return float(heightfield[j,i]*(1-u)*(1-v)+heightfield[j,i+1]*u*(1-v)+heightfield[j+1,i]*(1-u)*v+heightfield[j+1,i+1]*u*v)
mountainz=eroded_height
grid('GEO_HeroMassif_HydraulicErosion',-530,530,355,1100,NX,NY,mountainz,rock,'Mountains')
# Valley flanks and banks are one watertight heightfield; no overlapping sheets.

def shores(y):
    left=-63+.10*max(y,0)+5*math.sin(y*.029)+2*nz(y,0,.08)
    right=49-.079*max(y,0)+7*math.sin(y*.027+1)+3*nz(y,41,.05)-13*math.exp(-((y-52)/43)**2)
    return left,right

def landz(x,y):
    left,right=shores(y)
    dist=max(left-x,x-right)
    if y>318: dist=max(dist,(y-318)*.8)
    # Foreground rocky shelf at right, with an irregular curve toward the lake.
    fore=(-33-y)*.24 + (x-12)*.15
    if y < -19: dist=max(dist,fore)
    if y < -35: dist=max(dist,(-40-y)*.60+(-x-15)*.30)
    if dist<0: return -3+max(-1,dist*.02)
    h=.3+dist*.16+max(0,dist-20)*.22
    h+=nz(x,y,.075)*min(2,dist*.17)+nz(x,y,.45)*.27
    if y<5: h+=nz(x+21,y,.7)*.11
    return max(.08,h)
print('Building shoreline',flush=True)
grid('GEO_LakeBasin_ContinuousValleyBanks',-650,650,-65,725,520,460,landz,ground,'Terrain')

# Glacier tongues: ridged, gently broken surface in the central ravine.
verts=[]; faces=[]
for j in range(105):
    y=522+j*1.75
    center=-43+24*math.sin((y-520)*.012)
    width=17+13*math.sin(j/104*PI)**2+4*nz(y,82,.13)
    for i in range(15):
        x=center+(i/14*2-1)*width
        z=mountainz(x,y)+.28+math.sin(i*1.8+j*.17)*.23
        verts.append((x,y,z))
for j in range(104):
    for i in range(14):
        a=j*15+i; faces.append((a,a+1,a+16,a+15))
# Kept as an editable geological study, hidden until a better snow/ice blend is authored.
glacier=mesh('GEO_Glacier_CentralTongue',verts,faces,[ice],'Mountains',smooth=True); glacier.hide_render=True

# Spruce prototypes: actual trunks, radial boughs and irregular needle sprays, no cones/cards.
def make_spruce(seed):
    rng=random.Random(seed); vs=[]; fs=[]; mi=[]
    def tri(a,b,c,mat):
        i=len(vs); vs.extend([tuple(a),tuple(b),tuple(c)]); fs.append((i,i+1,i+2)); mi.append(mat)
    def tube(a,b,ra,rb,sides=6,mat=0):
        a=Vector(a); b=Vector(b); axis=(b-a).normalized(); u=axis.cross(Vector((0,1,.001))).normalized(); v=axis.cross(u)
        k=len(vs)
        for pt,r in [(a,ra),(b,rb)]:
            for s in range(sides): vs.append(tuple(pt+r*(u*math.cos(2*PI*s/sides)+v*math.sin(2*PI*s/sides))))
        for s in range(sides): fs.append((k+s,k+(s+1)%sides,k+sides+(s+1)%sides,k+sides+s)); mi.append(mat)
    tube((0,0,0),(.025,0,1),.018,.001,8)
    for tier in range(27):
        z=.13+tier*.031
        width=.225*(1-z)**.74
        count=rng.randint(5,8)
        for j in range(count):
            angle=j*2*PI/count+rng.uniform(0,.55)+tier*1.8
            axis=Vector((math.cos(angle),math.sin(angle),0)); cross=Vector((-axis.y,axis.x,0))
            length=width*rng.uniform(.7,1.2)
            root=Vector((0,0,z+rng.uniform(-.021,.021))); end=root+axis*length+Vector((0,0,rng.uniform(-.32,.03)*length))
            tube(root,end,.0028,.0003,4)
            for t in range(1,8):
                frac=t/8; c=root.lerp(end,frac); span=length*.34*(1-frac*.55)
                # three-dimensional feathered bough, loose pointed sprays
                for side in [-1,1]:
                    tip=c+cross*span*side+axis*span*.35+Vector((0,0,span*.15))
                    mat=1+rng.randrange(4)
                    tube(c,tip,.00065,.0001,3,0)
                    # Dense interior shoot mass plus individual silhouette needles.
                    tri(c-axis*.009,tip,c+axis*.021+Vector((0,0,.011)),mat)
                    tri(c+Vector((0,0,-.006)),tip+Vector((0,0,.006)),c+Vector((0,0,.014)),mat)
                    # Fine three-dimensional needles, not broad triangular leaf fans.
                    for q in range(7):
                        cc=c.lerp(tip,(q+.5)/7)
                        for needle_side in [-1,1]:
                            direction=(axis*needle_side+cross*.38*side+Vector((0,0,.35))).normalized()
                            ln=rng.uniform(.004,.010)
                            tri(cc-cross*.00075,cc+direction*ln,cc+cross*.00075,mat)
                        tri(cc-axis*.0006,cc+Vector((0,0,.008)),cc+axis*.0006,mat)
    tube((.025,0,.88),(.016,0,1.065),.002,.0001,4,2)
    return mesh('LIB_Spruce_%02d'%seed,vs,fs,[bark]+needle,'Forest',mi)
print('Building spruce libraries',flush=True)
protos=[make_spruce(100+i) for i in range(7)]
for ob in protos: ob.location=(0,0,-500)

def instance(proto,name,loc,scale,coll,rot=0):
    o=bpy.data.objects.new(name,proto.data); cols[coll].objects.link(o); o.location=loc
    o.scale=(scale,scale,scale) if isinstance(scale,(float,int)) else scale
    o.rotation_euler[2]=rot; return o

count=0
for i in range(2200):
    y=R.uniform(-12,395); x=R.uniform(-225,225)
    left,right=shores(y)
    if left-2<x<right+2 and y<322: continue
    z=landz(x,y)
    if z<.15: continue
    # Keep near shore open enough for boulders and reflection.
    if y<15 and x<right+8 and x>left-8: continue
    h=R.uniform(7,18)*(1 if y<230 else .8)
    instance(R.choice(protos),'TREE_Spruce_%04d'%count,(x,y,z-.05),(h*R.uniform(.85,1.13),h,h),'Forest',R.random()*2*PI); count+=1
# Framing trees with intentionally asymmetric silhouettes.
for x,y,h in [(42,-4,39),(49,23,38),(58,52,26),(-44,12,20),(-53,36,23),(-60,65,21),(36,65,19)]:
    instance(R.choice(protos),'TREE_Hero_Frame',(x,y,landz(x,y)),h,'Forest',R.random()*6)
# A second instanced belt covers the steep valley slopes, not just the flat banks.
for i in range(1950):
    side=R.choice([-1,1]); x=side*R.uniform(72,455); y=R.uniform(170,660)
    z=landz(x,y)
    h=R.uniform(8,17)
    instance(R.choice(protos),'TREE_ValleySlope_%04d'%i,(x,y,z-.1),h,'Forest',R.random()*6.28)
    count+=1
print('Forest instances',count,flush=True)

# Angular boulder variants with real displacement, shared mesh geometry.
rockprotos=[]
for i in range(9):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,radius=1)
    o=move(bpy.context.object,'Rocks'); o.name='LIB_Boulder_%02d'%i
    for v in o.data.vertices:
        co=v.co; r=1+nz(co.x+i*7,co.y+co.z*3,2)*.18+nz(co.x,co.z+i,.7)*.12
        v.co=(max(-.83,min(.81,co.x*r)),max(-.85,min(.82,co.y*r)),max(-.42,min(.49,co.z*r*.64)))
    o.data.materials.append(stone)
    for poly in o.data.polygons: poly.use_smooth=False
    bevel=o.modifiers.new('Soft weathered edges','BEVEL'); bevel.width=.025; bevel.segments=2
    o.location=(0,0,-510); rockprotos.append(o)
for i in range(540):
    y=R.uniform(-56,335); left,right=shores(y)
    side=R.choice([-1,1]); x=(left if side<0 else right)+side*R.uniform(-1.5,12)
    z=landz(x,y)
    if z<-.2: continue
    s=R.uniform(.25,1.6)*(1.4 if y<25 else 1)
    o=instance(R.choice(rockprotos),'ROCK_Shore_%04d'%i,(x,y,max(-.2,z)),(s*R.uniform(1,1.7),s,s*R.uniform(.7,1.3)),'Rocks',R.random()*6)
# Foreground quartz boulders, picture anchors.
for x,y,s in [(-13,-45,2.5),(-8,-46,1.6),(-18,-43,2.1),(18,-29,3.1),(25,-21,2.5),(33,-11,2.2)]:
    z=max(.2,landz(x,y)); instance(R.choice(rockprotos),'ROCK_Hero_Quartz',(x,y,z),(s*1.5,s,s*.8),'Rocks',R.random()*5)

# Combined meadow blades: inexpensive geometry, no alpha transparency noise.
print('Building meadow and lupines',flush=True)
vs=[]; fs=[]; ids=[]
for k in range(58000):
    y=R.uniform(-65,-19) if k<40000 else R.uniform(-65,110)
    x=R.uniform(-30,52) if k<40000 else R.uniform(-90,95); z=landz(x,y)
    if z<.12: continue
    if y>15 and R.random()<.65: continue
    for blade in range(R.randint(3,6)):
        ang=R.random()*2*PI; w=R.uniform(.012,.04); h=R.uniform(.15,.56)
        xx=x+R.uniform(-.13,.13); yy=y+R.uniform(-.13,.13)
        i=len(vs); dx=math.cos(ang)*w; dy=math.sin(ang)*w
        vs.extend([(xx-dx,yy-dy,z),(xx+dx,yy+dy,z),(xx+dx*1.5,yy+dy*1.5,z+h)])
        fs.append((i,i+1,i+2)); ids.append(R.randrange(4))
mesh('GEO_Meadow_IndividualBlades',vs,fs,grassm,'Groundcover',ids)
# Low bushes composed of small pointed leaves. Foreground only.
vs=[]; fs=[]; ids=[]
for k in range(170):
    x=R.uniform(-70,70); y=R.uniform(-62,80); z=landz(x,y)
    if z<.2: continue
    radius=R.uniform(.4,1.7)
    for leaf in range(95):
        a=R.random()*2*PI; r=radius*math.sqrt(R.random()); xx=x+r*math.cos(a); yy=y+r*math.sin(a); zz=z+radius*.65*max(0,1-(r/radius)**2)+R.uniform(-.12,.15)
        i=len(vs); w=R.uniform(.05,.13)
        vs.extend([(xx-w,yy,zz),(xx,yy-w,zz+.025),(xx+w*1.9,yy,zz+.07),(xx,yy+w,zz+.025)])
        fs.append((i,i+1,i+2,i+3)); ids.append(R.randrange(4))
mesh('GEO_Heather_Bilberry_Leaves',vs,fs,grassm,'Groundcover',ids)
# Lupines: stems, palmate leaves and whorled pea-flower petals.
vs=[]; fs=[]; ids=[]
def petal(cx,cy,cz,w,h,ang,mat):
    i=len(vs); d=Vector((math.cos(ang),math.sin(ang),0)); t=Vector((-d.y,d.x,0)); c=Vector((cx,cy,cz))
    vs.extend([tuple(c-t*w),tuple(c+d*w*1.6+Vector((0,0,h))),tuple(c+t*w),tuple(c-d*w*.4+Vector((0,0,h*.4)))])
    fs.append((i,i+1,i+2,i+3)); ids.append(mat)
for k in range(980):
    x=R.uniform(9,65) if R.random()<.8 else R.uniform(-50,-15); y=R.uniform(-62,16); z=landz(x,y)
    if z<.15: continue
    h=R.uniform(.38,.95); mat=R.choice([4,4,5,5,6])
    petal(x,y,z,.012,h,R.random()*6,0)
    for level in range(11):
        zz=z+h*.48+level*h*.045; width=.065*(1-level/14)
        for q in range(5):
            a=q*2*PI/5+level*.6
            petal(x+math.cos(a)*.035,y+math.sin(a)*.035,zz,width,h*.06,a,mat)
    for q in range(7): petal(x,y,z+.15,.032,.18,q*2*PI/7,1)
mesh('GEO_Lupine_WildflowerMeadow',vs,fs,grassm+flower,'Groundcover',ids)

# Water is a true dielectric surface: raytraced mountain/forest reflections.
water,ns,ls,p=material('MAT_Lake_Fresnel_AnimatedCapillaryRipples',(.035,.095,.087),.025)
p.inputs['IOR'].default_value=1.333; p.inputs['Transmission Weight'].default_value=.72
p.inputs['Coat Weight'].default_value=.3; p.inputs['Coat Roughness'].default_value=.025
tex=node(ns,'ShaderNodeTexCoord'); mapping=node(ns,'ShaderNodeMapping','Animated_Ripple_Drift'); ls.new(tex.outputs['Object'],mapping.inputs[0]); mapping.inputs['Scale'].default_value=(.45,1.5,1)
for f,x in [(1,0),(480,1.1)]:
    mapping.inputs['Location'].default_value=(x,x*.18,0); mapping.inputs['Location'].keyframe_insert('default_value',frame=f)
n=ntex(ns,ls,mapping.outputs[0],2.8,3,.55)
b=node(ns,'ShaderNodeBump'); b.inputs['Distance'].default_value=.008; b.inputs['Strength'].default_value=.18; ls.new(n,b.inputs['Height']); ls.new(b.outputs[0],p.inputs['Normal'])
mesh('GEO_Lake_WaterSurface',[(-300,-90,0),(300,-90,0),(300,360,0),(-300,360,0)],[(0,1,2,3)],[water],'Water')

# Procedural physical sky, softened directional daylight. No external HDRI.
world=bpy.data.worlds.new('WORLD_Clear_Alpine_Morning'); world.use_nodes=True; scene.world=world
ns=world.node_tree.nodes; ls=world.node_tree.links; ns.clear()
sky=node(ns,'ShaderNodeTexSky'); sky.sky_type='NISHITA'; sky.sun_elevation=math.radians(32); sky.sun_rotation=math.radians(128); sky.altitude=1.6; sky.air_density=1.05; sky.dust_density=.5; sky.ozone_density=1.2; sky.sun_disc=False
# A controllable spectral-blue sky gradient keeps clear mountain air from
# turning into Nishita's over-bright low-altitude haze under AgX.
tc=node(ns,'ShaderNodeTexCoord'); sz=node(ns,'ShaderNodeSeparateXYZ'); ls.new(tc.outputs['Normal'],sz.inputs[0])
skyheight=mathn(ns,ls,'MULTIPLY',sz.outputs['Z'],-1.)
skycol=ramp(ns,ls,skyheight,[(0,(.24,.40,.60)),(.18,(.075,.24,.49)),(.65,(.025,.14,.36)),(1,(.015,.08,.23))])
cloudnoise=ntex(ns,ls,tc.outputs['Normal'],7.5,5,.7)
cloud=ramp(ns,ls,cloudnoise,[(.62,(0,0,0)),(.77,(.6,.6,.6))])
skymix=node(ns,'ShaderNodeMixRGB'); ls.new(cloud,skymix.inputs[0]); ls.new(skycol,skymix.inputs[1]); skymix.inputs[2].default_value=(.65,.72,.79,1)
bg=node(ns,'ShaderNodeBackground'); bg.inputs[1].default_value=.7; ls.new(skymix.outputs[0],bg.inputs[0]); wout=node(ns,'ShaderNodeOutputWorld'); ls.new(bg.outputs[0],wout.inputs[0])
ld=bpy.data.lights.new('LGT_Morning_Sun','SUN'); ld.energy=2.5; ld.angle=math.radians(2); ld.color=(1,.92,.8)
lo=bpy.data.objects.new('LGT_Morning_Sun',ld); cols['Light'].objects.link(lo); lo.rotation_euler=Vector((.6,.45,-.75)).to_track_quat('-Z','Y').to_euler()
# Camera and slow physically meaningful parallax move.
cd=bpy.data.cameras.new('CAM_AlpineMirror_28mm'); cam=bpy.data.objects.new('CAM_AlpineMirror_Hero',cd); cols['Cameras'].objects.link(cam); scene.camera=cam
cd.lens=28; cd.sensor_width=36; cd.clip_end=4000; cd.clip_start=.1
for f,loc,target in [(1,(0,-74,8),(0,550,32)),(240,(.65,-72.7,8.12),(0,550,32)),(480,(1.5,-71,8.3),(0,550,32))]:
    cam.location=loc; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler(); cam.keyframe_insert('location',frame=f); cam.keyframe_insert('rotation_euler',frame=f)
if cam.animation_data:
    for fc in cam.animation_data.action.fcurves:
        for k in fc.keyframe_points: k.interpolation='BEZIER'

scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=64
scene.cycles.use_adaptive_sampling=True; scene.cycles.adaptive_threshold=.045; scene.cycles.use_denoising=True
scene.cycles.denoiser='OPENIMAGEDENOISE'; scene.cycles.max_bounces=6; scene.cycles.diffuse_bounces=2; scene.cycles.glossy_bounces=3; scene.cycles.transmission_bounces=4; scene.cycles.volume_bounces=0
scene.cycles.use_light_tree=True; scene.cycles.sample_clamp_indirect=3
scene.render.threads_mode='FIXED'; scene.render.threads=2; scene.render.use_persistent_data=True
scene.render.resolution_x=1920; scene.render.resolution_y=1080; scene.render.resolution_percentage=100
scene.render.fps=24; scene.frame_start=1; scene.frame_end=480
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'; scene.render.image_settings.color_depth='8'; scene.render.image_settings.compression=25
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'; scene.view_settings.exposure=.3
scene.render.film_transparent=False
scene['project']='Alpine Mirror | procedural reference reconstruction'; scene['seed']=9417
scene['reference']='reference/alpine-lake.png (analysis only, not projected)'
scene['delivery']='1920x1080, 24fps, 480 frames, 20 seconds'
scene['skills_source']='arjun988/blender-skills @ 8f778d2405a214b508d4c7d80742be8e43acdd52'
scene.frame_set(1)
scene.render.filepath=str(OUT/'frames'/'alpine_')
# Remove unused default collections.
for c in list(bpy.data.collections):
    if c.name=='Collection' and len(c.objects)==0: bpy.data.collections.remove(c)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Alpine_Mirror.blend'),compress=True)
stats={'objects':len(scene.objects),'mesh_datablocks':len(bpy.data.meshes),'unique_polygons':sum(len(m.polygons) for m in bpy.data.meshes),'trees':count+7,'resolution':[1920,1080],'fps':24,'frames':480,'seconds':20,'blender':bpy.app.version_string}
(OUT/'scene_manifest.json').write_text(json.dumps(stats,indent=2)); print(json.dumps(stats),flush=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
if '--preview' in args:
    scene.render.resolution_percentage=40; scene.cycles.samples=16; scene.render.filepath=str(OUT/'preview.png'); bpy.ops.render.render(write_still=True)
print('BUILD COMPLETE',flush=True)
