import * as T from 'three';
export function bladeGeometry(){
 const positions=[],colors=[],indices=[];
 for(let blade=0;blade<3;blade++){const angle=blade*2.399,h=[.38,.52,.44][blade],base=positions.length/3;
  for(let row=0;row<=4;row++){const t=row/4,w=.025*(1-t)+.001;for(const side of [-1,1]){positions.push(Math.cos(angle)*w*side+Math.sin(angle)*t*t*.12,t*h,Math.sin(angle)*w*side+Math.cos(angle)*t*t*.12);colors.push(.39+t*.20,.48+t*.18,.22+t*.12);}}
  for(let row=0;row<4;row++){const a=base+row*2;indices.push(a,a+1,a+2,a+1,a+3,a+2);}
 }
 const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(positions,3));g.setAttribute('color',new T.Float32BufferAttribute(colors,3));g.setIndex(indices);g.computeVertexNormals();return g;
}
export function addMeadow(world,placements){
 const geometry=bladeGeometry(),time={value:0},material=new T.MeshStandardMaterial({color:0x889b67,vertexColors:true,roughness:.94,side:T.DoubleSide});
 material.onBeforeCompile=shader=>{shader.uniforms.meadowTime=time;shader.vertexShader='uniform float meadowTime;\n'+shader.vertexShader;shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>
 float phase=instanceMatrix[3].x*.33+instanceMatrix[3].z*.27;float bend=position.y*position.y;
 transformed.x+=sin(meadowTime*1.35+phase)*bend*.24;transformed.z+=cos(meadowTime*.9+phase)*bend*.14;`);};
 const cells=new Map();for(const p of placements){const key=Math.floor(p[0]/64)+','+Math.floor(p[2]/64);if(!cells.has(key))cells.set(key,[]);cells.get(key).push(p);}
 const dummy=new T.Object3D();for(const plants of cells.values()){
  const mesh=new T.InstancedMesh(geometry,material,plants.length),center=new T.Vector3();plants.forEach((p,i)=>{dummy.position.set(p[0],p[1],p[2]);dummy.rotation.set(0,p[4],0);dummy.scale.setScalar(p[3]);dummy.updateMatrix();mesh.setMatrixAt(i,dummy.matrix);center.add(dummy.position);});
  center.multiplyScalar(1/plants.length);mesh.name='MeadowBlades';mesh.receiveShadow=true;mesh.castShadow=false;mesh.computeBoundingSphere();mesh.boundingSphere.radius+=.2;world.scene.add(mesh);world.staticRoots.push(mesh);world.details.push({mesh,center,range:105});
 }
 world.meadow={time,material,geometry,count:placements.length,cells:cells.size};
}
