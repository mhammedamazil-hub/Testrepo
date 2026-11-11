import * as T from 'three';

/** World-space meadow / fractured limestone. Licensed rock colour/AO/height maps, adapted from the MIT demo asset;
 * see world/mountain/material-provenance.json. Alpha stores rock height.
 * Normal detail fades with distance; distant terrain has no micro-bump cost.
 */
export function mountainMaterial(ground,rock){
  rock.colorSpace=T.SRGBColorSpace;rock.wrapS=rock.wrapT=T.RepeatWrapping;rock.anisotropy=4;
  const material=new T.MeshStandardMaterial({color:0xffffff,vertexColors:true,roughness:.96});
  material.onBeforeCompile=shader=>{
    shader.uniforms.meadowMap={value:ground};shader.uniforms.rockMap={value:rock};
    shader.vertexShader='varying vec3 vMountainWorld;varying vec3 vMountainNormal;\n'+shader.vertexShader;
    shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>
      vMountainWorld=(modelMatrix*vec4(position,1.0)).xyz;
      vMountainNormal=normalize(mat3(modelMatrix)*normal);
    `);
    shader.fragmentShader='uniform sampler2D meadowMap;uniform sampler2D rockMap;varying vec3 vMountainWorld;varying vec3 vMountainNormal;\n'+shader.fragmentShader;
    shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>',`
      vec3 p=vMountainWorld;
      vec3 weights=pow(abs(normalize(vMountainNormal)),vec3(4.0));weights/=max(dot(weights,vec3(1.0)),.001);
      vec4 rx=texture2D(rockMap,p.zy*.075),ry=texture2D(rockMap,p.xz*.075),rz=texture2D(rockMap,p.xy*.075);
      vec4 rockDetail=rx*weights.x+ry*weights.y+rz*weights.z;
      vec3 meadow=texture2D(meadowMap,p.xz*.12).rgb;
      vec3 broadRock=texture2D(rockMap,p.xz*.006).rgb;
      float slope=smoothstep(.08,.5,1.0-abs(normalize(vMountainNormal).y));
      float cliffMask=max(slope,smoothstep(450.0,800.0,p.y));
      float macro=.72+.5*dot(broadRock,vec3(.3333));
      vec3 terrainColour=mix(meadow*1.8,rockDetail.rgb*1.65,cliffMask)*macro;
      float snowLine=smoothstep(1050.0,1550.0,p.y+broadRock.r*180.0);
      float snowShelf=1.0-smoothstep(.25,.8,1.0-abs(normalize(vMountainNormal).y));
      terrainColour=mix(terrainColour,vec3(1.32,1.38,1.43),snowLine*snowShelf);
      diffuseColor.rgb*=terrainColour;
      float mountainBump=mix(dot(meadow,vec3(.3333))*.035,rockDetail.a*.32,cliffMask);
      float mountainDetailFade=1.0-smoothstep(150.0,1000.0,distance(cameraPosition,p));
    `);
    shader.fragmentShader=shader.fragmentShader.replace('#include <normal_fragment_maps>',`#include <normal_fragment_maps>
      if(mountainDetailFade>.01){
        vec3 q0=dFdx(-vViewPosition),q1=dFdy(-vViewPosition);
        vec3 r1=cross(q1,normal),r2=cross(normal,q0);
        float determinant=dot(q0,r1);
        vec3 surfaceGradient=dFdx(mountainBump)*r1+dFdy(mountainBump)*r2;
        normal=normalize(abs(determinant)*normal-sign(determinant)*surfaceGradient*mountainDetailFade);
      }
    `);
  };
  material.customProgramCacheKey=()=> 'alpine-fractured-limestone-v3';return material;
}
