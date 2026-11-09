import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import RAPIER from '@dimforge/rapier3d-compat';
import {AlpinePhysics} from '../src/physics.js';
import {ribbon,nearestRoute,CircuitProgress} from '../src/track.js';
import {meshesFromGLB} from './glb-fixture.js';
const track=JSON.parse(fs.readFileSync(new URL('../public/world/track/route.json',import.meta.url))),points=track.points;
const neutral={x:0,y:0,throttle:0,brake:false,jump:false,run:false};
async function setup(){const p=await AlpinePhysics.create();for(const m of meshesFromGLB(new URL('../public/world/track/terrain.glb',import.meta.url)))p.addTrimesh(m.vertices,m.indices,'ground');const r=ribbon(points);p.addTrimesh(r.positions,r.indices,'road');p.reset(points);p.settle(180);return p;}
test('all circuit center and wheel lanes are clear of underlying terrain',async()=>{
 const p=await setup();let hits=0,minClearance=Infinity;
 for(let i=0;i<points.length;i+=2){const start=points[i],b=points[(i+1)%points.length],a=start.map((v,k)=>(v+b[k])/2),dx=b[0]-start[0],dz=b[2]-start[2],len=Math.hypot(dx,dz);
  for(const offset of [-4,0,4]){const x=a[0]-dz/len*offset,z=a[2]+dx/len*offset;
   const ground=p.world.castRay(new RAPIER.Ray({x,y:a[1]+8,z},{x:0,y:-1,z:0}),30,true,undefined,undefined,undefined,undefined,c=>c.userData?.surface==='ground');
   if(ground){const clearance=ground.timeOfImpact-8;minClearance=Math.min(minClearance,clearance);assert.ok(clearance>.05,`Terrain intersects tarmac at ${i}, offset ${offset}, clearance ${clearance}`);}
   const road=p.world.castRay(new RAPIER.Ray({x,y:a[1]+8,z},{x:0,y:-1,z:0}),30,true,undefined,undefined,undefined,undefined,c=>c.userData?.surface==='road');assert.ok(road,`Road hole ${i}/${offset}`);assert.ok(Math.abs(road.timeOfImpact-8)<.12);hits++;
  }
 }
 assert.equal(hits,960);assert.ok(p.carGrounded);assert.equal(p.wheelStates.filter(w=>w.contact).length,4);p.dispose();
});
test('ordered forward gate crossing catches high-speed sweeps, rejects reverse, shortcuts and repeat camping',()=>{
 const race=new CircuitProgress(points),gate=points[160],next=points[161],dx=next[0]-gate[0],dz=next[2]-gate[2],len=Math.hypot(dx,dz);
 const before={x:gate[0]-dx/len*12,y:gate[1]+.55,z:gate[2]-dz/len*12},after={x:gate[0]+dx/len*12,y:gate[1]+.55,z:gate[2]+dz/len*12};
 race.step(after,1);race.step(before,1);assert.equal(race.next,0);assert.equal(race.step(after,1).type,'checkpoint');assert.equal(race.next,1);race.step(before,1);race.step(after,1);assert.equal(race.next,1);
 race.reset();race.step({...before,x:before.x+20},1);race.step({...after,x:after.x+20},1);assert.equal(race.next,0);
});
test('full ordered circuit requires finish crossing after all three sector gates',()=>{
 const race=new CircuitProgress(points);for(let lap=0;lap<2;lap++)for(let i=0;i<=points.length;i++){const a=points[i%points.length];race.step({x:a[0],y:a[1]+.55,z:a[2]},1/60);}assert.equal(race.laps,2);assert.equal(race.next,0);assert.ok(race.best>10);
});
test('nearest recovery works on both sides of the closed-loop seam',()=>{for(const i of [0,5,319,639]){const a=points[i],near=nearestRoute(points,{x:a[0]+.2,z:a[2]});assert.ok(near.distance<.21);assert.ok(Number.isFinite(near.y));}});
