import * as T from 'three';
import {Water} from 'three/addons/objects/Water.js';
import {EffectPass,FXAAEffect} from 'postprocessing';

// Opt-in export tool only. Not imported by the playable runtime and never changes
// its saved graphics settings. Camera motion is authored; this is not gameplay.
export const FILM={width:1920,height:1080,fps:60,seconds:3};
export async function prepareCinematic(game,{seconds=FILM.seconds,msaa=0}={}){
 const {renderer,world,physics,scene,camera,composer}=game;
 document.querySelectorAll('#game > :not(canvas)').forEach(node=>node.hidden=true);
 document.body.dataset.phase='cinematic';game.phase='cinematic';
 renderer.setPixelRatio(1);renderer.setSize(FILM.width,FILM.height,false);composer.setSize(FILM.width,FILM.height);composer.multisampling=msaa;
 camera.aspect=FILM.width/FILM.height;camera.fov=43;camera.near=.1;camera.updateProjectionMatrix();
 world.setNight(false);world.headlights=false;game.raysEnabled=false;game.syncEffects();game.clearEffects.renderToScreen=false;const antialias=new EffectPass(camera,new FXAAEffect());composer.addPass(antialias);
 // Park away from the start gantry, looking out across the actual alpine lake.
 const route=world.data.route,i=120;physics.reset([route[i],route[i+1],route[i+2]]);physics.settle(240);physics.inVehicle=true;
 world.person.visible=false;for(const m of [...world.markers,...world.flightGates])m.visible=false;
 world.lightDirection.set(140,110,-160).normalize();world.sun.color.set(0xffe5c6);world.sun.intensity=2.6;world.hemisphere.intensity=.85;scene.environmentIntensity=1.05;
 world.sun.shadow.map?.dispose();world.sun.shadow.map=null;world.sun.shadow.mapSize.set(2048,2048);Object.assign(world.sun.shadow.camera,{left:-38,right:38,top:38,bottom:-38});world.sun.shadow.camera.updateProjectionMatrix();
 // A real clearcoat BRDF (not an unused property on MeshStandardMaterial).
 // The source GLB stays byte-for-byte intact; paint is an export-only art choice.
 const paints=new Map();world.car.traverse(mesh=>{if(!mesh.isMesh||Array.isArray(mesh.material))return;const old=mesh.material;if(!/car_main_paint/i.test(old.name))return;if(!paints.has(old)){const paint=new T.MeshPhysicalMaterial({name:old.name+' / cinematic clearcoat',color:0x8d1828,metalness:.72,roughness:.24,clearcoat:1,clearcoatRoughness:.13,envMapIntensity:1.45,map:old.map,normalMap:old.normalMap,side:old.side});paints.set(old,paint);}mesh.material=paints.get(old);});
 const old=world.water,uniforms=old.material.uniforms;
 const water=new Water(old.geometry,{textureWidth:1024,textureHeight:1024,waterNormals:uniforms.normalSampler.value,sunDirection:world.lightDirection,sunColor:0xffe5c6,waterColor:0x124b48,distortionScale:1.1,fog:true});
 water.position.copy(old.position);water.rotation.copy(old.rotation);world.water=water;scene.remove(old);scene.add(water);
 if(!renderer.extensions.has('EXT_color_buffer_float'))water.material.uniforms.mirrorSampler.value.type=T.UnsignedByteType;
 const reflect=water.onBeforeRender;water.onBeforeRender=(...args)=>{if(world.lastMirrorFrame===world.frame)return;world.lastMirrorFrame=world.frame;world.reflectionFrames++;reflect.apply(water,args);};
 // Export-only contact-occlusion decal: a soft artistic ground shadow, not a
 // claim of ray-traced GI. It grounds the parked hero without extra light passes.
 const contactCanvas=document.createElement('canvas');contactCanvas.width=256;contactCanvas.height=256;const cx=contactCanvas.getContext('2d'),gradient=cx.createRadialGradient(128,128,25,128,128,126);gradient.addColorStop(0,'rgba(0,0,0,.65)');gradient.addColorStop(.55,'rgba(0,0,0,.35)');gradient.addColorStop(1,'rgba(0,0,0,0)');cx.fillStyle=gradient;cx.fillRect(0,0,256,256);
 const contact=new T.Mesh(new T.PlaneGeometry(3.2,6),new T.MeshBasicMaterial({map:new T.CanvasTexture(contactCanvas),transparent:true,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-1}));contact.rotation.set(-Math.PI/2,0,-physics.yaw);contact.position.set(physics.car.translation().x,route[i][1]+.012,physics.car.translation().z);scene.add(contact);
 const offset=new T.Vector3(),target=new T.Vector3(),right=new T.Vector3(),up=new T.Vector3(0,1,0),p=physics.car.translation();
 const panel=document.createElement('div');panel.id='cinematic-titles';panel.style.cssText='position:absolute;inset:0;pointer-events:none;color:#edf3ed;font-family:Arial,Helvetica,sans-serif;text-shadow:0 2px 18px #0009';
 panel.innerHTML='<div style="position:absolute;left:80px;top:68px;font-size:15px;letter-spacing:6px">A / D &nbsp; ALPINE</div><div id="film-title" style="position:absolute;left:80px;bottom:78px"><div style="font-size:12px;letter-spacing:5px;color:#cfdbd7">AN OFFLINE THREE.JS STUDY</div><div style="font-size:54px;letter-spacing:2px;font-weight:700;margin-top:12px">ROADSTER ’20</div><div style="font-size:13px;letter-spacing:3px;margin-top:16px">LAKESIDE &nbsp; / &nbsp; 1080P · 60 FPS</div></div><div style="position:absolute;right:80px;bottom:52px;font-size:10px;letter-spacing:1px;text-align:right;line-height:1.8">Model: metarex.4d · CC-BY-4.0<br>Sky / material sources: Poly Haven · project credits<br>Offline cinematic · not real-time performance</div>';
 document.getElementById('game').append(panel);
 const draw=frame=>{
  const time=frame/FILM.fps,t=Math.min(1,time/seconds),ease=t*t*(3-2*t),angle=T.MathUtils.degToRad(132-77*ease),radius=7.5-.5*Math.sin(t*Math.PI);
  world.update(camera,0);world.person.visible=false;
  offset.set(Math.sin(angle)*radius,1.35+.45*ease,Math.cos(angle)*radius).applyAxisAngle(up,physics.yaw);
  camera.position.set(p.x+offset.x,p.y+offset.y,p.z+offset.z);
  target.set(p.x,p.y+.23,p.z);right.crossVectors(offset,up).normalize();target.addScaledVector(right,-.6);
  camera.lookAt(target);camera.updateMatrixWorld(true);
  // Visibility/detail distances and moving-shadow focus use this exact camera.
  world.update(camera,0);world.person.visible=false;
  world.meadow.time.value=time;water.material.uniforms.time.value=time*.45;
  panel.style.opacity=String(Math.min(1,time*2.5+.05));
  game.renderScene(0);
  return {frame,time,calls:game.gpuStats.calls,triangles:game.gpuStats.triangles,render:[renderer.domElement.width,renderer.domElement.height]};
 };
 draw(0);await renderer.compileAsync(scene,camera);renderer.shadowMap.autoUpdate=false;
 return {draw,settings:{...FILM,seconds,frames:Math.round(seconds*FILM.fps),msaa:composer.multisampling,antialiasing:'FXAA at native 1920x1080; no upscaling',shadow_cache:'Static parked car/lights/scene only; same map reused after warmup',contact_shadow:'Artistic soft decal, not ray-traced GI',directional_shadow:2048,water_reflection:1024,paint:'Export-only red physical clearcoat. Original GLB unchanged.',rendering:'Actual Three.js raster/PBR + photographic sky, not path tracing or a real-time FPS benchmark.'}};
}
