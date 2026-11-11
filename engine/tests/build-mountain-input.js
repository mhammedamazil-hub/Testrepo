// Shared metre-space terrain samples for the Blender render-only environment.
import fs from 'node:fs';
import {buildRoute,terrainData,terrainHeight} from '../src/online/map.js';
const route=buildRoute(),terrain=terrainData(route,256);
const boundary=Array.from({length:256},(_,i)=>{const a=i/256*Math.PI*2,x=Math.cos(a),z=Math.sin(a),scale=1200/Math.max(Math.abs(x),Math.abs(z));return terrainHeight(x*scale,z*scale,route);});
const output=new URL('../../.cache/mountain/input.json',import.meta.url);fs.mkdirSync(new URL('.',output),{recursive:true});fs.writeFileSync(output,JSON.stringify({segments:256,vertices:Array.from(terrain.vertices),boundary}));
