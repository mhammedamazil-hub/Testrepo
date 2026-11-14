// LUMENFORGE — hero scene (Three.js, vendored, no CDN)
import * as THREE from './vendor/three.module.min.js';

const canvas = document.getElementById('scene');
const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

if (canvas && !reduce) boot();

function boot() {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.9));
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x06070b);
  scene.fog = new THREE.Fog(0x06070b, 11, 30);

  const camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.1, 90);
  camera.position.set(3.4, 2.2, 9.4);

  /* ---- the mark: two forged beams, rebuilt in 3D ---- */
  const UNIT = 0.34;
  const W = 2.5, H = 8.2, F = 7.0, D = 2.5;

  const boneMat = new THREE.MeshStandardMaterial({ color: 0xede7da, roughness: 0.42, metalness: 0.12 });
  const forgeMat = new THREE.MeshStandardMaterial({
    color: 0xff6b2c, roughness: 0.34, metalness: 0.18,
    emissive: 0xff3d00, emissiveIntensity: 0.22,
  });
  const darkMat = new THREE.MeshStandardMaterial({ color: 0x1b212b, roughness: 0.7, metalness: 0.35 });

  // stage holds the mark + rings + chips so the whole composition can be
  // pushed into the right half of the viewport, clear of the hero headline
  const stage = new THREE.Group();
  scene.add(stage);

  const group = new THREE.Group();
  stage.add(group);

  const addBox = (w, h, d, x, y, z, mat) => {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(w * UNIT, h * UNIT, d * UNIT), mat);
    mesh.position.set(x * UNIT, y * UNIT, z * UNIT);
    group.add(mesh);
    return mesh;
  };

  // foot (grounded) and upright beam, sharing the heel
  addBox(F, W, D, F / 2, W / 2, D / 2, forgeMat);
  const upright = addBox(W, H - W, D, W / 2, W + (H - W) / 2, D / 2, boneMat);
  // forged seam highlights
  addBox(W * 0.62, 0.22, 0.06, W / 2, W + (H - W) * 0.5, D + 0.02, new THREE.MeshBasicMaterial({ color: 0xffd9b8 }));
  addBox(0.22, W * 0.62, 0.06, W / 2, W * 0.5, D + 0.02, new THREE.MeshBasicMaterial({ color: 0xffb07a }));

  group.position.set(-1.15, -1.55, 0);
  group.rotation.y = 0.62;

  /* ---- orbit rings ---- */
  const ringA = new THREE.Mesh(
    new THREE.TorusGeometry(2.45, 0.012, 8, 220),
    new THREE.MeshBasicMaterial({ color: 0x22e8c8 })
  );
  ringA.rotation.set(1.32, 0.5, 0.12);
  ringA.position.set(-0.4, 0.15, 0);
  stage.add(ringA);

  const ringB = new THREE.Mesh(
    new THREE.TorusGeometry(3.05, 0.006, 8, 220),
    new THREE.MeshBasicMaterial({ color: 0xffb07a, transparent: true, opacity: 0.85 })
  );
  ringB.rotation.set(1.05, -0.6, 0.4);
  ringB.position.set(-0.4, 0.15, 0);
  stage.add(ringB);

  /* ---- floating chips ---- */
  const chips = new THREE.Group();
  stage.add(chips);
  const chipGeo = new THREE.BoxGeometry(0.34, 0.34, 0.34);
  const chipMats = [boneMat, darkMat, forgeMat];
  const chipData = [];
  for (let i = 0; i < 14; i++) {
    const m = new THREE.Mesh(chipGeo, chipMats[i % 3]);
    const a = (i / 14) * Math.PI * 2;
    m.position.set(Math.cos(a) * (2.2 + (i % 4) * 0.38) + 0.6, -1.1 + (i % 5) * 0.6, Math.sin(a) * 2.0 - 1.4);
    m.rotation.set(i, i * 1.7, i * 0.4);
    m.userData = { spin: 0.25 + (i % 5) * 0.12, baseY: m.position.y, phase: i };
    chips.add(m);
    chipData.push(m);
  }

  /* ---- dust ---- */
  const dustCount = 220;
  const dustPos = new Float32Array(dustCount * 3);
  for (let i = 0; i < dustCount; i++) {
    dustPos[i * 3] = (Math.random() - 0.5) * 20;
    dustPos[i * 3 + 1] = (Math.random() - 0.3) * 12;
    dustPos[i * 3 + 2] = (Math.random() - 0.9) * 12;
  }
  const dustGeo = new THREE.BufferGeometry();
  dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
  const dust = new THREE.Points(dustGeo, new THREE.PointsMaterial({
    color: 0x9fd8cd, size: 0.045, transparent: true, opacity: 0.55, sizeAttenuation: true,
  }));
  scene.add(dust);

  /* ---- light ---- */
  scene.add(new THREE.HemisphereLight(0xfff2e4, 0x0a0e14, 0.55));
  const key = new THREE.DirectionalLight(0xfff6ec, 2.4);
  key.position.set(-4, 6, 5);
  scene.add(key);
  const rimTeal = new THREE.PointLight(0x22e8c8, 14, 16, 2);
  rimTeal.position.set(4.2, -1.4, -3.2);
  scene.add(rimTeal);
  const ember = new THREE.PointLight(0xff6b2c, 18, 14, 2);
  ember.position.set(1.6, -1.9, 2.2);
  scene.add(ember);

  /* ---- floor grid ---- */
  const grid = new THREE.GridHelper(36, 44, 0x1f6f61, 0x123a35);
  grid.position.y = -2.35;
  grid.material.transparent = true;
  grid.material.opacity = 0.5;
  scene.add(grid);

  /* ---- interaction state ---- */
  const pointer = { x: 0, y: 0 };
  const target = { x: 0, y: 0 };
  let scrollN = 0;

  addEventListener('pointermove', (e) => {
    pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
    pointer.y = (e.clientY / window.innerHeight) * 2 - 1;
  }, { passive: true });

  addEventListener('scroll', () => {
    const max = Math.max(1, document.body.scrollHeight - window.innerHeight);
    scrollN = Math.min(1, window.scrollY / max);
  }, { passive: true });

  function resize() {
    const w = window.innerWidth, h = window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.fov = w < 760 ? 56 : 42;
    // desktop: art lives in the right half, type in the left. mobile: centred, lower.
    stage.position.x = w > 900 ? 3.5 : 0;
    stage.position.y = w > 900 ? -0.35 : -0.5;
    stage.scale.setScalar(w > 900 ? 0.9 : 0.8);
    camera.updateProjectionMatrix();
  }
  addEventListener('resize', resize);
  resize();

  const clock = new THREE.Clock();
  let frames = 0;

  function tick() {
    const t = clock.getElapsedTime();
    const dt = Math.min(clock.getDelta(), 0.05);

    target.x += (pointer.x * 0.22 - target.x) * 0.045;
    target.y += (pointer.y * 0.12 - target.y) * 0.045;

    // parallax camera
    camera.position.x = 3.4 + target.x * 1.8;
    camera.position.y = 2.2 - target.y * 1.1 + scrollN * 1.4;
    camera.position.z = 9.4 - scrollN * 2.4;
    camera.lookAt(stage.position.x * 0.55 - 0.4, 0.1 + scrollN * 0.8, 0);

    group.rotation.y = 0.62 + t * 0.06 + target.x * 0.5;
    group.position.y = -1.55 + Math.sin(t * 0.7) * 0.06 + scrollN * 0.5;

    ringA.rotation.z = 0.12 + t * 0.14;
    ringA.rotation.x = 1.32 + Math.sin(t * 0.4) * 0.06;
    ringB.rotation.z = 0.4 - t * 0.1;
    ringB.rotation.y = -0.6 + Math.cos(t * 0.33) * 0.08;

    ember.intensity = 15 + Math.sin(t * 2.1) * 3.5;
    rimTeal.intensity = 12 + Math.cos(t * 1.3) * 3;

    for (const c of chipData) {
      c.rotation.x += dt * c.userData.spin * 0.6;
      c.rotation.y += dt * c.userData.spin;
      c.position.y = c.userData.baseY + Math.sin(t * 0.8 + c.userData.phase) * 0.12;
    }

    dust.rotation.y = t * 0.012;
    dust.position.y = Math.sin(t * 0.2) * 0.2;

    renderer.render(scene, camera);
    frames++;
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);

  // expose a tiny hook for the showroom/self-test
  window.__lumenforge = { renderer, scene, camera, frames: () => frames };
}

/* ---- reel: only decode the ad while it is on screen, respect reduced motion ---- */
{
  const v = document.getElementById('reel');
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (v && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting && !reduce.matches) v.play().catch(() => {});
        else v.pause();
      },
      { threshold: 0.25 }
    );
    io.observe(v);
  }
}
