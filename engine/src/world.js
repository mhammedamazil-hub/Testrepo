import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Water} from 'three/addons/objects/Water.js';
import RAPIER from '@dimforge/rapier3d-compat';
import {ROADSTER} from './vehicle-spec.js';

export const asset=name=>new URL('world/'+name,document.baseURI).href;
export class AlpineWorld {
 constructor(scene,renderer,physics,level){this.scene=scene;this.renderer=renderer;this.physics=physics;this.level=level;this.loader=new GLTFLoader();this.textures=new T.TextureLoader();this.details=[];this.reflectionFrames=0;this.frame=0;this.lastMirrorFrame=-1;}
 async texture(name,color=false){const t=await this.textures.loadAsync(asset(name));t.colorSpace=color?T.SRGBColorSpace:T.NoColorSpace;t.wrapS=t.wrapT=T.RepeatWrapping;t.anisotropy=Math.min(4,this.renderer.capabilities.getMaxAnisotropy());return t;}
 async load(){
  this.data=await fetch(asset('world_data.json')).then(r=>r.json());
  this.scatter=await fetch(asset('world_data_detail.json')).then(r=>r.json());
  const [terrain,road,vehicle,character,pine,grass,rocks,sky,ground,groundNormal,groundArm,ripple,cutout,nightSky]=await Promise.all([
   ...['terrain','road','vehicle','character','pine','grass','rocks'].map(key=>this.loader.loadAsync(asset(this.level.assets[key]))),
   this.texture('sky.jpg',true),this.texture('library/ground_diff.jpg',true),this.texture('library/ground_normal.jpg'),this.texture('library/ground_arm.jpg'),this.texture('ground_detail_normal.png'),this.texture('spruce_impostor.png',true),this.texture('night/milky-way.jpg',true)
  ]);
  this.daySky=sky;this.nightSky=nightSky;nightSky.mapping=T.EquirectangularReflectionMapping;sky.mapping=T.EquirectangularReflectionMapping;this.scene.background=sky;this.scene.backgroundRotation.y=-Math.PI/2;
  const pmrem=new T.PMREMGenerator(this.renderer);this.dayEnvironment=pmrem.fromEquirectangular(sky).texture;this.nightEnvironment=pmrem.fromEquirectangular(nightSky).texture;this.scene.environment=this.dayEnvironment;this.scene.environmentRotation.y=-Math.PI/2;pmrem.dispose();
  this.scene.fog=new T.FogExp2(0xa5b9c0,.0008);
  this.hemisphere=new T.HemisphereLight(0xc3dcf0,0x535641,1.2);this.scene.add(this.hemisphere);
  this.sun=new T.DirectionalLight(0xffe5b6,2.3);this.sun.position.set(...this.level.sun);this.sun.castShadow=true;
  this.sun.shadow.mapSize.set(1024,1024);Object.assign(this.sun.shadow.camera,{left:-100,right:100,top:100,bottom:-100,near:1,far:1000});
  this.sun.shadow.bias=-.0002;this.sun.shadow.normalBias=.05;this.scene.add(this.sun,this.sun.target);
  this.sunDisk=new T.Mesh(new T.SphereGeometry(22,16,12),new T.MeshBasicMaterial({color:0xffe1ac,transparent:true,depthWrite:false,toneMapped:false,fog:false}));
  this.sunDisk.position.set(...this.level.sun);this.sunDisk.name='VisibleSunForOccludedShafts';this.scene.add(this.sunDisk);
  for(const root of [terrain.scene,road.scene]){
   this.scene.add(root);root.updateMatrixWorld(true);
   root.traverse(mesh=>{if(!mesh.isMesh)return;mesh.castShadow=false;mesh.receiveShadow=true;
    if(mesh.name.includes('Alpine_Ground')){
     mesh.material=mesh.material.clone();mesh.material.roughness=.96;
     mesh.material.onBeforeCompile=shader=>{
      Object.assign(shader.uniforms,{alpineGround:{value:ground},alpineFineNormal:{value:groundNormal},alpineArm:{value:groundArm}});
      shader.vertexShader='varying vec3 vAlpineWorld;\n'+shader.vertexShader;
      shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvAlpineWorld=(modelMatrix*vec4(transformed,1.0)).xyz;');
      shader.fragmentShader='varying vec3 vAlpineWorld; uniform sampler2D alpineGround; uniform sampler2D alpineFineNormal; uniform sampler2D alpineArm;\n'+shader.fragmentShader;
      shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>',`#include <map_fragment>
       float detailFade=1.0-smoothstep(35.0,190.0,distance(cameraPosition,vAlpineWorld));
       vec3 turf=texture2D(alpineGround,vAlpineWorld.xz*.35).rgb;
       diffuseColor.rgb=mix(diffuseColor.rgb,turf*.92,detailFade*.78);`);
      shader.fragmentShader=shader.fragmentShader.replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor=mix(roughnessFactor,texture2D(alpineArm,vAlpineWorld.xz*.35).g,detailFade*.8);');
      shader.fragmentShader=shader.fragmentShader.replace('#include <normal_fragment_maps>',`#include <normal_fragment_maps>
       { vec2 tile=vAlpineWorld.xz*.35; vec3 q0=dFdx(-vViewPosition),q1=dFdy(-vViewPosition);vec2 st0=dFdx(tile),st1=dFdy(tile);
         vec3 S=normalize(q0*st1.t-q1*st0.t),B=normalize(-q0*st1.s+q1*st0.s);
         vec3 fine=texture2D(alpineFineNormal,tile).xyz*2.0-1.0;fine.xy*=detailFade*.35;
         normal=normalize(mat3(S,B,normal)*normalize(fine)); }`);
     };
    }
    if(!mesh.name.includes('Center_Lines'))this.addCollider(mesh);
   });
  }
  this.car=vehicle.scene;this.person=character.scene;this.scene.add(this.car,this.person);
  for(const model of [this.car,this.person])model.traverse(m=>{if(m.isMesh){m.castShadow=true;m.receiveShadow=true;if(m.material)m.material.envMapIntensity=.8;}});
  this.wheels=ROADSTER.wheels.map(w=>{const spin=this.car.getObjectByName('Roadster_Spin_'+w.name),caliper=this.car.getObjectByName('Roadster_Caliper_'+w.name);return {spin,caliper,baseSpin:spin?.quaternion.clone(),baseCaliper:caliper?.quaternion.clone()};});
  this.lamps=[];this.headlights=true;this.tailMaterials=[];
  this.car.traverse(n=>{if(!n.isMesh)return;for(const m of Array.isArray(n.material)?n.material:[n.material]){if(/rear_lights/i.test(m.name))this.tailMaterials.push(m);if(/car_main_paint/i.test(m.name)){m.envMapIntensity=1.6;m.clearcoat=.65;m.clearcoatRoughness=.17;}}});
  for(const x of [-.61,.61]){const light=new T.SpotLight(0xd9ecff,4200,95,.30,.55,2);light.position.set(x,.56,-2.02);light.target.position.set(x,-.12,-65);light.castShadow=x<0;light.shadow.mapSize.set(512,512);light.shadow.bias=-.0002;light.shadow.normalBias=.035;this.car.add(light,light.target);this.lamps.push(light);}

  this.mixer=new T.AnimationMixer(this.person);this.clips={};for(const clip of character.animations)this.clips[clip.name.toLowerCase().includes('walk')?'walk':'idle']=this.mixer.clipAction(clip);
  this.activeClip=null;this.playAnimation('idle');
  const near=[],far=[];
  for(const p of this.data.forest){const close=this.data.route.some(r=>(r[0]-p[0])**2+(r[2]-p[2])**2<32**2);far.push({...p,near:close});if(close)near.push([...p,Math.abs(p[0]*.71)%(Math.PI*2)]);}
  for(const p of near)this.physics.world.createCollider(RAPIER.ColliderDesc.cylinder(p[3]*.4,Math.max(.14,p[3]*.018)).setTranslation(p[0],p[1]+p[3]*.4,p[2]).setFriction(.6));
  for(const p of this.scatter.rocks)this.physics.world.createCollider(RAPIER.ColliderDesc.ball(p[3]*.43).setTranslation(p[0],p[1]+p[3]*.36,p[2]).setFriction(.7));
  this.instances(pine.scene,near,60,115,'pine');this.instances(grass.scene,this.scatter.grass,35,70,'grass');this.instances(rocks.scene,this.scatter.rocks,60,150,'rocks');
  this.forest(cutout,far);
  this.water=new Water(new T.PlaneGeometry(...this.level.lake.size),{textureWidth:512,textureHeight:512,waterNormals:ripple,sunDirection:new T.Vector3(...this.level.sun).normalize(),sunColor:0xffe5bf,waterColor:0x124b48,distortionScale:1.7,fog:true});
  this.water.rotation.x=-Math.PI/2;this.water.position.set(...this.level.lake.position);this.water.name='CurrentFramePlanarLake';
  // LDR fallback avoids requiring float render attachments on older WebGL2 phones.
  if(!this.renderer.extensions.has('EXT_color_buffer_float'))this.water.material.uniforms.mirrorSampler.value.type=T.UnsignedByteType;
  const reflect=this.water.onBeforeRender;
  this.water.onBeforeRender=(...args)=>{if(this.lastMirrorFrame===this.frame)return;this.lastMirrorFrame=this.frame;this.reflectionFrames++;reflect.apply(this.water,args);};
  this.scene.add(this.water);
  this.markers=this.level.checkpoints.map(index=>{const m=new T.Mesh(new T.TorusGeometry(2.9,.055,6,40),new T.MeshBasicMaterial({color:0xa5e2bd}));const p=this.data.route[index];m.position.set(p[0],p[1]+2.9,p[2]);const next=this.data.route[(index+1)%this.data.route.length];m.rotation.y=Math.atan2(-(next[0]-p[0]),-(next[2]-p[2]));this.scene.add(m);return m;});
  this.setNight(true);
 }
 setNight(night){
  this.night=night;this.scene.background=night?this.nightSky:this.daySky;
  this.scene.backgroundRotation.y=night?1.1:-Math.PI/2;this.scene.backgroundIntensity=night?1.35:1;
  this.scene.environment=night?this.nightEnvironment:this.dayEnvironment;this.scene.environmentRotation.y=this.scene.backgroundRotation.y;
  this.scene.environmentIntensity=night?1.3:.85;
  this.scene.fog.color.set(night?0x091424:0xa5b9c0);this.scene.fog.density=night?.0007:.0008;
  this.hemisphere.color.set(night?0x779dce:0xc3dcf0);this.hemisphere.groundColor.set(night?0x182333:0x535641);this.hemisphere.intensity=night?.32:1.2;
  this.sun.color.set(night?0xabc9ff:0xffe5b6);this.sun.intensity=night?.6:2.3;this.sunDisk.visible=!night;
  this.lightDirection=new T.Vector3(...(night?[350,650,80]:this.level.sun)).normalize();
  this.water.material.uniforms.sunDirection.value.copy(this.lightDirection);this.water.material.uniforms.sunColor.value.set(night?0xb6cfff:0xffe5bf);this.water.material.uniforms.waterColor.value.set(night?0x06101d:0x124b48);
  this.forestMaterial.uniforms.fogColor.value.copy(this.scene.fog.color);this.forestMaterial.uniforms.tint.value.setRGB(...(night?[.22,.32,.49]:[1,1,1]));
 }
 addCollider(mesh){
  const p=mesh.geometry.getAttribute('position'),vertices=new Float32Array(p.count*3),v=new T.Vector3();
  for(let i=0;i<p.count;i++){v.fromBufferAttribute(p,i).applyMatrix4(mesh.matrixWorld);vertices.set([v.x,v.y,v.z],i*3);}
  const index=mesh.geometry.index;const indices=index?new Uint32Array(index.array):Uint32Array.from({length:p.count},(_,i)=>i);
  this.physics.addTrimesh(vertices,indices,mesh.name.includes('Road')?'road':'ground');
 }
 playAnimation(name){if(name===this.activeClip)return;if(this.activeClip&&this.clips[this.activeClip])this.clips[this.activeClip].fadeOut(.18);this.clips[name]?.reset().fadeIn(.18).play();this.activeClip=name;}
 instances(template,placements,size,range,kind){
  template.updateMatrixWorld(true);const cells=new Map();for(const p of placements){const key=Math.floor(p[0]/size)+','+Math.floor(p[2]/size);if(!cells.has(key))cells.set(key,[]);cells.get(key).push(p);}
  template.traverse(source=>{if(!source.isMesh)return;const geometry=source.geometry.clone().applyMatrix4(source.matrixWorld);let material=source.material.clone();
   material.transparent=false;material.depthWrite=true;material.alphaTest=kind==='pine'?.16:kind==='grass'?.32:0;material.side=T.DoubleSide;material.roughness=.94;
   for(const data of cells.values()){
    const m=new T.InstancedMesh(geometry,material,data.length),matrix=new T.Matrix4(),q=new T.Quaternion(),s=new T.Vector3();
    const center=new T.Vector3();for(let i=0;i<data.length;i++){const p=data[i];q.setFromAxisAngle(new T.Vector3(0,1,0),p[4]||0);s.setScalar(p[3]);matrix.compose(new T.Vector3(p[0],p[1],p[2]),q,s);m.setMatrixAt(i,matrix);center.add(new T.Vector3(p[0],p[1],p[2]));}
    center.multiplyScalar(1/data.length);m.name=kind+'Cell';m.castShadow=kind==='pine';m.receiveShadow=true;m.computeBoundingSphere();this.scene.add(m);this.details.push({mesh:m,center,range});
   }
  });
 }
 forest(texture,placements){
  const geometry=new T.PlaneGeometry(.5,1);const near=new Float32Array(placements.length);
  const material=new T.ShaderMaterial({uniforms:{sprite:{value:texture},fogColor:{value:new T.Color(0xa5b9c0)},tint:{value:new T.Color(1,1,1)}},side:T.DoubleSide,vertexShader:`attribute float alpineNear; varying vec2 vUv; varying float vDistance; varying float vNear;
   void main(){vUv=uv;vNear=alpineNear;vec3 centre=instanceMatrix[3].xyz;float h=length(instanceMatrix[1].xyz);vec3 right=normalize(vec3(cameraPosition.z-centre.z,0.0,centre.x-cameraPosition.x));vec3 world=centre+right*position.x*h+vec3(0.0,(position.y+.5)*h,0.0);vDistance=distance(world,cameraPosition);gl_Position=projectionMatrix*viewMatrix*vec4(world,1.0);}`,
   fragmentShader:`uniform sampler2D sprite; uniform vec3 fogColor;uniform vec3 tint;varying vec2 vUv;varying float vDistance;varying float vNear;
   void main(){vec4 c=texture2D(sprite,vUv);float fade=mix(1.0,smoothstep(70.0,100.0,vDistance),vNear);if(c.a*fade<.35)discard;float fog=1.0-exp(-.00000064*vDistance*vDistance);gl_FragColor=vec4(mix(c.rgb*tint,fogColor,fog),1.0);
   #include <tonemapping_fragment>
   #include <colorspace_fragment>
   }`});
  const mesh=new T.InstancedMesh(geometry,material,placements.length),matrix=new T.Matrix4();
  placements.forEach((p,i)=>{matrix.makeScale(p[3],p[3],p[3]);matrix.setPosition(p[0],p[1],p[2]);mesh.setMatrixAt(i,matrix);near[i]=p.near?1:0;});
  geometry.setAttribute('alpineNear',new T.InstancedBufferAttribute(near,1));mesh.frustumCulled=false;mesh.name='DistantForest';this.forestMaterial=material;this.scene.add(mesh);
 }
 update(camera,dt){
  this.frame++;this.water.material.uniforms.time.value+=dt*.45;
  for(const cell of this.details)cell.mesh.visible=cell.center.distanceToSquared(camera.position)<cell.range**2;
  const p=this.physics.car.translation(),q=this.physics.car.rotation();this.car.quaternion.copy(q);this.car.position.copy(p).add(new T.Vector3(0,-ROADSTER.centerOfMassHeight,0).applyQuaternion(this.car.quaternion));
  this.person.position.copy(this.physics.player.translation());this.person.visible=!this.physics.inVehicle;
  const speed=Math.hypot(this.physics.footVelocity.x,this.physics.footVelocity.z);this.playAnimation(speed>.3?'walk':'idle');this.mixer.update(dt);
  if(speed>.3)this.person.rotation.y=Math.atan2(-this.physics.footVelocity.x,-this.physics.footVelocity.z);
  for(let i=0;i<this.wheels.length;i++){const w=this.wheels[i],state=this.physics.wheelStates[i];if(!state)continue;
   const steer=new T.Quaternion().setFromAxisAngle(new T.Vector3(0,1,0),state.steering),roll=new T.Quaternion().setFromAxisAngle(new T.Vector3(1,0,0),-state.rotation);
   for(const mesh of [w.spin,w.caliper])if(mesh)mesh.position.set(state.connection.x,state.connection.y-state.suspension+ROADSTER.centerOfMassHeight,state.connection.z);
   if(w.spin)w.spin.quaternion.copy(steer).multiply(roll).multiply(w.baseSpin);
   if(w.caliper)w.caliper.quaternion.copy(steer).multiply(w.baseCaliper);
  }
  for(const m of this.tailMaterials)m.emissiveIntensity=this.physics.braking?6:2;
  for(const light of this.lamps)light.visible=this.night&&this.headlights;
  const focus=this.physics.inVehicle?p:this.physics.player.translation();this.sun.target.position.copy(focus);this.sun.position.copy(focus).add(this.lightDirection.clone().multiplyScalar(700));
 }
}
