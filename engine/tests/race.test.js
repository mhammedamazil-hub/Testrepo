import test from 'node:test';
import assert from 'node:assert/strict';
import {TimeTrial} from '../src/race.js';
const storage=()=>{const data=new Map();return {getItem:k=>data.get(k),setItem:(k,v)=>data.set(k,v)};};
test('countdown cannot go negative and reset retains saved best',()=>{const t=new TimeTrial(storage());t.advance(1);assert.equal(t.countdown,2);t.advance(5);assert.equal(t.countdown,0);t.checkpoint(25,true);t.checkpoint(55,true);t.checkpoint(85,true);assert.equal(t.finish(125,true).medal,'GOLD');t.reset();assert.equal(t.best.time,125);assert.equal(t.countdown,3);});
test('sector deltas and personal best survive storage roundtrip',()=>{const s=storage(),t=new TimeTrial(s);for(const split of [30,60,90])t.checkpoint(split,true);assert.equal(t.finish(140,true).record,true);const next=new TimeTrial(s);next.checkpoint(28,true);assert.equal(next.delta,-2);next.checkpoint(61,true);assert.equal(next.delta,1);next.checkpoint(92,true);assert.equal(next.finish(150,true).record,false);assert.equal(next.best.time,140);});
test('recovery, hops or missing sectors cannot become clean PBs',()=>{const t=new TimeTrial(storage());t.invalidate('RECOVERY');for(const split of [20,40,60])t.checkpoint(split,true);assert.equal(t.finish(100,true).valid,false);assert.equal(t.best,null);assert.equal(t.finish(90,true).valid,false);});
test('different assist mode never produces a misleading sector comparison',()=>{const t=new TimeTrial(storage());for(const split of [30,60,90])t.checkpoint(split,true);t.finish(140,true);t.checkpoint(25,false);assert.equal(t.delta,null);});
test('blocked or corrupted storage does not prevent gameplay',()=>{assert.doesNotThrow(()=>new TimeTrial({getItem(){throw Error('blocked');}}));assert.equal(new TimeTrial({getItem:()=>'{"time":-4}'}).best,null);});
