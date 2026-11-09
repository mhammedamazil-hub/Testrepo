import fs from 'node:fs';
export function meshesFromGLB(path){
 const bytes=fs.readFileSync(path),size=bytes.readUInt32LE(12),j=JSON.parse(bytes.subarray(20,20+size)),base=28+size;
 const array=index=>{const a=j.accessors[index],v=j.bufferViews[a.bufferView],offset=base+(v.byteOffset||0)+(a.byteOffset||0),count=a.count*(a.type==='VEC3'?3:1);const Type={5126:Float32Array,5125:Uint32Array,5123:Uint16Array}[a.componentType];return new Type(bytes.buffer.slice(bytes.byteOffset+offset,bytes.byteOffset+offset+count*Type.BYTES_PER_ELEMENT));};
 return j.meshes.flatMap(mesh=>mesh.primitives.map(p=>({name:mesh.name,vertices:array(p.attributes.POSITION),indices:Uint32Array.from(array(p.indices))})));
}
