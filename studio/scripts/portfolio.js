// LUMENFORGE — portfolio PDF (A4 landscape) built from the brand + case-study plates
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const { PDFDocument, rgb } = require('pdf-lib');
const fontkit = require('@pdf-lib/fontkit');
const { ROOT, C } = require('./lib');

const FONT_DIR = path.join(ROOT, 'fonts');
const F = {
  sans: 'space-grotesk-400-normal.ttf',
  bold: 'space-grotesk-700-normal.ttf',
  body: 'inter-400-normal.ttf',
  mono: 'jetbrains-mono-400-normal.ttf',
};

const A4L = [842, 595];

const hexToRgb = (h) => {
  const s = h.replace('#', '');
  return rgb(parseInt(s.slice(0, 2), 16) / 255, parseInt(s.slice(2, 4), 16) / 255, parseInt(s.slice(4, 6), 16) / 255);
};

async function png(rel) {
  return sharp(path.join(ROOT, rel)).png().toBuffer();
}

// Full-bleed page art: art pinned right on ink, with a soft left-to-right scrim so
// PDF typography reads cleanly while the render stays uncropped where it matters.
async function panel(rel, W, H, { artW = 0.74, fade = 0.52, base = C.ink } = {}) {
  W = Math.round(W); H = Math.round(H);
  const aw = Math.round(W * artW);
  const art = await sharp(path.join(ROOT, rel)).resize({ width: aw, height: H, fit: 'cover', position: 'right' }).png().toBuffer();
  const scrim = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">
    <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="${base}" stop-opacity="1"/>
      <stop offset="${fade * 0.55}" stop-color="${base}" stop-opacity="0.94"/>
      <stop offset="${fade}" stop-color="${base}" stop-opacity="0.35"/>
      <stop offset="1" stop-color="${base}" stop-opacity="0"/>
    </linearGradient></defs>
    <rect width="${W}" height="${H}" fill="url(#g)"/></svg>`);
  return sharp({ create: { width: W, height: H, channels: 3, background: base } })
    .composite([
      { input: art, left: W - aw, top: 0 },
      { input: scrim, left: 0, top: 0 },
    ])
    .png()
    .toBuffer();
}

async function coverFit(rel, w, h) {
  return sharp(path.join(ROOT, rel)).resize({ width: Math.round(w), height: Math.round(h), fit: 'cover', position: 'centre' }).png().toBuffer();
}

// Crop into the artwork only — skips the baked caption column on the left so the
// PDF can set its own type without printing the same words twice.
async function artCrop(rel, w, h, { lf = 0.40, tf = 0.06, wf = 0.60, hf = 1 } = {}) {
  const src = sharp(path.join(ROOT, rel));
  const { width: W, height: H } = await src.clone().metadata();
  const left = Math.round(W * lf);
  const top = Math.round(H * tf);
  const cw = Math.min(Math.round(W * wf), W - left);
  const ch = Math.min(Math.round(H * hf), H - top);
  return sharp(path.join(ROOT, rel))
    .extract({ left, top, width: cw, height: ch })
    .resize({ width: Math.round(w), height: Math.round(h), fit: 'cover', position: 'centre' })
    .png()
    .toBuffer();
}

async function main() {
  const pdf = await PDFDocument.create();
  pdf.setTitle('LUMENFORGE — interactive 3D studio portfolio');
  pdf.setAuthor('LUMENFORGE');
  pdf.setSubject('3D commerce, real-estate and product websites built with Blender, Three.js and React');

  pdf.registerFontkit(fontkit);
  const helv = await pdf.embedFont(fs.readFileSync(path.join(FONT_DIR, F.body)), { subset: true });
  const helvBold = await pdf.embedFont(fs.readFileSync(path.join(FONT_DIR, F.bold)), { subset: true });
  const courier = await pdf.embedFont(fs.readFileSync(path.join(FONT_DIR, F.mono)), { subset: true });

  const mark = await pdf.embedPng(await png('brand/exports/logo-mark-1024.png'));
  const markMono = await pdf.embedPng(await png('brand/exports/logo-mark-mono-512.png'));

  const page = () => pdf.addPage(A4L);
  const bg = (p, color) => {
    p.drawRectangle({ x: 0, y: 0, width: A4L[0], height: A4L[1], color: hexToRgb(color) });
  };
  const kicker = (p, t, x, y, color = C.arc) =>
    p.drawText(t.toUpperCase(), { x, y, size: 8, font: courier, color: hexToRgb(color), characterSpacing: 2 });
  const title = (p, t, x, y, size = 34, color = C.bone, font = helvBold) =>
    p.drawText(t, { x, y, size, font, color: hexToRgb(color) });
  const body = (p, t, x, y, size = 10.5, color = C.muted, width = 320) =>
    p.drawText(t, { x, y, size, font: helv, color: hexToRgb(color), lineHeight: size * 1.55, maxWidth: width });
  const rule = (p, x, y, w, color = '#1B2130') =>
    p.drawLine({ start: { x, y }, end: { x: x + w, y }, thickness: 0.7, color: hexToRgb(color) });

  /* ---- 1. cover ---- */
  let p = page();
  bg(p, C.ink);
  const hero = await pdf.embedPng(await panel('portfolio/plates/cover.png', 842, 595, { artW: 0.92, fade: 0.68 }));
  p.drawImage(hero, { x: 0, y: 0, width: 842, height: 595 });
  p.drawImage(mark, { x: 56, y: 470, width: 58, height: 58 });
  title(p, 'LUMENFORGE', 56, 400, 40);
  kicker(p, 'websites you can walk through', 58, 380);
  rule(p, 56, 358, 420);
  body(p, 'An interactive 3D studio. We model in Blender,\nbake with bpy, and ship Three.js + React sites\nthat load under 2 MB and hold 60 fps on a\nmid-range phone.', 56, 336, 10.5, C.muted, 300);
  kicker(p, 'portfolio 2026 · forge@lumenforge.studio', 56, 60, '#5F6878');

  /* ---- 2. position ---- */
  p = page();
  bg(p, C.ink);
  kicker(p, 'position', 56, 520);
  title(p, 'The web is still flat.', 56, 470, 34);
  title(p, 'Flat is expensive.', 56, 432, 34, C.forge);
  rule(p, 56, 400, 730);
  const cols = [
    ['Visitors cannot imagine scale', 'Static shots force customers to guess size, material and finish. Guessing is where carts die.'],
    ['Video is a dead end', 'A 4 MB hero video looks expensive, costs LCP and cannot be explored. A billboard, not a room.'],
    ['WebGL got a bad name', 'Most 3D sites are 40 MB showreels from studios that never had to ship on an Android.'],
  ];
  cols.forEach(([h, t], i) => {
    const x = 56 + i * 248;
    kicker(p, `0${i + 1}`, x, 356, C.forge);
    title(p, h, x, 330, 12, C.bone, helvBold);
    body(p, t, x, 300, 9.5, C.muted, 220);
  });
  kicker(p, 'beauty that survives a mid-range phone', 56, 64, C.arc);
  p.drawText('first load < 2.0 MB     60 fps      lighthouse 95+     <= 8 draw calls', {
    x: 56, y: 44, size: 10, font: courier, color: hexToRgb(C.bone), characterSpacing: 0.6,
  });

  /* ---- 3-5. case studies ---- */
  const cases = [
    ['case 01 · 3d commerce', 'Atelier Nova', 'A flagship store where every piece is a real object you can rotate, place and buy.',
      ['1.9 MB first load', '+38% add-to-cart', 'bpy asset pipeline', 'Three.js + R3F'], 'nova'],
    ['case 02 · 3d real estate', 'Meridian Towers', '48 unit interiors and sun studies computed in Blender, walkable on a phone.',
      ['3.1x longer sessions', 'KTX2 + Draco', 'sun study in bpy', 'WebGL 2 fallback'], 'meridian'],
    ['case 03 · product launch', 'Kinetic Labs', 'A scroll-driven reveal that turns a spec sheet into a launch moment.',
      ['2.4M campaign views', 'GLTF + Draco', 'GSAP + R3F', 'launch ad kit'], 'kinetic'],
  ];
  for (const [k, n, d, tags, img] of cases) {
    p = page();
    bg(p, C.ink);
    const plate = await pdf.embedPng(await panel(`portfolio/plates/${img}.png`, 842, 595, { artW: 0.9, fade: 0.56 }));
    p.drawImage(plate, { x: 0, y: 0, width: 842, height: 595 });
    kicker(p, k, 56, 236);
    title(p, n, 56, 186, 32);
    body(p, d, 56, 152, 10.5, C.muted, 430);
    tags.forEach((t, i) => {
      const x = 56 + i * 150;
      p.drawRectangle({ x, y: 92, width: 142, height: 22, borderColor: hexToRgb(i % 2 ? C.forge : C.arc), borderWidth: 0.6, color: hexToRgb(C.ink) });
      p.drawText(t.toUpperCase(), { x: x + 8, y: 99, size: 6.6, font: courier, color: hexToRgb(i % 2 ? C.forge : C.arc), characterSpacing: 0.8 });
    });
    kicker(p, 'lumenforge.studio', 690, 48, '#5F6878');
  }

  /* ---- 6. process ---- */
  p = page();
  bg(p, C.ink);
  kicker(p, 'the forge', 56, 520);
  title(p, 'Blockout · Forge · Budget · Wire · Harden', 56, 480, 28);
  rule(p, 56, 452, 730);
  const steps = [
    ['Blockout', 'Camera path, scale and light locked before a texture exists.'],
    ['Forge', 'bpy builds hero assets, bakes lightmaps, exports GLTF with LODs.'],
    ['Budget', 'Draco + KTX2 against a signed-off first-load ceiling.'],
    ['Wire', 'React Three Fiber scenes, scroll timelines, CMS bindings.'],
    ['Harden', 'GPU tiers, fallbacks, SEO-safe HTML, Lighthouse gate in CI.'],
  ];
  steps.forEach(([h, t], i) => {
    const x = 56 + i * 148;
    p.drawCircle({ x, y: 420, size: 5, color: hexToRgb(C.forge) });
    kicker(p, `0${i + 1}`, x, 396, C.forge);
    title(p, h, x, 372, 13, C.bone, helvBold);
    body(p, t, x, 344, 8.6, C.muted, 132);
  });
  const plate = await pdf.embedPng(await panel('portfolio/plates/process.png', 730, 240, { artW: 0.62, fade: 0.42 }));
  p.drawImage(plate, { x: 56, y: 76, width: 730, height: 240 });

  /* ---- 7. pricing ---- */
  p = page();
  bg(p, C.ink);
  kicker(p, 'commercials', 56, 520);
  title(p, 'Fixed scope, fixed number, fixed date.', 56, 480, 28);
  const tiers = [
    ['Spark', '$4,800', ['1 walkthrough scene', '3 art-directed stills', 'mobile + WebGL fallback', '2 weeks delivery']],
    ['Forge', '$12,500', ['up to 5 rooms or products', 'bpy asset pipeline', 'scroll camera + CMS', 'launch campaign kit', '3-5 weeks delivery']],
    ['Foundry', '$3,900 / mo', ['2 scenes per sprint', 'perf budget monitoring', 'asset library upkeep', 'rolling retainer']],
  ];
  for (const [i, [n, price, items]] of tiers.entries()) {
    const x = 56 + i * 248;
    const featured = i === 1;
    p.drawRectangle({
      x, y: 150, width: 232, height: 290,
      color: hexToRgb(featured ? '#140E0B' : C.panel),
      borderColor: hexToRgb(featured ? C.forge : '#1B2130'), borderWidth: featured ? 1.2 : 0.7,
    });
    kicker(p, n, x + 20, 412, featured ? C.forge : C.arc);
    title(p, price, x + 20, 366, 24);
    rule(p, x + 20, 348, 192);
    items.forEach((it, j) => {
      p.drawText('—', { x: x + 20, y: 326 - j * 20, size: 9, font: helv, color: hexToRgb(C.arc) });
      p.drawText(it, { x: x + 34, y: 326 - j * 20, size: 9, font: helv, color: hexToRgb(C.muted) });
    });
  }
  body(p, 'Every tier includes a written first-load budget, a Lighthouse gate in CI, source handover, and WebGL fallbacks for low-tier phones.', 56, 110, 10, C.muted, 730);

  /* ---- 8. contact ---- */
  p = page();
  bg(p, C.ink);
  const tower = await pdf.embedPng(await panel('portfolio/plates/contact.png', 842, 595, { artW: 0.8, fade: 0.44 }));
  p.drawImage(tower, { x: 0, y: 0, width: 842, height: 595 });
  p.drawImage(markMono, { x: 56, y: 480, width: 34, height: 34 });
  kicker(p, 'next step', 104, 492);
  title(p, 'Send us your product.', 56, 380, 32);
  title(p, 'We send back a room.', 56, 344, 32, C.forge);
  body(p, 'Within 48 hours you get a fixed price, a camera path and a load budget. No retainer to start, no discovery invoice.', 56, 300, 11, C.muted, 420);
  title(p, 'forge@lumenforge.studio', 56, 220, 16, C.arc, helvBold);
  p.drawText('lumenforge.studio  ·  showroom: lumenforge.studio/showroom', { x: 56, y: 196, size: 9, font: courier, color: hexToRgb('#5F6878') });
  rule(p, 56, 170, 420);
  p.drawText('Blender · bpy · Three.js · React Three Fiber · GSAP · Draco · KTX2', { x: 56, y: 148, size: 8, font: courier, color: hexToRgb(C.muted) });

  const out = path.join(ROOT, 'portfolio', 'LUMENFORGE-portfolio.pdf');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, await pdf.save());
  console.log('portfolio pdf:', out, (fs.statSync(out).size / 1024).toFixed(0) + ' KB', pdf.getPageCount(), 'pages');
}

main().catch((e) => { console.error(e); process.exit(1); });
