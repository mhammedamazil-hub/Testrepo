import * as T from 'three';
import {ribbon} from './track.js';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
// Original track art. No external downloads, lights or extra shadow maps.
function strip(route,width,offset,lift,material,striped=false){
 const data=ribbon(route,width,offset,lift),g=new T.BufferGeometry();g.setAttribute('position',new T.BufferAttribute(data.positions,3));g.setAttribute('uv',new T.BufferAttribute(data.uvs,2));g.setIndex(new T.BufferAttribute(data.indices,1));g.computeVertexNormals();
 let geometry=g;
 if(striped){geometry=g.toNonIndexed();g.dispose();const colors=new Float32Array(geometry.attributes.position.count*3);for(let i=0;i<colors.length/3;i++){const white=Math.floor(Math.floor(i/6)/2)%2===0;new T.Color(white?0xe9e5d7:0xaf302c).toArray(colors,i*3);}geometry.setAttribute('color',new T.BufferAttribute(colors,3));}
 const mesh=new T.Mesh(geometry,material);mesh.receiveShadow=true;return mesh;
}
export function addCircuitArt(world,roadMaterial){
 const group=new T.Group();group.name='CircuitPresentation';const route=world.data.route;
 const kerbMaterial=new T.MeshStandardMaterial({vertexColors:true,roughness:.86});
 for(const side of [-1,1])group.add(strip(route,.64,side*5.3,.027,kerbMaterial,true));
 // Retain original asphalt base map; a deterministic detail texture adds aggregate
 // and rubber variation without replacing the supplied texture or increasing size.
 const size=128,data=new Uint8Array(size*size*4);let seed=137;
 for(let i=0;i<size*size;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;const v=155+(seed>>>26);data.set([v,v,v,255],i*4);}
 const grain=new T.DataTexture(data,size,size);grain.wrapS=grain.wrapT=T.RepeatWrapping;grain.needsUpdate=true;
 roadMaterial.onBeforeCompile=shader=>{shader.uniforms.circuitGrain={value:grain};shader.vertexShader='varying vec2 circuitUV;\n'+shader.vertexShader;shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\ncircuitUV=uv;');shader.fragmentShader='varying vec2 circuitUV;uniform sampler2D circuitGrain;\n'+shader.fragmentShader;shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>',`#include <map_fragment>
 float aggregate=texture2D(circuitGrain,circuitUV*vec2(22.0,12.0)).r;
 float rubber=exp(-pow((circuitUV.x-.28)*24.0,2.0))+exp(-pow((circuitUV.x-.72)*24.0,2.0));
 diffuseColor.rgb*=mix(.88,1.12,aggregate)* (1.0-.13*rubber);`);};roadMaterial.customProgramCacheKey=()=> 'circuit-aggregate-v5';roadMaterial.needsUpdate=true;
 const white=new T.MeshStandardMaterial({color:0xe1e4df,roughness:.75}),dark=new T.MeshStandardMaterial({color:0x111c24,metalness:.55,roughness:.45});
 const origin=route[0],next=route[1],yaw=Math.atan2(-(next[0]-origin[0]),-(next[2]-origin[2])),start=new T.Group();start.position.set(...origin);start.rotation.y=yaw;group.add(start);
 // Flat painted checkerboard, entirely above the existing road collision surface.
 const checks=new T.InstancedMesh(new T.PlaneGeometry(.5,.5),white,40),dummy=new T.Object3D();let j=0;
 for(let row=0;row<4;row++)for(let col=0;col<20;col++)if((row+col)%2===0){dummy.position.set(-4.75+col*.5,.032,-row*.5);dummy.rotation.set(-Math.PI/2,0,0);dummy.updateMatrix();checks.setMatrixAt(j++,dummy.matrix);}checks.count=j;start.add(checks);
 for(const x of [-6.7,6.7]){const post=new T.Mesh(new T.BoxGeometry(.38,5.4,.38),dark);post.position.set(x,2.7,0);start.add(post);}
 const crossbar=new T.Mesh(new T.BoxGeometry(13.8,.68,.3),dark);crossbar.position.set(0,5.2,0);start.add(crossbar);
 const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=128;const ctx=canvas.getContext('2d');ctx.fillStyle='#11232c';ctx.fillRect(0,0,1024,128);ctx.fillStyle='#b9edf1';ctx.font='bold 50px sans-serif';ctx.textAlign='center';ctx.fillText('ALPINE  /  LAKESIDE CIRCUIT',512,67);ctx.fillStyle='#97aaa8';ctx.font='18px sans-serif';ctx.fillText('START / FINISH     •     TIME ATTACK',512,103);
 const banner=new T.Mesh(new T.PlaneGeometry(12,.65),new T.MeshBasicMaterial({map:new T.CanvasTexture(canvas),side:T.DoubleSide}));banner.position.set(0,5.2,.16);start.add(banner);
 // Repeated reflective course markers and bend signs share meshes/materials.
 const reflectors=new T.InstancedMesh(new T.BoxGeometry(.12,.14,.12),new T.MeshStandardMaterial({color:0xd5ecde,emissive:0x93b9a4,emissiveIntensity:.32,roughness:.5}),route.length/8*2);j=0;
 for(let i=0;i<route.length;i+=8){const a=route[i],b=route[(i+1)%route.length],dx=b[0]-a[0],dz=b[2]-a[2],length=Math.hypot(dx,dz);for(const side of [-1,1]){dummy.position.set(a[0]-dz/length*6*side,a[1]+.85,a[2]+dx/length*6*side);dummy.rotation.set(0,0,0);dummy.updateMatrix();reflectors.setMatrixAt(j++,dummy.matrix);}}group.add(reflectors);
 const boardCanvas=document.createElement('canvas');boardCanvas.width=128;boardCanvas.height=64;const b=boardCanvas.getContext('2d');b.fillStyle='#e6c77c';b.fillRect(0,0,128,64);b.strokeStyle='#12212a';b.lineWidth=13;for(const x of [28,70]){b.beginPath();b.moveTo(x-14,8);b.lineTo(x+14,32);b.lineTo(x-14,56);b.stroke();}
 const boardMat=new T.MeshBasicMaterial({map:new T.CanvasTexture(boardCanvas),side:T.DoubleSide}),boards=new T.InstancedMesh(new T.PlaneGeometry(1.8,.9),boardMat,24);j=0;
 for(let i=24;i<route.length&&j<24;i+=26){const a=route[(i+route.length-8)%route.length],p=route[i],n=route[(i+8)%route.length],dx=n[0]-p[0],dz=n[2]-p[2],len=Math.hypot(dx,dz),cross=(p[0]-a[0])*dz-(p[2]-a[2])*dx;if(Math.abs(cross)<2)continue;const side=Math.sign(cross);dummy.position.set(p[0]-dz/len*6.5*side,p[1]+1.25,p[2]+dx/len*6.5*side);dummy.rotation.set(0,Math.atan2(-dx,-dz),0);dummy.scale.set(side,1,1);dummy.updateMatrix();boards.setMatrixAt(j++,dummy.matrix);}boards.count=j;group.add(boards);
 // Bake/merge only same-material static meshes; checker/reflector instances,
 // original material appearance and all geometry stay unchanged.
 group.updateMatrixWorld(true);const groups=new Map();group.traverse(m=>{if(m.isMesh&&!m.isInstancedMesh){if(!groups.has(m.material))groups.set(m.material,[]);groups.get(m.material).push(m);}});
 for(const [material,meshes] of groups){if(meshes.length<2)continue;const parts=meshes.map(m=>m.geometry.clone().applyMatrix4(m.matrixWorld)),merged=mergeGeometries(parts);if(!merged){parts.forEach(g=>g.dispose());continue;}const mesh=new T.Mesh(merged,material);mesh.receiveShadow=meshes.some(m=>m.receiveShadow);mesh.name='MergedCircuitArt';group.add(mesh);for(const m of meshes){m.removeFromParent();m.geometry.dispose();}parts.forEach(g=>g.dispose());}
 world.scene.add(group);world.trackArt={group,kerbs:2,boards:j,reflectors:reflectors.count,grain};return group;
}
