// KILN showroom — a live rebuild of the Blender house set (plaster arch, plinth,
// terracotta vessel) so visitors can walk the same room that was rendered in Cycles.
import * as THREE from './vendor/three.module.min.js';

const canvas = document.getElementById('room');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
renderer.setSize(innerWidth, innerHeight, false);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.06;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0c0e);
scene.fog = new THREE.Fog(0x0b0c0e, 16, 44);

const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.1, 140);

/* ---------- materials ---------- */
const finishes = {
  bone: { color: 0xefe7d8, metalness: 0.03, roughness: 0.78, emissive: 0x000000 },
  terra: { color: 0xc2552c, metalness: 0.04, roughness: 0.62, emissive: 0x140500 },
  sage: { color: 0x6f7a5e, metalness: 0.05, roughness: 0.66, emissive: 0x030502 },
  steel: { color: 0x9c9a93, metalness: 0.86, roughness: 0.24, emissive: 0x000000 },
};

const plaster = new THREE.MeshStandardMaterial({ color: 0xefe7d8, roughness: 0.82, metalness: 0.02 });
const boneMat = new THREE.MeshStandardMaterial({ roughness: 0.52, metalness: 0.05 });
const floorMat = new THREE.MeshStandardMaterial({ color: 0x0d0e11, roughness: 0.34, metalness: 0.22 });

/* ---------- room ---------- */
const room = new THREE.Group();
scene.add(room);

const floor = new THREE.Mesh(new THREE.PlaneGeometry(70, 70), floorMat);
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
room.add(floor);

/* the kiln mouth: an extruded arch-shaped wall, exactly like the render */
function archWall(width, height, depth, openW, openH) {
  const s = new THREE.Shape();
  const x0 = -width / 2, x1 = width / 2;
  s.moveTo(x0, 0);
  s.lineTo(x1, 0);
  s.lineTo(x1, height);
  s.lineTo(x0, height);
  s.lineTo(x0, 0);

  const hole = new THREE.Path();
  const ox0 = -openW / 2, ox1 = openW / 2;
  hole.moveTo(ox0, 0.02);
  hole.lineTo(ox0, openH);
  hole.absarc(0, openH, ox1, Math.PI, 0, true);
  hole.lineTo(ox1, 0.02);
  hole.lineTo(ox0, 0.02);
  s.holes.push(hole);

  const geo = new THREE.ExtrudeGeometry(s, { depth, bevelEnabled: false, curveSegments: 48 });
  geo.translate(0, 0, -depth / 2);
  return geo;
}

const kiln = new THREE.Mesh(archWall(5.4, 4.0, 0.5, 1.7, 1.5), plaster);
kiln.position.set(1.25, 0, -3.5);
kiln.rotation.y = THREE.MathUtils.degToRad(-13);
kiln.castShadow = true;
kiln.receiveShadow = true;
room.add(kiln);

const stele = new THREE.Mesh(new THREE.BoxGeometry(1.05, 3.9, 1.05), plaster);
stele.position.set(-2.35, 1.95, -1.75);
stele.rotation.y = THREE.MathUtils.degToRad(11);
stele.castShadow = true;
stele.receiveShadow = true;
room.add(stele);

const bench = new THREE.Mesh(new THREE.BoxGeometry(3.0, 0.58, 1.35), plaster);
bench.position.set(0.35, 0.29, -0.55);
bench.rotation.y = THREE.MathUtils.degToRad(-7);
bench.castShadow = true;
bench.receiveShadow = true;
room.add(bench);

const vessel = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 1.05, 96, 1), boneMat);
vessel.position.set(0.28, 1.11, -0.5);
vessel.castShadow = true;
room.add(vessel);

const ball = new THREE.Mesh(new THREE.SphereGeometry(0.17, 48, 32), boneMat);
ball.position.set(-1.62, 0.17, 0.55);
ball.castShadow = true;
room.add(ball);

/* ---------- light rig (mirrors the Cycles setup) ---------- */
scene.add(new THREE.HemisphereLight(0xfff2e4, 0x0a0c10, 0.42));

const key = new THREE.DirectionalLight(0xffd9b0, 3.1);
key.position.set(-6.2, 6.0, -5.0);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.near = 1;
key.shadow.camera.far = 40;
key.shadow.camera.left = -12;
key.shadow.camera.right = 12;
key.shadow.camera.top = 12;
key.shadow.camera.bottom = -12;
key.shadow.bias = -0.0012;
scene.add(key);

