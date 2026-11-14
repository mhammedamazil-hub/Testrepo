// LUMENFORGE — motion ads. Frames are ray-raced in JS (scripts/renderer.js), captions are
// composited as SVG, then encoded: WebM/VP8 via webm-writer, GIF via gifenc. No ffmpeg here.
const fs = require('fs');
const gifenc = require('gifenc');
const path = require('path');
const sharp = require('sharp');
const { render } = require('./renderer');
const { ROOT } = require('./lib');

const C = { forge: '#FF6B2C', arc: '#22E8C8', bone: '#EDE7DA', ink: '#06070B', muted: '#8A93A6' };

const ease = (t) => 1 - Math.pow(1 - t, 3);
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = (e0, e1, x) => {
  const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
};

/* ---------- text overlay baked into the frame via SVG ---------- */
async function overlayText(w, h, svgBody) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">${svgBody}</svg>`;
  return sharp(Buffer.from(svg), { density: 72 }).png().toBuffer();
}

const fontCss = () => {
  const f = (p, n) =>
    `@font-face{font-family:'${n}';src:url(data:font/woff;base64,${fs.readFileSync(p).toString('base64')}) format('woff');}`;
  const F = '/tmp/build/node_modules/@fontsource';
  return `<style>${f(`${F}/space-grotesk/files/space-grotesk-latin-700-normal.woff`, 'g7')}${f(
    `${F}/jetbrains-mono/files/jetbrains-mono-latin-400-normal.woff`,
    'm4'
  )}</style>`;
};

/* ---------- scene per frame ---------- */
function frameScene(t, duration, variant = 'wide') {
  const p = t / duration;
  const camA = { eye: [3.6, 2.2, 12.6], target: [0, 0.55, 0], fov: 34 };
  const camB = { eye: [1.2, 1.0, 7.4], target: [0, 0.55, 0], fov: 38 };
  const k = ease(Math.min(1, p * 1.15));
  const eye = [lerp(camA.eye[0], camB.eye[0], k), lerp(camA.eye[1], camB.eye[1], k), lerp(camA.eye[2], camB.eye[2], k)];
  const theta = t * 0.42;

  const S = 0.34, W = 2.5, H = 8.2, F = 7.0, D = 2.5;
  const mk = (x0, x1, y0, y1, z0, z1, color, extra = {}) => {
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, cz = (z0 + z1) / 2;
    const th = 0.62;
    const rx = cx * Math.cos(th) + cz * Math.sin(th);
    const rz = -cx * Math.sin(th) + cz * Math.cos(th);
    return {
      geo: 'box',
      size: [(x1 - x0) * S, (y1 - y0) * S, (z1 - z0) * S],
      rot: [0, th, 0],
      pos: [rx * S - 0.25, (cy - H * 0.42) * S - 0.55, rz * S],
      color,
      flat: true,
      ...extra,
    };
  };

  const objects = [
    mk(0, W, 0, H, 0, D, '#EDE7DA'),
    mk(0, F, 0, W, 0, D, '#FF6B2C', { emissive: '#FF6B2C', emissiveAmt: 0.18 }),
    mk(0.5, W - 0.1, 0.6, H - 0.4, D, D + 0.04, '#FFF3E6', { emissive: '#FF8A4C', emissiveAmt: 0.5 + 0.35 * Math.sin(t * 3) }),
    mk(0.5, F - 0.2, W - 0.05, W, D, D + 0.04, '#FFD9B8', { emissive: C.forge, emissiveAmt: 0.6 }),
    { geo: 'torus', pos: [-0.25, 0.55, 0], R: 2.2 + Math.sin(t * 0.8) * 0.1, r: 0.011, rot: [1.3 + Math.sin(t * 0.5) * 0.1, 0.55 + t * 0.22, 0.1], color: '#8FF7E4', emissive: C.arc, emissiveAmt: 0.95 },
    { geo: 'torus', pos: [-0.25, 0.55, 0], R: 2.75, r: 0.005, rot: [1.05, -0.6 - t * 0.16, 0.42], color: '#FFC79B', emissive: C.forge, emissiveAmt: 0.9 },
    { geo: 'sphere', pos: [-3.2, -1.4, 1.2], scale: 0.22, color: '#FF8A4C', emissive: C.forge, emissiveAmt: 0.9 },
    { geo: 'box', pos: [3.1, -1.55, -0.3], size: [0.32, 0.32, 0.32], rot: [0.4, 0.9 + t * 0.3, 0.3], color: '#DDD5C5', flat: true },
    { geo: 'sphere', pos: [1.9, 2.1, -1.4], scale: 0.06, color: C.arc, emissive: C.arc, emissiveAmt: 1 },
    { geo: 'sphere', pos: [-2.1, 2.4, -1.8], scale: 0.04, color: C.forge, emissive: C.forge, emissiveAmt: 1 },
  ];
  for (let i = 0; i < 20; i++) {
    const a = i * 1.7 + t * 0.3;
    objects.push({
      geo: 'sphere',
      pos: [Math.cos(a) * (3.4 + (i % 4) * 0.5), -1.2 + (i % 6) * 0.6, Math.sin(a) * 2.2 - 0.8],
      scale: 0.02 + (i % 3) * 0.008,
      color: i % 2 ? C.arc : C.forge,
      emissive: i % 2 ? C.arc : C.forge,
      emissiveAmt: 0.9,
    });
  }

  return {
    bg: { top: '#0C1018', bottom: '#020409' },
    glow: { x: 0.55, y: 0.45, r: 0.55, color: C.forge, strength: 0.30 + 0.06 * Math.sin(t * 1.4) },
    fog: { near: 10, far: 32, color: '#020409' },
    light: { dir: [-0.5, 0.85, 0.8], color: '#FFF6EC', intensity: 2.0 },
    rim: { color: C.arc, intensity: 1.0 },
    grid: { y: -2.25, extent: 15, step: 0.9, color: '#16705F', near: 10, far: 28 },
    camera: { eye, target: [0, 0.55 + p * 0.15, 0], fov: lerp(camA.fov, camB.fov, k) },
    vignetteStrength: 0.6,
    objects,
  };
}

