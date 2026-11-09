const keys={KeyW:'forward',ArrowUp:'forward',KeyS:'back',ArrowDown:'back',KeyA:'left',ArrowLeft:'left',KeyD:'right',ArrowRight:'right',ShiftLeft:'run',ShiftRight:'run',Space:'jump'};
/** Independent pointer ownership and source-counted actions prevent stuck pedals. */
export class AlpineInput {
 constructor(canvas,command,look){
  this.canvas=canvas;this.command=command;this.look=look;this.wheelValue=0;this.gear=1;this.steeringMode='wheel';
  try{this.steeringMode=localStorage.getItem('alpine-steering')||'wheel';}catch{}
  if(!['wheel','arrows'].includes(this.steeringMode))this.steeringMode='wheel';document.body.dataset.steering=this.steeringMode;this.sources=new Map();this.pending=new Set();this.stick={x:0,y:0};this.pointers=new Map();this.touch=matchMedia('(pointer:coarse)').matches||navigator.maxTouchPoints>0;
  document.body.classList.toggle('touch',this.touch);
  addEventListener('keydown',e=>{
   if(keys[e.code]){e.preventDefault();this.press('key:'+e.code,keys[e.code]);}
   else if(!e.repeat){const action={KeyE:'interact',KeyR:'reset',Escape:'pause',KeyM:'mute',KeyF:'fullscreen',KeyG:'rays',KeyQ:'rear',KeyN:'night',KeyH:'headlights'}[e.code];if(action)this.command(action);}
  });
  addEventListener('keyup',e=>this.release('key:'+e.code));
  const release=()=>{this.clear();this.command('focusLost');};
  addEventListener('blur',release);document.addEventListener('visibilitychange',()=>{if(document.hidden)release();});
  for(const button of document.querySelectorAll('[data-hold]')){
   button.addEventListener('pointerdown',e=>{e.preventDefault();button.setPointerCapture(e.pointerId);this.press('pointer:'+e.pointerId,button.dataset.hold);button.classList.add('held');});
   for(const type of ['pointerup','pointercancel','lostpointercapture'])button.addEventListener(type,e=>{this.release('pointer:'+e.pointerId);button.classList.remove('held');});
  }
  for(const button of document.querySelectorAll('[data-command]'))button.addEventListener('click',()=>this.command(button.dataset.command));
  this.bindWheel();
  const joy=document.querySelector('#joystick'),knob=joy.querySelector('i');
  const move=e=>{const r=joy.getBoundingClientRect(),radius=r.width/2,x=(e.clientX-r.x-radius)/radius,y=(e.clientY-r.y-radius)/radius,n=Math.max(1,Math.hypot(x,y));this.stick={x:x/n,y:y/n};knob.style.transform=`translate(${this.stick.x*35}px,${this.stick.y*35}px)`;};
  joy.addEventListener('pointerdown',e=>{e.preventDefault();if(this.pointers.has('stick'))return;this.pointers.set('stick',e.pointerId);joy.setPointerCapture(e.pointerId);move(e);});
  joy.addEventListener('pointermove',e=>{if(this.pointers.get('stick')===e.pointerId)move(e);});
  for(const type of ['pointerup','pointercancel','lostpointercapture'])joy.addEventListener(type,e=>{if(this.pointers.get('stick')===e.pointerId){this.pointers.delete('stick');this.stick={x:0,y:0};knob.style.transform='translate(0,0)';}});
  canvas.addEventListener('pointerdown',e=>{if(e.pointerType!=='mouse'&&e.clientX<innerWidth*.4)return;canvas.setPointerCapture(e.pointerId);this.pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});});
  canvas.addEventListener('pointermove',e=>{const previous=this.pointers.get(e.pointerId);if(previous){this.look(e.clientX-previous.x,e.clientY-previous.y);this.pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});}});
  for(const type of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(type,e=>this.pointers.delete(e.pointerId));
  canvas.addEventListener('wheel',e=>{e.preventDefault();this.command(e.deltaY>0?'zoomOut':'zoomIn');},{passive:false});
 }
 setSteeringMode(mode){this.clear();this.steeringMode=mode;document.body.dataset.steering=mode;try{localStorage.setItem('alpine-steering',mode);}catch{}}
 bindWheel(){
  const wheel=document.getElementById('steering-wheel');let owner=null,last=0,total=0;
  this.releaseWheel=()=>{const id=owner;owner=null;total=0;this.wheelValue=0;wheel.style.setProperty('--wheel-angle','0rad');wheel.classList.remove('held');if(id!==null&&wheel.hasPointerCapture(id))wheel.releasePointerCapture(id);};
  const angle=e=>{const r=wheel.getBoundingClientRect();return Math.atan2(e.clientY-r.y-r.height/2,e.clientX-r.x-r.width/2);};
  wheel.addEventListener('pointerdown',e=>{e.preventDefault();if(owner!==null)return;owner=e.pointerId;last=angle(e);total=0;wheel.setPointerCapture(owner);wheel.classList.add('held');});
  wheel.addEventListener('pointermove',e=>{if(e.pointerId!==owner)return;const a=angle(e),delta=Math.atan2(Math.sin(a-last),Math.cos(a-last));last=a;total=Math.max(-2.27,Math.min(2.27,total+delta));this.wheelValue=total/2.27;wheel.style.setProperty('--wheel-angle',total+'rad');});
  for(const type of ['pointerup','pointercancel','lostpointercapture'])wheel.addEventListener(type,e=>{if(e.pointerId===owner){owner=null;total=0;this.wheelValue=0;wheel.style.setProperty('--wheel-angle','0rad');wheel.classList.remove('held');}});
 }
 press(source,action){if(!this.held(action))this.pending.add(action);this.sources.set(source,action);}
 release(source){this.sources.delete(source);}
 held(action){return [...this.sources.values()].includes(action);}
 consume(action){const v=this.pending.has(action);this.pending.delete(action);return v;}
 clear(){this.releaseWheel?.();this.sources.clear();this.pending.clear();this.pointers.clear();this.stick={x:0,y:0};this.wheelValue=0;document.getElementById('steering-wheel')?.style.setProperty('--wheel-angle','0rad');document.querySelectorAll('.held').forEach(n=>n.classList.remove('held'));const knob=document.querySelector('#joystick i');if(knob)knob.style.transform='translate(0,0)';}
 sample(driving,consume=true){
  let x=(this.held('right')?1:0)-(this.held('left')?1:0)+(driving?(this.steeringMode==='wheel'?this.wheelValue:0):this.stick.x);
  let y=(this.held('back')?1:0)-(this.held('forward')?1:0)+(driving?0:this.stick.y);
  const n=driving?1:Math.max(1,Math.hypot(x,y));x=Math.max(-1,Math.min(1,x/n));y=Math.max(-1,Math.min(1,y/n));
  return {x:Math.abs(x)>.1?x:0,y:Math.abs(y)>.1?y:0,throttle:(this.held('forward')?this.gear:0)-(this.held('back')?1:0),brake:this.held('jump')||this.held('brake'),jump:consume?this.consume('jump'):this.pending.has('jump'),run:this.held('run')};
 }
}
