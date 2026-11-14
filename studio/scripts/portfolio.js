// KILN — portfolio (A4 landscape, 9 pages).
//
// Type is the identity's own: Instrument Serif for display, Inter Tight for text,
// JetBrains Mono for labels — embedded, subset, same tracking as the site.
// Every image is a Cycles plate; nothing here is drawn in JS.
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const { PDFDocument, rgb } = require('pdf-lib');
const fontkit = require('@pdf-lib/fontkit');
const { ROOT } = require('./lib');

const FD = path.join(ROOT, 'fonts');
const RN = path.join(ROOT, 'brand', 'renders');

const C = {
  ink: '#0B0C0E',
  paper: '#F2EDE4',
  ember: '#D8542A',
  emberLit: '#EE7541',
  kiln: '#8A8578',
  smoke: '#55544F',
  body: '#C4BEB1',
  rule: '#2A2B2F',
};

const hex = (h) => {
  const s = h.replace('#', '');
  return rgb(parseInt(s.slice(0, 2), 16) / 255, parseInt(s.slice(2, 4), 16) / 255, parseInt(s.slice(4, 6), 16) / 255);
};

const W = 842;
const H = 595;
const M = 58;

async function cover(rel, w, h, pos = 'centre') {
  return sharp(path.join(RN, rel)).resize({ width: Math.round(w), height: Math.round(h), fit: 'cover', position: pos }).png().toBuffer();
}

