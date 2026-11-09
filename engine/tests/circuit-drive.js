// Actual dynamics endurance check. A test-only pursuit driver supplies inputs;
// no position/rotation/velocity assignment after spawning. Not a human/mobile test.
import fs from 'node:fs';
import RAPIER from '@dimforge/rapier3d-compat';
import {AlpinePhysics} from '../src/physics.js';
import {ribbon,nearestRoute,CircuitProgress} from '../src/track.js';
import {meshesFromGLB} from './glb-fixture.js';
const track=JSON.parse(fs.readFileSync(new URL('../public/world/track/route.json',import.meta.url))),route=track.points;
const p=await AlpinePhysics.create();for(const mesh of meshesFromGLB(new URL('../public/world/track/terrain.glb',import.meta.url)))p.addTrimesh(mesh.vertices,mesh.indices,'ground');
const strip=ribbon(route);p.addTrimesh(strip.positions,strip.indices,'road');// Match the runtime rail proxies, not merely an isolated flat/surface strip.
for(let i=0;i<route.length;i+=4){const a=route[i],b=route[(i+4)%route.length],dx=b[0]-a[0],dz=b[2]-a[2],length=Math.hypot(dx,dz),angle=Math.atan2(dx,dz);for(const side of [-1,1])p.world.createCollider(RAPIER.ColliderDesc.cuboid(.10,.45,length/2+.04).setTranslation((a[0]+b[0])/2-dz/length*6.1*side,(a[1]+b[1])/2+.55,(a[2]+b[2])/2+dx/length*6.1*side).setRotation({x:0,y:Math.sin(angle/2),z:0,w:Math.cos(angle/2)}).setFriction(.15).setRestitution(.02));}
p.reset(route);p.settle(180);p.interact();
const race=new CircuitProgress(route);let maxDistance=0,ticks=0,minContacts=4;const trail=[];
for(;ticks<18000&&race.laps<1;ticks++){
 const position=p.car.translation(),near=nearestRoute(route,position),target=route[(near.index+5)%route.length];
 const desired=Math.atan2(-(target[0]-position.x),-(target[2]-position.z)),error=Math.atan2(Math.sin(desired-p.yaw),Math.cos(desired-p.yaw));
 const input={x:Math.max(-1,Math.min(1,-error*2.8)),y:0,throttle:p.speed<8?.3:0,brake:p.speed>9,jump:false,run:false};
 p.step(1/60,input,p.yaw);race.step(p.car.translation(),1/60);maxDistance=Math.max(maxDistance,near.distance);minContacts=Math.min(minContacts,p.wheelStates.filter(w=>w.contact).length);
 if(ticks%60===0)trail.push({tick:ticks,index:near.index,speed:p.speed,distance:near.distance,y:p.car.translation().y});
 if(near.distance>15||position.y<0)break;
}
const result={scope:'Actual 60Hz Rapier full circuit with graded terrain, road and runtime-matching guardrail colliders; test-only input pursuit driver. No runtime autopilot or scripted body movement.',passed:race.laps===1,laps:race.laps,gates_passed:race.next,ticks,seconds:ticks/60,max_centerline_distance_m:maxDistance,min_wheel_contacts:minContacts,trail};p.dispose();
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({...result,trail:trail.slice(-4)},null,2));if(!result.passed)process.exitCode=1;
