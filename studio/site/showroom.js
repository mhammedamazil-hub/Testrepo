// LUMENFORGE showroom — orbitable generated room with live material switching.
import * as THREE from './vendor/three.module.min.js';

const canvas = document.getElementById('room');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
renderer.setSize(innerWidth, innerHeight, false);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.02;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x06070b);
scene.fog = new THREE.Fog(0x06070b, 14, 38);

const camera = new THREE.PerspectiveCamera(46, innerWidth / innerHeight, 0.1, 120);

/* ---------- room ---------- */
const room = new THREE.Group();
scene.add(room);

const FLOOR = 16;
const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(FLOOR, FLOOR, 1, 1),
  new THREE.MeshStandardMaterial({ color: 0x0a0c12, roughness: 0.72, metalness: 0.28 })
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -1.6;
floor.receiveShadow = true;
room.add(floor);

const grid = new THREE.GridHelper(FLOOR, 32, 0x1c6e60, 0x0f302c);
grid.position.y = -1.595;
grid.material.transparent = true;
grid.material.opacity = 0.42;
room.add(grid);

/* ---------- plinth + hero object ---------- */
const plinth = new THREE.Mesh(
  new THREE.CylinderGeometry(1.65, 1.85, 0.34, 64),
  new THREE.MeshStandardMaterial({ color: 0x12161f, roughness: 0.5, metalness: 0.55 })
);
plinth.position.y = -1.44;
plinth.castShadow = true;
plinth.receiveShadow = true;
room.add(plinth);

const finishes = {
  bone: { color: 0xede7da, metalness: 0.14, roughness: 0.42, emissive: 0x000000 },
  forge: { color: 0xff6b2c, metalness: 0.22, roughness: 0.3, emissive: 0x3a1200 },
  arc: { color: 0x22e8c8, metalness: 0.3, roughness: 0.26, emissive: 0x003a33 },
  steel: { color: 0x8a93a6, metalness: 0.92, roughness: 0.18, emissive: 0x000000 },
};

const heroMat = new THREE.MeshStandardMaterial({ ...finishes.bone });
const hero = new THREE.Mesh(new THREE.TorusKnotGeometry(0.86, 0.28, 220, 32), heroMat);
hero.position.y = 0.18;
hero.castShadow = true;
room.add(hero);

/* three orbiting shards */
const shardMats = [
  new THREE.MeshStandardMaterial({ color: 0xff6b2c, metalness: 0.2, roughness: 0.35, emissive: 0x2a0c00 }),
  new THREE.MeshStandardMaterial({ color: 0xede7da, metalness: 0.2, roughness: 0.4 }),
  new THREE.MeshStandardMaterial({ color: 0x22e8c8, metalness: 0.35, roughness: 0.25, emissive: 0x003029 }),
];
const shards = [];
for (let i = 0; i < 3; i++) {
  const m = new THREE.Mesh(new THREE.IcosahedronGeometry(0.26, 0), shardMats[i]);
  m.castShadow = true;
  room.add(m);
  shards.push(m);
}

/* ---------- the portal: two piers + a lintel, framing the hero object ---------- */
const pierMat = new THREE.MeshStandardMaterial({ color: 0x11151d, metalness: 0.55, roughness: 0.52 });
const trimMat = new THREE.MeshStandardMaterial({ color: 0xff6b2c, metalness: 0.3, roughness: 0.42, emissive: 0x2c0a00 });

const PORTAL = { x: 2.85, z: -3.4, h: 3.7 };
for (const sx of [-1, 1]) {
  const pier = new THREE.Mesh(new THREE.BoxGeometry(0.46, PORTAL.h, 0.46), pierMat);
  pier.position.set(sx * PORTAL.x, -1.6 + PORTAL.h / 2, PORTAL.z);
  pier.castShadow = true;
  room.add(pier);

  // thin forged seam up each pier, the same detail language as the hero mark
  const seam = new THREE.Mesh(new THREE.BoxGeometry(0.05, PORTAL.h - 0.5, 0.05), trimMat);
  seam.position.set(sx * (PORTAL.x - 0.24), -1.6 + PORTAL.h / 2, PORTAL.z + 0.24);
  room.add(seam);
}
const lintel = new THREE.Mesh(new THREE.BoxGeometry(PORTAL.x * 2 + 0.46, 0.36, 0.5), pierMat);
lintel.position.set(0, -1.6 + PORTAL.h, PORTAL.z);
lintel.castShadow = true;
room.add(lintel);
const lintelSeam = new THREE.Mesh(new THREE.BoxGeometry(PORTAL.x * 2 - 0.2, 0.04, 0.52), trimMat);
lintelSeam.position.set(0, -1.6 + PORTAL.h - 0.16, PORTAL.z);
room.add(lintelSeam);

// a back wall keeps the room from reading as black void
const back = new THREE.Mesh(
  new THREE.PlaneGeometry(18, 9),
  new THREE.MeshStandardMaterial({ color: 0x080a10, roughness: 0.9, metalness: 0.1 })
);
back.position.set(0, 1.4, -6.4);
room.add(back);

