// Generate a smooth custom-runtime circuit; original shared/Godot assets are untouched.
import fs from 'node:fs';
import {makeRoute,TRACK_WIDTH} from '../../engine/src/track.js';
const source=JSON.parse(fs.readFileSync(new URL('../../game/assets/world_data.json',import.meta.url))).route;
const points=makeRoute(source);
const target=new URL('../../engine/public/world/track/',import.meta.url);fs.mkdirSync(target,{recursive:true});
fs.writeFileSync(new URL('route.json',target),JSON.stringify({schema:'alpine.circuit.v2',width:TRACK_WIDTH,points,gates:[160,320,480,0],modifications:'Original lakeside route resampled by centripetal Catmull-Rom to 640 arc-length points, smoothed elevation, 10m surface; shared original assets unchanged.'})+'\n');
