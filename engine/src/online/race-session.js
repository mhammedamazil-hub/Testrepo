import {nearestRoute} from '../track.js';
import {gates,pickupIndices,ROAD_WIDTH,gridPosition,MAP_ID} from './map.js';
import {profile,carState,MAX_PLAYERS,Limiter,cleanChat} from './protocol.js';
// Host owns roster, ordered crossings, clock, inventory, recovery and results.
// Clients own their local Rapier driving simulation; this is not secure esports
// anti-cheat or cross-peer car-collision physics.
export class RaceSession {
 constructor(route,hostId,guest,now=()=>performance.now()){this.route=route;this.hostId=hostId;this.now=now;this.players=new Map();this.phase='lobby';this.laps=2;this.round=0;this.startAt=0;this.events=[];this.add(hostId,guest);}
 add(id,guest){const p=profile(guest);if(!p)return 'Choose a valid guest name and colour.';if(this.players.has(id))return 'Already in room.';if(this.phase!=='lobby')return 'Race in progress. Join after the host returns to the lobby.';if(this.players.size>=MAX_PLAYERS)return 'Room is full (6 racers).';this.players.set(id,{id,...p,ready:false,connected:true,slot:this.players.size,state:null,seq:-1,gates:0,last:null,lastAt:this.now(),finish:null,penalty:0,nitro:1,boostUntil:0,pickups:{},chat:new Limiter(.5,3),recoverAt:-Infinity,rate:new Limiter(35,40)});return null;}
 remove(id){const p=this.players.get(id);if(!p)return;if(this.phase==='lobby'){this.players.delete(id);[...this.players.values()].forEach((v,i)=>v.slot=i);}else{p.connected=false;p.dnf=true;}this.checkEnd();}
 ready(id,value){const p=this.players.get(id);if(p&&this.phase==='lobby')p.ready=!!value;}
 start(id,laps=2){if(id!==this.hostId||this.phase!=='lobby')return false;const racers=[...this.players.values()];if(racers.length<2||!racers.every(p=>p.ready))return false;this.laps=Math.max(1,Math.min(3,Math.round(laps)||2));this.phase='countdown';this.round++;this.startAt=this.now()+4000;for(const p of racers){p.gates=0;p.last=null;p.state=null;p.seq=-1;p.lastAt=this.startAt;p.finish=null;p.dnf=false;p.penalty=0;p.nitro=1;p.boostUntil=0;p.pickups={};p.recoverAt=-Infinity;p.expected=gridPosition(this.route,p.slot);}return true;}
 lobby(id){if(id!==this.hostId)return false;this.phase='lobby';for(const [key,p] of this.players){if(!p.connected)this.players.delete(key);else{p.ready=false;p.state=null;p.last=null;p.seq=-1;p.finish=null;p.dnf=false;}}[...this.players.values()].forEach((p,i)=>p.slot=i);return true;}
 update(){if(this.phase==='countdown'&&this.now()>=this.startAt)this.phase='racing';if(this.phase==='racing'&&this.now()-this.startAt>1200000){for(const p of this.players.values())if(!p.finish)p.dnf=true;this.phase='finished';}}
 acceptState(id,value){const p=this.players.get(id),s=carState(value),now=this.now();if(!p||!s||!p.rate.take(now)||s.seq<=p.seq||p.finish||p.dnf)return false;this.update();
  const pos={x:s.p[0],y:s.p[1],z:s.p[2]},near=nearestRoute(this.route,pos),dt=Math.max(.05,(now-p.lastAt)/1000);
  if(pos.y>near.y+4||pos.y< -30||near.distance>100)return false;
  if(!p.last&&p.expected&&Math.hypot(pos.x-p.expected.x,pos.z-p.expected.z)>5)return false;
  if(p.last&&Math.hypot(pos.x-p.last.x,pos.y-p.last.y,pos.z-p.last.z)>70*Math.min(dt,2)+4)return false;
  if(this.phase==='countdown'){const grid=gridPosition(this.route,p.slot);if(Math.hypot(pos.x-grid.x,pos.z-grid.z)>4)return false;}
  if(this.phase==='racing'&&p.last){const index=gates[p.gates%gates.length],a=this.route[index],b=this.route[(index+1)%this.route.length],dx=b[0]-a[0],dz=b[2]-a[2],len=Math.hypot(dx,dz),prev=((p.last.x-a[0])*dx+(p.last.z-a[2])*dz)/len,along=((pos.x-a[0])*dx+(pos.z-a[2])*dz)/len;
   if(prev<0&&along>=0){const t=-prev/(along-prev),x=p.last.x+(pos.x-p.last.x)*t,z=p.last.z+(pos.z-p.last.z)*t,y=p.last.y+(pos.y-p.last.y)*t;if(Math.hypot(x-a[0],z-a[2])<ROAD_WIDTH/2+1&&Math.abs(y-a[1])<3){p.gates++;if(p.gates===this.laps*gates.length){p.finish=(now-this.startAt)/1000+p.penalty;this.events.push({type:'finish',id,time:p.finish});this.checkEnd();}}}
  }
  if(this.phase==='racing')for(const index of pickupIndices){const point=this.route[index];if(Math.hypot(pos.x-point[0],pos.z-point[2])<8&&Math.abs(pos.y-point[1])<2.5&&now-(p.pickups[index]??-Infinity)>12000){p.pickups[index]=now;p.nitro=1;}}
  p.expected=null;p.last=pos;p.lastAt=now;p.seq=s.seq;p.state=s;p.routeIndex=near.index;return true;
 }
 boost(id){const p=this.players.get(id);this.update();if(!p||this.phase!=='racing'||p.finish||p.dnf||!p.nitro||!p.last||this.now()<p.boostUntil||nearestRoute(this.route,p.last).distance>ROAD_WIDTH/2+1)return false;p.nitro=0;p.boostUntil=this.now()+2500;return true;}
 recover(id){const p=this.players.get(id),now=this.now();if(!p||this.phase!=='racing'||p.finish||p.dnf||now-p.recoverAt<5000)return null;const index=p.gates?gates[(p.gates-1)%gates.length]:gridPosition(this.route,p.slot).index;p.recoverAt=now;p.penalty+=3;p.boostUntil=0;p.last=null;p.state=null;p.lastAt=now;p.expected={x:this.route[index][0],z:this.route[index][2]};return {type:'recover',index,penalty:p.penalty};}
 chat(id,text){const p=this.players.get(id),value=cleanChat(text);return p&&value&&p.chat.take(this.now())?{id,name:p.name,text:value,time:this.now()}:null;}
 checkEnd(){if(this.phase==='racing'&&[...this.players.values()].every(p=>p.finish!==null||p.dnf))this.phase='finished';}
 snapshot(){this.update();return {map:MAP_ID,phase:this.phase,round:this.round,laps:this.laps,startAt:this.startAt,hostNow:this.now(),hostId:this.hostId,players:[...this.players.values()].map(p=>({id:p.id,name:p.name,colour:p.colour,ready:p.ready,connected:p.connected,slot:p.slot,state:p.state,gates:p.gates,finish:p.finish,dnf:!!p.dnf,penalty:p.penalty,nitro:p.nitro,boostUntil:p.boostUntil,routeIndex:p.routeIndex??0}))};}
}
