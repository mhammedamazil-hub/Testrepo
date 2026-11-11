import {CatmullRomCurve3,Vector3} from 'three';
import {nearestRoute} from '../track.js';
export const MAP_ID='alpine-grand-prix-1',ROAD_WIDTH=14,MAP_SIZE=2400,COUNT=1024;
export function buildRoute(){
 const knots=[[-420,12,570],[-420,12,180],[-540,16,-120],[-650,20,-470],[-420,25,-680],[-120,29,-560],[0,24,-330],[220,17,-440],[510,14,-680],[700,11,-440],[600,14,-100],[350,24,20],[250,24,260],[520,17,430],[640,13,650],[300,12,740],[20,11,570],[-180,13,700]];
 return new CatmullRomCurve3(knots.map(p=>new Vector3(...p)),true,'centripetal').getSpacedPoints(COUNT).slice(0,COUNT).map(v=>v.toArray());
}
export function routeLength(route){return route.reduce((sum,p,i)=>{const b=route[(i+1)%route.length];return sum+Math.hypot(b[0]-p[0],b[1]-p[1],b[2]-p[2]);},0);}
function terrainNoise(x,z){
 const ix=Math.floor(x),iz=Math.floor(z),u=x-ix,v=z-iz,s=u*u*(3-2*u),t=v*v*(3-2*v);
 const h=(a,b)=>{let n=Math.imul(a,374761393)^Math.imul(b,668265263);n=Math.imul(n^(n>>>13),1274126177);return ((n^(n>>>16))>>>0)/4294967295;};
 return (h(ix,iz)*(1-s)+h(ix+1,iz)*s)*(1-t)+(h(ix,iz+1)*(1-s)+h(ix+1,iz+1)*s)*t;
}
export function terrainHeight(x,z,route,out={}){
 const near=nearestRoute(route,{x,z},out),broad=terrainNoise(x/400,z/400),ridge=1-Math.abs(terrainNoise(x/180,z/180)*2-1),detail=terrainNoise(x/65,z/65),rim=Math.max(0,(Math.max(Math.abs(x),Math.abs(z))-800)/400);
 const base=4+broad*12+ridge**5*35+detail*3+rim*(60+broad*60);
 const blend=Math.max(0,Math.min(1,(near.distance-ROAD_WIDTH/2-18)/30)),smooth=blend*blend*(3-2*blend);return (near.y-.45)*(1-smooth)+base*smooth;
}
export function terrainData(route,segments=128){const vertices=new Float32Array((segments+1)**2*3),indices=new Uint32Array(segments*segments*6),near={};let j=0;
 for(let z=0;z<=segments;z++)for(let x=0;x<=segments;x++){const px=x/segments*MAP_SIZE-MAP_SIZE/2,pz=z/segments*MAP_SIZE-MAP_SIZE/2;vertices.set([px,terrainHeight(px,pz,route,near),pz],j);j+=3;}
 j=0;for(let z=0;z<segments;z++)for(let x=0;x<segments;x++){const a=z*(segments+1)+x,b=a+segments+1;indices.set([a,b,a+1,a+1,b,b+1],j);j+=6;}return {vertices,indices};}
export const gates=Array.from({length:8},(_,i)=>(i+1)*128%COUNT);
export const pickupIndices=[64,300,560,790];
export function gridPosition(route,slot){const index=(COUNT-4-Math.floor(slot/2)*2)%COUNT,p=route[index],n=route[(index+1)%COUNT],dx=n[0]-p[0],dz=n[2]-p[2],length=Math.hypot(dx,dz),offset=(slot%2?1:-1)*2.4;return {index,x:p[0]-dz/length*offset,y:p[1],z:p[2]+dx/length*offset};}
