import test from 'node:test';
import assert from 'node:assert/strict';
import RAPIER from '@dimforge/rapier3d-compat';
import {AlpinePhysics,distanceXZ} from '../src/physics.js';
const neutral={x:0,y:0,throttle:0,jump:false,run:false,brake:false};
const route=[[0,0,0],[0,0,-2],[0,0,-4]];
async function setup(){const p=await AlpinePhysics.create();p.addTrimesh(new Float32Array([-100,0,-100,100,0,-100,100,0,100,-100,0,100]),new Uint32Array([0,2,1,0,3,2]),'road');p.reset(route);for(let i=0;i<60;i++)p.step(1/60,neutral,0);return p;}

test('real Rapier floor supports the character and parked car',async()=>{const p=await setup();assert.ok(p.grounded);assert.ok(p.carGrounded);assert.ok(Math.abs(p.player.translation().y)<.07);assert.ok(p.car.translation().y>.45&&p.car.translation().y<.7);p.dispose();});
test('walk, run, jump and gravity use collision-controlled displacement',async()=>{const p=await setup(),start={...p.player.translation()};for(let i=0;i<60;i++)p.step(1/60,{...neutral,y:-1},0);const walked=distanceXZ(start,p.player.translation());assert.ok(walked>3&&walked<4);const before={...p.player.translation()};for(let i=0;i<60;i++)p.step(1/60,{...neutral,y:-1,run:true},0);assert.ok(distanceXZ(before,p.player.translation())>6);p.step(1/60,{...neutral,jump:true},0);assert.ok(p.player.translation().y>.09);for(let i=0;i<120;i++)p.step(1/60,neutral,0);assert.ok(p.grounded);p.dispose();});
test('enter, accelerate, prohibit moving exit, brake, then exit safely',async()=>{const p=await setup();assert.equal(p.interact().ok,true);assert.equal(p.inVehicle,true);const start={...p.car.translation()};for(let i=0;i<120;i++)p.step(1/60,{...neutral,throttle:1},0);assert.ok(distanceXZ(start,p.car.translation())>10);assert.equal(p.interact().ok,false);for(let i=0;i<180;i++)p.step(1/60,{...neutral,brake:true},0);assert.ok(Math.abs(p.speed)<.01);assert.equal(p.interact().ok,true);assert.equal(p.inVehicle,false);p.dispose();});
test('car is stopped by a real static collision wall',async()=>{const p=await setup();p.world.createCollider(RAPIER.ColliderDesc.cuboid(5,2,.3).setTranslation(0,2,-12));p.world.step();p.interact();for(let i=0;i<360;i++)p.step(1/60,{...neutral,throttle:1},0);assert.ok(p.car.translation().z> -9.7);assert.ok(p.car.translation().z< -7);p.dispose();});
test('recovery preserves vehicle mode and resets motion',async()=>{const p=await setup();p.interact();for(let i=0;i<60;i++)p.step(1/60,{...neutral,throttle:1,x:1},0);p.reset(route);assert.equal(p.inVehicle,true);assert.equal(p.speed,0);assert.ok(distanceXZ(p.car.translation(),{x:0,z:0})<.001);p.dispose();});
