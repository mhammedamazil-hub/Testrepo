// Exact CPU optimization only: freeze transforms of truly static scene branches.
// Visibility, shader wind and material uniforms remain live. Dynamic descendants
// (car/wheels/headlights, character, sun, water and animated gates) are excluded.
export function freezeStatic(root){
 root.updateWorldMatrix(true,true);let count=0;
 root.traverse(node=>{node.matrixAutoUpdate=false;node.matrixWorldAutoUpdate=false;count++;});return count;
}
export function thawStatic(root){root.traverse(node=>{node.matrixAutoUpdate=true;node.matrixWorldAutoUpdate=true;});}