const rim = new THREE.PointLight(0xff7a33, 34, 22, 2);
rim.position.set(1.5, 1.5, -5.6);
scene.add(rim);

const fill = new THREE.DirectionalLight(0xcfd6e0, 0.5);
fill.position.set(6.4, 3.0, -6.4);
scene.add(fill);

/* ---------- orbit ---------- */
const orbit = {
  theta: 0.20, phi: 1.24, radius: 12.6,
  thetaT: 0.20, phiT: 1.24, radiusT: 12.6,
  minPhi: 0.5, maxPhi: 1.5, minR: 6.5, maxR: 20,
};
let dragging = false, lastX = 0, lastY = 0, idle = true;

canvas.addEventListener('pointerdown', (e) => {
  dragging = true; idle = false;
  lastX = e.clientX; lastY = e.clientY;
  canvas.setPointerCapture?.(e.pointerId);
});
canvas.addEventListener('pointermove', (e) => {
  if (!dragging) return;
  orbit.thetaT -= (e.clientX - lastX) * 0.005;
  orbit.phiT = Math.min(orbit.maxPhi, Math.max(orbit.minPhi, orbit.phiT - (e.clientY - lastY) * 0.004));
  lastX = e.clientX; lastY = e.clientY;
});
addEventListener('pointerup', () => { dragging = false; });

canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  idle = false;
  orbit.radiusT = Math.min(orbit.maxR, Math.max(orbit.minR, orbit.radiusT + e.deltaY * 0.005));
}, { passive: false });

let pinch = 0;
canvas.addEventListener('touchstart', (e) => {
  if (e.touches.length === 2) pinch = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
}, { passive: true });
canvas.addEventListener('touchmove', (e) => {
  if (e.touches.length !== 2) return;
  const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
  if (pinch) orbit.radiusT = Math.min(orbit.maxR, Math.max(orbit.minR, orbit.radiusT - (d - pinch) * 0.02));
  pinch = d;
}, { passive: true });

/* ---------- finish switching ---------- */
const swButtons = [...document.querySelectorAll('.sw')];
swButtons.forEach((btn) => {
  btn.addEventListener('click', () => {
    swButtons.forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    const f = finishes[btn.dataset.finish];
    boneMat.color.setHex(f.color);
    boneMat.metalness = f.metalness;
    boneMat.roughness = f.roughness;
    boneMat.emissive.setHex(f.emissive);
  });
});

/* ---------- loop ---------- */
const callsEl = document.getElementById('calls');
const fpsEl = document.getElementById('fps');
const trisEl = document.getElementById('tris');

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.fov = innerWidth < 760 ? 54 : 38;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight, false);
});
camera.fov = innerWidth < 760 ? 54 : 38;
camera.updateProjectionMatrix();

const t0 = performance.now();
let frames = 0, acc = 0, last = t0;

function tick(now) {
  const dt = Math.min((now - last) / 1000, 0.05);
  last = now;
  const t = (now - t0) / 1000;

  if (idle && !dragging) orbit.thetaT += dt * 0.045;

  orbit.theta += (orbit.thetaT - orbit.theta) * 0.06;
  orbit.phi += (orbit.phiT - orbit.phi) * 0.06;
  orbit.radius += (orbit.radiusT - orbit.radius) * 0.06;

  const sp = Math.sin(orbit.phi);
  // on desktop, bias the frame right so the panel does not sit on the subject
  const shift = innerWidth > 900 ? 1.55 : 0;
  camera.position.set(
    Math.sin(orbit.theta) * sp * orbit.radius + shift,
    Math.cos(orbit.phi) * orbit.radius * 0.9 + 0.9,
    Math.cos(orbit.theta) * sp * orbit.radius
  );
  camera.lookAt(shift * 0.78, 1.35, -1.1);

  vessel.rotation.y = t * 0.12;
  rim.intensity = 32 + Math.sin(t * 1.7) * 2.4;

  renderer.render(scene, camera);

  frames++; acc += dt;
  if (acc > 0.5) {
    fpsEl.textContent = Math.round(frames / acc);
    callsEl.textContent = renderer.info.render.calls;
    trisEl.textContent = renderer.info.render.triangles.toLocaleString();
    frames = 0; acc = 0;
  }
  requestAnimationFrame(tick);
}

// expose for CI verification
window.__kiln = { renderer, scene, camera, frames: () => frames };
requestAnimationFrame(tick);
