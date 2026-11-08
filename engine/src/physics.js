import RAPIER from '@dimforge/rapier3d-compat';

export const moveToward=(v,t,d)=>v<t?Math.min(t,v+d):Math.max(t,v-d);
export const distanceXZ=(a,b)=>Math.hypot(a.x-b.x,a.z-b.z);
const identity={x:0,y:0,z:0,w:1};

/** Original gameplay/controller layer over the actual Rapier WASM solver. */
export class AlpinePhysics {
 static async create(){await RAPIER.init();return new AlpinePhysics();}
 constructor(){
  this.world=new RAPIER.World({x:0,y:-18,z:0});this.world.timestep=1/60;
  this.player=this.world.createRigidBody(RAPIER.RigidBodyDesc.kinematicPositionBased());
  this.playerCollider=this.world.createCollider(RAPIER.ColliderDesc.capsule(.62,.27).setTranslation(0,.89,0),this.player);
  this.car=this.world.createRigidBody(RAPIER.RigidBodyDesc.kinematicPositionBased());
  this.carCollider=this.world.createCollider(RAPIER.ColliderDesc.cuboid(.91,.70,2.10).setTranslation(0,.7,0),this.car);
  this.walker=this.world.createCharacterController(.025);this.driver=this.world.createCharacterController(.03);
  for(const c of [this.walker,this.driver]){c.enableSnapToGround(.35);c.setMaxSlopeClimbAngle(.83);c.setMinSlopeSlideAngle(.9);}
  this.walker.enableAutostep(.25,.15,false);
  this.inVehicle=false;this.speed=0;this.steering=0;this.yaw=0;this.playerVy=0;this.carVy=0;
  this.grounded=false;this.carGrounded=false;this.footVelocity={x:0,z:0};
 }
 addTrimesh(vertices,indices){return this.world.createCollider(RAPIER.ColliderDesc.trimesh(vertices,indices));}
 reset(route){
  const a=route[0],b=route[2];this.yaw=Math.atan2(-(b[0]-a[0]),-(b[2]-a[2]));
  this.speed=0;this.steering=0;this.playerVy=0;this.carVy=0;this.footVelocity={x:0,z:0};
  this.car.setTranslation({x:a[0],y:a[1]+.13,z:a[2]},true);
  this.car.setRotation({x:0,y:Math.sin(this.yaw/2),z:0,w:Math.cos(this.yaw/2)},true);
  this.player.setTranslation({x:a[0]+Math.cos(this.yaw)*2.5,y:a[1]+.18,z:a[2]-Math.sin(this.yaw)*2.5},true);
  this.player.setEnabled(!this.inVehicle);this.world.step();
 }
 interact(){
  const car=this.car.translation(),person=this.player.translation();
  if(!this.inVehicle){
   if(distanceXZ(car,person)>4.3)return {ok:false,message:'Walk closer to your car.'};
   this.inVehicle=true;this.player.setEnabled(false);return {ok:true,message:'Follow the markers. Use BRAKE to stop.'};
  }
  if(Math.abs(this.speed)>1.5)return {ok:false,message:'Stop before stepping out.'};
  for(const sign of [1,-1]){
   const target={x:car.x+Math.cos(this.yaw)*2.3*sign,y:car.y+.15,z:car.z-Math.sin(this.yaw)*2.3*sign};
   const ray=new RAPIER.Ray({x:target.x,y:target.y+5,z:target.z},{x:0,y:-1,z:0});
   const hit=this.world.castRay(ray,12,true,RAPIER.QueryFilterFlags.EXCLUDE_KINEMATIC);
   if(hit)target.y=target.y+5-hit.timeOfImpact+.08;
   const blocked=this.world.intersectionWithShape({x:target.x,y:target.y+.89,z:target.z},identity,this.playerCollider.shape,undefined,undefined,this.carCollider,this.player);
   if(blocked)continue;
   this.player.setEnabled(true);this.player.setTranslation(target,true);this.playerVy=0;this.inVehicle=false;
   return {ok:true,message:'Back on foot.'};
  }
  return {ok:false,message:'Doors are blocked. Move to open ground.'};
 }
 step(dt,input,cameraYaw){
  let movement={x:0,y:0,z:0};
  if(!this.inVehicle){
   const x=input.x,y=input.y,scale=input.run?7.3:3.8;
   const dx=(Math.cos(cameraYaw)*x+Math.sin(cameraYaw)*y)*scale;
   const dz=(-Math.sin(cameraYaw)*x+Math.cos(cameraYaw)*y)*scale;
   this.footVelocity.x=moveToward(this.footVelocity.x,dx,22*dt);this.footVelocity.z=moveToward(this.footVelocity.z,dz,22*dt);
   this.playerVy=this.grounded?-.4:this.playerVy-18*dt;
   if(input.jump&&this.grounded)this.playerVy=6.3;
   this.walker.computeColliderMovement(this.playerCollider,{x:this.footVelocity.x*dt,y:this.playerVy*dt,z:this.footVelocity.z*dt});
   movement=this.walker.computedMovement();this.grounded=this.walker.computedGrounded();
   const p=this.player.translation();this.player.setNextKinematicTranslation({x:p.x+movement.x,y:p.y+movement.y,z:p.z+movement.z});
  }
  const throttle=this.inVehicle?input.throttle:0;
  const steer=this.inVehicle?input.x:0;
  const limit=.48-(.32*Math.min(Math.abs(this.speed)/24,1));
  this.steering=moveToward(this.steering,steer*limit,dt*1.7);
  const brake=this.inVehicle&&input.brake;
  this.speed=moveToward(this.speed,brake?0:throttle*(throttle>=0?30:9),(brake?20:Math.abs(throttle)>.05?7.5:2.4)*dt);
  if(this.carGrounded)this.yaw-=this.speed/2.65*Math.tan(this.steering)*dt;
  this.carVy=this.carGrounded?-.8:this.carVy-18*dt;
  this.driver.computeColliderMovement(this.carCollider,{x:-Math.sin(this.yaw)*this.speed*dt,y:this.carVy*dt,z:-Math.cos(this.yaw)*this.speed*dt});
  const drive=this.driver.computedMovement();this.carGrounded=this.driver.computedGrounded();
  const c=this.car.translation();this.car.setNextKinematicTranslation({x:c.x+drive.x,y:c.y+drive.y,z:c.z+drive.z});
  this.car.setNextKinematicRotation({x:0,y:Math.sin(this.yaw/2),z:0,w:Math.cos(this.yaw/2)});
  if(Math.abs(this.speed)>1.5&&Math.hypot(drive.x,drive.z)<Math.abs(this.speed)*dt*.25)this.speed*=.5;
  this.world.step();
  return movement;
 }
 dispose(){this.world.free();}
}
