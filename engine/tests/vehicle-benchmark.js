// Reproduce the actual solver figures; no rendered or timed speed animation.
// node engine/tests/vehicle-benchmark.js [output.json]
import fs from 'node:fs';
import {AlpinePhysics,distanceXZ} from '../src/physics.js';
import {ROADSTER} from '../src/vehicle-spec.js';
const p=await AlpinePhysics.create(),dt=1/60;
const neutral={x:0,y:0,throttle:0,brake:false,jump:false,run:false};
p.addTrimesh(new Float32Array([-100,0,-1000,100,0,-1000,100,0,100,-100,0,100]),new Uint32Array([0,2,1,0,3,2]),'road');
p.reset([[0,0,0],[0,0,-2],[0,0,-4]]);p.settle(180);p.interact();
let ticks=0;while(p.speed<26.8224&&ticks<1200){p.step(dt,{...neutral,throttle:1},0);ticks++;}
const initialSpeed=p.speed,from={...p.car.translation()};let braking=0;
while(Math.abs(p.speed)>=.1&&braking<1200){p.step(dt,{...neutral,brake:true},0);braking++;}
const result={scope:'Actual Rapier WASM flat dry-road simulation; not manufacturer telemetry or a certified real-car test.',mass_kg:ROADSTER.mass,gravity_ms2:9.81,timestep_s:dt,zero_to_60mph_s:ticks*dt,brake_initial_speed_ms:initialSpeed,brake_to_below_0_1ms_s:braking*dt,braking_distance_m:distanceXZ(from,p.car.translation()),assumptions:ROADSTER.assumptions};
p.dispose();console.log(JSON.stringify(result,null,2));if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2)+'\n');
