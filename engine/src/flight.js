import {rotate} from './vehicle-math.js';
// Fictional game-only thrusters. Not a Tesla specification or manufacturer system.
export class RoadsterFlight {
 constructor(mass=2200){this.mass=mass;this.active=false;this.energy=100;this.landing=false;this.targetHeight=0;this.boosting=false;this.thrust=0;}
 engage(body){if(this.active)return;this.active=true;this.landing=false;this.targetHeight=body.translation().y+6;this.energy=100;}
 reset(){this.active=false;this.landing=false;this.boosting=false;this.energy=100;this.thrust=0;}
 land(){if(this.active)this.landing=true;}
 apply(body,dt,input,groundY,grounded){
  if(!this.active){this.energy=Math.min(100,this.energy+18*dt);return;}
  const p=body.translation(),v=body.linvel(),q=body.rotation(),w=body.angvel(),up=rotate(q,{x:0,y:1,z:0}),forward=rotate(q,{x:0,y:0,z:-1});
  if(this.landing)this.targetHeight=Math.max(groundY+.56,this.targetHeight-3.5*dt);
  else this.targetHeight=Math.max(groundY+1.1,Math.min(120,this.targetHeight+(input.lift||0)*7*dt));
  const acceleration=Math.max(-7,Math.min(11,(this.targetHeight-p.y)*3.6-v.y*3));
  this.thrust=this.mass*(9.81+acceleration);
  this.boosting=!!input.boost&&this.energy>1&&!this.landing;
  this.energy=Math.max(0,Math.min(100,this.energy+(this.boosting?-25:15)*dt));
  const engine=this.landing?0:Math.max(0,input.throttle||0)*9000+(this.boosting?18000:0),drag=(input.flightBrake||this.landing)?this.mass*2.1:this.mass*.23;
  body.addForce({x:forward.x*engine-v.x*drag,y:this.thrust,z:forward.z*engine-v.z*drag},true);
  body.addTorque({x:-up.z*22000-w.x*9000,y:(this.landing?0:-(input.x||0)*10000)-w.y*6000,z:up.x*22000-w.z*9000},true);
  if(this.landing&&grounded&&p.y<groundY+1&&Math.abs(v.y)<.6&&Math.hypot(v.x,v.z)<.6)this.reset();
 }
}
export function flightCourse(route){return [32,128,224,320,448,576].map((i,k)=>({x:route[i][0],y:route[i][1]+12+(k%3)*5,z:route[i][2]}));}
export class FlightChallenge{
 constructor(gates){this.gates=gates;this.reset();}
 reset(){this.next=0;this.completed=0;this.elapsed=0;this.last=null;}
 step(p,dt){this.elapsed+=dt;let event=null;const target=this.gates[this.next];if(this.last){const dx=p.x-this.last.x,dy=p.y-this.last.y,dz=p.z-this.last.z,len=dx*dx+dy*dy+dz*dz,t=len?Math.max(0,Math.min(1,((target.x-this.last.x)*dx+(target.y-this.last.y)*dy+(target.z-this.last.z)*dz)/len)):0;
  if(Math.hypot(this.last.x+dx*t-target.x,this.last.y+dy*t-target.y,this.last.z+dz*t-target.z)<6){this.next++;event={type:'gate',number:this.next};if(this.next===this.gates.length){this.next=0;this.completed++;event={type:'complete',time:this.elapsed};this.elapsed=0;}}
 }this.last={x:p.x,y:p.y,z:p.z};return event;}
}