/* ---------- caption track ---------- */
function caption(t, duration, w, h) {
  const p = t / duration;
  const lines = [
    { at: 0.02, text: 'THE WEB WAS FLAT.', second: 'WE FORGED IT SOLID.' },
    { at: 0.34, text: '3D COMMERCE.', second: 'SHIPPED IN REACT.' },
    { at: 0.66, text: 'WALK THROUGH IT.', second: 'UNDER 2 MB · 60 FPS' },
  ];
  const idx = p < 0.34 ? 0 : p < 0.66 ? 1 : 2;
  const cur = lines[idx];
  const last = idx === 2;
  const localT = last ? (p - cur.at) / 0.34 : (p - cur.at) / 0.32;
  // the final card holds to the last frame so the ad never ends on a caption-less scene
  const alpha = Math.min(1, smooth(0.0, 0.14, localT)) * (last ? 1 - smooth(0.40, 0.58, localT) : 1 - smooth(0.88, 1, localT));
  const lockAlpha = last ? smooth(0.52, 0.74, localT) : 0;
  const rise = (1 - ease(Math.min(1, localT * 2.4))) * 26;
  const size = Math.round(w * 0.046);
  const x = w * 0.065;
  const baseY = h * 0.775;
  return `${fontCss()}
  <defs>
    <linearGradient id="scrim" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#04050A" stop-opacity="0"/>
      <stop offset="1" stop-color="#04050A" stop-opacity=".88"/>
    </linearGradient>
  </defs>
  <rect x="0" y="${h * 0.56}" width="${w}" height="${h * 0.44}" fill="url(#scrim)"/>
  <g opacity="${alpha.toFixed(3)}" transform="translate(0,${rise.toFixed(1)})">
    <text x="${x}" y="${baseY}" font-family="g7" font-size="${size}" fill="${C.bone}" letter-spacing="${size * 0.02}">${cur.text}</text>
    <text x="${x}" y="${baseY + size * 1.12}" font-family="g7" font-size="${size}" fill="${C.forge}" letter-spacing="${size * 0.02}">${cur.second}</text>
  </g>
  <g opacity="${alpha.toFixed(3)}">
    <rect x="${x}" y="${h * 0.9}" width="${w * 0.11}" height="${Math.max(3, w * 0.004)}" fill="${C.forge}"/>
    <text x="${x}" y="${h * 0.945}" font-family="m4" font-size="${Math.round(w * 0.017)}" fill="${C.arc}" letter-spacing="${w * 0.0035}">LUMENFORGE.STUDIO</text>
  </g>
  <g opacity="${lockAlpha.toFixed(3)}">
    
    <text x="${w * 0.5}" y="${h * 0.455}" text-anchor="middle" font-family="g7" font-size="${Math.round(w * 0.088)}" fill="${C.bone}" letter-spacing="${w * 0.004}">LUMEN<tspan fill="${C.forge}">FORGE</tspan></text>
    <text x="${w * 0.5}" y="${h * 0.512}" text-anchor="middle" font-family="m4" font-size="${Math.round(w * 0.019)}" fill="${C.arc}" letter-spacing="${w * 0.0055}">BOOK A FORGE SLOT</text>
  </g>`;
}

