import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {COLOURS,cleanName} from './online/protocol.js';
import './design.css';
const $=id=>document.getElementById(id);
const assets=new URL('world/',document.baseURI);
const refs=[['01-mountain-world','Mountain world'],['02-guest-live-car','Guest / live car'],['03-room-lobby','Room lobby'],['04-desktop-race','Desktop racing'],['05-mobile-race','Touch racing'],['06-track-map','Track map'],['07-race-results','Results / rematch'],['08-settings','Settings'],['09-pause-connection','Online pause / connection'],['10-solo-home-garage','Solo home / garage']];
for(const [file,title] of refs){const a=document.createElement('a');a.href=new URL('design-reference/'+file+'.jpg',document.baseURI);a.target='_blank';a.rel='noopener';const img=document.createElement('img');img.src=a.href;img.alt=title+' — AI-generated design reference, not gameplay';img.loading='lazy';const caption=document.createElement('span');caption.textContent=title;a.append(img,caption);$('references').append(a);}
let colour=COLOURS[0],renderer,car,controls,scene,camera,paint=[];
for(const value of COLOURS){const b=document.createElement('button');b.type='button';b.style.setProperty('--paint',value);b.setAttribute('aria-label','Car paint '+value);b.setAttribute('aria-pressed',String(value===colour));b.onclick=()=>{colour=value;for(const p of paint)p.color.set(value);for(const other of $('swatches').children)other.setAttribute('aria-pressed',String(other===b));};$('swatches').append(b);}
function name(){const value=cleanName($('driver').value)||'YOUR NAME';$('name-preview').textContent=value;$('driver-label').textContent=value;}
$('driver').addEventListener('input',name);name();
$('test-drive').onclick=()=>{try{sessionStorage.setItem('alpine-guest-name',cleanName($('driver').value)||'Guest');sessionStorage.setItem('alpine-preview-colour',colour);}catch{}location.href='multiplayer.html?practice=1';};
async function init(){
 try{
  renderer=new T.WebGLRenderer({canvas:$('car-preview'),antialias:true,powerPreference:'low-power'});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setClearColor(0x141618);renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;
  scene=new T.Scene();camera=new T.PerspectiveCamera(38,1,.1,100);camera.position.set(5.6,2.3,-6.8);
  controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,.75,0);controls.enableDamping=true;controls.enablePan=false;controls.minDistance=5;controls.maxDistance=12;controls.maxPolarAngle=Math.PI*.49;
  const [model,sky]=await Promise.all([new GLTFLoader().loadAsync(new URL('roadster/roadster.glb',assets).href),new T.TextureLoader().loadAsync(new URL('sky.jpg',assets).href)]);
  sky.colorSpace=T.SRGBColorSpace;sky.mapping=T.EquirectangularReflectionMapping;const pmrem=new T.PMREMGenerator(renderer);scene.environment=pmrem.fromEquirectangular(sky).texture;pmrem.dispose();sky.dispose();scene.environmentIntensity=1.2;
  car=model.scene;car.traverse(m=>{if(m.isMesh&&!Array.isArray(m.material)&&/car_main_paint/i.test(m.material.name)){m.material=m.material.clone();m.material.color.set(colour);m.material.metalness=.6;m.material.roughness=.24;paint.push(m.material);}});scene.add(car);
  scene.add(new T.HemisphereLight(0xe9efff,0x2d2a26,2));for(const [position,intensity] of [[[4,7,5],3],[[-5,3,-4],2]]){const light=new T.DirectionalLight(0xffefdc,intensity);light.position.set(...position);scene.add(light);}
  const platform=new T.Mesh(new T.CylinderGeometry(3.8,3.8,.12,64),new T.MeshStandardMaterial({color:0x24272a,roughness:.78,metalness:.25}));platform.position.y=-.08;scene.add(platform);
  const ring=new T.Mesh(new T.RingGeometry(3.8,3.82,96),new T.MeshBasicMaterial({color:0xcba36b,side:T.DoubleSide}));ring.rotation.x=-Math.PI/2;ring.position.y=-.012;scene.add(ring);
  const ground=new T.Mesh(new T.PlaneGeometry(100,100),new T.MeshStandardMaterial({color:0x131517,roughness:1}));ground.rotation.x=-Math.PI/2;ground.position.y=-.15;scene.add(ground);scene.fog=new T.Fog(0x141618,16,40);
  function resize(){const box=$('preview-stage').getBoundingClientRect();renderer.setSize(Math.max(1,box.width),Math.max(1,box.height),false);camera.aspect=box.width/Math.max(1,box.height);camera.updateProjectionMatrix();}
  new ResizeObserver(resize).observe($('preview-stage'));resize();$('preview-status').textContent='LIVE THREE.JS / DRAG TO ORBIT';
  let last=0;function frame(now){requestAnimationFrame(frame);if(document.hidden||now-last<1000/24)return;last=now;controls.update();renderer.render(scene,camera);}requestAnimationFrame(frame);
  window.garagePreview={renderer,scene,camera,car,paint,render(){resize();controls.update();renderer.render(scene,camera);}};
 }catch(error){$('preview-status').textContent='Preview unavailable: '+error.message;}
}
init();
