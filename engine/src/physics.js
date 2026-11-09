import RAPIER from '@dimforge/rapier3d-compat';
import {ROADSTER as SPEC} from './vehicle-spec.js';
export const moveToward=(v,t,d)=>v<t?Math.min(t,v+d):Math.max(t,v-d);
export const distanceXZ=(a,b)=>Math.hypot(a.x-b.x,a.z-b.z);
const identity={x:0,y:0,z:0,w:1};
const neutral={x:0,y:0,throttle:0,brake:false,jump:false,run:false};
export function rotate(q,v){
 const tx=2*(q.y*v.z-q.z*v.y),ty=2*(q.z*v.x-q.x*v.z),tz=2*(q.x*v.y-q.y*v.x);
 return {x:v.x+q.w*tx+q.y*tz-q.z*ty,y:v.y+q.w*ty+q.z*tx-q.x*tz,z:v.z+q.w*tz+q.x*ty-q.y*tx};
}

/** Dynamic rigid-body vehicle + actual Rapier raycast tire/spring solver.
 * No direct speed/yaw/translation assignment during ordinary driving.
 */
export class AlpinePhysics {
 static async create(){await RAPIER.init();return new AlpinePhysics();}
 constructor(){
  this.world=new RAPIER.World({x:0,y:-9.81,z:0});this.world.timestep=1/60;
  this.player=this.world.createRigidBody(RAPIER.RigidBodyDesc.kinematicPositionBased());
  this.playerCollider=this.world.createCollider(RAPIER.ColliderDesc.capsule(.62,.27).setTranslation(0,.89,0),this.player);
  const body=RAPIER.RigidBodyDesc.dynamic().setCcdEnabled(true).setCanSleep(true).setLinearDamping(.035).setAngularDamping(.15)
   .setAdditionalMassProperties(SPEC.mass,{x:0,y:0,z:0},{x:3800,y:4300,z:900},identity);
  this.car=this.world.createRigidBody(body);
  this.carCollider=this.world.createCollider(RAPIER.ColliderDesc.cuboid(.86,.25,2.08).setTranslation(0,-.02,0).setDensity(0).setFriction(.55).setRestitution(.08),this.car);
  this.roofCollider=this.world.createCollider(RAPIER.ColliderDesc.cuboid(.67,.17,.85).setTranslation(0,.34,.1).setDensity(0).setFriction(.55),this.car);
  this.driver=this.world.createVehicleController(this.car);this.driver.indexUpAxis=1;this.driver.setIndexForwardAxis=2;
  for(let i=0;i<4;i++){
   const w=SPEC.wheels[i],staticCompression=9.81/(4*SPEC.suspensionStiffness);
   this.driver.addWheel({x:w.center[0],y:w.radius-SPEC.centerOfMassHeight+SPEC.suspensionRest-staticCompression,z:w.center[2]}, {x:0,y:-1,z:0},{x:1,y:0,z:0},SPEC.suspensionRest,w.radius);
   this.driver.setWheelSuspensionStiffness(i,SPEC.suspensionStiffness);
   this.driver.setWheelSuspensionCompression(i,SPEC.compressionDamping);
   this.driver.setWheelSuspensionRelaxation(i,SPEC.reboundDamping);
   this.driver.setWheelMaxSuspensionTravel(i,SPEC.suspensionTravel);
   this.driver.setWheelMaxSuspensionForce(i,SPEC.maxSuspensionForce);
   this.driver.setWheelFrictionSlip(i,SPEC.dryGrip);this.driver.setWheelSideFrictionStiffness(i,1);
  }
  this.walker=this.world.createCharacterController(.025);this.walker.enableSnapToGround(.35);this.walker.setMaxSlopeClimbAngle(.83);this.walker.setMinSlopeSlideAngle(.9);this.walker.enableAutostep(.25,.15,false);
  this.walker.setApplyImpulsesToDynamicBodies(true);this.walker.setCharacterMass(78);
  this.inVehicle=false;this.speed=0;this.steering=0;this.yaw=0;this.playerVy=0;this.grounded=false;this.carGrounded=false;this.autoHold=true;
  this.footVelocity={x:0,z:0};this.wheelStates=[];this.acceleration=0;this.lastSpeed=0;this.braking=false;
 }
 addTrimesh(vertices,indices,surface='ground'){
  const collider=this.world.createCollider(RAPIER.ColliderDesc.trimesh(vertices,indices,RAPIER.TriMeshFlags.FIX_INTERNAL_EDGES).setFriction(surface==='road'?.95:.65));
  collider.userData={surface};return collider;
 }
 reset(route){
  const a=route[0],b=route[2];this.yaw=Math.atan2(-(b[0]-a[0]),-(b[2]-a[2]));
  this.speed=0;this.lastSpeed=0;this.steering=0;this.playerVy=0;this.autoHold=true;this.footVelocity={x:0,z:0};
  this.car.resetForces(true);this.car.resetTorques(true);this.car.setLinvel({x:0,y:0,z:0},true);this.car.setAngvel({x:0,y:0,z:0},true);
  this.car.setTranslation({x:a[0],y:a[1]+SPEC.centerOfMassHeight+.16,z:a[2]},true);
  this.car.setRotation({x:0,y:Math.sin(this.yaw/2),z:0,w:Math.cos(this.yaw/2)},true);
  this.player.setTranslation({x:a[0]+Math.cos(this.yaw)*2.5,y:a[1]+.18,z:a[2]-Math.sin(this.yaw)*2.5},true);
  this.player.setEnabled(!this.inVehicle);this.world.step();
 }
 settle(steps=120){for(let i=0;i<steps;i++)this.step(1/60,neutral,this.yaw);}
 interact(){
  const car=this.car.translation(),person=this.player.translation();
  if(!this.inVehicle){
   if(distanceXZ(car,person)>4.3)return {ok:false,message:'Walk closer to the Roadster.'};
   this.inVehicle=true;this.player.setEnabled(false);return {ok:true,message:'AWD ready. Ease into the throttle; brake before the bends.'};
  }
  const velocity=this.car.linvel();if(Math.hypot(velocity.x,velocity.y,velocity.z)>1.5)return {ok:false,message:'Stop before stepping out.'};
  const up=rotate(this.car.rotation(),{x:0,y:1,z:0});if(up.y<.35)return {ok:false,message:'Vehicle overturned. Use RECOVER.'};
  for(const sign of [1,-1]){
   const side=rotate(this.car.rotation(),{x:2.3*sign,y:0,z:0});
   const target={x:car.x+side.x,y:car.y,z:car.z+side.z};
   const hit=this.world.castRay(new RAPIER.Ray({x:target.x,y:target.y+5,z:target.z},{x:0,y:-1,z:0}),12,true,undefined,undefined,undefined,this.car);
   if(hit)target.y=target.y+5-hit.timeOfImpact+.08;
   if(this.world.intersectionWithShape({x:target.x,y:target.y+.89,z:target.z},identity,this.playerCollider.shape,undefined,undefined,undefined,this.player,c=>c.parent()?.handle!==this.car.handle))continue;
   this.player.setEnabled(true);this.player.setTranslation(target,true);this.playerVy=0;this.inVehicle=false;this.autoHold=true;
   return {ok:true,message:'Parking brake engaged. Back on foot.'};
  }
  return {ok:false,message:'Doors blocked. Move to open ground.'};
 }
 step(dt,input,cameraYaw){
  this.world.timestep=dt;
  let movement={x:0,y:0,z:0};
  if(!this.inVehicle){
   const scale=input.run?7.3:3.8;
   this.footVelocity.x=moveToward(this.footVelocity.x,(Math.cos(cameraYaw)*input.x+Math.sin(cameraYaw)*input.y)*scale,22*dt);
   this.footVelocity.z=moveToward(this.footVelocity.z,(-Math.sin(cameraYaw)*input.x+Math.cos(cameraYaw)*input.y)*scale,22*dt);
   this.playerVy=this.grounded?-.4:this.playerVy-9.81*dt;if(input.jump&&this.grounded)this.playerVy=5;
   this.walker.computeColliderMovement(this.playerCollider,{x:this.footVelocity.x*dt,y:this.playerVy*dt,z:this.footVelocity.z*dt});
   movement=this.walker.computedMovement();this.grounded=this.walker.computedGrounded();const p=this.player.translation();
   this.player.setNextKinematicTranslation({x:p.x+movement.x,y:p.y+movement.y,z:p.z+movement.z});
  }
  const throttle=this.inVehicle?input.throttle:0;
  if(Math.abs(throttle)>.05)this.autoHold=false;
  const limit=SPEC.steeringMax/(1+(Math.abs(this.speed)/21)**1.35);
  this.steering=moveToward(this.steering,-(this.inVehicle?input.x:0)*limit,dt*1.6);
  const meanRadius=SPEC.wheels.reduce((sum,w)=>sum+w.radius,0)/4;
  let driveForce=throttle*Math.min(SPEC.wheelTorque/meanRadius,SPEC.power/Math.max(1,Math.abs(this.speed)));
  if(throttle<0&&this.speed< -SPEC.reverseLimit)driveForce=0;
  const reversingAgainstMotion=throttle*this.speed< -1;
  this.braking=!!(input.brake&&this.inVehicle)||reversingAgainstMotion||!this.inVehicle||this.autoHold;
  if(this.braking)driveForce=0;
  const wheelbase=Math.abs(SPEC.wheels[0].center[2]-SPEC.wheels[2].center[2]);
  const turnRadius=Math.abs(this.steering)>.001?wheelbase/Math.tan(Math.abs(this.steering)):Infinity;
  for(let i=0;i<4;i++){
   const w=SPEC.wheels[i],front=i<2;
   // Ackermann front geometry; no orientation assignment to the chassis.
   const inner=(this.steering<0?w.center[0]>0:w.center[0]<0);
   const steer=front?Math.sign(this.steering)*Math.atan(wheelbase/Math.max(.1,turnRadius+(inner?-1:1)*Math.abs(w.center[0]))):0;
   this.driver.setWheelSteering(i,steer);
   const surface=this.driver.wheelGroundObject(i)?.userData?.surface;
   const mu=surface==='road'||surface==='test'?SPEC.dryGrip:SPEC.grassGrip;
   this.driver.setWheelFrictionSlip(i,mu);
   // Rapier's Bullet-style slip parameter isn't a calibrated tire coefficient.
   // Enforce an explicit load-based longitudinal friction circle, including
   // the previous substep's lateral tire impulse, instead of unlimited torque.
   const load=this.driver.wheelIsInContact(i)?Math.max(0,this.driver.wheelSuspensionForce(i)||0):0;
   const lateral=(this.driver.wheelSideImpulse(i)||0)/dt;
   const longitudinalLimit=Math.sqrt(Math.max(0,(mu*load)**2-lateral*lateral));
   const requested=driveForce*(front?SPEC.frontDriveShare:1-SPEC.frontDriveShare)/2;
   this.driver.setWheelEngineForce(i,Math.max(-longitudinalLimit,Math.min(longitudinalLimit,requested)));
   const brakeImpulse=Math.min(SPEC.brakeForce*(front?.6:.4)*dt/2,longitudinalLimit*dt);
   this.driver.setWheelBrake(i,this.braking?brakeImpulse:0);
  }
  this.car.resetForces(true);this.car.resetTorques(true);
  const v=this.car.linvel(),speed=Math.hypot(v.x,v.y,v.z);
  const drag=.5*SPEC.airDensity*SPEC.dragArea*speed;
  const rolling=this.carGrounded?SPEC.rollingCoefficient*SPEC.mass*9.81/Math.max(1,speed):0;
  this.car.addForce({x:-v.x*(drag+rolling),y:-v.y*drag,z:-v.z*(drag+rolling)},true);
  if(this.carGrounded)this.car.addForce({x:0,y:-.5*SPEC.airDensity*SPEC.downforceArea*speed*speed,z:0},true);
  this.driver.updateVehicle(dt,RAPIER.QueryFilterFlags.EXCLUDE_KINEMATIC,undefined,c=>c.parent()?.handle!==this.car.handle);
  this.world.step();
  const forward=rotate(this.car.rotation(),{x:0,y:0,z:-1}),newV=this.car.linvel();
  this.speed=newV.x*forward.x+newV.y*forward.y+newV.z*forward.z;
  this.yaw=Math.atan2(-forward.x,-forward.z);this.acceleration=(this.speed-this.lastSpeed)/dt;this.lastSpeed=this.speed;
  this.wheelStates=SPEC.wheels.map((w,i)=>({name:w.name,contact:this.driver.wheelIsInContact(i),suspension:this.driver.wheelSuspensionLength(i),rotation:this.driver.wheelRotation(i),steering:this.driver.wheelSteering(i),force:this.driver.wheelSuspensionForce(i),radius:w.radius,connection:this.driver.wheelChassisConnectionPointCs(i)}));
  this.carGrounded=this.wheelStates.some(w=>w.contact);
  return movement;
 }
 dispose(){this.world.free();}
}
