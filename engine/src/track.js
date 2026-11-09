import {CatmullRomCurve3,Vector3} from 'three';
export const TRACK_WIDTH=10;
export function makeRoute(source,count=640){
 const curve=new CatmullRomCurve3(source.map(p=>new Vector3(...p)),true,'centripetal');
 const points=curve.getSpacedPoints(count).slice(0,count).map(p=>[p.x,p.y,p.z]);
 // Remove vertical bumps without straightening the plan-view mountain bends.
 for(let pass=0;pass<8;pass++){const y=points.map((p,i)=>(points[(i+count-1)%count][1]+2*p[1]+points[(i+1)%count][1])/4);points.forEach((p,i)=>p[1]=y[i]);}
 return points;
}
// Exact all-segment search, but no per-candidate objects or square roots.
export function nearestRoute(points,p,out={}){
 let best=Infinity,index=0,tBest=0,bx=0,bz=0,bdx=0,bdz=0,blen=1;
 for(let i=0;i<points.length;i++){
  const a=points[i],b=points[(i+1)%points.length],dx=b[0]-a[0],dz=b[2]-a[2],length2=dx*dx+dz*dz;
  const t=Math.max(0,Math.min(1,((p.x-a[0])*dx+(p.z-a[2])*dz)/length2)),x=a[0]+t*dx,z=a[2]+t*dz,d2=(p.x-x)**2+(p.z-z)**2;
  if(d2<best){best=d2;index=i;tBest=t;bx=x;bz=z;bdx=dx;bdz=dz;blen=length2;}
 }
 const length=Math.sqrt(blen);out.index=index;out.t=tBest;out.x=bx;out.z=bz;out.y=points[index][1]+(points[(index+1)%points.length][1]-points[index][1])*tBest;out.distance=Math.sqrt(best);out.tangent||={x:0,z:0};out.tangent.x=bdx/length;out.tangent.z=bdz/length;out.signed=((p.x-bx)*-bdz+(p.z-bz)*bdx)/length;return out;
}
// Identical vertices are used by the rendered surface and the Rapier collider.
export function ribbon(points,width=TRACK_WIDTH,offset=0,lift=0){
 const positions=[],uvs=[],indices=[];let distance=0;
 for(let i=0;i<points.length;i++){
  const p=points[i],a=points[(i+points.length-1)%points.length],b=points[(i+1)%points.length],dx=b[0]-a[0],dz=b[2]-a[2],len=Math.hypot(dx,dz);
  if(i)distance+=Math.hypot(p[0]-points[i-1][0],p[2]-points[i-1][2]);
  for(const side of [-1,1]){const d=offset+side*width/2;positions.push(p[0]-dz/len*d,p[1]+lift,p[2]+dx/len*d);uvs.push(side<0?0:1,distance/6);}
  const j=(i+1)%points.length;indices.push(i*2,j*2+1,j*2,i*2,i*2+1,j*2+1);
 }
 return {positions:new Float32Array(positions),uvs:new Float32Array(uvs),indices:new Uint32Array(indices)};
}
export function routeHint(points,nearest,speed){
 const i=nearest.index,n=points.length,look=Math.max(6,Math.round(Math.abs(speed)*.65));
 const a=points[i],b=points[(i+look)%n],c=points[(i+look*2)%n];
 const ab={x:b[0]-a[0],z:b[2]-a[2]},bc={x:c[0]-b[0],z:c[2]-b[2]};
 const angle=Math.atan2(ab.x*bc.z-ab.z*bc.x,ab.x*bc.x+ab.z*bc.z);
 const radius=Math.hypot(ab.x,ab.z)/Math.max(.02,Math.abs(angle));
 return {recommended:Math.max(7,Math.min(25,Math.sqrt(radius*3.4))),turn:Math.abs(angle)<.13?'STRAIGHT':angle<0?'LEFT':'RIGHT',angle};
}
export class CircuitProgress{
 constructor(points,gates=[160,320,480,0]){this.points=points;this.gates=gates;this.reset();}
 reset(){this.next=0;this.laps=0;this.elapsed=0;this.last=null;this.recoveryIndex=0;this.best=Infinity;}
 step(p,dt){
  this.elapsed+=dt;const index=this.gates[this.next],a=this.points[index],b=this.points[(index+1)%this.points.length],dx=b[0]-a[0],dz=b[2]-a[2],len=Math.hypot(dx,dz);
  const along=((p.x-a[0])*dx+(p.z-a[2])*dz)/len;
  let event=null;
  if(this.last){const prev=((this.last.x-a[0])*dx+(this.last.z-a[2])*dz)/len;
   if(prev<0&&along>=0){const t=-prev/(along-prev),x=this.last.x+(p.x-this.last.x)*t,z=this.last.z+(p.z-this.last.z)*t,y=this.last.y+(p.y-this.last.y)*t;
    if(Math.hypot(x-a[0],z-a[2])<TRACK_WIDTH/2+1&&Math.abs(y-a[1])<3){this.recoveryIndex=index;this.next++;
     if(this.next===this.gates.length){this.next=0;this.laps++;this.best=Math.min(this.best,this.elapsed);event={type:'lap',time:this.elapsed};this.elapsed=0;}else event={type:'checkpoint',number:this.next};
    }
   }
  }
  this.last={...p};return event;
 }
}
