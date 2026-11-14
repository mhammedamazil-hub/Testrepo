// LUMENFORGE — ad/posters/portfolio key art via the software 3D renderer
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const { render } = require('./renderer');
const { ROOT, C, FONT_FILES, ensureDir, write } = require('./lib');
const { mark } = require('./brand');

const css = () => {
  const f = (p, n) =>
    `@font-face{font-family:'${n}';src:url(data:font/woff;base64,${fs.readFileSync(p).toString('base64')}) format('woff');}`;
  return `<style>${f(FONT_FILES.grotesk400, 'g4')}${f(FONT_FILES.grotesk, 'g5')}${f(FONT_FILES.grotesk700, 'g7')}${f(FONT_FILES.inter, 'i4')}${f(FONT_FILES.inter700, 'i7')}${f(FONT_FILES.mono, 'm4')}</style>`;
};

/* ---------- reusable 3D scenes ---------- */
const S = 0.32, BW = 2.5, BH = 8.2, BF = 7.0, BD = 2.5, TH = 0.62;
const rotXZ = (x, z, th) => [x * Math.cos(th) + z * Math.sin(th), -x * Math.sin(th) + z * Math.cos(th)];

function forgeMark({ scale = 1, th = TH, ox = 0, oy = 0, oz = 0, color = '#EDE7DA', accent = C.forge, metal = false, unit = S } = {}) {
  const mk = (x0, x1, y0, y1, z0, z1, c, extra = {}) => {
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, cz = (z0 + z1) / 2;
    const [rx, rz] = rotXZ(cx, cz, th);
    return {
      geo: 'box',
      size: [(x1 - x0) * unit * scale, (y1 - y0) * unit * scale, (z1 - z0) * unit * scale],
      rot: [0, th, 0],
      pos: [rx * unit * scale + ox, (cy - BH * 0.42) * unit * scale + oy, rz * unit * scale + oz],
      color: c,
      flat: true,
      metal,
      ...extra,
    };
  };
  return [
    mk(0, BW, 0, BH, 0, BD, color),
    mk(0, BF, 0, BW, 0, BD, accent),
    mk(0.5, BW - 0.1, BH * 0.06, BH - 0.25, BD, BD + 0.04, '#FFF3E6', { emissive: '#FFB07A', emissiveAmt: 0.35 }),
    mk(0.5, BF - 0.1, BW - 0.06, BW - 0.02, BD, BD + 0.04, '#FFD9B8', { emissive: C.forge, emissiveAmt: 0.55 }),
  ];
}

function orbits({ cx = 0, cy = 0, r1 = 2.75, r2 = 3.25, t1 = '#8FF7E4', t2 = '#FFC79B', e1 = C.arc, e2 = C.forge, amt = 0.95 } = {}) {
  return [
    { geo: 'torus', pos: [cx, cy, 0], R: r1, r: 0.009, rot: [1.3, 0.6, 0.08], color: t1, emissive: e1, emissiveAmt: amt },
    { geo: 'torus', pos: [cx, cy, 0], R: r2, r: 0.0045, rot: [1.02, -0.62, 0.4], color: t2, emissive: e2, emissiveAmt: amt },
  ];
}

const dust = (seed = 1) => {
  let s = seed * 9301 + 49297;
  const rnd = () => ((s = (s * 9301 + 49297) % 233280) / 233280);
  const out = [];
  for (let i = 0; i < 26; i++) {
    const warm = rnd() > 0.5;
    out.push({
      geo: 'sphere',
      pos: [(rnd() - 0.5) * 9, (rnd() - 0.35) * 6, (rnd() - 0.9) * 5],
      scale: 0.014 + rnd() * 0.03,
      color: warm ? C.forge : C.arc,
      emissive: warm ? C.forge : C.arc,
      emissiveAmt: 0.75 + rnd() * 0.25,
    });
  }
  return out;
};

