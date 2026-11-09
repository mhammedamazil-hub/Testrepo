import * as T from 'three';
// Exact original geometry/materials. Transparent glass keeps its original sorting.
// Native multi-draw required; unsupported devices keep the unchanged mesh path.
export function batchVehicle(root,renderer){
 const groups=new Map(),batches=[],inverse=new T.Matrix4(),matrix=new T.Matrix4();let enabled=false;
 const update=()=>{root.updateMatrixWorld(true);inverse.copy(root.matrixWorld).invert();for(const b of batches)for(const item of b.items){matrix.multiplyMatrices(inverse,item.source.matrixWorld);b.mesh.setMatrixAt(item.id,matrix);}};
 const setEnabled=value=>{enabled=!!value&&batches.length>0;for(const b of batches){b.mesh.visible=enabled;for(const item of b.items)item.source.visible=enabled?false:item.visible;}};
 if(renderer.extensions.has('WEBGL_multi_draw')){
  root.traverse(mesh=>{if(!mesh.isMesh||mesh.isSkinnedMesh||!mesh.visible||Array.isArray(mesh.material)||mesh.material.transparent)return;
   const g=mesh.geometry,key=mesh.material.uuid+'|'+Object.entries(g.attributes).map(([n,a])=>n+':'+a.itemSize+':'+a.normalized).sort().join(',')+'|'+!!g.index+'|'+mesh.castShadow+'|'+mesh.receiveShadow+'|'+mesh.renderOrder;
   if(!groups.has(key))groups.set(key,[]);groups.get(key).push(mesh);
  });
  for(const sources of groups.values()){
   if(sources.length<2)continue;
   const vertices=sources.reduce((n,m)=>n+m.geometry.getAttribute('position').count,0),indices=sources.reduce((n,m)=>n+(m.geometry.index?.count||0),0);
   const mesh=new T.BatchedMesh(sources.length,vertices,indices,sources[0].material);mesh.name='RoadsterExactMaterialBatch';mesh.castShadow=sources[0].castShadow;mesh.receiveShadow=sources[0].receiveShadow;mesh.renderOrder=sources[0].renderOrder;mesh.frustumCulled=false;
   const items=sources.map(source=>{const geometryId=mesh.addGeometry(source.geometry),id=mesh.addInstance(geometryId);return {source,id,visible:source.visible};});root.add(mesh);batches.push({mesh,items});
  }
  update();setEnabled(true);
 }
 return {update,setEnabled,get enabled(){return enabled;},batch_count:batches.length,source_meshes:batches.reduce((n,b)=>n+b.items.length,0),get meshes(){return batches.map(b=>b.mesh);}};
}
