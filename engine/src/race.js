// Pure time-trial state: no transforms, autopilot or frame-rate dependent scoring.
export class TimeTrial {
 constructor(storage){this.storage=storage;this.best=null;try{const v=JSON.parse(storage?.getItem('alpine-time-trial-v5')||'null');if(v&&Number.isFinite(v.time)&&v.time>0&&Array.isArray(v.splits)&&v.splits.length===3&&v.splits.every(x=>Number.isFinite(x)&&x>0)&&typeof v.assisted==='boolean')this.best=v;}catch{}this.reset();}
 reset(){this.countdown=3;this.splits=[];this.valid=true;this.reason='';this.delta=null;this.result=null;}
 invalidate(reason){this.valid=false;this.reason=reason;}
 advance(dt){this.countdown=Math.max(0,this.countdown-dt);}
 checkpoint(time,assisted){this.splits.push(time);const reference=this.best?.assisted===assisted?this.best.splits[this.splits.length-1]:undefined;this.delta=reference===undefined?null:time-reference;}
 finish(time,assisted){
  const valid=this.valid&&this.splits.length===3,comparable=this.best?.assisted===assisted,record=valid&&(!comparable||time<this.best.time);
  this.result={time,valid,record,assisted,medal:!valid?'PRACTICE':time<=130?'GOLD':time<=160?'SILVER':'BRONZE',reason:this.reason};
  if(record){this.best={time,splits:[...this.splits],assisted};try{this.storage?.setItem('alpine-time-trial-v5',JSON.stringify(this.best));}catch{}}
  this.valid=true;this.reason='';this.splits=[];return this.result;
 }
}
