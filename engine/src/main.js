import * as T from 'three';
import {EffectComposer,RenderPass,EffectPass,GodRaysEffect,ToneMappingEffect,ToneMappingMode} from 'postprocessing';
import RAPIER from '@dimforge/rapier3d-compat';
import level from '../level.json';
import {AlpinePhysics,distanceXZ} from './physics.js';
import {AlpineInput} from './input.js';
import {AlpineWorld} from './world.js';
import {ROADSTER} from './vehicle-spec.js';
import {CircuitProgress,nearestRoute,routeHint} from './track.js';
import {FlightChallenge,flightCourse,HOP} from './flight.js';
import {TimeTrial} from './race.js';
import {updateText,updateHTML} from './ui-value.js';
import './style.css';
const elements=new Map();const $=id=>{if(!elements.has(id))elements.set(id,document.getElementById(id));return elements.get(id);};

/** Small, original scene/game framework; Three renders, Rapier solves collision. */
class AlpineGame {
 async init(){
  let storage;try{storage=localStorage;}catch{}this.trial=new TimeTrial(storage);this.cameraTarget=new T.Vector3();this.cameraOffset=new T.Vector3();this.cameraDesired=new T.Vector3();this.dirty=true;this.launchMode='drive';this.lastHUD=0;this.lastTelemetry=0;this.gpuStats={};this.quality='full';try{this.quality=localStorage.getItem('alpine-graphics')||'full';}catch{}if(!['full','balanced','performance'].includes(this.quality))this.quality='full';this.assist=true;this.throttle=0;this.offroadTime=0;this.phase='loading';this.elapsed=0;this.laps=0;this.checkpoint=0;this.cameraYaw=0;this.cameraPitch=-.19;this.cameraDistance=7.4;this.orbitUntil=0;this.accumulator=0;this.frames=[];this.raysEnabled=true;this.muted=true;
  this.renderer=new T.WebGLRenderer({canvas:$('canvas'),antialias:false,powerPreference:'high-performance',preserveDrawingBuffer:false,alpha:false});
  this.renderer.info.autoReset=false;this.renderer.setPixelRatio(1);this.renderer.setSize(...level.viewport,false);this.renderer.outputColorSpace=T.SRGBColorSpace;
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
  this.effects=new EffectPass(this.camera,this.rays,this.tonemap);this.composer.addPass(this.effects);this.clearEffects=new EffectPass(this.camera,new ToneMappingEffect({mode:ToneMappingMode.ACES_FILMIC}));this.composer.addPass(this.clearEffects);this.composer.setSize(1920,1080);
  this.flightChallenge=new FlightChallenge(flightCourse(this.world.data.route));this.circuit=new CircuitProgress(this.world.data.route,this.world.track.gates);this.initMap();this.reset();this.resize();addEventListener('resize',()=>this.resize());this.phase='menu';this.syncEffects();this.updateCamera(1/60);this.world.update(this.camera,0);$('loading').querySelector('p').textContent='Warming materials for a smoother first drive…';await this.renderer.compileAsync(this.scene,this.camera);this.telemetry();$('loading').hidden=true;$('menu').hidden=false;updateText($('status'),'ALPINE 0.5 / READY TO LAUNCH');
  window.alpineGame=this;window.alpineReady=true;
  this.lastTime=performance.now();this.lastRender=0;requestAnimationFrame(t=>this.frame(t));
 }
 syncEffects(){const enabled=this.raysEnabled&&!this.world.night;this.effects.enabled=enabled;this.clearEffects.enabled=!enabled;this.rays.blendMode.opacity.value=enabled?1:0;this.effects.renderToScreen=enabled;this.clearEffects.renderToScreen=!enabled;}
 renderScene(dt){this.renderer.info.reset();this.composer.render(dt);this.gpuStats={calls:this.renderer.info.render.calls,triangles:this.renderer.info.render.triangles};}
 resize(){
  this.dirty=true;
  const width=$('game').clientWidth,height=$('game').clientHeight,budget={full:1920*1080,balanced:1280*720,performance:960*540}[this.quality],scale=Math.sqrt(budget/(width*height));
  const w=Math.round(width*scale),h=Math.round(height*scale);this.renderer.setSize(w,h,false);this.composer.setSize(w,h);this.camera.aspect=width/height;this.camera.updateProjectionMatrix();
 }
 initMap(){
  const points=this.world.data.route,x=points.map(p=>p[0]),z=points.map(p=>p[2]),minX=Math.min(...x),minZ=Math.min(...z),scale=170/Math.max(Math.max(...x)-minX,Math.max(...z)-minZ);
  this.mapPoint=p=>({x:15+(p.x-minX)*scale,y:15+(p.z-minZ)*scale});
  const d=points.filter((_,i)=>i%4===0).map((p,i)=>{const v=this.mapPoint({x:p[0],z:p[2]});return (i?'L':'M')+v.x.toFixed(1)+' '+v.y.toFixed(1);}).join(' ')+' Z';
  $('map-outline').setAttribute('d',d);$('map-route').setAttribute('d',d);
 }
 reset(){this.physics.reset(this.world.data.route);this.physics.settle();this.elapsed=0;this.checkpoint=0;this.laps=0;this.circuit?.reset();this.flightChallenge?.reset();this.trial.reset();this.throttle=0;this.offroadTime=0;this.input&&(this.input.gear=1);this.cameraYaw=this.physics.yaw;this.cameraPitch=-.19;this.accumulator=0;this.cameraInitialized=false;this.input?.clear();this.message('Lakeside circuit · four gates · cross the finish to complete a lap.');}
 recover(){
  this.trial.invalidate('RECOVERY USED');const near=nearestRoute(this.world.data.route,this.physics.car.translation()),i=near.index,n=this.world.data.route.length;
  this.physics.reset([this.world.data.route[i],this.world.data.route[(i+1)%n],this.world.data.route[(i+2)%n]]);this.physics.settle();this.cameraYaw=this.physics.yaw;this.cameraInitialized=false;this.throttle=0;this.offroadTime=0;this.input.clear();this.input.gear=1;this.circuit.last=null;
  // Recovery cannot teleport over the next ordered checkpoint to earn progress.
  this.message('Recovered to the nearest safe road position. Lap timer continues.');
 }
 command(action){
  this.dirty=true;
  if(action==='start'||action==='walkStart'){
   if(this.phase==='menu'){
    this.physics.inVehicle=false;this.reset();
    if(action==='start')this.physics.interact();
   }
   if(this.launchMode==='flight'&&action==='start'&&this.phase==='menu')this.physics.flight.engage(this.physics.car);
   this.phase='playing';$('menu').hidden=true;$('pause').hidden=true;this.closeDrawers();this.startAudio();return;
  }
  if(action==='selectDrive'||action==='selectFlight'){this.launchMode=action==='selectFlight'?'flight':'drive';this.hud();return;}
  if(action==='training'){this.launchMode='flight';this.phase='menu';this.command('start');return;}
  if(action==='flight'){if(!this.physics.inVehicle){this.message('Enter the Roadster to arm fictional flight.');return;}if(this.physics.flight.active)this.physics.flight.land();else{const ok=this.physics.flight.engage(this.physics.car);if(ok){this.trial.countdown=0;this.trial.invalidate('THRUSTER HOP USED');this.input.clear();this.message('SHORT HOP · shared gas supply · auto descent · ground-only refill.');}else this.message('Hop needs ground contact and 85% gas. Refill on the ground (20s game setting).');}return;}
  if(action==='land'){this.physics.flight.land();return;}
  if(action==='wheel'||action==='arrows'||action==='steering'){this.input.setSteeringMode(action==='steering'?(this.input.steeringMode==='wheel'?'arrows':'wheel'):action);return;}
  if(action==='quality'){const modes=['full','balanced','performance'];this.quality=modes[(modes.indexOf(this.quality)+1)%3];try{localStorage.setItem('alpine-graphics',this.quality);}catch{}this.resize();return;}
  if(action==='assist'){this.assist=!this.assist;if(this.elapsed>0)this.trial.invalidate('ASSIST CHANGED');return;}
  if(action==='gear'){if(Math.abs(this.physics.speed)>1.5){this.message('Brake to a stop before changing D / R.');return;}this.input.clear();this.input.gear*=-1;this.physics.autoHold=true;this.throttle=0;return;}
  if(action==='expedition'){this.closeDrawers();return;}
  if(action==='garage'||action==='settings'){
   const id=action==='garage'?'garage-panel':'settings-panel',show=$(id).hidden;
   if(this.phase==='playing')this.command('pause');this.closeDrawers();$(id).hidden=!show;return;
  }
  if(action==='menu'){this.physics.inVehicle=false;this.reset();this.phase='menu';this.input.clear();$('pause').hidden=true;$('menu').hidden=false;this.closeDrawers();return;}
  if(action==='restart'){this.phase='playing';$('pause').hidden=true;this.reset();return;}
  if(action==='night'){this.world.setNight(!this.world.night);this.syncEffects();return;}
  if(action==='headlights'){this.world.headlights=!this.world.headlights;this.message(this.world.headlights?'Headlights on':'Headlights off');return;}
  if(action==='pause'||action==='focusLost'){
   if(this.phase==='playing'){this.phase='paused';this.input.clear();$('pause').hidden=false;}
   else if(action==='pause'&&this.phase==='paused')this.command('start');return;
  }
  if(action==='fullscreen'){const p=document.fullscreenElement?document.exitFullscreen():$('game').requestFullscreen();p?.catch(()=>this.message('Fullscreen is unavailable in this browser.'));return;}
  if(action==='mute'){this.muted=!this.muted;this.startAudio();this.message(this.muted?'Sound off':'Sound on');return;}
  if(action==='rays'){this.raysEnabled=!this.raysEnabled;this.syncEffects();this.message(this.raysEnabled?'Sun shafts on':'Sun shafts off');return;}
  if(action==='zoomIn'||action==='zoomOut'){this.cameraDistance=T.MathUtils.clamp(this.cameraDistance+(action==='zoomIn'?-1:1),3,14);return;}
  if(action==='rear'){this.cameraYaw+=Math.PI;this.orbitUntil=performance.now()+2500;return;}
  if(this.phase!=='playing')return;
  if(action==='reset'){this.recover();}
  if(action==='interact'){const result=this.physics.interact();this.message(result.message);if(result.ok){this.cameraInitialized=false;this.throttle=0;this.input.clear();}}
 }
 closeDrawers(){$('garage-panel').hidden=true;$('settings-panel').hidden=true;}
 startAudio(){
  if(!this.audio&&!this.muted){const Context=window.AudioContext||window.webkitAudioContext;if(Context){this.audio=new Context();this.osc=this.audio.createOscillator();this.osc.type='triangle';this.gain=this.audio.createGain();this.gain.gain.value=0;this.osc.connect(this.gain).connect(this.audio.destination);this.osc.start();}}
  this.audio?.resume().catch(()=>{});
 }
 message(text){updateText($('message'),text);this.messageUntil=performance.now()+6000;}
 tick(dt){
  const input=this.input.sample(this.physics.inVehicle),car=this.physics.car.translation();
  this.nearest=nearestRoute(this.world.data.route,car,this.nearest);this.hint=routeHint(this.world.data.route,this.nearest,this.physics.speed);
  if(this.physics.inVehicle&&this.launchMode==='drive'&&this.trial.countdown>0){this.trial.advance(dt);input.throttle=0;input.brake=true;this.throttle=0;this.physics.step(dt,input,this.cameraYaw);return;}
  // Accessible road assist changes force requests, never the rigid body's transform or velocity.
  const requested=input.throttle;this.throttle=T.MathUtils.damp(this.throttle,requested,requested?2.2:9,dt);input.throttle=this.throttle;if(requested*this.physics.speed<-.3)input.brake=true;
  if(this.assist&&this.physics.inVehicle&&!this.physics.flight.active&&requested>0){const limit=this.hint.recommended;input.throttle*=T.MathUtils.clamp((limit+2-this.physics.speed)/4,0,1);if(this.physics.speed>limit+3)input.brake=true;}
  this.physics.step(dt,input,this.cameraYaw);
  const p=this.physics.inVehicle?this.physics.car.translation():this.physics.player.translation();
  if(p.y< -1.5){this.recover();return;}
  if(this.physics.inVehicle&&this.physics.flight.active){this.trial.invalidate('THRUSTER HOP USED');this.circuit.last=null;const event=this.flightChallenge.step(p,dt);if(event)this.message(event.type==='complete'?'FLIGHT COURSE COMPLETE · '+event.time.toFixed(1)+'s':'AIR GATE '+event.number+' / 6');return;}
  if(this.physics.inVehicle){
   this.offroadTime=this.nearest.distance>12?this.offroadTime+dt:0;if(this.offroadTime>8){this.recover();return;}
   const event=this.circuit.step(p,dt);this.elapsed=this.circuit.elapsed;this.checkpoint=this.circuit.next;this.laps=this.circuit.laps;
   if(event?.type==='lap'){const result=this.trial.finish(event.time,this.assist);this.message((result.valid?result.medal+' · '+(result.record?'PERSONAL BEST':'LAP COMPLETE'):'PRACTICE LAP · '+result.reason)+' · '+event.time.toFixed(2)+'s · next lap is live');}
   else if(event){this.trial.checkpoint(this.circuit.elapsed,this.assist);this.message('SECTOR '+event.number+' / 3 · '+(this.trial.delta===null?'set your first benchmark':(this.trial.delta<=0?'AHEAD ':'BEHIND ')+Math.abs(this.trial.delta).toFixed(2)+'s'));}
  }
 }
 updateCamera(dt){
  if(this.phase==='menu'){
   const p=this.physics.car.translation(),yaw=this.physics.yaw;
   const offset=new T.Vector3(-5.2,1.05,7.4).multiplyScalar(this.camera.aspect<1?1.4:1).applyAxisAngle(new T.Vector3(0,1,0),yaw);
   const right=new T.Vector3(offset.z,0,-offset.x).normalize();
   this.camera.position.set(p.x+offset.x,p.y+offset.y,p.z+offset.z);
   this.camera.lookAt(new T.Vector3(p.x,p.y+1.85,p.z).addScaledVector(right,this.camera.aspect<1?-.4:-2.0));
   this.camera.fov=49;this.camera.updateProjectionMatrix();this.camera.updateMatrixWorld();return;
  }
  if(this.camera.fov!==66){this.camera.fov=66;this.camera.updateProjectionMatrix();this.cameraInitialized=false;}
  if(this.physics.inVehicle&&performance.now()>this.orbitUntil){const delta=Math.atan2(Math.sin(this.physics.yaw-this.cameraYaw),Math.cos(this.physics.yaw-this.cameraYaw));this.cameraYaw+=delta*(1-Math.exp(-3*dt));}
  const p=this.physics.inVehicle?this.physics.car.translation():this.physics.player.translation();
  const target=this.cameraTarget.set(p.x,p.y+(this.physics.inVehicle?.45:1.35),p.z),offset=this.cameraOffset.set(Math.sin(this.cameraYaw)*Math.cos(this.cameraPitch),-Math.sin(this.cameraPitch),Math.cos(this.cameraYaw)*Math.cos(this.cameraPitch));
  const viewDistance=this.cameraDistance*(this.camera.aspect<1?1.45:1);
  const hit=this.physics.world.castRay(new RAPIER.Ray(target,offset),viewDistance,true,RAPIER.QueryFilterFlags.EXCLUDE_KINEMATIC,undefined,undefined,this.physics.inVehicle?this.physics.car:undefined);
  const desired=this.cameraDesired.copy(target).addScaledVector(offset,hit?Math.max(1.2,hit.timeOfImpact-.25):viewDistance);
  if(!this.cameraInitialized){this.camera.position.copy(desired);this.cameraInitialized=true;}else this.camera.position.lerp(desired,1-Math.exp(-12*dt));
  this.camera.lookAt(target);this.camera.updateMatrixWorld();
 }
 telemetry(){
  const p=this.physics,position=p.inVehicle?p.car.translation():p.player.translation();
  const sample=this.frames.slice(-120),sorted=[...sample].sort((a,b)=>a-b);
  window.alpineTelemetry={framework:'Alpine 0.5 / Short Hop Time Attack',physics:'Rapier dynamic rigid body / 4 raycast wheels',vehicle_model:'Tesla Roadster 2020 / metarex.4d',vehicle_mass_kg:p.car.mass(),car_dynamic:p.car.isDynamic(),night:this.world.night,headlights:this.world.headlights,wheel_contacts:p.wheelStates.filter(w=>w.contact).length,wheel_suspension:p.wheelStates.map(w=>w.suspension),acceleration_g:p.acceleration/9.81,vehicle_assumptions:ROADSTER.assumptions,authoring:level.compiler,phase:this.phase,paused:this.phase==='paused',in_vehicle:p.inVehicle,touch_enabled:this.input.touch,render_size:[this.renderer.domElement.width,this.renderer.domElement.height],position:{...position},car_position:{...p.car.translation()},player_position:{...p.player.translation()},speed:p.speed,grounded:p.grounded,car_grounded:p.carGrounded,flight_active:p.flight.active,flight_seconds_left:Math.max(0,HOP.poweredSeconds-p.flight.elapsed),flight_powered_limit:HOP.poweredSeconds,flight_refill_ground_only:true,race_valid:this.trial.valid,race_countdown:this.trial.countdown,race_best:this.trial.best,static_nodes:this.world.staticNodes,track_art:{kerbs:this.world.trackArt.kerbs,boards:this.world.trackArt.boards,reflectors:this.world.trackArt.reflectors},flight_boost:p.flight.energy,flight_target_height:p.flight.targetHeight,flight_landing:p.flight.landing,flight_gate:this.flightChallenge.next,meadow_instances:this.world.meadow.count,vehicle_batch_enabled:this.world.vehicleBatch.enabled,vehicle_batches:this.world.vehicleBatch.batch_count,gpu:this.gpuStats,night_pass_bypassed:!this.effects.enabled,preserve_drawing_buffer:this.renderer.getContext().getContextAttributes().preserveDrawingBuffer,input:this.input.sample(p.inVehicle,false),checkpoint:this.checkpoint,laps:this.laps,elapsed:this.elapsed,reflection_frames:this.world.reflectionFrames,water:'real-time planar mirrored camera',shafts:'screen-space depth-occluded radial scattering',rays_enabled:this.raysEnabled&&!this.world.night,grass_instances:this.world.scatter.grass.length,pine_instances:this.world.data.forest.length,library_grass_triangles:79,native_1080:false,graphics_quality:this.quality,render_pixel_budget:{full:1920*1080,balanced:1280*720,performance:960*540}[this.quality],responsive_view:true,steering_mode:this.input.steeringMode,road_assist:this.assist,track_width:this.world.track.width,route_distance:this.nearest?.distance||0,measured_fps:sample.length?1000/(sample.reduce((a,b)=>a+b,0)/sample.length):0,frame_p95_ms:sorted[Math.floor(sorted.length*.95)]||0,physical_phone_tested:false,target_60fps_verified:false};
  updateText($('performance-summary'),(window.alpineTelemetry.measured_fps||0).toFixed(0)+' FPS locally · '+(this.gpuStats.calls||0)+' draw calls · '+this.quality.toUpperCase()+' graphics. Device-specific; not a 60 FPS certificate.');
 }
 hud(){
  const driving=this.physics.inVehicle,flying=this.physics.flight.active;document.body.classList.toggle('flight',flying);document.body.dataset.phase=this.phase;document.body.classList.toggle('driving',driving);
  updateText($('mode'),flying?'ROADSTER / SHORT THRUSTER HOP':driving?'ROADSTER / AWD':'EXPEDITION / ON FOOT');updateText($('gear'),!driving?'P':this.input.gear<0||this.physics.speed<-.3?'R':'D');updateText($('grip'),this.physics.wheelStates.filter(w=>w.contact).length+' / 4 CONTACT');updateText($('gforce'),(Math.abs(this.physics.acceleration)/9.81).toFixed(2)+' G');updateText($('sky-button'),this.world.night?'☾ NIGHT':'☀ DAY');updateText($('sound-button'),this.muted?'SOUND OFF':'SOUND ON');updateText($('speed'),driving?Math.round(Math.abs(this.physics.speed)*3.6):Math.round(Math.hypot(this.physics.footVelocity.x,this.physics.footVelocity.z)*3.6));
  updateText($('checkpoint'),`${this.checkpoint} / ${this.world.markers.length}`);updateText($('lap'),this.laps);
  updateText($('interact'),driving?'EXIT':'ENTER');updateText($('jump'),'JUMP');
  updateHTML($('reverse-gear'),this.input.gear<0?'R <span>/ D</span>':'D <span>/ R</span>');$('reverse-gear').setAttribute('aria-pressed',String(this.input.gear<0));
  for(const mode of ['wheel','arrows'])$('setting-'+mode).setAttribute('aria-pressed',String(this.input.steeringMode===mode));
  updateText($('setting-quality'),'GRAPHICS · '+this.quality.toUpperCase());
  $('setting-assist').setAttribute('aria-pressed',String(this.assist));updateText($('setting-assist'),this.assist?'ROAD ASSIST ON':'ROAD ASSIST OFF');updateText($('assist-state'),this.assist?'ROAD ASSIST ON':'ROAD ASSIST OFF');
  const car=this.physics.car.translation(),near=this.nearest||nearestRoute(this.world.data.route,car),hint=this.hint||routeHint(this.world.data.route,near,0),gate=this.world.data.route[this.world.track.gates[this.checkpoint]];
  const pos=this.mapPoint(driving?car:this.physics.player.translation()),target=this.mapPoint({x:gate[0],z:gate[2]});$('map-car').setAttribute('transform',`translate(${pos.x} ${pos.y}) rotate(${-this.physics.yaw*180/Math.PI})`);$('map-target').setAttribute('cx',target.x);$('map-target').setAttribute('cy',target.y);
  $('progress-fill').style.width=(near.index/this.world.data.route.length*100)+'%';
  const velocity=this.physics.car.linvel(),wrongWay=velocity.x*near.tangent.x+velocity.z*near.tangent.z< -2;
  updateText($('turn-icon'),near.distance>6?'↩':wrongWay?'↶':hint.turn==='LEFT'?'↰':hint.turn==='RIGHT'?'↱':'↑');updateText($('route-hint'),near.distance>6?'RETURN TO THE ROAD':wrongWay?'WRONG WAY':hint.turn==='STRAIGHT'?'FOLLOW THE CIRCUIT':hint.turn+' BEND');updateText($('route-distance'),driving?Math.round(hint.recommended*3.6)+' KM/H':'');
  updateText($('time'),Math.floor(this.elapsed/60)+':'+(this.elapsed%60).toFixed(1).padStart(4,'0'));
  this.flightHUD(flying);
  const best=this.trial.best,comparable=best?.assisted===this.assist;updateText($('trial-best'),'PB '+(comparable?best.time.toFixed(2)+'s':'—')+' · '+(this.assist?'ASSIST':'MANUAL'));updateText($('trial-delta'),!this.trial.valid?'PRACTICE · '+this.trial.reason:this.trial.delta===null?'GOLD ≤2:10 · 3 SECTORS':(this.trial.delta<=0?'−':'+')+Math.abs(this.trial.delta).toFixed(2)+'s LAST SPLIT');$('trial-delta').dataset.ahead=String(this.trial.delta!==null&&this.trial.delta<=0);$('countdown').hidden=!(driving&&this.launchMode==='drive'&&this.trial.countdown>0&&this.phase==='playing');updateText($('countdown'),Math.ceil(this.trial.countdown));$('trial-readout').hidden=this.launchMode==='flight'||!driving;
  if(performance.now()>this.messageUntil)updateText($('message'),driving?'':distanceXZ(this.physics.player.translation(),this.physics.car.translation())<4.3?'E / ENTER · Get in your car':'WASD to walk · Shift to run · Space to jump');
  for(let i=0;i<this.world.markers.length;i++)this.world.markers[i].material.color.set(i===this.checkpoint?0xb7f5aa:0x648c7c);
  if(this.gain){this.gain.gain.setTargetAtTime(this.muted||this.phase!=='playing'?0:driving?.014:.002,this.audio.currentTime,.1);this.osc.frequency.setTargetAtTime(driving?110+Math.abs(this.physics.speed)*13:35,this.audio.currentTime,.1);}
 }
 flightHUD(flying){
  $('launch-drive').setAttribute('aria-pressed',String(this.launchMode==='drive'));$('launch-flight').setAttribute('aria-pressed',String(this.launchMode==='flight'));updateText($('launch-subtitle'),this.launchMode==='flight'?'SHORT HOP TRAINING':'LAKESIDE CIRCUIT');updateText($('launch-description'),this.launchMode==='flight'?'Finite cold-gas-inspired hops. 6s powered limit / 20s ground refill are game settings.':'Four-wheel suspension. One continuous mountain circuit.');
  const f=this.physics.flight;updateText($('flight-toggle'),flying?'LAND':'HOP');updateText($('boost-level'),Math.round(f.energy));updateText($('hop-time'),flying?(Math.max(0,HOP.poweredSeconds-f.elapsed)).toFixed(1)+'s MAX':(f.energy>=85?'READY':'GROUND REFILL'));$('boost-fill').style.width=f.energy+'%';$('boost-control').style.setProperty('--boost',f.energy+'%');updateText($('altitude'),Math.max(0,Math.round(this.physics.car.translation().y)));updateText($('discipline'),flying?'THRUSTER HOP':'LAKESIDE / TIME ATTACK');
  if(flying){updateText($('lap'),this.flightChallenge.completed);const target=this.flightChallenge.gates[this.flightChallenge.next],pos=this.mapPoint(target);$('map-target').setAttribute('cx',pos.x);$('map-target').setAttribute('cy',pos.y);updateText($('checkpoint'),this.flightChallenge.next+' / 6');updateText($('route-hint'),f.energy<=0?'GAS EMPTY · GRAVITY':f.landing?'DESCENT · RESERVE GAS':'SHORT HOP · FINITE GAS');updateText($('turn-icon'),f.landing?'↓':'◇');updateText($('route-distance'),Math.round(target.y)+' M ALT');updateText($('time'),this.flightChallenge.elapsed.toFixed(1)+'s');$('progress-fill').style.width=this.flightChallenge.next/6*100+'%';}
 }
 frame(now){
  requestAnimationFrame(t=>this.frame(t));if(document.hidden||(this.phase!=='playing'&&!this.dirty)){this.lastTime=now;return;}if(now-this.lastRender<1000/60-.5)return;
  const wall=(now-this.lastTime)/1000;this.lastTime=now;this.lastRender=now;this.frames.push(wall*1000);if(this.frames.length>180)this.frames.shift();
  const dt=Math.min(wall,.1);if(this.phase==='playing'){this.accumulator+=dt;while(this.accumulator>=1/60){this.tick(1/60);this.accumulator-=1/60;}}
  this.updateCamera(dt);this.world.update(this.camera,this.phase==='playing'?dt:0);this.world.person.visible=this.phase!=='menu'&&!this.physics.inVehicle;for(const [i,marker] of this.world.markers.entries())marker.visible=this.phase!=='menu'&&!this.physics.flight.active&&i===this.checkpoint;for(const [i,gate] of this.world.flightGates.entries())gate.visible=this.phase==='playing'&&this.physics.flight.active&&i===this.flightChallenge.next;this.renderScene(dt);this.dirty=false;if(now-this.lastHUD>50){this.hud();this.lastHUD=now;}if(now-this.lastTelemetry>250){this.telemetry();this.lastTelemetry=now;}
 }
}
const game=new AlpineGame();game.init().catch(error=>{console.error(error);updateText($('loading'),'Unable to start WebGL2: '+error.message+'. Try a current WebGL2-capable browser and reload.');updateText($('status'),'STARTUP ERROR');});
