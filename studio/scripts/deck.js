// KILN — pitch deck.
//
// deck/KILN-pitch-deck.pdf — 16:9, 1280×720, Instrument Serif / Inter Tight /
// JetBrains Mono, embedded and subset.
//
// A .pptx version was built and is deliberately not shipped: PowerPoint can only use
// fonts installed on the viewer's machine, so every slide would fall back to Georgia
// and Consolas at the same measures — the type would reflow and the deck would look
// like the default template it was trying not to be. A deck that cannot set its own
// type should not pretend to.
//
// Text is laid out by hand rather than by a slide library, because a deck that is
// merely "generated" looks generated: default margins, centred titles, bullet indents.
// Here every text block has an explicit measure and baseline, the same grid as the site.
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const { PDFDocument, rgb } = require('pdf-lib');
const fontkit = require('@pdf-lib/fontkit');
const PptxGenJS = require('pptxgenjs');
const { ROOT } = require('./lib');

const W = 1280;
const H = 720;
const M = 86;          // left margin
const MB = 74;         // bottom margin

const C = {
  ink: '#0B0C0E', ink2: '#121316', paper: '#F2EDE4', ember: '#D8542A',
  emberLit: '#EE7541', kiln: '#8A8578', smoke: '#55544F', body: '#C0BAAE', rule: '#26272B',
};

const hex = (h) => {
  const s = h.replace('#', '');
  return rgb(parseInt(s.slice(0, 2), 16) / 255, parseInt(s.slice(2, 4), 16) / 255, parseInt(s.slice(4, 6), 16) / 255);
};

const OUT = path.join(ROOT, 'deck');

// 1400 px JPEG derivatives: the PNG plates are 2–4 MB each and a 16 MB deck is not
// a deck anybody can email
const IMG = (name) => {
  const jpg = path.join('/tmp/deckimg', name.replace(/\.png$/, '.jpg'));
  return fs.existsSync(jpg) ? jpg : path.join(ROOT, 'brand', 'renders', name);
};

const SLIDES = [
  { id: 'cover' }, { id: 'problem' }, { id: 'offers' }, { id: 'atelier' },
  { id: 'meridian' }, { id: 'kinetic' }, { id: 'method' }, { id: 'perf' },
  { id: 'studio' }, { id: 'rates' }, { id: 'why' }, { id: 'next' },
];

