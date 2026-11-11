import * as T from 'three';

// Original procedural limestone detail, not a photogrammetry claim. The existing
// licensed ground photograph is retained on flat meadow surfaces. World-space
// projection avoids stretched cliff UVs and visible large repeating squares.
export function limestoneTexture(){
  const size=256,data=new Uint8Array(size*size*4);let seed=917;
  for(let y=0;y<size;y++)for(let x=0;x<size;x++){
    seed=(Math.imul(seed,1664525)+1013904223)>>>0;
    const strata=Math.sin(y*.21+Math.sin(x*.035)*1.7)*8+Math.sin(y*.77+x*.018)*4;
    const v=155+strata+(seed>>>27)-16,i=(y*size+x)*4;
    data.set([v+7,v+6,v,255],i);
  }
  const texture=new T.DataTexture(data,size,size);texture.colorSpace=T.SRGBColorSpace;texture.wrapS=texture.wrapT=T.RepeatWrapping;texture.generateMipmaps=true;texture.minFilter=T.LinearMipmapLinearFilter;texture.needsUpdate=true;return texture;
}
export function mountainMaterial(ground,rock){
  const mat=new T.MeshStandardMaterial({color:0xffffff,vertexColors:true,roughness:.94});
  mat.onBeforeCompile=shader=>{
    shader.uniforms.meadowMap={value:ground};shader.uniforms.rockMap={value:rock};
    shader.vertexShader='varying vec3 vMountainWorld; varying vec3 vMountainNormal;\n'+shader.vertexShader;
    shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvMountainWorld=(modelMatrix*vec4(position,1.0)).xyz;vMountainNormal=normalize(mat3(modelMatrix)*normal);');
    shader.fragmentShader='uniform sampler2D meadowMap;uniform sampler2D rockMap;varying vec3 vMountainWorld;varying vec3 vMountainNormal;\n'+shader.fragmentShader;
    shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>', `
      vec3 weights=pow(abs(normalize(vMountainNormal)),vec3(4.0));weights/=max(dot(weights,vec3(1.0)),.001);
      vec3 p=vMountainWorld;
      vec3 cliff=texture2D(rockMap,p.zy*.085).rgb*weights.x+texture2D(rockMap,p.xz*.085).rgb*weights.y+texture2D(rockMap,p.xy*.085).rgb*weights.z;
      vec3 meadow=texture2D(meadowMap,p.xz*.11).rgb;
      float slope=smoothstep(.10,.52,1.0-abs(normalize(vMountainNormal).y));
      float altitude=smoothstep(350.0,650.0,p.y);
      float macro=.88+.12*sin(p.x*.009+sin(p.z*.007)*2.0)*sin(p.z*.012);
      float strata=.87+.13*sin(p.y*.037+sin(p.x*.009+p.z*.013)*4.0+sin(p.z*.04));
      cliff*=strata;
      diffuseColor.rgb*=mix(meadow*1.7,cliff*1.3,max(slope,altitude))*macro;
    `);
  };
  mat.customProgramCacheKey=()=> 'alpine-triplanar-v1';return mat;
}