function baseScene(over) {
  return {
    bg: { top: '#0C1018', bottom: '#020409' },
    glow: { x: 0.5, y: 0.5, r: 0.55, color: C.forge, strength: 0.26 },
    fog: { near: 10, far: 34, color: '#020409' },
    light: { dir: [-0.5, 0.9, 0.75], color: '#FFF6EC', intensity: 2.0 },
    rim: { color: C.arc, intensity: 1.0 },
    grid: { y: -2.25, extent: 15, step: 0.9, color: '#16705F', near: 10, far: 30 },
    camera: { eye: [3.4, 2.5, 10.6], target: [-0.25, 0.05, 0], fov: 31 },
    vignetteStrength: 0.6,
    objects: [...forgeMark(), ...orbits({ cx: -0.2 }), ...dust(3)],
    ...over,
  };
}

const TW = { forge: C.forge, arc: C.arc, bone: C.bone, mut: '#98A2B3' };

/** Compose render + typographic overlay into one PNG via sharp. */
async function poster({ out, W = 1600, H = 2000, scene, overlay, bgColor = '#05060A' }) {
  scene = scene || baseScene({ camera: { eye: [3.2, 2.6, 12.0], target: [-0.35, 0.1, 0], fov: 30 } });
  const buf = render(scene, W, H, 2);
  const svgOK = true;
  const base = await sharp(buf, { raw: { width: W, height: H, channels: 3 } }).png().toBuffer();
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">${css()}${overlay}</svg>`;
  const over = await sharp(Buffer.from(svg), { density: 72 }).png().toBuffer();
  const p = path.join(ROOT, out);
  ensureDir(path.dirname(p));
  await sharp(base).composite([{ input: over }]).png({ compressionLevel: 9 }).toFile(p);
  return p;
}

/* ---------- brand micro components in SVG ---------- */
const chip = (x, y, text, color = TW.arc, size = 22, pad = 18) =>
  `<g transform="translate(${x},${y})"><rect x="0" y="0" rx="${size * 0.9}" width="${text.length * size * 0.62 + pad * 2}" height="${size * 1.9}" fill="none" stroke="${color}" stroke-opacity=".55"/><text x="${pad}" y="${size * 1.3}" font-family="m4" font-size="${size}" letter-spacing="${size * 0.18}" fill="${color}">${text}</text></g>`;

// wrap + lay out body copy so nothing ever runs past the canvas edge
const wrap = (text, maxChars) => {
  const out = [];
  let line = '';
  for (const w of text.split(' ')) {
    if (!line) line = w;
    else if ((line + ' ' + w).length <= maxChars) line += ' ' + w;
    else { out.push(line); line = w; }
  }
  if (line) out.push(line);
  return out;
};

const block = (x, y, text, { size = 36, maxChars = 46, fill = TW.mut, font = 'i4', lh = 1.35 } = {}) =>
  wrap(text, maxChars)
    .map((l, i) => `<text x="${x}" y="${Math.round(y + i * size * lh)}" font-family="${font}" font-size="${size}" fill="${fill}">${l}</text>`)
    .join('');

// bottom-up scrim so type stays legible over the render
const scrim = (W, H, from = 0.52, op = 0.9, id = 'sc') =>
  `<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">
     <stop offset="0" stop-color="#04050A" stop-opacity="0"/>
     <stop offset="0.55" stop-color="#04050A" stop-opacity="${(op * 0.55).toFixed(2)}"/>
     <stop offset="1" stop-color="#04050A" stop-opacity="${op}"/>
   </linearGradient></defs>
   <rect x="0" y="${Math.round(H * from)}" width="${W}" height="${Math.round(H * (1 - from))}" fill="url(#${id})"/>`;

const logoTag = (x, y, size = 40, light = true) =>
  `<g transform="translate(${x},${y}) scale(${size / 512})">${mark({ size: 512, glow: true }).replace(/^<svg[^>]*>/, '').replace(/<\/svg>$/, '')}</g>`;