/* ---------- encode ---------- */
async function renderFrame(t, duration, W, H, ss = 2) {
  const rgb = render(frameScene(t, duration), W, H, ss);
  const base = sharp(Buffer.from(rgb), { raw: { width: W, height: H, channels: 3 } }).png();
  const cap = await overlayText(W, H, caption(t, duration, W, H));
  return base.composite([{ input: cap }]).png().toBuffer();
}

async function makeGif({ out, W = 720, H = 720, frames = 40, duration = 4, ss = 2 }) {
  const enc = gifenc.GIFEncoder();
  const delay = Math.round((duration * 1000) / frames);
  for (let i = 0; i < frames; i++) {
    const t = (i / frames) * duration;
    const png = await renderFrame(t, duration, W, H, ss);
    const { data } = await sharp(png).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
    const rgba = new Uint8ClampedArray(data);
    const palette = gifenc.quantize(rgba, 200);
    const index = gifenc.applyPalette(rgba, palette);
    enc.writeFrame(index, W, H, { palette, delay, repeat: 0 });
    if (i % 8 === 0) process.stdout.write(`  gif frame ${i}/${frames}\r`);
  }
  enc.finish();
  const buf = Buffer.from(enc.bytes());
  fs.mkdirSync(path.dirname(path.join(ROOT, out)), { recursive: true });
  fs.writeFileSync(path.join(ROOT, out), buf);
  console.log(`\n${out}  ${(buf.length / 1024).toFixed(0)} KB`);
}

async function makeWebMFile({ out, W = 720, H = 720, fps = 20, duration = 6, ss = 2 }) {
  const WebMWriter = require('webm-writer');
  // webm-writer is browser-only: it wants a canvas and window.atob. Shim both — sharp
  // already encodes WebP, so we hand the writer a fake canvas that returns a data URL.
  if (!global.window) global.window = { atob: (b64) => Buffer.from(b64, 'base64').toString('latin1') };
  const tmp = path.join('/tmp', `webm-${Date.now()}.webm`);
  const writer = new WebMWriter({ fd: fs.openSync(tmp, 'w'), frameRate: fps, quality: 0.9, videoCodec: 'vp8' });
  const canvas = (png) => ({
    width: W,
    height: H,
    toDataURL: async () => 'data:image/webp;base64,' + (await sharp(png).webp({ quality: 90 }).toBuffer()).toString('base64'),
  });
  const total = Math.round(duration * fps);
  for (let i = 0; i < total; i++) {
    const t = (i / total) * duration;
    const png = await renderFrame(t, duration, W, H, ss);
    const c = canvas(png);
    c.toDataURL = () => c._url; // writer calls toDataURL synchronously
    c._url = await canvas(png).toDataURL();
    writer.addFrame(c);
    if (i % 5 === 0) process.stdout.write(`\r  webm frame ${i}/${total}`);
  }
  await writer.complete();
  fs.mkdirSync(path.dirname(path.join(ROOT, out)), { recursive: true });
  fs.copyFileSync(tmp, path.join(ROOT, out));
  const kb = (fs.statSync(path.join(ROOT, out)).size / 1024).toFixed(0);
  console.log(`\n${out}  ${kb} KB`);
  fs.unlinkSync(tmp);
}

async function main() {
  const mode = process.argv[2] || 'all';
  if (mode === 'all' || mode === 'gif') {
    await makeGif({ out: 'ads/video/lumenforge-loop-720.gif', W: 720, H: 720, frames: 44, duration: 5, ss: 2 });
  }
  if (mode === 'all' || mode === 'video') {
    await makeWebMFile({ out: 'ads/video/lumenforge-ad-720.webm', W: 720, H: 720, fps: 20, duration: 6, ss: 2 });
  }
  if (mode === 'poster') {
    fs.mkdirSync(path.join(ROOT, 'ads/video'), { recursive: true });
    const png = await renderFrame(2.52, 6, 1280, 1280, 2);
    fs.writeFileSync(path.join(ROOT, 'ads/video/lumenforge-video-poster.png'), png);
    console.log('poster written');
  }
}

if (require.main === module) main().catch((e) => { console.error(e); process.exit(1); });
module.exports = { renderFrame, frameScene };