/* ───────────────────────────────────────── PDF ───────────────────────────── */
async function pdf() {
  const doc = await PDFDocument.create();
  doc.setTitle('KILN — rooms, not pages');
  doc.setAuthor('KILN');
  doc.setSubject('Interactive architecture: Blender-rendered rooms shipped as React sites');
  doc.registerFontkit(fontkit);

  const F = (f) => doc.embedFont(fs.readFileSync(path.join(ROOT, 'fonts', f)), { subset: true });
  const serif = await F('instrument-serif.ttf');
  const sans = await F('inter-tight-400.ttf');
  const sansM = await F('inter-tight-500.ttf');
  const mono = await F('jetbrains-mono.ttf');

  const page = async (img, { frac = 0.5, side = 'right', fade = 0.5, pos = 'centre' } = {}) => {
    const p = doc.addPage([W, H]);
    p.drawRectangle({ x: 0, y: 0, width: W, height: H, color: hex(C.ink) });
    if (img) {
      const aw = Math.round(W * frac);
      const art = await sharp(IMG(img)).resize({ width: aw, height: H, fit: 'cover', position: pos }).png().toBuffer();
      const x = side === 'right' ? W - aw : 0;
      const grad = side === 'right'
        ? `<stop offset="0" stop-color="${C.ink}" stop-opacity="1"/><stop offset="${fade * 0.62}" stop-color="${C.ink}" stop-opacity="0.9"/><stop offset="${fade}" stop-color="${C.ink}" stop-opacity="0.22"/><stop offset="1" stop-color="${C.ink}" stop-opacity="0"/>`
        : `<stop offset="0" stop-color="${C.ink}" stop-opacity="0"/><stop offset="${1 - fade}" stop-color="${C.ink}" stop-opacity="0.22"/><stop offset="${1 - fade * 0.62}" stop-color="${C.ink}" stop-opacity="0.9"/><stop offset="1" stop-color="${C.ink}" stop-opacity="1"/>`;
      const x1 = side === 'right' ? 0 : 1;
      const x2 = side === 'right' ? 1 : 0;
      const scrim = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">
        <defs><linearGradient id="g" x1="${x1}" y1="0" x2="${x2}" y2="0">${grad}</linearGradient></defs>
        <rect width="${W}" height="${H}" fill="url(#g)"/></svg>`);
      const plate = await sharp({ create: { width: W, height: H, channels: 3, background: C.ink } })
        .composite([{ input: art, left: x, top: 0 }, { input: scrim, left: 0, top: 0 }])
        .png().toBuffer();
      p.drawImage(await doc.embedPng(plate), { x: 0, y: 0, width: W, height: H });
    }
    return p;
  };

  const T = (p, t, x, yTop, size, font, color, opts = {}) =>
    p.drawText(t, { x, y: H - yTop, size, font, color: hex(color), ...opts });
  const kick = (p, t, yTop = 108, color = C.ember) =>
    T(p, t.toUpperCase(), M, yTop, 8.4, mono, color, { characterSpacing: 2.4 });
  const body = (p, t, x, yTop, w, size = 12.5, color = C.body, lh = 1.62) =>
    T(p, t, x, yTop, size, sans, color, { maxWidth: w, lineHeight: size * lh });
  const disp = (p, t, x, yTop, size, color = C.paper, lh = 0.96) =>
    T(p, t, x, yTop, size, serif, color, { lineHeight: size * lh });
  const rule = (p, x, yTop, w, color = C.rule) =>
    p.drawRectangle({ x, y: H - yTop, width: w, height: 0.8, color: hex(color) });
  const foot = (p, t) =>
    T(p, t.toUpperCase(), M, H - 42, 7.2, mono, C.smoke, { characterSpacing: 1.6 });
  const num = (p, n) =>
    T(p, String(n).padStart(2, '0'), W - M - 18, H - 42, 7.2, mono, C.smoke, { characterSpacing: 1.4 });

  const mark = await doc.embedPng(await sharp(path.join(ROOT, 'brand/exports/mark-512.png')).resize(140).png().toBuffer());

  /* 01 cover */
  let p = await page('keyart-1600x2000.png', { frac: 0.52, fade: 0.46 });
  p.drawImage(mark, { x: M, y: H - 118, width: 26, height: 26 });
  T(p, 'KILN', M + 38, 116, 15, serif, C.paper, { characterSpacing: 2.6 });
  disp(p, 'Rooms,', M, 470, 62);
  disp(p, 'not pages.', M, 528, 62, C.emberLit);
  rule(p, M, 566, 118, '#3A3A3E');
  body(p, 'An interactive architecture studio. We model the space in Blender, light it with bpy and ship it in React — under two megabytes, sixty frames on a phone.', M, 592, 380, 11.6);
  foot(p, 'Pitch deck · 2026 · studio@kiln.studio');
  num(p, 1);

  /* 02 the problem */
  p = await page('hero-2400x1600.png', { frac: 0.46, fade: 0.5 });
  kick(p, 'The problem');
  disp(p, 'A page is a photograph', M, 200, 44);
  disp(p, 'of a place.', M, 244, 44, C.emberLit);
  body(p, 'Customers are asked to judge size, material and finish from a flat image — then guess wrong at the moment they would have bought. Video does not help: it cannot be explored. And most “3D websites” are forty-megabyte showreels that melt a phone on 4G.', M, 316, 470, 12.4);
  [['No sense of scale', 'A 1.9 m sofa and a 1.4 m sofa photograph identically.'],
   ['No sense of material', 'Plaster and stone differ in how they take light, not in colour.'],
   ['No sense of light', 'A north window at four in the afternoon is a buying argument.']]
    .forEach(([h, t], i) => {
      const y = 452 + i * 58;
      p.drawRectangle({ x: M, y: H - y + 9, width: 14, height: 1.4, color: hex(C.ember) });
      T(p, h, M + 26, y, 12.4, sansM, C.paper);
      T(p, t, M + 26, y + 19, 9.6, sans, C.kiln);
    });
  foot(p, 'the argument'); num(p, 2);

  /* 03 what we make — three columns, each carrying its own plate */
  p = await page(null);
  kick(p, 'The work');
  disp(p, 'Three rooms, three trades.', M, 176, 42);
  rule(p, M, 232, W - M * 2);
  const offers = [
    ['COMMERCE', 'A gallery you can shop', 'Every piece is a real object: turn it, place it, buy it.', 'work-atelier.png'],
    ['PROPERTY', 'Every unit walkable', 'Sun studies baked in Blender, forty-eight apartments on one link.', 'work-meridian.png'],
    ['LAUNCH', 'A moment, not a page', 'A scroll-driven reveal that turns a spec sheet into something people forward.', 'work-kinetic.png'],
  ];
  for (const [i, [tag, head, text, img]] of offers.entries()) {
    const x = M + i * 358;
    const crop = await sharp(IMG(img)).resize({ width: 320, height: 240, fit: 'cover', position: 'centre' }).png().toBuffer();
    p.drawImage(await doc.embedPng(crop), { x, y: H - 480, width: 320, height: 240 });
    T(p, tag, x, 508, 8, mono, C.ember, { characterSpacing: 2.2 });
    disp(p, head, x, 532, 20);
    body(p, text, x, 560, 306, 10.6);
  }
  foot(p, 'what we build'); num(p, 3);

  /* 04–06 cases */
  const cases = [
    ['case 01 · commerce', 'Atelier Nova', 'A flagship where every piece is a real object you turn, place and buy.', [['+38%', 'add-to-cart'], ['1.9 MB', 'first load'], ['7', 'draw calls']], 'work-atelier.png'],
    ['case 02 · property', 'Meridian Towers', 'Forty-eight apartments, each lit for its real orientation. Sun studies computed in Blender and baked to a lightmap, so a phone draws the floor plate in one pass.', [['3.1×', 'session length'], ['48', 'units walkable'], ['0', 'render farm']], 'work-meridian.png'],
    ['case 03 · launch', 'Kinetic Labs', 'A scroll-driven reveal built from one turned form. The launch film is rendered from the same geometry, so the ad and the site are the same object.', [['2.4M', 'campaign views'], ['1', 'asset set'], ['6 wks', 'to launch']], 'work-kinetic.png'],
  ];
  for (const [i, [k, n, d, stats, img]] of cases.entries()) {
    p = await page(img, { frac: 0.52, fade: 0.48 });
    kick(p, k);
    disp(p, n, M, 208, 40);
    body(p, d, M, 264, 440, 12);
    stats.forEach(([v, l], j) => {
      const y = 420 + j * 52;
      T(p, v, M, y, 20, serif, C.emberLit);
      T(p, l.toUpperCase(), M + 96, y - 1, 7.4, mono, C.kiln, { characterSpacing: 1.5 });
    });
    foot(p, 'rendered in blender · shipped in react'); num(p, 4 + i);
  }

  /* 07 method */
  p = await page(null);
  kick(p, 'Method');
  disp(p, 'Blockout · Forge · Budget · Wire · Harden', M, 186, 30);
  rule(p, M, 232, W - M * 2);
  [['Blockout', 'Camera path, scale and light locked before a texture exists.'],
   ['Forge', 'bpy builds the hero geometry, bakes lightmaps, exports glTF with LODs.'],
   ['Budget', 'Draco and KTX2 measured against a ceiling signed off up front.'],
   ['Wire', 'React Three Fiber scenes, scroll timelines, CMS bindings.'],
   ['Harden', 'GPU tiers, fallbacks, SEO-safe HTML, a Lighthouse gate in CI.']]
    .forEach(([h, t], i) => {
      const x = M + i * 216;
      p.drawRectangle({ x, y: H - 276, width: 16, height: 1.4, color: hex(C.ember) });
      T(p, `0${i + 1}`, x, 296, 7.4, mono, C.ember, { characterSpacing: 1.4 });
      T(p, h, x, 318, 13.5, serif, C.paper);
      body(p, t, x, 340, 190, 9.4);
    });
  p.drawImage(await doc.embedPng(await sharp(IMG('hero-2400x1600.png'))
    .resize({ width: 1110, height: 220, fit: 'cover', position: 'south' }).png().toBuffer()),
    { x: M, y: 58, width: W - M * 2, height: 220 });
  foot(p, 'the method'); num(p, 7);

  /* 08 engineering */
  p = await page('square-1600x1600.png', { frac: 0.42, fade: 0.48 });
  kick(p, 'Engineering');
  disp(p, 'Beauty that survives', M, 196, 40);
  disp(p, 'a mid-range phone.', M, 238, 40, C.emberLit);
  [['< 2.0 MB', 'first load, fonts and JS included'],
   ['60 fps', 'on a Pixel 6a / iPhone 12 tier GPU'],
   ['≤ 8', 'draw calls in the hero scene'],
   ['95+', 'Lighthouse, gated in CI']]
    .forEach(([v, t], i) => {
      const x = M + (i % 2) * 250;
      const y = 330 + Math.floor(i / 2) * 130;
      T(p, v, x, y, 30, serif, i % 2 ? C.emberLit : C.paper);
      body(p, t, x, y + 34, 220, 10);
    });
  foot(p, 'the budget is the design'); num(p, 8);

  /* 09 studio */
  p = await page(null);
  kick(p, 'The studio');
  disp(p, 'Blender hands,', M, 200, 40);
  disp(p, 'browser discipline.', M, 242, 40, C.emberLit);
  body(p, 'KILN is three people on purpose: an asset engineer writing bpy automation, a creative developer owning the WebGL layer, and a motion designer who ships the campaign with every build. One pipeline, no handoff to a render farm.', M, 320, 490, 12.4);
  ['Blender', 'bpy', 'Cycles', 'Three.js', 'React Three Fiber', 'gsap', 'Draco', 'KTX2', 'Playwright']
    .forEach((t, i) => {
      const x = M + (i % 3) * 128;
      const y = 452 + Math.floor(i / 3) * 34;
      p.drawRectangle({ x, y: H - y - 16, width: 120, height: 26, borderColor: hex(C.rule), borderWidth: 0.6, color: hex(C.ink2) });
      T(p, t, x + 10, y, 8, mono, C.kiln, { characterSpacing: 0.8 });
    });
  // portrait panel from a portrait plate: a 16:9 detail crop would be a single blur
  p.drawImage(await doc.embedPng(await sharp(IMG('work-atelier.png'))
    .resize({ width: 470, height: H, fit: 'cover', position: 'left' }).png().toBuffer()),
    { x: W - 470, y: 0, width: 470, height: H });
  p.drawRectangle({ x: W - 470, y: 0, width: 90, height: H, color: hex(C.ink), opacity: 0.86 });
  foot(p, 'the studio'); num(p, 9);

  /* 10 rates */
  p = await page(null);
  kick(p, 'Rates');
  disp(p, 'Fixed scope. Fixed number.', M, 190, 38);
  body(p, 'Every tier includes a written load budget, a Lighthouse gate in CI, source handover and WebGL fallbacks.', M, 224, 620, 11.2);
  const tiers = [
    ['Spar', '$4,800', '2 weeks', 'One walkthrough scene, three art-directed stills, source handover.'],
    ['Kiln', '$12,500', '3–5 weeks', 'Up to five rooms, bpy pipeline, CMS, launch kit, thirty days of support.'],
    ['Firing', '$3,900 / mo', 'rolling', 'Two scenes per sprint, performance monitoring, monthly ad creative.'],
  ];
  tiers.forEach(([n, price, when, what], i) => {
    const x = M + i * 358;
    const feat = i === 1;
    p.drawRectangle({
      x, y: 96, width: 330, height: 250,
      color: hex(feat ? '#14100E' : C.ink2),
      borderColor: hex(feat ? C.ember : C.rule), borderWidth: feat ? 1 : 0.6,
    });
    T(p, n.toUpperCase(), x + 24, 320, 8, mono, feat ? C.emberLit : C.kiln, { characterSpacing: 2.2 });
    T(p, price, x + 24, 356, 26, serif, C.paper);
    T(p, when, x + 24, 372, 8, mono, C.smoke, { characterSpacing: 1 });
    rule(p, x + 24, 388, 282, '#26272B');
    body(p, what, x + 24, 404, 282, 10.2);
  });
  foot(p, 'rates'); num(p, 10);

  /* 11 why */
  p = await page('work-atelier.png', { frac: 0.5, fade: 0.5 });
  kick(p, 'Why it holds together');
  disp(p, 'One set,', M, 200, 40);
  disp(p, 'many pictures.', M, 242, 40, C.emberLit);
  body(p, 'Every KILN build starts as a real Blender scene. That single decision pays three times: the site is lit correctly, the launch film is rendered from the same geometry, and the ad stills are photographs rather than illustrations. One asset, one invoice, three channels.', M, 316, 470, 12.4);
  foot(p, 'provenance'); num(p, 11);

  /* 12 next */
  p = await page('work-meridian.png', { frac: 0.46, fade: 0.46 });
  kick(p, 'Next step');
  disp(p, 'Send the product.', M, 246, 44);
  disp(p, 'We send the room.', M, 292, 44, C.emberLit);
  body(p, 'Within two working days: a fixed price, a camera path and a load budget. No discovery invoice, no retainer to start.', M, 372, 430, 12.4);
  T(p, 'studio@kiln.studio', M, 470, 17, sansM, C.emberLit, { characterSpacing: 0.3 });
  T(p, 'kiln.studio  ·  +44 20 7946 0812  ·  showroom at /showroom', M, 494, 8.4, mono, C.kiln, { characterSpacing: 0.8 });
  foot(p, 'kiln · 2026'); num(p, 12);

  fs.mkdirSync(OUT, { recursive: true });
  const file = path.join(OUT, 'KILN-pitch-deck.pdf');
  fs.writeFileSync(file, await doc.save());
  console.log('deck pdf:', file, (fs.statSync(file).size / 1024).toFixed(0) + ' KB', doc.getPageCount(), 'slides');
}

/* ───────────────────────────────────────── PPTX ────────────────────────────
   Kept behind a flag for anyone who needs to edit the copy in PowerPoint and accepts
   the font substitution. Not run by default, not committed.
*/
async function pptx() {
  const pptx = new PptxGenJS();
  pptx.layout = 'LAYOUT_16x9';
  pptx.title = 'KILN — rooms, not pages';
  pptx.author = 'KILN';
  const EW = 13.333;
  const EH = 7.5;
  const em = (pt) => pt / 72;          // points → inches, so sizes match the PDF
  const ex = (x) => (x / W) * EW;
  const ey = (y) => (y / H) * EH;

  const slide = (img, { frac = 0.5, side = 'right' } = {}) => {
    const s = pptx.addSlide();
    s.background = { color: C.ink.replace('#', '') };
    if (img) {
      const w = EW * frac;
      s.addImage({
        path: IMG(img), x: side === 'right' ? EW - w : 0, y: 0, w, h: EH,
        sizing: { type: 'cover', w, h: EH },
      });
      // a scrim so type is never set on the busy half
      s.addShape(pptx.ShapeType.rect, {
        x: side === 'right' ? EW - w : 0, y: 0, w: w * 0.85, h: EH,
        fill: { color: C.ink.replace('#', ''), transparency: 22 }, line: { color: C.ink.replace('#', ''), width: 0 },
      });
    }
    return s;
  };
  const T = (s, t, x, y, size, font, color, opts = {}) =>
    s.addText(t, { x: ex(x), y: ey(y), w: opts.w || 6, h: opts.h || 0.6, fontSize: size, fontFace: font, color, charSpacing: opts.cs || 0, lineSpacingMultiple: opts.lh || 1.2, valign: 'top', bold: !!opts.bold });
  const SERIF = 'Georgia';
  const SANS = 'Arial';
  const MONO = 'Consolas';
  const kick = (s, t) => T(s, t.toUpperCase(), M, 108, 8.4, MONO, C.ember.replace('#', ''), { cs: 2.4 });
  const foot = (s, t) => T(s, t.toUpperCase(), M, 668, 7.2, MONO, C.smoke.replace('#', ''), { cs: 1.6 });

  let s = slide('keyart-1600x2000.png', { frac: 0.52 });
  T(s, 'KILN', 124, 100, 15, SERIF, C.paper.replace('#', ''), { cs: 2.6 });
  T(s, 'Rooms,', M, 400, 62, SERIF, C.paper.replace('#', ''), { w: 6 });
  T(s, 'not pages.', M, 452, 62, SERIF, C.emberLit.replace('#', ''), { w: 6 });
  T(s, 'An interactive architecture studio. We model the space in Blender, light it with bpy and ship it in React — under two megabytes, sixty frames on a phone.', M, 528, 11.6, SANS, C.body.replace('#', ''), { w: 4.2, lh: 1.4 });
  foot(s, 'Pitch deck · 2026 · studio@kiln.studio');

  s = slide('hero-2400x1600.png', { frac: 0.46 });
  kick(s, 'The problem');
  T(s, 'A page is a photograph', M, 176, 44, SERIF, C.paper.replace('#', ''));
  T(s, 'of a place.', M, 222, 44, SERIF, C.emberLit.replace('#', ''));
  T(s, 'Customers are asked to judge size, material and finish from a flat image — then guess wrong at the moment they would have bought. Video does not help: it cannot be explored. And most “3D websites” are forty-megabyte showreels that melt a phone on 4G.', M, 300, 12.4, SANS, C.body.replace('#', ''), { w: 5.4, lh: 1.45 });
  ['No sense of scale · No sense of material · No sense of light'].forEach((t) =>
    T(s, t, M, 480, 10, MONO, C.kiln.replace('#', ''), { cs: 1 }));
  foot(s, 'the argument');

  s = slide(null);
  kick(s, 'The work');
  T(s, 'Three rooms, three trades.', M, 176, 42, SERIF, C.paper.replace('#', ''));
  const offers = [
    ['COMMERCE', 'A gallery you can shop', 'work-atelier.png'],
    ['PROPERTY', 'Every unit walkable', 'work-meridian.png'],
    ['LAUNCH', 'A moment, not a page', 'work-kinetic.png'],
  ];
  offers.forEach(([tag, head, img], i) => {
    const x = M + i * 358;
    s.addImage({ path: IMG(img), x: ex(x), y: ey(250), w: ex(320), h: ey(240), sizing: { type: 'cover', w: ex(320), h: ey(240) } });
    T(s, tag, x, 510, 8, MONO, C.ember.replace('#', ''), { cs: 2.2 });
    T(s, head, x, 528, 19, SERIF, C.paper.replace('#', ''));
  });
  foot(s, 'what we build');

  const cases = [
    ['case 01 · commerce', 'Atelier Nova', 'A flagship where every piece is a real object you turn, place and buy.', [['+38%', 'add-to-cart'], ['1.9 MB', 'first load'], ['7', 'draw calls']], 'work-atelier.png'],
    ['case 02 · property', 'Meridian Towers', 'Forty-eight apartments, each lit for its real orientation. Sun studies computed in Blender and baked to a lightmap, so a phone draws the floor plate in one pass.', [['3.1×', 'session length'], ['48', 'units walkable'], ['0', 'render farm']], 'work-meridian.png'],
    ['case 03 · launch', 'Kinetic Labs', 'A scroll-driven reveal built from one turned form. The launch film is rendered from the same geometry, so the ad and the site are the same object.', [['2.4M', 'campaign views'], ['1', 'asset set'], ['6 wks', 'to launch']], 'work-kinetic.png'],
  ];
  for (const [i, [k, n, d, stats, img]] of cases.entries()) {
    p = await page(img, { frac: 0.52, fade: 0.48 });
    kick(p, k);
    disp(p, n, M, 208, 40);
    body(p, d, M, 264, 440, 12);
    stats.forEach(([v, l], j) => {
      const y = 420 + j * 52;
      T(p, v, M, y, 20, serif, C.emberLit);
      T(p, l.toUpperCase(), M + 96, y - 1, 7.4, mono, C.kiln, { characterSpacing: 1.5 });
    });
    foot(p, 'rendered in blender · shipped in react'); num(p, 4 + i);
  }

  /* 07 method */
  p = await page(null);
  kick(p, 'Method');
  disp(p, 'Blockout · Forge · Budget · Wire · Harden', M, 186, 30);
  rule(p, M, 232, W - M * 2);
  [['Blockout', 'Camera path, scale and light locked before a texture exists.'],
   ['Forge', 'bpy builds the hero geometry, bakes lightmaps, exports glTF with LODs.'],
   ['Budget', 'Draco and KTX2 measured against a ceiling signed off up front.'],
   ['Wire', 'React Three Fiber scenes, scroll timelines, CMS bindings.'],
   ['Harden', 'GPU tiers, fallbacks, SEO-safe HTML, a Lighthouse gate in CI.']]
    .forEach(([h, t], i) => {
      const x = M + i * 216;
      p.drawRectangle({ x, y: H - 276, width: 16, height: 1.4, color: hex(C.ember) });
      T(p, `0${i + 1}`, x, 296, 7.4, mono, C.ember, { characterSpacing: 1.4 });
      T(p, h, x, 318, 13.5, serif, C.paper);
      body(p, t, x, 340, 190, 9.4);
    });
  p.drawImage(await doc.embedPng(await sharp(IMG('hero-2400x1600.png'))
    .resize({ width: 1110, height: 220, fit: 'cover', position: 'south' }).png().toBuffer()),
    { x: M, y: 58, width: W - M * 2, height: 220 });
  foot(p, 'the method'); num(p, 7);

  /* 08 engineering */
  p = await page('square-1600x1600.png', { frac: 0.42, fade: 0.48 });
  kick(p, 'Engineering');
  disp(p, 'Beauty that survives', M, 196, 40);
  disp(p, 'a mid-range phone.', M, 238, 40, C.emberLit);
  [['< 2.0 MB', 'first load, fonts and JS included'],
   ['60 fps', 'on a Pixel 6a / iPhone 12 tier GPU'],
   ['≤ 8', 'draw calls in the hero scene'],
   ['95+', 'Lighthouse, gated in CI']]
    .forEach(([v, t], i) => {
      const x = M + (i % 2) * 250;
      const y = 330 + Math.floor(i / 2) * 130;
      T(p, v, x, y, 30, serif, i % 2 ? C.emberLit : C.paper);
      body(p, t, x, y + 34, 220, 10);
    });
  foot(p, 'the budget is the design'); num(p, 8);

  /* 09 studio */
  p = await page(null);
  kick(p, 'The studio');
  disp(p, 'Blender hands,', M, 200, 40);
  disp(p, 'browser discipline.', M, 242, 40, C.emberLit);
  body(p, 'KILN is three people on purpose: an asset engineer writing bpy automation, a creative developer owning the WebGL layer, and a motion designer who ships the campaign with every build. One pipeline, no handoff to a render farm.', M, 320, 490, 12.4);
  ['Blender', 'bpy', 'Cycles', 'Three.js', 'React Three Fiber', 'gsap', 'Draco', 'KTX2', 'Playwright']
    .forEach((t, i) => {
      const x = M + (i % 3) * 128;
      const y = 452 + Math.floor(i / 3) * 34;
      p.drawRectangle({ x, y: H - y - 16, width: 120, height: 26, borderColor: hex(C.rule), borderWidth: 0.6, color: hex(C.ink2) });
      T(p, t, x + 10, y, 8, mono, C.kiln, { characterSpacing: 0.8 });
    });
  // portrait panel from a portrait plate: a 16:9 detail crop would be a single blur
  p.drawImage(await doc.embedPng(await sharp(IMG('work-atelier.png'))
    .resize({ width: 470, height: H, fit: 'cover', position: 'left' }).png().toBuffer()),
    { x: W - 470, y: 0, width: 470, height: H });
  p.drawRectangle({ x: W - 470, y: 0, width: 90, height: H, color: hex(C.ink), opacity: 0.86 });
  foot(p, 'the studio'); num(p, 9);

  /* 10 rates */
  p = await page(null);
  kick(p, 'Rates');
  disp(p, 'Fixed scope. Fixed number.', M, 190, 38);
  body(p, 'Every tier includes a written load budget, a Lighthouse gate in CI, source handover and WebGL fallbacks.', M, 224, 620, 11.2);
  const tiers = [
    ['Spar', '$4,800', '2 weeks', 'One walkthrough scene, three art-directed stills, source handover.'],
    ['Kiln', '$12,500', '3–5 weeks', 'Up to five rooms, bpy pipeline, CMS, launch kit, thirty days of support.'],
    ['Firing', '$3,900 / mo', 'rolling', 'Two scenes per sprint, performance monitoring, monthly ad creative.'],
  ];
  tiers.forEach(([n, price, when, what], i) => {
    const x = M + i * 358;
    const feat = i === 1;
    p.drawRectangle({
      x, y: 96, width: 330, height: 250,
      color: hex(feat ? '#14100E' : C.ink2),
      borderColor: hex(feat ? C.ember : C.rule), borderWidth: feat ? 1 : 0.6,
    });
    T(p, n.toUpperCase(), x + 24, 320, 8, mono, feat ? C.emberLit : C.kiln, { characterSpacing: 2.2 });
    T(p, price, x + 24, 356, 26, serif, C.paper);
    T(p, when, x + 24, 372, 8, mono, C.smoke, { characterSpacing: 1 });
    rule(p, x + 24, 388, 282, '#26272B');
    body(p, what, x + 24, 404, 282, 10.2);
  });
  foot(p, 'rates'); num(p, 10);

  /* 11 why */
  p = await page('work-atelier.png', { frac: 0.5, fade: 0.5 });
  kick(p, 'Why it holds together');
  disp(p, 'One set,', M, 200, 40);
  disp(p, 'many pictures.', M, 242, 40, C.emberLit);
  body(p, 'Every KILN build starts as a real Blender scene. That single decision pays three times: the site is lit correctly, the launch film is rendered from the same geometry, and the ad stills are photographs rather than illustrations. One asset, one invoice, three channels.', M, 316, 470, 12.4);
  foot(p, 'provenance'); num(p, 11);

  /* 12 next */
  p = await page('work-meridian.png', { frac: 0.46, fade: 0.46 });
  kick(p, 'Next step');
  disp(p, 'Send the product.', M, 246, 44);
  disp(p, 'We send the room.', M, 292, 44, C.emberLit);
  body(p, 'Within two working days: a fixed price, a camera path and a load budget. No discovery invoice, no retainer to start.', M, 372, 430, 12.4);
  T(p, 'studio@kiln.studio', M, 470, 17, sansM, C.emberLit, { characterSpacing: 0.3 });
  T(p, 'kiln.studio  ·  +44 20 7946 0812  ·  showroom at /showroom', M, 494, 8.4, mono, C.kiln, { characterSpacing: 0.8 });
  foot(p, 'kiln · 2026'); num(p, 12);

  fs.mkdirSync(OUT, { recursive: true });
  const file = path.join(OUT, 'KILN-pitch-deck.pdf');
  fs.writeFileSync(file, await doc.save());
  console.log('deck pdf:', file, (fs.statSync(file).size / 1024).toFixed(0) + ' KB', doc.getPageCount(), 'slides');
}

/* ───────────────────────────────────────── PPTX ────────────────────────────
   Kept behind a flag for anyone who needs to edit the copy in PowerPoint and accepts
   the font substitution. Not run by default, not committed.
*/
async function pptx() {
  const pptx = new PptxGenJS();
  pptx.layout = 'LAYOUT_16x9';
  pptx.title = 'KILN — rooms, not pages';
  pptx.author = 'KILN';
  const EW = 13.333;
  const EH = 7.5;
  const em = (pt) => pt / 72;          // points → inches, so sizes match the PDF
  const ex = (x) => (x / W) * EW;
  const ey = (y) => (y / H) * EH;

  const slide = (img, { frac = 0.5, side = 'right' } = {}) => {
    const s = pptx.addSlide();
    s.background = { color: C.ink.replace('#', '') };
    if (img) {
      const w = EW * frac;
      s.addImage({
        path: IMG(img), x: side === 'right' ? EW - w : 0, y: 0, w, h: EH,
        sizing: { type: 'cover', w, h: EH },
      });
      // a scrim so type is never set on the busy half
      s.addShape(pptx.ShapeType.rect, {
        x: side === 'right' ? EW - w : 0, y: 0, w: w * 0.85, h: EH,
        fill: { color: C.ink.replace('#', ''), transparency: 22 }, line: { color: C.ink.replace('#', ''), width: 0 },
      });
    }
    return s;
  };
  const T = (s, t, x, y, size, font, color, opts = {}) =>
    s.addText(t, { x: ex(x), y: ey(y), w: opts.w || 6, h: opts.h || 0.6, fontSize: size, fontFace: font, color, charSpacing: opts.cs || 0, lineSpacingMultiple: opts.lh || 1.2, valign: 'top', bold: !!opts.bold });
  const SERIF = 'Georgia';
  const SANS = 'Arial';
  const MONO = 'Consolas';
  const kick = (s, t) => T(s, t.toUpperCase(), M, 108, 8.4, MONO, C.ember.replace('#', ''), { cs: 2.4 });
  const foot = (s, t) => T(s, t.toUpperCase(), M, 668, 7.2, MONO, C.smoke.replace('#', ''), { cs: 1.6 });

  let s = slide('keyart-1600x2000.png', { frac: 0.52 });
  T(s, 'KILN', 124, 100, 15, SERIF, C.paper.replace('#', ''), { cs: 2.6 });
  T(s, 'Rooms,', M, 400, 62, SERIF, C.paper.replace('#', ''), { w: 6 });
  T(s, 'not pages.', M, 452, 62, SERIF, C.emberLit.replace('#', ''), { w: 6 });
  T(s, 'An interactive architecture studio. We model the space in Blender, light it with bpy and ship it in React — under two megabytes, sixty frames on a phone.', M, 528, 11.6, SANS, C.body.replace('#', ''), { w: 4.2, lh: 1.4 });
  foot(s, 'Pitch deck · 2026 · studio@kiln.studio');

  s = slide('hero-2400x1600.png', { frac: 0.46 });
  kick(s, 'The problem');
  T(s, 'A page is a photograph', M, 176, 44, SERIF, C.paper.replace('#', ''));
  T(s, 'of a place.', M, 222, 44, SERIF, C.emberLit.replace('#', ''));
  T(s, 'Customers are asked to judge size, material and finish from a flat image — then guess wrong at the moment they would have bought. Video does not help: it cannot be explored. And most “3D websites” are forty-megabyte showreels that melt a phone on 4G.', M, 300, 12.4, SANS, C.body.replace('#', ''), { w: 5.4, lh: 1.45 });
  ['No sense of scale · No sense of material · No sense of light'].forEach((t) =>
    T(s, t, M, 480, 10, MONO, C.kiln.replace('#', ''), { cs: 1 }));
  foot(s, 'the argument');

  s = slide(null);
  kick(s, 'The work');
  T(s, 'Three rooms, three trades.', M, 176, 42, SERIF, C.paper.replace('#', ''));
  [['COMMERCE', 'A gallery you can shop'], ['PROPERTY', 'Every unit walkable'], ['LAUNCH', 'A moment, not a page']]
    .forEach(([tag, head], i) => {
      T(s, tag, M + i * 358, 300, 8, MONO, C.ember.replace('#', ''), { cs: 2.2 });
      T(s, head, M + i * 358, 324, 19, SERIF, C.paper.replace('#', ''));
    });
  s.addImage({ path: IMG('hero-2400x1600.png'), x: ex(M), y: ey(430), w: ex(1110), h: ey(190), sizing: { type: 'cover', w: ex(1110), h: ey(190) }, rounding: false });
  foot(s, 'what we build');

  const cases = [
    ['case 01 · commerce', 'Atelier Nova', 'A flagship where every piece is a real object you turn, place and buy.', ['+38% add-to-cart', '1.9 MB first load', '7 draw calls'], 'work-atelier.png'],
    ['case 02 · property', 'Meridian Towers', 'Forty-eight apartments, each lit for its real orientation. Sun studies computed in Blender and baked to a lightmap.', ['3.1× session length', '48 units walkable', '0 render farm'], 'work-meridian.png'],
    ['case 03 · launch', 'Kinetic Labs', 'A scroll-driven reveal built from one turned form. The launch film is rendered from the same geometry.', ['2.4M campaign views', '1 asset set', '6 wks to launch'], 'work-kinetic.png'],
  ];
  for (const [k, n, d, stats, img] of cases) {
    s = slide(img, { frac: 0.52 });
    kick(s, k);
    T(s, n, M, 190, 40, SERIF, C.paper.replace('#', ''));
    T(s, d, M, 250, 12, SANS, C.body.replace('#', ''), { w: 5, lh: 1.45 });
    stats.forEach((t, j) => T(s, t, M, 400 + j * 34, 11, MONO, C.emberLit.replace('#', ''), { cs: 1 }));
    foot(s, 'rendered in blender · shipped in react');
  }

  s = slide(null);
  kick(s, 'Method');
  T(s, 'Blockout · Forge · Budget · Wire · Harden', M, 172, 30, SERIF, C.paper.replace('#', ''));
  [['Blockout', 'Camera path, scale and light locked before a texture exists.'],
   ['Forge', 'bpy builds the hero geometry, bakes lightmaps, exports glTF with LODs.'],
   ['Budget', 'Draco and KTX2 measured against a ceiling signed off up front.'],
   ['Wire', 'React Three Fiber scenes, scroll timelines, CMS bindings.'],
   ['Harden', 'GPU tiers, fallbacks, SEO-safe HTML, a Lighthouse gate in CI.']]
    .forEach(([h, t], i) => {
      T(s, `0${i + 1}`, M + i * 216, 296, 7.4, MONO, C.ember.replace('#', ''), { cs: 1.4 });
      T(s, h, M + i * 216, 312, 13, SERIF, C.paper.replace('#', ''));
      T(s, t, M + i * 216, 336, 9.4, SANS, C.body.replace('#', ''), { w: 1.9, lh: 1.35 });
    });
  s.addImage({ path: IMG('hero-2400x1600.png'), x: ex(M), y: ey(430), w: ex(1110), h: ey(210), sizing: { type: 'cover', w: ex(1110), h: ey(210) } });
  foot(s, 'the method');

  s = slide('square-1600x1600.png', { frac: 0.42 });
  kick(s, 'Engineering');
  T(s, 'Beauty that survives', M, 180, 40, SERIF, C.paper.replace('#', ''));
  T(s, 'a mid-range phone.', M, 226, 40, SERIF, C.emberLit.replace('#', ''));
  [['< 2.0 MB', 'first load, fonts and JS included'], ['60 fps', 'on a Pixel 6a / iPhone 12 tier GPU'],
   ['≤ 8', 'draw calls in the hero scene'], ['95+', 'Lighthouse, gated in CI']]
    .forEach(([v, t], i) => {
      const x = M + (i % 2) * 250;
      const y = 320 + Math.floor(i / 2) * 120;
      T(s, v, x, y, 26, SERIF, (i % 2 ? C.emberLit : C.paper).replace('#', ''));
      T(s, t, x, y + 34, 10, SANS, C.body.replace('#', ''), { w: 2.2 });
    });
  foot(s, 'the budget is the design');

  s = slide(null);
  kick(s, 'The studio');
  T(s, 'Blender hands,', M, 184, 40, SERIF, C.paper.replace('#', ''));
  T(s, 'browser discipline.', M, 230, 40, SERIF, C.emberLit.replace('#', ''));
  T(s, 'KILN is three people on purpose: an asset engineer writing bpy automation, a creative developer owning the WebGL layer, and a motion designer who ships the campaign with every build.', M, 310, 12.4, SANS, C.body.replace('#', ''), { w: 5.2, lh: 1.45 });
  T(s, 'Blender · bpy · Cycles · Three.js · R3F · gsap · Draco · KTX2 · Playwright', M, 460, 9, MONO, C.kiln.replace('#', ''), { cs: 1, w: 6.4 });
  s.addImage({ path: IMG('work-atelier.png'), x: EW - 4.9, y: 0, w: 4.9, h: EH, sizing: { type: 'cover', w: 4.9, h: EH } });
  foot(s, 'the studio');

  s = slide(null);
  kick(s, 'Rates');
  T(s, 'Fixed scope. Fixed number.', M, 176, 38, SERIF, C.paper.replace('#', ''));
  [['Spar', '$4,800', '2 weeks', 'One walkthrough scene, three art-directed stills, source handover.'],
   ['Kiln', '$12,500', '3–5 weeks', 'Up to five rooms, bpy pipeline, CMS, launch kit, thirty days of support.'],
   ['Firing', '$3,900 / mo', 'rolling', 'Two scenes per sprint, performance monitoring, monthly ad creative.']]
    .forEach(([n, price, when, what], i) => {
      const x = M + i * 358;
      const feat = i === 1;
      s.addShape(pptx.ShapeType.rect, {
        x: ex(x), y: ey(250), w: ex(330), h: ey(250),
        fill: { color: (feat ? '#14100E' : C.ink2).replace('#', '') },
        line: { color: (feat ? C.ember : C.rule).replace('#', ''), width: feat ? 1.2 : 0.6 },
      });
      T(s, n.toUpperCase(), x + 24, 270, 8, MONO, (feat ? C.emberLit : C.kiln).replace('#', ''), { cs: 2.2 });
      T(s, price, x + 24, 300, 24, SERIF, C.paper.replace('#', ''));
      T(s, when, x + 24, 330, 8, MONO, C.smoke.replace('#', ''));
      T(s, what, x + 24, 360, 10, SANS, C.body.replace('#', ''), { w: 2.9, lh: 1.35 });
    });
  foot(s, 'rates');

  s = slide('work-atelier.png', { frac: 0.5 });
  kick(s, 'Why it holds together');
  T(s, 'One set,', M, 184, 40, SERIF, C.paper.replace('#', ''));
  T(s, 'many pictures.', M, 230, 40, SERIF, C.emberLit.replace('#', ''));
  T(s, 'Every KILN build starts as a real Blender scene. That single decision pays three times: the site is lit correctly, the launch film is rendered from the same geometry, and the ad stills are photographs rather than illustrations. One asset, one invoice, three channels.', M, 310, 12.4, SANS, C.body.replace('#', ''), { w: 5, lh: 1.45 });
  foot(s, 'provenance');

  s = slide('work-meridian.png', { frac: 0.46 });
  kick(s, 'Next step');
  T(s, 'Send the product.', M, 230, 44, SERIF, C.paper.replace('#', ''));
  T(s, 'We send the room.', M, 280, 44, SERIF, C.emberLit.replace('#', ''));
  T(s, 'Within two working days: a fixed price, a camera path and a load budget. No discovery invoice, no retainer to start.', M, 360, 12.4, SANS, C.body.replace('#', ''), { w: 4.8, lh: 1.45 });
  T(s, 'studio@kiln.studio', M, 462, 16, SANS, C.emberLit.replace('#', ''));
  T(s, 'kiln.studio  ·  +44 20 7946 0812  ·  showroom at /showroom', M, 492, 8.4, MONO, C.kiln.replace('#', ''), { cs: 0.8, w: 6.4 });
  foot(s, 'kiln · 2026');

  const file = path.join(OUT, 'KILN-pitch-deck.pptx');
  await pptx.writeFile({ fileName: file });
  console.log('deck pptx:', file, (fs.statSync(file).size / 1024).toFixed(0) + ' KB', pptx.slides.length, 'slides');
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  await pdf();
  if (process.argv.includes('--pptx')) await pptx();
}

main().catch((e) => { console.error(e); process.exit(1); });
