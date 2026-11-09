import {rotate} from './vehicle-math.js';
// Cold-gas-inspired GAME settings, NOT a published Tesla flight time/refill rate.
export const HOP=Object.freeze({poweredSeconds:6,manualSeconds:2.8,refillSeconds:20,minLaunchCharge:85,maxHeight:8});
export class RoadsterFlight {
 constructor(mass=2200){this.mass=mass;this.reset();}
 engage(body){
  if(this.active||!this.grounded||this.energy<HOP.minLaunchCharge)return false;
  this.active=true;this.landing=false;this.elapsed=0;this.airborne=false;this.boosting=false;return true;
 }
 reset(){this.active=false;this.energy=100;this.landing=false;this.elapsed=0;this.airborne=false;this.grounded=false;this.boosting=false;this.thrust=0;this.targetHeight=0;}
 land(){if(this.active)this.landing=true;}
 apply(body,dt,input,groundY,grounded){
  this.grounded=grounded;this.boosting=false;this.thrust=0;
  if(!this.active){if(grounded)this.energy=Math.min(100,this.energy+100/HOP.refillSeconds*dt);return;}
  this.elapsed+=dt;
  const p=body.translation(),v=body.linvel(),q=body.rotation(),w=body.angvel(),up=rotate(q,{x:0,y:1,z:0}),forward=rotate(q,{x:0,y:0,z:-1}),height=Math.max(0,p.y-groundY-.56);
  if(!grounded)this.airborne=true;
  if(this.elapsed>=HOP.manualSeconds||this.energy<35)this.landing=true;
  // Touchdown ends the hop. No re-arming in mid-air and no replenishment on engagement.
  if(grounded&&this.elapsed>.65&&(this.airborne||this.elapsed>1.5)&&Math.abs(v.y)<1.2){this.active=false;return;}
  // A hard powered-time ceiling also bounds use at tiny throttle. Empty means ballistic.
  if(this.energy<=0||this.elapsed>=HOP.poweredSeconds){this.energy=0;this.landing=true;return;}
  const weight=this.mass*9.81;
  let fraction=this.landing?Math.max(0,Math.min(1.6,1+((.15-height)*2.6-v.y*4)/9.81)):
   this.elapsed<.5?1.65:input.lift>0?1.3:input.lift<0?.15:.65;
  if(height>HOP.maxHeight&&!this.landing)fraction=Math.min(fraction,.35);
  this.boosting=!!input.boost&&!this.landing;
  const engine=this.landing?0:Math.max(0,input.throttle||0)*3500+(this.boosting?16000:0);
  // Air braking/attitude corrections consume the SAME finite gas supply.
  const brake=(input.flightBrake||this.landing)?this.mass*.65:0;
  const torque={x:-up.z*22000-w.x*6500,y:(this.landing?0:-(input.x||0)*6500)-w.y*4000,z:up.x*22000-w.z*6500};
  const force={x:forward.x*engine-v.x*brake,y:weight*fraction,z:forward.z*engine-v.z*brake};
  const demand=Math.hypot(force.x,force.y,force.z)+Math.hypot(torque.x,torque.y,torque.z)/2;
  const cost=100/HOP.poweredSeconds*dt*demand/weight,scale=cost>this.energy?this.energy/cost:1;
  this.energy=Math.max(0,this.energy-cost);this.thrust=force.y*scale;
  body.addForce({x:force.x*scale,y:force.y*scale,z:force.z*scale},true);
  body.addTorque({x:torque.x*scale,y:torque.y*scale,z:torque.z*scale},true);
 }
}
export function flightCourse(route){return [32,128,224,320,448,576].map((i,k)=>({x:route[i][0],y:route[i][1]+3,z:route[i][2]}));}
export class FlightChallenge{
 constructor(gates){this.gates=gates;this.reset();}
 reset(){this.next=0;this.completed=0;this.elapsed=0;this.last=null;}
 step(p,dt){this.elapsed+=dt;let event=null;const target=this.gates[this.next];if(this.last){const dx=p.x-this.last.x,dy=p.y-this.last.y,dz=p.z-this.last.z,len=dx*dx+dy*dy+dz*dz,t=len?Math.max(0,Math.min(1,((target.x-this.last.x)*dx+(target.y-this.last.y)*dy+(target.z-this.last.z)*dz)/len)):0;
  if(Math.hypot(this.last.x+dx*t-target.x,this.last.y+dy*t-target.y,this.last.z+dz*t-target.z)<6){this.next++;event={type:'gate',number:this.next};if(this.next===this.gates.length){this.next=0;this.completed++;event={type:'complete',time:this.elapsed};this.elapsed=0;}}
 }this.last={x:p.x,y:p.y,z:p.z};return event;}
}