// Plate pinned to one side with a directional scrim so type stays legible without
// flattening the render. `fade` is where the scrim becomes fully transparent.
async function panel(rel, w, h, { side = 'right', frac = 0.62, fade = 0.55, base = C.ink, pos = 'centre' } = {}) {
  w = Math.round(w); h = Math.round(h);
  const aw = Math.round(w * frac);
  const art = await cover(rel, aw, h, pos);
  const x = side === 'right' ? w - aw : 0;
  const dir = side === 'right' ? [0, 1] : [1, 0];
  const stops =
    side === 'right'
      ? `<stop offset="0" stop-color="${base}" stop-opacity="1"/><stop offset="${fade * 0.6}" stop-color="${base}" stop-opacity="0.92"/><stop offset="${fade}" stop-color="${base}" stop-opacity="0.28"/><stop offset="1" stop-color="${base}" stop-opacity="0"/>`
      : `<stop offset="0" stop-color="${base}" stop-opacity="0"/><stop offset="${1 - fade}" stop-color="${base}" stop-opacity="0.28"/><stop offset="${1 - fade * 0.6}" stop-color="${base}" stop-opacity="0.92"/><stop offset="1" stop-color="${base}" stop-opacity="1"/>`;
  const scrim = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">
    <defs><linearGradient id="g" x1="${dir[0]}" y1="0" x2="${dir[1]}" y2="0">${stops}</linearGradient></defs>
    <rect width="${w}" height="${h}" fill="url(#g)"/></svg>`);
  return sharp({ create: { width: w, height: h, channels: 3, background: base } })
    .composite([{ input: art, left: x, top: 0 }, { input: scrim, left: 0, top: 0 }])
    .png()
    .toBuffer();
}

async function main() {
  const pdf = await PDFDocument.create();
  pdf.setTitle('KILN — portfolio');
  pdf.setAuthor('KILN');
  pdf.setSubject('Interactive architecture: Blender-rendered rooms shipped as React sites');
  pdf.setCreator('KILN studio');
  pdf.registerFontkit(fontkit);

  const F = (file) => pdf.embedFont(fs.readFileSync(path.join(FD, file)), { subset: true });
  const serif = await F('instrument-serif.ttf');
  const sans = await F('inter-tight-400.ttf');
  const sansM = await F('inter-tight-500.ttf');
  const mono = await F('jetbrains-mono.ttf');

  const page = () => {
    const p = pdf.addPage([W, H]);
    p.drawRectangle({ x: 0, y: 0, width: W, height: H, color: hex(C.ink) });
    return p;
  };

  // drawText with the PDF's origin at bottom-left; `y` here is distance from the TOP
  const T = (p, t, x, yTop, size, font, color, opts = {}) =>
    p.drawText(t, { x, y: H - yTop, size, font, color: hex(color), ...opts });
  const kicker = (p, t, x, yTop, color = C.ember) =>
    T(p, t.toUpperCase(), x, yTop, 7.4, mono, color, { characterSpacing: 2.1 });
  const body = (p, t, x, yTop, w, size = 9.4, color = C.body, lh = 1.62) =>
    T(p, t, x, yTop, size, sans, color, { maxWidth: w, lineHeight: size * lh });
  const disp = (p, t, x, yTop, size, color = C.paper) =>
    T(p, t, x, yTop, size, serif, color, { lineHeight: size * 0.98 });
  const rule = (p, x, yTop, w, color = C.rule) =>
    p.drawLine({ start: { x, y: H - yTop }, end: { x: x + w, y: H - yTop }, thickness: 0.6, color: hex(color) });

  const mark = await pdf.embedPng(await sharp(path.join(ROOT, 'brand/exports/mark-512.png')).resize(160).png().toBuffer());

  /* ── 01 cover ── */
  let p = page();
  p.drawImage(await pdf.embedPng(await panel('keyart-1600x2000.png', W, H, { frac: 0.56, fade: 0.5 })), { x: 0, y: 0, width: W, height: H });
  p.drawImage(mark, { x: M, y: H - M - 26, width: 26, height: 26 });
  T(p, 'KILN', M + 38, M + 8, 15, serif, C.paper, { characterSpacing: 2.4 });
  kicker(p, 'portfolio · 2026', M, H - M);
  disp(p, 'Rooms,', M, 300, 54);
  disp(p, 'not pages.', M, 348, 54, C.emberLit);
  rule(p, M, 372, 210, '#3A3A3E');
  body(p, 'An interactive architecture studio. We model the space in Blender, light it in bpy and ship it in React — under two megabytes, sixty frames, on a phone.', M, 392, 300, 9.2);
  T(p, 'studio@kiln.studio', M, H - 44, 8, mono, C.kiln, { characterSpacing: 1 });

  /* ── 02 the argument ── */
  p = page();
  kicker(p, 'the argument', M, M + 6);
  disp(p, 'A page is a photograph', M, 116, 34);
  disp(p, 'of a place.', M, 154, 34, C.emberLit);
  rule(p, M, 196, 726);
  const cols = [
    ['Scale', 'A 1.9 m sofa and a 1.4 m sofa photograph identically. Customers guess — and they guess wrong at the exact moment they would have bought.'],
    ['Material', 'Plaster, terracotta, stone: the difference is not colour, it is how the surface takes light. A flat image flattens that away.'],
    ['Light', 'North light at 4 pm is a buying argument for a room. A photograph cannot let anybody move the sun.'],
  ];
  cols.forEach(([h, t], i) => {
    const x = M + i * 246;
    kicker(p, `0${i + 1}`, x, 232, C.ember);
    T(p, h, x, 258, 12, sansM, C.paper);
    body(p, t, x, 274, 222, 8.8);
  });
  p.drawImage(await pdf.embedPng(await cover('detail-2400x1350.png', 726, 190, 'centre')), { x: M, y: 40, width: 726, height: 190 });
  T(p, 'Cycles render, 512 samples, no post.', M + 10, 208, 6.8, mono, C.kiln, { characterSpacing: 1.2 });

  /* ── 03–05 case studies ── */
  const cases = [
    {
      k: 'case 01 · commerce', n: 'Atelier Nova',
      d: 'A flagship where every piece is a real object: turn it, place it in the room, buy it. Product photography replaced by a place.',
      stats: [['+38%', 'add-to-cart'], ['1.9 MB', 'first load'], ['7', 'draw calls']],
      plate: 'work-atelier.png', pos: 'centre',
    },
    {
      k: 'case 02 · property', n: 'Meridian Towers',
      d: 'Forty-eight apartments, each lit for its real orientation. Sun studies computed in Blender and baked to a lightmap, so a phone draws the floor plate in one pass.',
      stats: [['3.1×', 'session length'], ['48', 'units walkable'], ['0', 'render farm']],
      plate: 'work-meridian.png', pos: 'centre',
    },
    {
      k: 'case 03 · launch', n: 'Kinetic Labs',
      d: 'A scroll-driven reveal built from one turned form. The launch film is rendered from the same geometry, so the ad and the site are the same object.',
      stats: [['2.4M', 'campaign views'], ['1', 'asset set'], ['6 wks', 'to launch']],
      plate: 'work-kinetic.png', pos: 'centre',
    },
  ];

  for (const c of cases) {
    p = page();
    p.drawImage(await pdf.embedPng(await panel(c.plate, W, H, { frac: 0.66, fade: 0.52, pos: c.pos })), { x: 0, y: 0, width: W, height: H });
    kicker(p, c.k, M, M + 6);
    disp(p, c.n, M, 122, 36);
    body(p, c.d, M, 168, 296, 9.2);
    c.stats.forEach(([n, l], i) => {
      const y = 300 + i * 46;
      T(p, n, M, y, 19, serif, C.emberLit);
      T(p, l.toUpperCase(), M + 78, y - 2, 6.6, mono, C.kiln, { characterSpacing: 1.4 });
    });
    T(p, 'rendered in blender · shipped in react', M, H - 34, 6.8, mono, C.smoke, { characterSpacing: 1.2 });
  }

  /* ── 06 method ── */
  p = page();
  kicker(p, 'method', M, M + 6);
  disp(p, 'Blockout · Forge · Budget · Wire · Harden', M, 106, 25);
  rule(p, M, 130, 726);
  const steps = [
    ['Blockout', 'Camera path, scale and light locked before a texture exists.'],
    ['Forge', 'bpy scripts build the hero geometry, bake lightmaps, export glTF with LODs.'],
    ['Budget', 'Draco and KTX2 measured against a first-load ceiling signed off up front.'],
    ['Wire', 'React Three Fiber scenes, scroll timelines, CMS bindings.'],
    ['Harden', 'GPU tiers, fallbacks, SEO-safe HTML, a Lighthouse gate in CI.'],
  ];
  steps.forEach(([h, t], i) => {
    const x = M + i * 146;
    p.drawRectangle({ x, y: H - 152, width: 14, height: 1.6, color: hex(C.ember) });
    kicker(p, `0${i + 1}`, x, 174, C.ember);
    T(p, h, x, 194, 11, sansM, C.paper);
    body(p, t, x, 208, 132, 7.9, C.body, 1.5);
  });
  p.drawImage(await pdf.embedPng(await cover('hero-2400x1600.png', 726, 232, 'centre')), { x: M, y: 42, width: 726, height: 232 });

  /* ── 07 rates ── */
  p = page();
  kicker(p, 'rates', M, M + 6);
  disp(p, 'Fixed scope. Fixed number.', M, 106, 26);
  body(p, 'Every tier includes a written load budget, a Lighthouse gate in CI, source handover and WebGL fallbacks.', M, 124, 420, 8.8);
  const tiers = [
    ['Spar', '$4,800', '2 weeks', ['1 walkthrough scene', '3 art-directed stills', 'mobile + WebGL fallback']],
    ['Kiln', '$12,500', '3–5 weeks', ['up to 5 rooms or products', 'bpy asset pipeline', 'scroll camera + CMS', 'launch campaign kit']],
    ['Firing', '$3,900 / mo', 'rolling', ['2 scenes per sprint', 'perf budget monitoring', 'asset library upkeep']],
  ];
  p.drawImage(await pdf.embedPng(await panel('square-1600x1600.png', W, H, { frac: 0.42, fade: 0.44, side: 'right' })), { x: 0, y: 0, width: W, height: H });
  tiers.forEach(([n, price, when, items], i) => {
    const x = M + i * 164;
    const featured = i === 1;
    p.drawRectangle({
      x, y: H - 500, width: 154, height: 252,
      color: hex(featured ? '#14100E' : '#101114'),
      borderColor: hex(featured ? C.ember : C.rule), borderWidth: featured ? 1 : 0.6,
    });
    kicker(p, n, x + 15, 274, featured ? C.emberLit : C.kiln);
    T(p, price, x + 15, 308, 19, serif, C.paper);
    T(p, when, x + 15, 324, 7, mono, C.smoke, { characterSpacing: 0.8 });
    rule(p, x + 15, 342, 122, '#26272B');
    items.forEach((it, j) => T(p, it, x + 15, 362 + j * 16, 7.6, sans, C.body));
  });

  /* ── 08 the studio ── */
  p = page();
  kicker(p, 'the studio', M, M + 6);
  disp(p, 'Blender hands,', M, 112, 34);
  disp(p, 'browser discipline.', M, 150, 34, C.emberLit);
  body(p, 'KILN is three people on purpose: an asset engineer writing bpy automation, a creative developer owning the WebGL layer, and a motion designer who ships the campaign with every build. One pipeline, no handoff to a render farm.', M, 200, 330, 9.4);
  const stack = ['Blender', 'bpy', 'Cycles', 'Three.js', 'React Three Fiber', 'gsap', 'Draco', 'KTX2', 'Playwright'];
  stack.forEach((t, i) => {
    T(p, t, M + (i % 3) * 112, 300 + Math.floor(i / 3) * 20, 7, mono, C.kiln, { characterSpacing: 1.1 });
  });
  p.drawImage(await pdf.embedPng(await panel('hero-2400x1600.png', 380, H, { frac: 1.0, fade: 1, base: C.ink })), { x: W - 380, y: 0, width: 380, height: H });
  p.drawRectangle({ x: W - 380, y: 0, width: 120, height: H, color: hex(C.ink), opacity: 0.9 });

  /* ── 09 contact ── */
  p = page();
  p.drawImage(await pdf.embedPng(await panel('work-kinetic.png', W, H, { frac: 0.6, fade: 0.5 })), { x: 0, y: 0, width: W, height: H });
  p.drawImage(mark, { x: M, y: H - M - 24, width: 24, height: 24 });
  kicker(p, 'next step', M + 34, M + 4);
  disp(p, 'Send the product.', M, 300, 38);
  disp(p, 'We send the room.', M, 342, 38, C.emberLit);
  body(p, 'Within two working days: a fixed price, a camera path and a load budget. No discovery invoice, no retainer to start.', M, 382, 300, 9.2);
  T(p, 'studio@kiln.studio', M, 452, 13, sansM, C.emberLit, { characterSpacing: 0.4 });
  T(p, 'kiln.studio  ·  +44 20 7946 0812  ·  showroom at /showroom', M, 470, 7, mono, C.kiln, { characterSpacing: 0.8 });

  const out = path.join(ROOT, 'portfolio', 'KILN-portfolio.pdf');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, await pdf.save());
  console.log('portfolio:', out, (fs.statSync(out).size / 1024).toFixed(0) + ' KB', pdf.getPageCount(), 'pages');
}

main().catch((e) => { console.error(e); process.exit(1); });
