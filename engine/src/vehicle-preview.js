import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';

/** Actual asset preview, with a separate bounded, disposable WebGL lifecycle. */
export class VehiclePreview {
  constructor(canvas,colour,onStatus=()=>{}){this.canvas=canvas;this.colour=colour;this.onStatus=onStatus;this.paint=[];this.disposed=false;this.last=0;this.ready=false;this.load().catch(e=>{if(!this.disposed)this.onStatus('Preview unavailable · '+e.message);});}
  async load(){
    this.renderer=new T.WebGLRenderer({canvas:this.canvas,antialias:true,alpha:true,powerPreference:'low-power'});this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));this.renderer.outputColorSpace=T.SRGBColorSpace;this.renderer.toneMapping=T.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.05;this.renderer.setClearColor(0x141618,0);
    this.scene=new T.Scene();this.camera=new T.PerspectiveCamera(37,1,.1,70);this.camera.position.set(5.7,2.2,-6.7);
    this.controls=new OrbitControls(this.camera,this.canvas);this.controls.target.set(0,.65,0);this.controls.enableDamping=true;this.controls.enablePan=false;this.controls.minDistance=5;this.controls.maxDistance=11;this.controls.maxPolarAngle=Math.PI*.49;
    const base=new URL('world/',document.baseURI),loader=new GLTFLoader();
    const [model,sky]=await Promise.all([loader.loadAsync(new URL('roadster/roadster.glb',base).href),new T.TextureLoader().loadAsync(new URL('sky.jpg',base).href)]);
    this.car=model.scene;this.scene.add(this.car);this.car.traverse(m=>{if(m.isMesh&&!Array.isArray(m.material)&&/car_main_paint/i.test(m.material.name)){m.material=m.material.clone();m.material.metalness=.5;m.material.roughness=.25;this.paint.push(m.material);}});this.setColour(this.colour);
    if(this.disposed){sky.dispose();this.disposeResources();return;}
    sky.colorSpace=T.SRGBColorSpace;sky.mapping=T.EquirectangularReflectionMapping;const pmrem=new T.PMREMGenerator(this.renderer);this.environment=pmrem.fromEquirectangular(sky).texture;pmrem.dispose();sky.dispose();this.scene.environment=this.environment;this.scene.environmentIntensity=.8;
    this.scene.add(new T.HemisphereLight(0xdde6ef,0x332f2a,1.4));for(const [xyz,power] of [[[3,6,-4],2.4],[[-4,3,5],1.8]]){const sun=new T.DirectionalLight(0xffefdc,power);sun.position.set(...xyz);this.scene.add(sun);}
    const floor=new T.Mesh(new T.CircleGeometry(4.2,80),new T.MeshBasicMaterial({color:0x1c2023}));floor.rotation.x=-Math.PI/2;floor.position.y=-.04;this.scene.add(floor);
    const canvas=document.createElement('canvas');canvas.width=canvas.height=128;const ctx=canvas.getContext('2d'),gradient=ctx.createRadialGradient(64,64,5,64,64,64);gradient.addColorStop(0,'#000b');gradient.addColorStop(1,'#0000');ctx.fillStyle=gradient;ctx.fillRect(0,0,128,128);const shadow=new T.Mesh(new T.PlaneGeometry(4.5,6),new T.MeshBasicMaterial({map:new T.CanvasTexture(canvas),transparent:true,depthWrite:false}));shadow.rotation.x=-Math.PI/2;shadow.position.y=-.025;this.scene.add(shadow);
    const ring=new T.Mesh(new T.RingGeometry(4.18,4.19,100),new T.MeshBasicMaterial({color:0x8d7759,side:T.DoubleSide}));ring.rotation.x=-Math.PI/2;ring.position.y=-.03;this.scene.add(ring);
    this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(this.canvas.parentElement);this.ready=true;this.resize();this.onStatus('LIVE ROADSTER / DRAG TO ORBIT');
    const frame=now=>{if(this.disposed)return;this.raf=requestAnimationFrame(frame);if(document.hidden||now-this.last<1000/24)return;this.last=now;this.render();};this.raf=requestAnimationFrame(frame);
  }
  setColour(value){this.colour=value;for(const material of this.paint)material.color.set(value);}
  resize(){if(this.disposed||!this.renderer)return;const r=this.canvas.parentElement.getBoundingClientRect();if(r.width<1||r.height<1)return;this.renderer.setSize(Math.round(r.width),Math.round(r.height),false);this.camera.aspect=r.width/r.height;this.camera.updateProjectionMatrix();}
  render(){if(!this.ready||this.disposed)return;this.resize();this.controls.update();this.renderer.render(this.scene,this.camera);}
  disposeResources(){const geometries=new Set(),materials=new Set(),textures=new Set();this.scene?.traverse(o=>{if(!o.isMesh)return;geometries.add(o.geometry);for(const m of Array.isArray(o.material)?o.material:[o.material]){materials.add(m);for(const value of Object.values(m))if(value?.isTexture)textures.add(value);}});for(const g of geometries)g.dispose();for(const m of materials)m.dispose();for(const t of textures)t.dispose();this.environment?.dispose();}
  dispose(){this.disposed=true;cancelAnimationFrame(this.raf);this.observer?.disconnect();this.controls?.dispose();this.disposeResources();this.renderer?.dispose();this.renderer?.forceContextLoss();}
}
