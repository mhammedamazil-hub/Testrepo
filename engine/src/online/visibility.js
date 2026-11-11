import * as T from 'three';

/** Render-only spatial LODs. Never owns or disables physics bodies.
 * Bounds are conservative unions of ALL levels; no centre-point culling.
 * Frustum is evaluated AFTER camera movement. Hysteresis avoids threshold flicker.
 */
export class VisibilitySystem {
  constructor(){this.cells=[];this.frustum=new T.Frustum();this.matrix=new T.Matrix4();this.stats={};this.enabled=true;}
  add(levels,distances,{radius=0,kind='scenery'}={}){
    if(levels.length!==distances.length||!levels.length)throw Error('One distance per LOD required');
    const box=new T.Box3();
    for(const object of levels){object.updateWorldMatrix(true,true);box.union(new T.Box3().setFromObject(object));object.visible=false;}
    const sphere=box.getBoundingSphere(new T.Sphere());sphere.radius+=radius;
    const cell={levels,distances,sphere,kind,level:-1};this.cells.push(cell);return cell;
  }
  update(camera){
    camera.updateMatrixWorld();this.matrix.multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse);this.frustum.setFromProjectionMatrix(this.matrix);
    const stats={cells:this.cells.length,visible:0,culled:0,near:0,mid:0,far:0};
    for(const cell of this.cells){
      const distance=Math.max(0,camera.position.distanceTo(cell.sphere.center)-cell.sphere.radius);
      let level=-1;
      if(!this.enabled){level=0;}else if(this.frustum.intersectsSphere(cell.sphere)){
        level=cell.distances.findIndex((limit,i)=>distance<limit*(i===cell.level?1.08:1));
      }
      for(let i=0;i<cell.levels.length;i++)cell.levels[i].visible=i===level;
      cell.level=level;if(level<0)stats.culled++;else{stats.visible++;stats[['near','mid','far'][Math.min(level,2)]]++;}
    }
    this.stats=stats;return stats;
  }
}

export function partitionInstances(matrices,size=300){
  const groups=new Map();
  for(const matrix of matrices){const e=matrix.elements,key=Math.floor(e[12]/size)+','+Math.floor(e[14]/size);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(matrix);}
  return [...groups.values()];
}
export function instanceGroup(parts,matrices){
  const group=new T.Group();
  for(const {geometry,material} of parts){const mesh=new T.InstancedMesh(geometry,material,matrices.length);matrices.forEach((matrix,i)=>mesh.setMatrixAt(i,matrix));mesh.computeBoundingBox();mesh.computeBoundingSphere();group.add(mesh);}
  return group;
}
