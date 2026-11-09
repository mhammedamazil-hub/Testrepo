// CPU-only microbenchmark, NOT whole-game FPS or tablet evidence.
import fs from 'node:fs';
import {performance} from 'node:perf_hooks';
import {nearestRoute} from '../src/track.js';
const route=JSON.parse(fs.readFileSync(new URL('../public/world/track/route.json',import.meta.url))).points;
function previous(points,p){let best={distance:Infinity};for(let i=0;i<points.length;i++){const a=points[i],b=points[(i+1)%points.length],dx=b[0]-a[0],dz=b[2]-a[2],length=Math.hypot(dx,dz),t=Math.max(0,Math.min(1,((p.x-a[0])*dx+(p.z-a[2])*dz)/(length*length))),x=a[0]+t*dx,z=a[2]+t*dz,distance=Math.hypot(p.x-x,p.z-z);if(distance<best.distance)best={index:i,t,x,z,y:a[1]+(b[1]-a[1])*t,distance,tangent:{x:dx/length,z:dz/length},signed:((p.x-x)*-dz+(p.z-z)*dx)/length};}return best;}
const queries=Array.from({length:5000},(_,i)=>({x:Math.sin(i*1.618)*180,z:-140+Math.cos(i*.73)*220})),out={};
for(const q of queries.slice(0,100)){const a=previous(route,q),b=nearestRoute(route,q,out);if(Math.abs(a.distance-b.distance)>1e-8)throw Error('Mismatch');}
function run(fn){const start=performance.now();for(const q of queries)fn(route,q,out);return performance.now()-start;}
run(previous);run(nearestRoute);const old=[],next=[];for(let i=0;i<5;i++){old.push(run(previous));next.push(run(nearestRoute));}
const median=a=>[...a].sort((x,y)=>x-y)[2],result={scope:'CPU-only nearest-route microbenchmark over the same exact 640-segment closed route and 5000 deterministic queries. Historical v3 algorithm versus exact squared-distance/reusable-result implementation. Not FPS or physical-tablet evidence.',queries:queries.length,previous_ms:old,optimized_ms:next,previous_median_ms:median(old),optimized_median_ms:median(next),median_speedup:median(old)/median(next)};
console.log(JSON.stringify(result,null,2));if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2)+'\n');
