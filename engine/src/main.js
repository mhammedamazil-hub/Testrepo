import * as T from 'three';
import {EffectComposer,RenderPass,EffectPass,GodRaysEffect,ToneMappingEffect,ToneMappingMode} from 'postprocessing';
import RAPIER from '@dimforge/rapier3d-compat';
import level from '../level.json';
import {AlpinePhysics,distanceXZ} from './physics.js';
import {AlpineInput} from './input.js';
import {AlpineWorld} from './world.js';
import {ROADSTER} from './vehicle-spec.js';
import './style.css';
const $=id=>document.getElementById(id);

/** Small, original scene/game framework; Three renders, Rapier solves collision. */
class AlpineGame {
 async init(){
  this.phase='loading';this.elapsed=0;this.laps=0;this.checkpoint=0;this.cameraYaw=0;this.cameraPitch=-.19;this.cameraDistance=7.4;this.orbitUntil=0;this.accumulator=0;this.frames=[];this.raysEnabled=true;this.muted=true;
  this.renderer=new T.WebGLRenderer({canvas:$('canvas'),antialias:false,powerPreference:'high-performance',preserveDrawingBuffer:true});
  this.renderer.setPixelRatio(1);this.renderer.setSize(...level.viewport,false);this.renderer.outputColorSpace=T.SRGBColorSpace;
  this.renderer.shadowMap.enabled=true;this.renderer.shadowMap.type=T.PCFShadowMap;this.renderer.toneMapping=T.NoToneMapping;
  this.scene=new T.Scene();this.camera=new T.PerspectiveCamera(66,1920/1080,.15,2200);
  this.physics=await AlpinePhysics.create();this.world=new AlpineWorld(this.scene,this.renderer,this.physics,level);await this.world.load();
  this.input=new AlpineInput($('canvas'),action=>this.command(action),(x,y)=>{
   if(this.phase!=='playing')return;this.cameraYaw-=x*.004;this.cameraPitch=T.MathUtils.clamp(this.cameraPitch-y*.003,-.8,.3);this.orbitUntil=performance.now()+2500;
  });
  this.composer=new EffectComposer(this.renderer,{frameBufferType:this.renderer.extensions.has('EXT_color_buffer_float')?T.HalfFloatType:T.UnsignedByteType});
  this.composer.addPass(new RenderPass(this.scene,this.camera));
  this.rays=new GodRaysEffect(this.camera,this.world.sunDisk,{height:270,samples:48,density:.96,decay:.96,weight:.7,exposure:.45,clampMax:1,blur:true});
  this.tonemap=new ToneMappingEffect({mode:ToneMappingMode.ACES_FILMIC});
  this.effects=new EffectPass(this.camera,this.rays,this.tonemap);this.composer.addPass(this.effects);this.composer.setSize(1920,1080);
  this.reset();this.phase='menu';this.rays.blendMode.opacity.value=0;this.telemetry();$('loading').hidden=true;$('menu').hidden=false;$('status').textContent='ALPINE 0.2 / READY FOR EXPEDITION';
  window.alpineGame=this;window.alpineReady=true;
  this.lastTime=performance.now();this.lastRender=0;requestAnimationFrame(t=>this.frame(t));
 }
 reset(){this.physics.reset(this.world.data.route);this.physics.settle();this.elapsed=0;this.checkpoint=0;this.cameraYaw=this.physics.yaw;this.cameraPitch=-.19;this.accumulator=0;this.cameraInitialized=false;this.input?.clear();this.message('Your Roadster is ready at the overlook.');}
 command(action){
  if(action==='start'||action==='walkStart'){
   if(this.phase==='menu'){
    this.physics.inVehicle=false;this.reset();
    if(action==='start')this.physics.interact();
   }
   this.phase='playing';$('menu').hidden=true;$('pause').hidden=true;this.closeDrawers();this.startAudio();return;
  }
  if(action==='expedition'){this.closeDrawers();return;}
  if(action==='garage'||action==='settings'){
   const id=action==='garage'?'garage-panel':'settings-panel',show=$(id).hidden;
   if(this.phase==='playing')this.command('pause');this.closeDrawers();$(id).hidden=!show;return;
  }
  if(action==='menu'){this.phase='menu';this.input.clear();$('pause').hidden=true;$('menu').hidden=false;this.closeDrawers();return;}
  if(action==='restart'){this.phase='playing';$('pause').hidden=true;this.reset();return;}
  if(action==='night'){this.world.setNight(!this.world.night);this.rays.blendMode.opacity.value=this.raysEnabled&&!this.world.night?1:0;return;}
  if(action==='headlights'){this.world.headlights=!this.world.headlights;this.message(this.world.headlights?'Headlights on':'Headlights off');return;}
  if(action==='pause'||action==='focusLost'){
   if(this.phase==='playing'){this.phase='paused';this.input.clear();$('pause').hidden=false;}
   else if(action==='pause'&&this.phase==='paused')this.command('start');return;
  }
  if(action==='fullscreen'){const p=document.fullscreenElement?document.exitFullscreen():$('game').requestFullscreen();p?.catch(()=>this.message('Fullscreen is unavailable in this browser.'));return;}
  if(action==='mute'){this.muted=!this.muted;this.startAudio();this.message(this.muted?'Sound off':'Sound on');return;}
  if(action==='rays'){this.raysEnabled=!this.raysEnabled;this.rays.blendMode.opacity.value=this.raysEnabled&&!this.world.night?1:0;this.message(this.raysEnabled?'Sun shafts on':'Sun shafts off');return;}
  if(action==='zoomIn'||action==='zoomOut'){this.cameraDistance=T.MathUtils.clamp(this.cameraDistance+(action==='zoomIn'?-1:1),3,14);return;}
  if(action==='rear'){this.cameraYaw+=Math.PI;this.orbitUntil=performance.now()+2500;return;}
  if(this.phase!=='playing')return;
  if(action==='reset'){this.reset();this.message('Recovered to the start.');}
  if(action==='interact'){const result=this.physics.interact();this.message(result.message);if(result.ok){this.cameraInitialized=false;this.input.clear();}}
 }
 closeDrawers(){$('garage-panel').hidden=true;$('settings-panel').hidden=true;}
 startAudio(){
  if(!this.audio&&!this.muted){const Context=window.AudioContext||window.webkitAudioContext;if(Context){this.audio=new Context();this.osc=this.audio.createOscillator();this.osc.type='triangle';this.gain=this.audio.createGain();this.gain.gain.value=0;this.osc.connect(this.gain).connect(this.audio.destination);this.osc.start();}}
  this.audio?.resume().catch(()=>{});
 }
 message(text){$('message').textContent=text;this.messageUntil=performance.now()+6000;}
 tick(dt){
  const input=this.input.sample(this.physics.inVehicle);this.physics.step(dt,input,this.cameraYaw);this.elapsed+=dt;
  const p=this.physics.inVehicle?this.physics.car.translation():this.physics.player.translation();if(p.y< -12){this.reset();return;}
  if(this.physics.inVehicle){const marker=this.world.markers[this.checkpoint];if(distanceXZ(p,marker.position)<7){this.checkpoint++;if(this.checkpoint===this.world.markers.length){this.checkpoint=0;this.laps++;const best=Number(localStorage.getItem('alpine-after-dark-best-v2')||Infinity);if(this.elapsed<best)localStorage.setItem('alpine-after-dark-best-v2',this.elapsed);this.message('Lap complete! '+this.elapsed.toFixed(1)+' seconds');this.elapsed=0;}else this.message('Checkpoint '+this.checkpoint+' / '+this.world.markers.length);}}
 }
 updateCamera(dt){
  if(this.phase==='menu'){
   const p=this.physics.car.translation(),yaw=this.physics.yaw;
   const offset=new T.Vector3(-5.2,1.05,7.4).applyAxisAngle(new T.Vector3(0,1,0),yaw);
   const right=new T.Vector3(offset.z,0,-offset.x).normalize();
   this.camera.position.set(p.x+offset.x,p.y+offset.y,p.z+offset.z);
   this.camera.lookAt(new T.Vector3(p.x,p.y+1.85,p.z).addScaledVector(right,-2.0));
   this.camera.fov=49;this.camera.updateProjectionMatrix();this.camera.updateMatrixWorld();return;
  }
  if(this.camera.fov!==66){this.camera.fov=66;this.camera.updateProjectionMatrix();this.cameraInitialized=false;}
  if(this.physics.inVehicle&&performance.now()>this.orbitUntil){const delta=Math.atan2(Math.sin(this.physics.yaw-this.cameraYaw),Math.cos(this.physics.yaw-this.cameraYaw));this.cameraYaw+=delta*(1-Math.exp(-3*dt));}
  const p=this.physics.inVehicle?this.physics.car.translation():this.physics.player.translation();
  const target=new T.Vector3(p.x,p.y+(this.physics.inVehicle?.45:1.35),p.z),offset=new T.Vector3(Math.sin(this.cameraYaw)*Math.cos(this.cameraPitch),-Math.sin(this.cameraPitch),Math.cos(this.cameraYaw)*Math.cos(this.cameraPitch));
  const hit=this.physics.world.castRay(new RAPIER.Ray(target,offset),this.cameraDistance,true,RAPIER.QueryFilterFlags.EXCLUDE_KINEMATIC,undefined,undefined,this.physics.inVehicle?this.physics.car:undefined);
  const desired=target.clone().addScaledVector(offset,hit?Math.max(1.2,hit.timeOfImpact-.25):this.cameraDistance);
  if(!this.cameraInitialized){this.camera.position.copy(desired);this.cameraInitialized=true;}else this.camera.position.lerp(desired,1-Math.exp(-12*dt));
  this.camera.lookAt(target);this.camera.updateMatrixWorld();
 }
 telemetry(){
  const p=this.physics,position=p.inVehicle?p.car.translation():p.player.translation();
  const sample=this.frames.slice(-120),sorted=[...sample].sort((a,b)=>a-b);
  window.alpineTelemetry={framework:'Alpine 0.2 / After Dark',physics:'Rapier dynamic rigid body / 4 raycast wheels',vehicle_model:'Tesla Roadster 2020 / metarex.4d',vehicle_mass_kg:p.car.mass(),car_dynamic:p.car.isDynamic(),night:this.world.night,headlights:this.world.headlights,wheel_contacts:p.wheelStates.filter(w=>w.contact).length,wheel_suspension:p.wheelStates.map(w=>w.suspension),acceleration_g:p.acceleration/9.81,vehicle_assumptions:ROADSTER.assumptions,authoring:level.compiler,phase:this.phase,paused:this.phase==='paused',in_vehicle:p.inVehicle,touch_enabled:this.input.touch,render_size:[this.renderer.domElement.width,this.renderer.domElement.height],position:{...position},car_position:{...p.car.translation()},player_position:{...p.player.translation()},speed:p.speed,grounded:p.grounded,car_grounded:p.carGrounded,input:this.input.sample(false,false),checkpoint:this.checkpoint,laps:this.laps,elapsed:this.elapsed,reflection_frames:this.world.reflectionFrames,water:'real-time planar mirrored camera',shafts:'screen-space depth-occluded radial scattering',rays_enabled:this.raysEnabled&&!this.world.night,grass_instances:this.world.scatter.grass.length,pine_instances:this.world.data.forest.length,library_grass_triangles:79,native_1080:true,measured_fps:sample.length?1000/(sample.reduce((a,b)=>a+b,0)/sample.length):0,frame_p95_ms:sorted[Math.floor(sorted.length*.95)]||0,physical_phone_tested:false,target_60fps_verified:false};
 }
 hud(){
  const driving=this.physics.inVehicle;document.body.dataset.phase=this.phase;document.body.classList.toggle('driving',driving);
  $('mode').textContent=driving?'ROADSTER / AWD':'EXPEDITION / ON FOOT';$('gear').textContent=!driving?'P':Math.abs(this.physics.speed)<.3?'N':this.physics.speed<0?'R':'D';$('grip').textContent=this.physics.wheelStates.filter(w=>w.contact).length+' / 4 CONTACT';$('gforce').textContent=(Math.abs(this.physics.acceleration)/9.81).toFixed(2)+' G';$('sky-button').textContent=this.world.night?'☾ NIGHT':'☀ DAY';$('sound-button').textContent=this.muted?'SOUND OFF':'SOUND ON';$('speed').textContent=driving?Math.round(Math.abs(this.physics.speed)*3.6):Math.round(Math.hypot(this.physics.footVelocity.x,this.physics.footVelocity.z)*3.6);
  $('checkpoint').textContent=`${this.checkpoint} / ${this.world.markers.length}`;$('time').textContent=this.elapsed.toFixed(1)+'s';$('lap').textContent=this.laps;
  $('interact').textContent=driving?'EXIT':'ENTER';$('jump').textContent=driving?'BRAKE':'JUMP';
  if(performance.now()>this.messageUntil)$('message').textContent=driving?'Follow the green checkpoint rings.':distanceXZ(this.physics.player.translation(),this.physics.car.translation())<4.3?'E / ENTER · Get in your car':'WASD to walk · Shift to run · Space to jump';
  for(let i=0;i<this.world.markers.length;i++)this.world.markers[i].material.color.set(i===this.checkpoint?0xb7f5aa:0x648c7c);
  if(this.gain){this.gain.gain.setTargetAtTime(this.muted||this.phase!=='playing'?0:driving?.014:.002,this.audio.currentTime,.1);this.osc.frequency.setTargetAtTime(driving?110+Math.abs(this.physics.speed)*13:35,this.audio.currentTime,.1);}
 }
 frame(now){
  requestAnimationFrame(t=>this.frame(t));if(now-this.lastRender<1000/60-.5)return;
  const wall=(now-this.lastTime)/1000;this.lastTime=now;this.lastRender=now;this.frames.push(wall*1000);if(this.frames.length>180)this.frames.shift();
  const dt=Math.min(wall,.1);if(this.phase==='playing'){this.accumulator+=dt;while(this.accumulator>=1/60){this.tick(1/60);this.accumulator-=1/60;}}
  this.updateCamera(dt);this.world.update(this.camera,this.phase==='playing'?dt:0);this.world.person.visible=this.phase!=='menu'&&!this.physics.inVehicle;for(const marker of this.world.markers)marker.visible=this.phase!=='menu';this.composer.render(dt);this.hud();this.telemetry();
 }
}
const game=new AlpineGame();game.init().catch(error=>{console.error(error);$('loading').textContent='Unable to start WebGL2: '+error.message+'. Try a current WebGL2-capable browser and reload.';$('status').textContent='STARTUP ERROR';});
