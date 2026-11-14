// KILN — brand guidelines. A4 landscape, 10 pages, generated from the same sources
// as everything else: the mark's SVG geometry, the Cycles plates, the three faces.
//
// A guidelines document is where a studio proves it made decisions rather than
// choices. Every rule here is stated with the number it comes from.
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const { PDFDocument, rgb } = require('pdf-lib');
const fontkit = require('@pdf-lib/fontkit');
const { ROOT } = require('./lib');

const W = 842;
const H = 595;
const M = 52;

const C = {
  ink: '#0B0C0E', ink2: '#121316', paper: '#F2EDE4', ember: '#D8542A',
  emberLit: '#EE7541', kiln: '#8A8578', smoke: '#55544F', body: '#C1BBAF', rule: '#26272B',
};

const hex = (h) => {
  const s = h.replace('#', '');
  return rgb(parseInt(s.slice(0, 2), 16) / 255, parseInt(s.slice(2, 4), 16) / 255, parseInt(s.slice(4, 6), 16) / 255);
};

const R = (f) => path.join(ROOT, 'brand', 'renders', f);
const L = (f) => path.join(ROOT, 'brand', 'logo', f);
const E = (f) => path.join(ROOT, 'brand', 'exports', f);

async function main() {
  const doc = await PDFDocument.create();
  doc.setTitle('KILN — brand guidelines');
  doc.setAuthor('KILN');
  doc.setSubject('Mark, lockups, type, colour, image, motion, voice');
  doc.registerFontkit(fontkit);

  const F = (f) => doc.embedFont(fs.readFileSync(path.join(ROOT, 'fonts', f)), { subset: true });
  const serif = await F('instrument-serif.ttf');
  const sans = await F('inter-tight-400.ttf');
  const sansM = await F('inter-tight-500.ttf');
  const mono = await F('jetbrains-mono.ttf');

  const png = async (file, w, h, pos = 'centre') =>
    doc.embedPng(await sharp(file).resize({ width: Math.round(w), height: Math.round(h), fit: 'cover', position: pos }).png().toBuffer());
  const fit = async (file, w) =>
    doc.embedPng(await sharp(file).resize({ width: Math.round(w), withoutEnlargement: false }).png().toBuffer());

  const page = (bg = C.ink) => {
    const p = doc.addPage([W, H]);
    p.drawRectangle({ x: 0, y: 0, width: W, height: H, color: hex(bg) });
    return p;
  };
  const T = (p, t, x, yTop, size, font, color, opts = {}) =>
    p.drawText(t, { x, y: H - yTop, size, font, color: hex(color), ...opts });
  const kick = (p, t, yTop = 56, color = C.ember) =>
    T(p, t.toUpperCase(), M, yTop, 7.2, mono, color, { characterSpacing: 2.1 });
  const body = (p, t, x, yTop, w, size = 9, color = C.body, lh = 1.62) =>
    T(p, t, x, yTop, size, sans, color, { maxWidth: w, lineHeight: size * lh });
  const display = (p, t, x, yTop, size, color = C.paper) =>
    T(p, t, x, yTop, size, serif, color, { lineHeight: size * 0.98 });
  const rule = (p, x, yTop, w, color = C.rule) =>
    p.drawRectangle({ x, y: H - yTop, width: w, height: 0.7, color: hex(color) });
  const foot = (p, t, n) => {
    T(p, t.toUpperCase(), M, H - 30, 6.4, mono, C.smoke, { characterSpacing: 1.5 });
    const s = String(n).padStart(2, '0');
    T(p, s, W - M - mono.widthOfTextAtSize(s, 6.4), H - 30, 6.4, mono, C.smoke, { characterSpacing: 1.2 });
  };

  /* 01 cover */
  let p = page();
  p.drawImage(await png(R('keyart-1600x2000.png'), 330, H, 'centre'), { x: W - 330, y: 0, width: 330, height: H });
  p.drawRectangle({ x: W - 330, y: 0, width: 120, height: H, color: hex(C.ink), opacity: 0.9 });
  p.drawImage(await fit(E('mark-512.png'), 30), { x: M, y: H - 90, width: 30, height: 30 });
  T(p, 'KILN', M + 44, 88, 16, serif, C.paper, { characterSpacing: 2.8 });
  display(p, 'Brand', M, 300, 54);
  display(p, 'guidelines', M, 352, 54, C.emberLit);
  rule(p, M, 392, 120, '#3A3A3E');
  body(p, 'Version 1 · 2026. Every rule in this document is derived from a number: the arch is a true semicircle, the tracking is 0.06 em, the clear space is 0.16 of the block. Nothing here is a preference.', M, 416, 330, 9.4);
  foot(p, 'kiln · interactive architecture', 1);

  /* 02 the mark */
  p = page();
  kick(p, '01 · the mark');
  display(p, 'One arch. Nothing else.', M, 108, 32);
  p.drawImage(await fit(E('mark-512.png'), 150), { x: M, y: H - 330, width: 150, height: 150 });
  body(p, 'The mark is a section through a kiln wall. A 1000-unit block with a 300-unit opening cut through it. The head is a true semicircle: radius equals half the opening, so it springs 120 units above the block centre. The legs run past the foot of the block, because a kiln mouth is a passage, not a window.', M + 190, 176, 250, 9.6);
  body(p, 'It is the same arch the studio renders and the same arch the studio sells. That is the whole idea, and it is why there is no second mark.', M + 190, 268, 250, 9.6);
  p.drawImage(await fit(L('kiln-construction.png'), 400), { x: M + 470, y: H - 380, width: 400, height: 234 });
  T(p, 'CONSTRUCTION SHEET · 1:1', M + 470, 232, 6.4, mono, C.kiln, { characterSpacing: 1.4 });
  rule(p, M, 400, W - M * 2);
  [['Never', 'outline it, glow it, bevel it, or place it on a gradient.'],
   ['Ink field', 'paper door. That is the mark. Paper inverts it exactly.'],
   ['Ember', 'is a signal, never a field.'],
   ['Clear space', '0.16 × the block on all sides, with no type or rule inside it.']]
    .forEach(([a, b], i) => {
      const x = M + i * 186;
      T(p, a.toUpperCase(), x, 424, 6.6, mono, C.ember, { characterSpacing: 1.6 });
      body(p, b, x, 440, 168, 8.6);
    });
  foot(p, '01 · the mark', 2);

  /* 03 scale */
  p = page();
  kick(p, '01 · the mark, at size');
  display(p, 'It has to survive 16 px.', M, 108, 30);
  const scale = [[128, 'avatar'], [64, 'favicon'], [32, 'favicon 32'], [16, 'browser tab']];
  const markBuf = fs.readFileSync(E('mark-512.png'));
  for (const [i, [px, label]] of scale.entries()) {
    const x = M + i * 150;
    const im = await doc.embedPng(await sharp(markBuf).resize(px).png().toBuffer());
    p.drawImage(im, { x, y: H - 260, width: px, height: px });
    T(p, `${px} px`, x, 290, 7.6, mono, C.paper, { characterSpacing: 0.8 });
    T(p, label.toUpperCase(), x, 306, 6.4, mono, C.smoke, { characterSpacing: 1.2 });
  }
  rule(p, M, 352, W - M * 2);
  body(p, 'Below 32 px the door is widened to 62% of the block and the block is dropped, because at 16 px a 30% opening fills in and the mark becomes a white square. This is the only permitted deviation from the construction.', M, 376, 340, 9.4);
  body(p, 'At favicon size the field is ink and the door is paper, so the tab reads as a hole rather than a tile. The favicon in this repo is drawn at 64 px and scaled down, never the reverse.', M + 380, 376, 300, 9.4);
  p.drawImage(await fit(E('favicon-32.png'), 128), { x: W - M - 128, y: H - 470, width: 128, height: 128 });
  T(p, 'favicon · 32 px actual size, shown 4×', W - M - 128, 486, 6.4, mono, C.kiln, { characterSpacing: 1.2 });
  foot(p, '01 · the mark, at size', 3);

  /* 04 lockups */
  p = page();
  kick(p, '02 · lockups');
  display(p, 'Set on the baseline, never floated.', M, 100, 26);
  body(p, 'The mark sits at cap height with its foot on the wordmark baseline. Clear space between block and wordmark is 0.55 cap. An ember hairline — 0.035 cap wide, 1.34 cap tall — separates the descriptor, which is optically centred on the cap height rather than mathematically centred on the bounding box.', M, 128, 540, 9);
  p.drawImage(await fit(E('lockup-2400.png'), 480), { x: M, y: H - 320, width: 480, height: 98 });
  // nothing else may occupy the primary lockup's box
  T(p, 'PRIMARY · INK', M, 214, 6.4, mono, C.kiln, { characterSpacing: 1.6 });
  p.drawRectangle({ x: M, y: H - 452, width: 480, height: 100, color: hex(C.paper) });
  p.drawImage(await fit(E('lockup-ink-2400.png'), 440), { x: M + 20, y: H - 438, width: 440, height: 86 });
  T(p, 'REVERSE · PAPER', M, 462, 6.4, mono, C.kiln, { characterSpacing: 1.6 });
    // wordmark specimen, right column, clear of the primary lockup's box
  p.drawImage(await fit(E('wordmark-2400.png'), 230), { x: 566, y: H - 248, width: 230, height: 69 });
  T(p, 'WORDMARK · +0.06 EM', 566, 264, 6.4, mono, C.kiln, { characterSpacing: 1.4 });
  body(p, 'The wordmark is the mark\'s companion, not a substitute: where the lockup will not fit, the wordmark stands alone, and the mark is never stacked above it.', 566, 282, 224, 7.6, C.kiln);
  foot(p, '02 · lockups', 4);

  /* 05 type */
  p = page();
  kick(p, '03 · type');
  display(p, 'A serif with a temper, a grotesque with none.', M, 108, 26);
  T(p, 'Aa', M, 240, 96, serif, C.emberLit);
  T(p, 'Aa', M + 260, 240, 96, sans, C.paper);
  T(p, 'Aa', M + 470, 240, 96, mono, C.kiln);
  const cols = [
    ['INSTRUMENT SERIF', 'Display only. Headlines, the wordmark, prices. High-contrast didone skeleton with a sharp foot serif: holds at 104 px, stays out of the way at 28. Never below 28 px, never all caps, never tracked except +0.06 em in the wordmark and −0.01 em in headlines.'],
    ['INTER TIGHT', 'Body, UI, captions. 400 for reading, 500 for interface labels. Measure 62–68 characters. Leading 1.45 for body, 1.3 for UI. The only face permitted below 18 px.'],
    ['JETBRAINS MONO', 'Labels, data, provenance notes. 10–11 px at 0.16–0.22 em tracking, always uppercase. It exists to sound like a specification, not like a brand.'],
  ];
  cols.forEach(([h, t], i) => {
    const x = M + i * 250;
    T(p, h, x, 300, 6.6, mono, C.ember, { characterSpacing: 1.8 });
    body(p, t, x, 316, 226, 8.6);
  });
  rule(p, M, 400, W - M * 2);
  body(p, 'Scale: h1 clamp(46px, 7.2vw, 104px) / 0.94 · h2 clamp(34px, 4.6vw, 64px) / 1.02 · lede clamp(16px, 1.35vw, 19px) / 1.55 · label 10.5px / 0.22 em.', M, 424, 700, 8.8);
  foot(p, '03 · type', 5);

  /* 06 colour */
  p = page();
  kick(p, '04 · colour');
  display(p, 'Warm ink, cold nothing.', M, 108, 30);
  body(p, 'There is no blue in this palette. Everything sits between 20° and 40° hue: the black is warm, the white is cream, and the one saturated colour is the temperature of a firing.', M, 140, 700, 9.2);
  const swatches = [
    ['Ink', '0B0C0E', 'Field. Every surface starts here.'],
    ['Paper', 'F2EDE4', 'Type on ink, and the door of the mark.'],
    ['Ember', 'D8542A', 'One per screen. Links, active states.'],
    ['Ember lit', 'EE7541', 'Hover; emphasis inside a headline.'],
    ['Kiln', '8A8578', 'Secondary type, rules, metadata.'],
    ['Smoke', '55544F', 'Disabled, captions on paper.'],
  ];
  swatches.forEach(([name, h, use], i) => {
    const x = M + i * 122;
    p.drawRectangle({ x, y: H - 268, width: 104, height: 64, color: hex(h) });
    T(p, name, x, 292, 8.4, sansM, C.paper);
    T(p, `#${h}`, x, 306, 6.4, mono, C.emberLit, { characterSpacing: 0.6 });
    body(p, use, x, 322, 102, 7.2, C.kiln);
  });
  // surface study sits below the swatches on its own baseline, caption underneath
  p.drawImage(await png(R('detail-2400x1350.png'), 738, 128, 'centre'), { x: M, y: 80, width: 738, height: 128 });
  T(p, 'SURFACE STUDY · PLASTER, TERRACOTTA, DAYLIGHT · CYCLES, 512 SAMPLES', M, 372, 6.4, mono, C.kiln, { characterSpacing: 1.3 });
  foot(p, '04 · colour', 6);

  /* 07 image */
  p = page();
  kick(p, '05 · image');
  display(p, 'Photographs of buildings that do not exist.', M, 108, 26);
  body(p, 'Every image in this system comes out of Cycles at 512 samples with no post beyond a crop. One key at 35° elevation, one cool fill, one ember rim. Surfaces carry a noise bump at 0.003–0.008 so plaster breaks up under raking light. No gradients, no glows, no composited light leaks: those are the tell of a synthetic image.', M, 140, 380, 9);
  const plates = ['work-atelier.png', 'work-meridian.png', 'work-kinetic.png'];
  for (const [i, f] of plates.entries()) {
    p.drawImage(await png(R(f), 190, 238, 'centre'), { x: M + i * 202, y: 56, width: 190, height: 238 });
  }
  T(p, 'CASE PLATES · 1400 × 1750 · 56 SAMPLES', M, 306, 6.4, mono, C.kiln, { characterSpacing: 1.3 });
  body(p, 'One set, many pictures: the site, the film and the ads all come from the same scene, so the brand stays consistent by construction rather than by supervision.', M + 600, 176, 148, 8.4);
  foot(p, '05 · image', 7);

  /* 08 motion */
  p = page();
  kick(p, '06 · motion');
  display(p, 'Slow enough to be architecture.', M, 108, 28);
  body(p, 'One easing curve, everywhere: cubic-bezier(0.16, 1, 0.3, 1). Entrances 700–900 ms, exits 320 ms. Nothing bounces, nothing overshoots, nothing spins. Camera moves are dolly and crane only. Reveals are masked from the bottom: the subject is uncovered, never pushed in.', M, 140, 400, 9.2);
  body(p, 'Under prefers-reduced-motion every transform becomes a 200 ms opacity fade and the camera holds still. This is not optional and it is the first thing to check in review.', M, 232, 400, 9.2);
  p.drawImage(await png(R('square-1600x1600.png'), 208, 208, 'centre'), { x: W - M - 208, y: H - 368, width: 208, height: 208 });
  T(p, 'IDENTITY STING · 6 S · 24 FPS · THE ARCH OPENS FROM THE MARK', W - M - 208, 386, 6.4, mono, C.kiln, { characterSpacing: 1.0, maxWidth: 208 });
  const moves = [['draw', '0–1.0 s', 'the ember hairline draws to the lockup'], ['open', '1.0–2.6 s', 'the door opens onto the rendered room'], ['hold', '2.6–3.8 s', 'a slow push inside the arch'], ['close', '3.8–5.1 s', 'the arch contracts back to the mark'], ['settle', '5.1–6.0 s', 'the door comes to rest on the baseline']];
  moves.forEach(([n, t, d], i) => {
    const y = 340 + i * 34;
    T(p, n.toUpperCase(), M, y, 6.6, mono, C.ember, { characterSpacing: 1.6 });
    T(p, t, M + 90, y, 6.6, mono, C.kiln, { characterSpacing: 1.0 });
    body(p, d, M + 180, y - 1, 380, 8.4);
  });
  foot(p, '06 · motion', 8);

  /* 09 voice */
  p = page();
  kick(p, '07 · voice');
  display(p, 'Specify. Do not enthuse.', M, 108, 28);
  body(p, 'Write like the person who built it. Numbers, materials, constraints. If a sentence could appear on any studio site in the world, it is not a sentence for this one.', M, 140, 700, 9.2);
  rule(p, M, 200, W - M * 2);
  const rows = [
    ['Write', 'Not'],
    ['Under two megabytes, sixty frames on a phone.', 'Immersive experiences that push boundaries.'],
    ['Three to five weeks, fixed price, camera path agreed first.', 'A bespoke journey tailored to your brand.'],
    ['Turn it. Place it. Buy it.', 'Seamless, delightful, frictionless commerce.'],
    ['Every KILN build begins as a room in Blender.', 'Where creativity meets technology.'],
  ];
  rows.forEach(([a, b], i) => {
    const y = 232 + i * 44;
    T(p, a, M, y, i ? 11 : 6.6, i ? sans : mono, i ? C.paper : C.ember, i ? {} : { characterSpacing: 1.8 });
    T(p, b, M + 430, y, i ? 11 : 6.6, i ? sans : mono, i ? C.smoke : C.ember, i ? {} : { characterSpacing: 1.8 });
  });
  rule(p, M, 460, W - M * 2);
  body(p, 'Tiers are the process in order: a spar is the small fire you start with, the kiln is where the work is fired, firing is the ongoing cycle. Spar $4,800 · Kiln $12,500 · Firing $3,900 per month.', M, 480, 700, 8.8);
  foot(p, '07 · voice', 9);

  /* 10 assets */
  p = page();
  kick(p, '08 · what exists');
  display(p, 'Everything is generated.', M, 108, 28);
  body(p, 'There is no stock imagery, no hand-drawn mark and no mock-up in this identity. Each file below is produced by a script in scripts/, and each script is listed with what it writes.', M, 140, 700, 9.2);
  rule(p, M, 196, W - M * 2);
  const rows2 = [
    ['wordmark.js', 'mark, wordmark, lockups, favicons, this page\'s construction sheet'],
    ['kiln_render.py', 'hero, key art, square, detail — Cycles, bpy'],
    ['kiln_work.py', 'three case plates, 1400 × 1750'],
    ['kiln_posters.py', 'posters, social set, key-art card, avatars'],
    ['kiln_motion.py', 'the 6 s sting: mp4, webm, gif, poster'],
    ['portfolio.js', 'portfolio PDF, 9 pages'],
    ['deck.js', 'pitch deck PDF, 12 slides'],
    ['onepager.js', 'one-pager PDF'],
  ];
  rows2.forEach(([a, b], i) => {
    const y = 224 + i * 30;
    T(p, a, M, y, 8.4, mono, C.emberLit, { characterSpacing: 0.4 });
    T(p, b, M + 170, y, 8.4, sans, C.body);
  });
  rule(p, M, 480, W - M * 2);
  T(p, 'studio@kiln.studio  ·  kiln.studio  ·  +44 20 7946 0812', M, 504, 8, mono, C.kiln, { characterSpacing: 0.8 });
  foot(p, '08 · what exists', 10);

  const out = path.join(ROOT, 'docs', 'KILN-brand-guidelines.pdf');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, await doc.save());
  fs.copyFileSync(out, path.join(ROOT, 'site', 'assets', 'docs', 'kiln-brand-guidelines.pdf'));
  console.log('guidelines:', out, (fs.statSync(out).size / 1024).toFixed(0) + ' KB', doc.getPageCount(), 'pages');
}

main().catch((e) => { console.error(e); process.exit(1); });