/* =================== artifacts =================== */
async function main() {
  const out = [];

  // ---------- A. hero key art (used by the site + portfolio) ----------
  out.push(
    await poster({
      out: 'ads/keyart/hero-1600x2000.png',
      W: 1600,
      H: 2000,
      scene: baseScene({ camera: { eye: [3.6, 2.6, 11.2], target: [-0.3, 0.1, 0], fov: 30 } }),
      overlay: `
        ${logoTag(96, 960, 300)}
        <text x="96" y="1330" font-family="g7" font-size="150" letter-spacing="6" fill="${TW.bone}">LUMEN<tspan fill="${TW.forge}">FORGE</tspan></text>
        <text x="100" y="1410" font-family="m4" font-size="34" letter-spacing="14" fill="${TW.arc}">WEBSITES YOU CAN WALK THROUGH</text>
        <line x1="96" y1="1470" x2="1504" y2="1470" stroke="${TW.bone}" stroke-opacity=".14"/>
        ${block(96, 1548, 'Blender bpy pipelines · Three.js · React — launch-ready 3D commerce, real-estate and product sites.', { size: 38, maxChars: 46, lh: 1.4 })}
        ${chip(96, 1680, '3D COMMERCE')}${chip(430, 1680, 'REAL ESTATE')}${chip(760, 1680, 'WEBGL PRODUCT')}
        <text x="96" y="1900" font-family="m4" font-size="26" letter-spacing="6" fill="${TW.mut}">60FPS · MOBILE FIRST · SEO SAFE · LIGHTHOUSE 95+</text>`
    })
  );

  // ---------- B. ad set: square + story + landscape ----------
  const adCopy = {
    square: {
      W: 1080,
      H: 1080,
      head: ['YOUR SITE.', 'NOT A SLIDE.'],
      sub: 'A 3D world your customers can explore — built in Blender, shipped in React.',
      cta: 'BOOK A FORGE SLOT',
    },
    story: {
      W: 1080,
      H: 1920,
      head: ['WALK', 'THROUGH', 'YOUR SITE.'],
      sub: 'Interactive 3D websites. No plugins. Loads in under 2s.',
      cta: 'SWIPE UP',
    },
    wide: {
      W: 1920,
      H: 1080,
      head: ['TAKE THE WALKTHROUGH'],
      sub: 'Blender-authored. Three.js-powered. React-native performance.',
      cta: 'LUMENFORGE.STUDIO',
    },
  };

  for (const [k, v] of Object.entries(adCopy)) {
    const scene = baseScene({
      camera: { eye: [3.2, 2.2, 11.4], target: [-0.35, 0.1, 0], fov: 30 },
      glow: { x: 0.62, y: 0.42, r: 0.6, color: C.forge, strength: 0.34 },
    });
    // bottom-anchored stack: CTA fixed, then body copy, then the headline above it
    const headSize = k === 'story' ? 112 : k === 'wide' ? 104 : 108;
    const lead = Math.round(headSize * 1.16);
    const subChars = k === 'wide' ? 46 : k === 'story' ? 32 : 40;
    const subSize = k === 'wide' ? 38 : 36;
    const subLines = wrap(v.sub, subChars).length;
    const subY = v.H - 186 - (subLines - 1) * Math.round(subSize * 1.34);
    const headBottom = subY - 74;
    const headTop = headBottom - (v.head.length - 1) * lead;
    const big = v.head
      .map((t, i) => `<text x="80" y="${headTop + i * lead}" font-family="g7" font-size="${headSize}" letter-spacing="2" fill="${i === v.head.length - 1 && k !== 'wide' ? TW.forge : TW.bone}">${t}</text>`)
      .join('');
    out.push(
      await poster({
        out: `ads/set/lumenforge-${k}-${v.W}x${v.H}.png`,
        W: v.W,
        H: v.H,
        scene,
        overlay: `
          ${scrim(v.W, v.H, k === 'wide' ? 0.34 : 0.46, 0.94)}
          ${logoTag(72, 64, 120)}
          <text x="208" y="146" font-family="g7" font-size="52" letter-spacing="4" fill="${TW.bone}">LUMEN<tspan fill="${TW.forge}">FORGE</tspan></text>
          ${big}
          ${block(84, subY, v.sub, { size: subSize, maxChars: subChars, lh: 1.34 })}
          <g transform="translate(${v.W - 80 - 470},${v.H - 110})">
            <rect rx="46" width="470" height="76" fill="${TW.forge}"/>
            <text x="235" y="50" text-anchor="middle" font-family="g7" font-size="28" letter-spacing="4" fill="#0A0503">${v.cta}</text>
          </g>`
      })
    );
  }

  // ---------- C. posters ----------
  const posters = [
    {
      out: 'ads/posters/poster-manifesto-1200x1600.png',
      W: 1200,
      H: 1600,
      overlay: `
        ${scrim(1200, 1600, 0.0, 0.62, 'mf')}
        <rect x="0" y="0" width="1200" height="1600" fill="#04050A" opacity=".22"/>
        ${logoTag(72, 72, 132)}
        <text x="72" y="330" font-family="m4" font-size="26" letter-spacing="12" fill="${TW.arc}">MANIFESTO / 001</text>
        <text x="72" y="470" font-family="g7" font-size="100" fill="${TW.bone}">THE WEB</text>
        <text x="72" y="576" font-family="g7" font-size="100" fill="${TW.bone}">WAS FLAT.</text>
        <text x="72" y="682" font-family="g7" font-size="100" fill="${TW.forge}">WE FORGED</text>
        <text x="72" y="788" font-family="g7" font-size="100" fill="${TW.forge}">IT SOLID.</text>
        <line x1="72" y1="860" x2="1128" y2="860" stroke="${TW.bone}" stroke-opacity=".16"/>
        ${block(72, 940, 'Every LUMENFORGE build starts as geometry in Blender, gets its physics in Three.js, and ships as a React app your customers can walk through — on a phone, on 4G.', { size: 32, maxChars: 48, lh: 1.45 })}
        <text x="72" y="1500" font-family="m4" font-size="24" letter-spacing="8" fill="${TW.mut}">LUMENFORGE.STUDIO · INTERACTIVE 3D STUDIO</text>`,
    },
    {
      out: 'ads/posters/poster-towers-1200x1600.png',
      W: 1200,
      H: 1600,
      scene: baseScene({
        camera: { eye: [4.6, 3.2, 12.4], target: [-0.4, 0.3, 0], fov: 32 },
        objects: [
          ...forgeMark({ oy: 0.4 }),
          ...orbits({ cx: -0.2, r1: 3.2, r2: 3.8 }),
          { geo: 'box', pos: [-4.2, -1.2, 1.4], size: [0.9, 2.6, 0.9], rot: [0, 0.6, 0], color: '#151A22', flat: true, metal: true },
          { geo: 'box', pos: [-3.0, -1.5, 0.4], size: [0.7, 2.0, 0.7], rot: [0, 0.3, 0], color: '#1B212B', flat: true, metal: true },
          { geo: 'box', pos: [3.6, -1.35, -0.8], size: [0.8, 2.3, 0.8], rot: [0, 0.9, 0], color: '#E6DFD1', flat: true },
          ...dust(7),
        ],
        glow: { x: 0.4, y: 0.55, r: 0.62, color: C.forge, strength: 0.3 },
      }),
      overlay: `
        ${scrim(1200, 1600, 0.60, 0.92, 'tw')}
        <text x="72" y="180" font-family="m4" font-size="26" letter-spacing="12" fill="${TW.arc}">CASE / ATELIER NOVA</text>
        <text x="72" y="1240" font-family="g7" font-size="104" fill="${TW.bone}">A FLAGSHIP</text>
        <text x="72" y="1350" font-family="g7" font-size="104" fill="${TW.forge}">YOU CAN ENTER.</text>
        ${block(72, 1430, '3D flagship store · 1.9 MB budget · 58 FPS on a Pixel 6a', { size: 30, maxChars: 54, lh: 1.3 })}`,
    },
    {
      out: 'ads/posters/poster-hiring-1200x1600.png',
      W: 1200,
      H: 1600,
      scene: baseScene({
        camera: { eye: [2.6, 3.4, 10.2], target: [-0.2, 0.2, 0], fov: 34 },
        glow: { x: 0.5, y: 0.35, r: 0.7, color: C.arc, strength: 0.18 },
      }),
      overlay: `
        ${scrim(1200, 1600, 0.40, 0.9, 'hr')}
        <rect x="0" y="0" width="1200" height="1600" fill="#04050A" opacity=".18"/>
        ${logoTag(72, 72, 132)}
        <text x="72" y="360" font-family="m4" font-size="26" letter-spacing="12" fill="${TW.arc}">NOW FORGING</text>
        <text x="72" y="510" font-family="g7" font-size="116" fill="${TW.bone}">WE NEED</text>
        <text x="72" y="632" font-family="g7" font-size="116" fill="${TW.bone}">A BLENDER</text>
        <text x="72" y="754" font-family="g7" font-size="116" fill="${TW.forge}">WIZARD.</text>
        ${block(72, 872, 'bpy automation · glTF budgets · shader restraint. Remote. Paid per build. Portfolio over CV.', { size: 32, maxChars: 46, lh: 1.45 })}
        <text x="72" y="1480" font-family="m4" font-size="26" letter-spacing="6" fill="${TW.arc}">JOBS@LUMENFORGE.STUDIO</text>`,
    },
  ];
  for (const p of posters) out.push(await poster(p));

  // ---------- D. portfolio plates (3 case studies) ----------
  const cases = [
    {
      slug: 'atelier-nova',
      title: 'ATELIER NOVA',
      kicker: 'CASE 01 · 3D COMMERCE',
      meta: ['Three.js + R3F', 'Blender bpy asset pipeline', '1.9 MB first load', '+38% add-to-cart'],
      scene: baseScene({
        camera: { eye: [3.9, 2.4, 10.8], target: [-0.3, 0.15, 0], fov: 31 },
        objects: [
          ...forgeMark({ color: '#E6DFD1', accent: '#0E7C6B' }),
          { geo: 'torus', pos: [-0.2, 0.1, 0], R: 3.0, r: 0.008, rot: [1.28, 0.6, 0.1], color: '#8FF7E4', emissive: C.arc, emissiveAmt: 0.9 },
          { geo: 'box', pos: [-3.4, -1.45, 1.1], size: [0.55, 0.55, 0.55], rot: [0.5, 0.65, 0.2], color: '#EFE9DC', flat: true },
          { geo: 'box', pos: [3.2, -1.55, -0.5], size: [0.42, 0.42, 0.42], rot: [0.35, 0.9, 0.3], color: '#FF8A4C', flat: true, emissive: C.forge, emissiveAmt: 0.2 },
          ...dust(11),
        ],
        glow: { x: 0.58, y: 0.5, r: 0.6, color: C.arc, strength: 0.2 },
      }),
    },
    {
      slug: 'meridian-towers',
      title: 'MERIDIAN TOWERS',
      kicker: 'CASE 02 · 3D REAL ESTATE',
      meta: ['Sun-study in bpy', '48 unit interiors', 'WebGL + KTX2', '3.1× longer sessions'],
      scene: baseScene({
        camera: { eye: [5.4, 3.6, 12.8], target: [-0.5, 0.4, 0], fov: 33 },
        objects: [
          ...forgeMark({ oy: 0.5, scale: 0.9 }),
          { geo: 'box', pos: [-4.4, -0.9, 1.6], size: [1.0, 3.2, 1.0], rot: [0, 0.55, 0], color: '#141A22', flat: true, metal: true },
          { geo: 'box', pos: [-3.1, -1.2, 0.5], size: [0.8, 2.4, 0.8], rot: [0, 0.25, 0], color: '#1B2230', flat: true, metal: true },
          { geo: 'box', pos: [3.9, -1.0, -0.9], size: [0.9, 2.8, 0.9], rot: [0, 0.95, 0], color: '#E6DFD1', flat: true },
          { geo: 'box', pos: [2.9, -1.5, 0.9], size: [0.6, 1.8, 0.6], rot: [0, 0.4, 0], color: '#CFC7B6', flat: true },
          ...orbits({ cx: -0.2, r1: 3.3, r2: 3.9 }),
          ...dust(5),
        ],
        glow: { x: 0.45, y: 0.42, r: 0.66, color: C.forge, strength: 0.28 },
      }),
    },
    {
      slug: 'kinetic-labs',
      title: 'KINETIC LABS',
      kicker: 'CASE 03 · 3D PRODUCT LAUNCH',
      meta: ['Scroll-driven timeline', 'GLTF + Draco', 'Motion via GSAP + R3F', '2.4M campaign views'],
      scene: baseScene({
        camera: { eye: [2.8, 1.9, 9.6], target: [-0.2, 0.15, 0], fov: 34 },
        objects: [
          { geo: 'sphere', sub: 3, pos: [-0.15, 0.2, 0], scale: 1.35, color: '#1C222C', metal: true },
          { geo: 'torus', pos: [-0.15, 0.2, 0], R: 1.9, r: 0.012, rot: [1.32, 0.5, 0.12], color: '#FFC79B', emissive: C.forge, emissiveAmt: 0.95 },
          { geo: 'torus', pos: [-0.15, 0.2, 0], R: 2.35, r: 0.006, rot: [1.0, -0.6, 0.45], color: '#8FF7E4', emissive: C.arc, emissiveAmt: 0.9 },
          { geo: 'box', pos: [-2.9, -1.5, 1.0], size: [0.5, 0.5, 0.5], rot: [0.45, 0.7, 0.2], color: '#EDE7DA', flat: true },
          { geo: 'box', pos: [2.7, -1.6, -0.4], size: [0.36, 0.36, 0.36], rot: [0.3, 0.95, 0.35], color: '#FF8A4C', flat: true, emissive: C.forge, emissiveAmt: 0.25 },
          ...dust(23),
        ],
        glow: { x: 0.55, y: 0.45, r: 0.6, color: C.forge, strength: 0.32 },
      }),
    },
  ];

  for (const c of cases) {
    const W = 1800, H = 1200;
    const buf = render(c.scene, W, H, 2);
    const base = await sharp(buf, { raw: { width: W, height: H, channels: 3 } }).png().toBuffer();
    const ov = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">${css()}
      <rect x="0" y="0" width="${W}" height="${H}" fill="url(#g)"/>
      <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#04060A" stop-opacity=".92"/>
        <stop offset=".55" stop-color="#04060A" stop-opacity=".35"/>
        <stop offset="1" stop-color="#04060A" stop-opacity="0"/>
      </linearGradient></defs>
      ${logoTag(72, 64, 104)}
      <text x="72" y="470" font-family="m4" font-size="26" letter-spacing="10" fill="${TW.arc}">${c.kicker}</text>
      <text x="72" y="600" font-family="g7" font-size="104" fill="${TW.bone}">${c.title.split(' ')[0]}</text>
      <text x="72" y="706" font-family="g7" font-size="104" fill="${TW.forge}">${c.title.split(' ').slice(1).join(' ')}</text>
      ${c.meta.map((m, i) => `<text x="76" y="${800 + i * 46}" font-family="i4" font-size="30" fill="${TW.mut}">— ${m}</text>`).join('')}
      <text x="${W - 300}" y="${H - 54}" font-family="m4" font-size="22" letter-spacing="6" fill="${TW.mut}">LUMENFORGE.STUDIO</text>
    </svg>`;
    const over = await sharp(Buffer.from(ov), { density: 72 }).png().toBuffer();
    const p = path.join(ROOT, `portfolio/${c.slug}-1800x1200.png`);
    ensureDir(path.dirname(p));
    await sharp(base).composite([{ input: over }]).png({ compressionLevel: 9 }).toFile(p);
    out.push(p);
  }

  console.log(`key art: ${out.length} files`);
  for (const f of out) console.log(' ', path.relative(ROOT, f));
}

if (require.main === module) {
  main().catch((e) => {
    console.error(e);
    process.exit(1);
  });
}

module.exports = { poster, baseScene, forgeMark, orbits, dust, css, chip, logoTag, TW };
