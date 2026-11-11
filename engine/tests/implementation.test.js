import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {buildRoute,terrainHeight} from '../src/online/map.js';
import {PRESETS} from '../src/online/quality.js';
const read=p=>fs.readFileSync(new URL(p,import.meta.url));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
test('licensed rock colour/AO/height originals and packed runtime map match provenance',()=>{
 const meta=JSON.parse(read('../public/world/mountain/material-provenance.json'));assert.equal(meta.license,'MIT');assert.match(meta.source,/b761b4cd5718a7118f2c95eb55f181d0a5f004f1/);
 for(const [name,sha] of Object.entries(meta.sources))assert.equal(hash(read('../../game/assets/mountain/pbr-original/'+name)),sha);
 assert.equal(hash(read('../public/world/mountain/limestone-pbr.png')),meta.output_sha256);assert.match(read('../../game/assets/mountain/pbr-original/LICENSE.txt').toString(),/Permission is hereby granted/);
});
test('valley stays open and varies naturally rather than excavating a road trench through a high sheet',()=>{
 const route=buildRoute(),heights=[];for(const x of [-700,-350,0,350,700])for(const z of [-700,-350,0,350,700])heights.push(terrainHeight(x,z,route));assert.ok(heights.every(Number.isFinite));assert.ok(Math.max(...heights)<60);assert.ok(Math.max(...heights)-Math.min(...heights)>10);
 for(let i=0;i<1024;i+=16){const p=route[i];assert.ok(Math.abs(terrainHeight(p[0],p[2],route)-(p[1]-.45))<1e-5);}
});
test('expanded forest counts retain low/balanced/high distinction and bounded near detail',()=>{assert.ok(PRESETS.low.trees<PRESETS.balanced.trees);assert.ok(PRESETS.balanced.trees<PRESETS.high.trees);assert.ok(PRESETS.high.trees>=10000);assert.equal(PRESETS.low.shadows,false);});
test('all Blender terrain meshes have finite bounding positions and a non-flat mountain skyline',()=>{
 const glb=read('../public/world/mountain/alpine-massif.glb');assert.equal(glb.toString('ascii',0,4),'glTF');const json=JSON.parse(glb.subarray(20,20+glb.readUInt32LE(12)));const maxima=[];
 for(const mesh of json.meshes){for(const primitive of mesh.primitives){const accessor=json.accessors[primitive.attributes.POSITION];assert.ok(accessor.min.every(Number.isFinite)&&accessor.max.every(Number.isFinite));if(mesh.name.startsWith('Massif_'))maxima.push(accessor.max[1]);}}
 assert.ok(Math.max(...maxima)>1200);assert.ok(Math.max(...maxima)-Math.min(...maxima)>500);
});

test('Blender terrain is rebuilt from the current runtime elevation source',()=>{
 const manifest=JSON.parse(read('../public/world/mountain/manifest.json'));
 assert.equal(manifest.terrain_source_sha256,hash(read('../src/online/map.js')));
 assert.equal(manifest.sha256,hash(read('../public/world/mountain/alpine-massif.glb')));
});
