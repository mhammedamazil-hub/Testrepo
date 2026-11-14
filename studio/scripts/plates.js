// LUMENFORGE — clean art plates for the portfolio PDF & showroom
// Renders caption-free 3D frames (no baked text) so the PDF can set its own type.
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const { render } = require('./renderer');
const { ROOT } = require('./lib');

const ease = (t) => 1 - Math.pow(1 - t, 3);
const lerp = (a, b, t) => a + (b - a) * t;

const PALETTES = {
  nova: { accent: '#FF6B2C', rim: '#22E8C8', glow: '#FF6B2C', grid: '#16705F', slab: '#EDE7DA', slab2: '#22E8C8' },
  meridian: { accent: '#22E8C8', rim: '#7C5CFF', glow: '#2C7BFF', grid: '#1B5E7A', slab: '#EDE7DA', slab2: '#7C5CFF' },
  kinetic: { accent: '#7C5CFF', rim: '#FF6B2C', glow: '#FF4D6D', grid: '#5B2A6B', slab: '#EDE7DA', slab2: '#FF6B2C' },
  process: { accent: '#FF6B2C', rim: '#22E8C8', glow: '#FF6B2C', grid: '#16705F', slab: '#EDE7DA', slab2: '#FFA96B' },
};

function scene(t, variant) {
  const P = PALETTES[variant] || PALETTES.nova;
  const cams = {
    nova: [{ eye: [4.2, 2.3, 12.4], target: [0, 0.5, 0], fov: 33 }, { eye: [1.3, 1.1, 8.2], target: [0, 0.5, 0], fov: 37 }],
    meridian: [{ eye: [-4.6, 3.0, 11.6], target: [0, 0.6, 0], fov: 32 }, { eye: [-1.6, 1.5, 7.8], target: [0, 0.6, 0], fov: 37 }],
    kinetic: [{ eye: [2.0, 3.4, 12.8], target: [0, 0.4, 0], fov: 34 }, { eye: [0.8, 1.4, 7.4], target: [0, 0.4, 0], fov: 39 }],
    process: [{ eye: [5.0, 2.2, 12.0], target: [0, 0.5, 0], fov: 33 }, { eye: [1.8, 1.2, 8.4], target: [0, 0.5, 0], fov: 37 }],
  };
  const [camA, camB] = cams[variant] || cams.nova;
  const k = ease(Math.min(1, t));
  const eye = [0, 1, 2].map((i) => lerp(camA.eye[i], camB.eye[i], k));
  const theta = 0.62 + t * 0.42;

  const S = 0.34, W = 2.5, H = 8.2, F = 7.0, D = 2.5;
  const mk = (x0, x1, y0, y1, z0, z1, color, extra = {}) => {
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, cz = (z0 + z1) / 2;
    const rx = cx * Math.cos(theta) + cz * Math.sin(theta);
    const rz = -cx * Math.sin(theta) + cz * Math.cos(theta);
    return {
      geo: 'box',
      size: [(x1 - x0) * S, (y1 - y0) * S, (z1 - z0) * S],
      rot: [0, theta, 0],
      pos: [rx * S - 0.25, (cy - H * 0.42) * S - 0.55, rz * S],
      color,
      flat: true,
      ...extra,
    };
  };

  const objects = [
    mk(0, W, 0, H, 0, D, P.slab),
    mk(0, F, 0, W, 0, D, P.accent, { emissive: P.accent, emissiveAmt: 0.16 }),
    mk(0.5, W - 0.1, 0.6, H - 0.4, D, D + 0.04, '#FFF3E6', { emissive: P.accent, emissiveAmt: 0.55 }),
    { geo: 'torus', pos: [-0.25, 0.55, 0], R: 2.3, r: 0.010, rot: [1.28, 0.55 + t * 0.2, 0.1], color: '#8FF7E4', emissive: P.rim, emissiveAmt: 0.95 },
    { geo: 'torus', pos: [-0.25, 0.55, 0], R: 2.85, r: 0.005, rot: [1.02, -0.6 - t * 0.14, 0.42], color: '#FFC79B', emissive: P.accent, emissiveAmt: 0.9 },
    { geo: 'box', pos: [3.3, -1.5, -0.2], size: [0.34, 0.34, 0.34], rot: [0.4, 0.9 + t * 0.3, 0.3], color: '#DDD5C5', flat: true },
    { geo: 'sphere', pos: [-3.3, -1.4, 1.0], scale: 0.2, color: P.accent, emissive: P.accent, emissiveAmt: 0.9 },
    { geo: 'sphere', pos: [2.6, 2.3, -1.6], scale: 0.07, color: P.rim, emissive: P.rim, emissiveAmt: 1 },
  ];
  for (let i = 0; i < 26; i++) {
    const a = i * 1.7 + t * 0.3;
    objects.push({
      geo: 'sphere',
      pos: [Math.cos(a) * (3.2 + (i % 4) * 0.55), -1.3 + (i % 7) * 0.55, Math.sin(a) * 2.4 - 0.9],
      scale: 0.018 + (i % 3) * 0.008,
      color: i % 2 ? P.rim : P.accent,
      emissive: i % 2 ? P.rim : P.accent,
      emissiveAmt: 0.9,
    });
  }

  return {
    bg: { top: '#0C1018', bottom: '#020409' },
    glow: { x: 0.54, y: 0.44, r: 0.55, color: P.glow, strength: 0.30 },
    fog: { near: 10, far: 32, color: '#020409' },
    light: { dir: [-0.5, 0.85, 0.8], color: '#FFF6EC', intensity: 2.0 },
    rim: { color: P.rim, intensity: 1.0 },
    grid: { y: -2.25, extent: 15, step: 0.9, color: P.grid, near: 10, far: 28 },
    camera: { eye, target: [0, 0.55, 0], fov: lerp(camA.fov, camB.fov, k) },
    vignetteStrength: 0.62,
    objects,
  };
}

async function plate(name, variant, t, W, H, ss = 2) {
  const rgb = render(scene(t, variant), W, H, ss);
  const out = path.join(ROOT, 'portfolio', 'plates', `${name}.png`);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  await sharp(Buffer.from(rgb), { raw: { width: W, height: H, channels: 3 } }).png({ compressionLevel: 9 }).toFile(out);
  console.log('plate', name, W + 'x' + H, (fs.statSync(out).size / 1024).toFixed(0) + ' KB');
}

async function main() {
  await plate('nova', 'nova', 0.35, 1600, 1200);
  await plate('meridian', 'meridian', 0.62, 1600, 1200);
  await plate('kinetic', 'kinetic', 0.9, 1600, 1200);
  await plate('process', 'process', 0.5, 1920, 760);
  await plate('contact', 'meridian', 0.15, 1200, 1700);
  await plate('cover', 'nova', 0.05, 2000, 1400);
}

if (require.main === module) main().catch((e) => { console.error(e); process.exit(1); });
module.exports = { scene, plate };