/* ---------- lights ---------- */
scene.add(new THREE.HemisphereLight(0xfff2e4, 0x0b1018, 0.85));
const key = new THREE.DirectionalLight(0xfff6ec, 2.6);
key.position.set(-5, 8, 6);
key.castShadow = true;
key.shadow.mapSize.set(1024, 1024);
key.shadow.radius = 3;
key.shadow.bias = -0.0015;
key.shadow.camera.near = 1;
key.shadow.camera.far = 30;
scene.add(key);

const warm = new THREE.PointLight(0xff6b2c, 26, 20, 2);
warm.position.set(3.6, -0.4, 2.8);
scene.add(warm);
const cool = new THREE.PointLight(0x22e8c8, 20, 20, 2);
cool.position.set(-4.2, 0.6, -2.6);
scene.add(cool);

/* ---------- orbit controls (compact, no addons) ---------- */
const orbit = {
  theta: 0.26, phi: 1.16, radius: 9.8,
  thetaT: 0.26, phiT: 1.16, radiusT: 9.8,
  minPhi: 0.45, maxPhi: 1.52, minR: 5.2, maxR: 16,
};
let dragging = false, lastX = 0, lastY = 0, idleSpin = true;

function down(e) {
  dragging = true; idleSpin = false;
  lastX = e.clientX; lastY = e.clientY;
  canvas.setPointerCapture?.(e.pointerId);
}
function move(e) {
  if (!dragging) return;
  const dx = e.clientX - lastX, dy = e.clientY - lastY;
  lastX = e.clientX; lastY = e.clientY;
  orbit.thetaT -= dx * 0.006;
  orbit.phiT = Math.min(orbit.maxPhi, Math.max(orbit.minPhi, orbit.phiT - dy * 0.005));
}
function up() { dragging = false; }
canvas.addEventListener('pointerdown', down);
canvas.addEventListener('pointermove', move);
addEventListener('pointerup', up);
canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  idleSpin = false;
  orbit.radiusT = Math.min(orbit.maxR, Math.max(orbit.minR, orbit.radiusT + e.deltaY * 0.004));
}, { passive: false });

/* touch pinch */
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

/* ---------- UI ---------- */
const swButtons = [...document.querySelectorAll('.sw')];
const callsEl = document.getElementById('calls');
const fpsEl = document.getElementById('fps');
const trisEl = document.getElementById('tris');

swButtons.forEach((btn) => {
  btn.addEventListener('click', () => {
    swButtons.forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    const f = finishes[btn.dataset.finish];
    heroMat.color.setHex(f.color);
    heroMat.metalness = f.metalness;
    heroMat.roughness = f.roughness;
    heroMat.emissive.setHex(f.emissive);
    shardMats[2].color.setHex(f.color);
  });
});

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.fov = innerWidth < 760 ? 60 : 46;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight, false);
});

/* ---------- loop ---------- */
const t0 = performance.now();
let frames = 0, fpsAcc = 0, last = t0;

function tick(now) {
  const dt = Math.min((now - last) / 1000, 0.05);
  last = now;
  const t = (now - t0) / 1000;

  if (idleSpin && !dragging) orbit.thetaT += dt * 0.06;

  orbit.theta += (orbit.thetaT - orbit.theta) * 0.07;
  orbit.phi += (orbit.phiT - orbit.phi) * 0.07;
  orbit.radius += (orbit.radiusT - orbit.radius) * 0.07;

  const sp = Math.sin(orbit.phi);
  const shift = innerWidth > 900 ? 1.45 : 0; // clear the overlay panel
  camera.position.set(
    Math.sin(orbit.theta) * sp * orbit.radius + shift,
    Math.cos(orbit.phi) * orbit.radius * 0.86 + 0.6,
    Math.cos(orbit.theta) * sp * orbit.radius
  );
  camera.lookAt(shift * 0.86, 0.5, 0);

  hero.rotation.y = t * 0.35;
  hero.rotation.x = Math.sin(t * 0.4) * 0.16;

  shards.forEach((s, i) => {
    const a = t * (0.5 + i * 0.22) + (i * Math.PI * 2) / 3;
    const r = 2.0 + i * 0.34;
    s.position.set(Math.cos(a) * r, 0.5 + Math.sin(a * 1.6 + i) * 0.55, Math.sin(a) * r);
    s.rotation.set(a * 1.2, a, a * 0.7);
  });

  warm.intensity = 24 + Math.sin(t * 1.9) * 4;
  cool.intensity = 18 + Math.cos(t * 1.3) * 4;

  renderer.render(scene, camera);

  frames++;
  fpsAcc += dt;
  if (fpsAcc > 0.5) {
    fpsEl.textContent = Math.round(frames / fpsAcc);
    callsEl.textContent = renderer.info.render.calls;
    trisEl.textContent = renderer.info.render.triangles.toLocaleString();
    frames = 0; fpsAcc = 0;
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
