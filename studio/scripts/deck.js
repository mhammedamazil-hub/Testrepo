// KILN — pitch deck (pptxgenjs). 16:9, 12 slides, photographic plates.
// DeckCraft's CLI could not be provisioned in this environment (GitHub release assets are
// blocked), so the deck is generated with pptxgenjs — same output format, no binary.
const path = require('path');
const fs = require('fs');
const PptxGenJS = require('pptxgenjs');

const ROOT = path.resolve(__dirname, '..');
// the deck uses 1400 px JPEG derivatives: the PNG plates are 2–4 MB each and a
// 30 MB deck is not a deck anybody can email
const ALIAS = {
  'keyart-1600x2000.png': 'keyart.jpg',
  'hero-2400x1600.png': 'hero.jpg',
  'square-1600x1600.png': 'square.jpg',
  'work-atelier.png': 'work-atelier.jpg',
  'work-meridian.png': 'work-meridian.jpg',
  'work-kinetic.png': 'work-kinetic.jpg',
  'kiln-icon.png': 'mark.png',
};
const IMG = (...p) => {
  const jpg = ALIAS[p[p.length - 1]] && path.join('/tmp/deckimg', ALIAS[p[p.length - 1]]);
  return jpg && fs.existsSync(jpg) ? jpg : path.join(ROOT, ...p);
};

const C = {
  ink: '0B0C0E',
  ink2: '121316',
  paper: 'F2EDE4',
  ember: 'D8542A',
  emberLit: 'EE7541',
  kiln: '8A8578',
  smoke: '55544F',
  rule: '2A2B2F',
};

const W = 13.333;
const H = 7.5;
const M = 0.85; // left margin

async function main() {
  const pptx = new PptxGenJS();
  pptx.layout = 'LAYOUT_16x9';
  pptx.author = 'KILN';
  pptx.company = 'KILN — interactive architecture';
  pptx.title = 'KILN — rooms, not pages';

  const slide = (bg = C.ink) => {
    const s = pptx.addSlide();
    s.background = { color: bg };
    return s;
  };

  const eyebrow = (s, t, x = M, y = 0.62, color = C.kiln) =>
    s.addText(t.toUpperCase(), {
      x, y, w: 9, h: 0.3, fontSize: 9.5, color, fontFace: 'Consolas', charSpacing: 3.2,
    });

  // display type: Georgia is the nearest widely available serif to Instrument Serif
  const display = (s, t, x, y, size, { w = 10.5, color = C.paper, italic = false, h = 1.3 } = {}) =>
    s.addText(t, {
      x, y, w, h, fontSize: size, color, fontFace: 'Georgia', italic,
      charSpacing: -0.4, lineSpacingMultiple: 0.94,
    });

  const body = (s, t, x, y, w = 5.0, size = 12.5) =>
    s.addText(t, { x, y, w, fontSize: size, color: 'C9C3B6', fontFace: 'Arial', lineSpacingMultiple: 1.45 });

  // 4.x has addShape, not addLine: a hairline is a zero-height rectangle
  const rule = (s, x, y, w = 11.6, color = C.rule) =>
    s.addShape(pptx.ShapeType.rect, { x, y, w, h: 0.008, fill: { color } });

  /* ── 01 cover */
  let s = slide();
  s.addImage({
    path: IMG('brand', 'renders', 'keyart-1600x2000.png'),
    x: 6.2, y: 0, w: 7.13, h: H,
    sizing: { type: 'cover', w: 7.13, h: H },
  });
  s.addImage({ path: IMG('brand', 'logo', 'kiln-icon.png'), x: M, y: 0.85, w: 0.62, h: 0.62 });
  s.addText('KILN', {
    x: M + 0.8, y: 0.88, w: 4, h: 0.6, fontSize: 26, color: C.paper,
    fontFace: 'Georgia', charSpacing: 6,
  });
  display(s, 'Rooms,', M, 3.05, 54, { w: 5.6 });
  display(s, 'not pages.', M, 3.85, 54, { w: 5.6, color: C.emberLit, italic: true });
  rule(s, M, 5.12, 4.9, '3A3A3E');
  body(s, 'An interactive architecture studio. We model the space in Blender, light it with bpy and ship it in React — under two megabytes, sixty frames on a phone.', M, 5.3, 5.1, 12);
  s.addText('Pitch deck · 2026 · studio@kiln.studio', {
    x: M, y: 6.72, w: 6, h: 0.3, fontSize: 9.5, color: C.smoke, fontFace: 'Consolas', charSpacing: 1.4,
  });

  /* ── 02 the problem */
  s = slide();
  eyebrow(s, 'The problem');
  display(s, 'A page is a photograph\nof a place.', M, 1.1, 40, { w: 7.2 });
  body(s, 'Customers are asked to judge size, material and finish from a flat image — then they guess wrong at the moment they would have bought. Video does not help: it cannot be explored. And most “3D websites” are forty-megabyte showreels that melt a phone on 4G.', M, 3.9, 6.2, 13);

  ['No sense of scale', 'No sense of material', 'No sense of light'].forEach((t, i) => {
    const y = 5.5 + i * 0.42;
    s.addShape(pptx.ShapeType.rect, { x: M, y: y + 0.06, w: 0.16, h: 0.015, fill: { color: C.ember } });
    s.addText(t, { x: M + 0.34, y, w: 4, h: 0.34, fontSize: 12, color: 'C9C3B6', fontFace: 'Arial' });
  });

  s.addImage({
    path: IMG('brand', 'renders', 'hero-2400x1600.png'),
    x: 7.5, y: 1.1, w: 5.0, h: 5.0,
    sizing: { type: 'cover', w: 5.0, h: 5.0 },
  });

  /* ── 03 what we make */
  s = slide();
  eyebrow(s, 'The work');
  display(s, 'Three rooms,\nthree trades.', M, 1.0, 38);
  rule(s, M, 2.85, 11.6);
  const offers = [
    ['Commerce', 'A gallery you can shop', 'Every piece is a real object: turn it, place it, buy it. Product photography replaced by a room.'],
    ['Property', 'Every unit walkable', 'Sun studies baked in Blender, forty-eight apartments on one link, no render farm.'],
    ['Launch', 'A moment, not a page', 'A scroll-driven reveal that turns a spec sheet into something people forward.'],
  ];
  offers.forEach(([tag, head, text], i) => {
    const x = M + i * 3.9;
    s.addText(tag.toUpperCase(), { x, y: 3.1, w: 3.4, h: 0.3, fontSize: 9, color: C.ember, fontFace: 'Consolas', charSpacing: 2.4 });
    s.addText(head, { x, y: 3.45, w: 3.5, h: 0.6, fontSize: 19, color: C.paper, fontFace: 'Georgia' });
    body(s, text, x, 4.2, 3.4, 11.5);
  });

  /* ── 04–06 case studies */
  const cases = [
    ['Atelier Nova', 'COMMERCE · 2025', 'A flagship where every ceramic piece is a real object you turn, place and buy.', '+38% add-to-cart', 'work-atelier.png'],
    ['Meridian Towers', 'PROPERTY · 2025', 'Forty-eight apartments with sun studies baked in Blender, walkable on a mid-range phone.', '3.1× session length', 'work-meridian.png'],
    ['Kinetic Labs', 'LAUNCH · 2026', 'A scroll-driven reveal that turns a spec sheet into a launch moment.', '2.4M campaign views', 'work-kinetic.png'],
  ];

  for (const [name, tag, text, stat, img] of cases) {
    s = slide();
    s.addImage({
      path: IMG('brand', 'renders', img), x: 6.9, y: 0, w: W - 6.9, h: H,
      sizing: { type: 'cover', w: W - 6.9, h: H },
    });
    eyebrow(s, tag, M, 1.5);
    display(s, name, M, 1.95, 40, { w: 5.4 });
    body(s, text, M, 3.35, 4.9, 13);
    s.addText(stat, {
      x: M, y: 5.5, w: 5, h: 0.5, fontSize: 17, color: C.emberLit, fontFace: 'Consolas',
    });
    s.addText('Rendered in Blender · shipped in React', {
      x: M, y: 6.0, w: 5, h: 0.3, fontSize: 9.5, color: C.smoke, fontFace: 'Consolas',
    });
  }

  /* ── 07 method */
  s = slide();
  eyebrow(s, 'Method');
  display(s, 'Blockout → Forge → Budget → Wire → Harden', M, 1.0, 26, { w: 11.6 });
  const steps = [
    ['Blockout', 'Camera path, scale and light locked before any texture exists.'],
    ['Forge', 'bpy scripts build hero geometry, bake lightmaps, export glTF with LODs.'],
    ['Budget', 'Draco + KTX2 against a first-load ceiling signed off up front.'],
    ['Wire', 'React Three Fiber scenes, scroll timelines, CMS bindings.'],
    ['Harden', 'GPU tiers, fallbacks, SEO-safe HTML, Lighthouse gate in CI.'],
  ];
  steps.forEach(([h, t], i) => {
    const x = M + i * 2.34;
    s.addShape(pptx.ShapeType.rect, { x, y: 2.75, w: 0.14, h: 0.015, fill: { color: C.ember } });
    s.addText(`0${i + 1}`, { x, y: 2.95, w: 1, h: 0.3, fontSize: 9, color: C.ember, fontFace: 'Consolas' });
    s.addText(h, { x, y: 3.25, w: 2.1, h: 0.4, fontSize: 15, color: C.paper, fontFace: 'Georgia' });
    body(s, t, x, 3.7, 2.05, 10.5);
  });
  s.addImage({
    path: IMG('brand', 'renders', 'hero-2400x1600.png'),
    x: M, y: 5.35, w: 11.6, h: 1.75,
    sizing: { type: 'cover', w: 11.6, h: 1.75 },
  });

  /* ── 08 performance */
  s = slide();
  eyebrow(s, 'Engineering');
  display(s, 'Beauty that survives\na mid-range phone.', M, 1.0, 34, { w: 7.4 });
  const nums = [
    ['< 2.0 MB', 'first load, fonts and JS included'],
    ['60 fps', 'on a Pixel 6a / iPhone 12 tier GPU'],
    ['≤ 8', 'draw calls in the hero scene'],
    ['95+', 'Lighthouse, gated in CI'],
  ];
  nums.forEach(([n, t], i) => {
    const x = M + (i % 2) * 3.3;
    const y = 3.6 + Math.floor(i / 2) * 1.5;
    s.addText(n, { x, y, w: 3.0, h: 0.6, fontSize: 27, color: i % 2 ? C.emberLit : C.paper, fontFace: 'Georgia' });
    body(s, t, x, y + 0.62, 2.9, 10.5);
  });
  s.addImage({
    path: IMG('brand', 'renders', 'square-1600x1600.png'),
    x: 8.4, y: 1.0, w: 4.4, h: 5.7,
    sizing: { type: 'cover', w: 4.4, h: 5.7 },
  });

  /* ── 09 the studio */
  s = slide();
  eyebrow(s, 'The studio');
  display(s, 'Blender hands,\nbrowser discipline.', M, 1.0, 36, { w: 6.4 });
  body(s, 'KILN is small on purpose: an asset engineer writing bpy automation, a creative developer owning the WebGL layer, and a motion designer who ships the campaign with every build. One pipeline, three people, no handoffs to a render farm.', M, 3.3, 6.0, 13);
  const stack = ['Blender', 'bpy', 'Cycles', 'Three.js', 'React Three Fiber', 'gsap', 'Draco', 'KTX2', 'Playwright'];
  stack.forEach((t, i) => {
    s.addText(t, {
      x: M + (i % 3) * 2.05, y: 5.35 + Math.floor(i / 3) * 0.5, w: 1.9, h: 0.34,
      fontSize: 9.5, color: C.kiln, fontFace: 'Consolas', charSpacing: 1.2,
      shape: pptx.ShapeType.roundRect, rectRadius: 0.04, line: { color: C.rule, width: 0.6 }, fill: { color: C.ink2 },
      align: 'center',
    });
  });

  /* ── 10 rates */
  s = slide();
  eyebrow(s, 'Rates');
  display(s, 'Fixed scope.\nFixed number.', M, 1.0, 34);
  const rows = [
    [{ text: ' ', options: { fill: { color: C.ink2 } } },
     { text: 'Spar', options: { bold: true, color: C.paper, fill: { color: C.ink2 } } },
     { text: 'Kiln', options: { bold: true, color: C.emberLit, fill: { color: C.ink2 } } },
     { text: 'Firing', options: { bold: true, color: C.paper, fill: { color: C.ink2 } } }],
    ['Price', '$4,800', '$12,500', '$3,900 / mo'],
    ['Scenes', '1', 'up to 5', '2 per sprint'],
    ['bpy pipeline', '—', 'included', 'included'],
    ['CMS + analytics', '—', 'included', 'included'],
    ['Launch kit', 'stills', 'stills + loop', 'monthly'],
    ['Delivery', '2 weeks', '3–5 weeks', 'rolling'],
  ];
  s.addTable(rows, {
    x: M, y: 3.5, w: 11.6, colW: [2.8, 2.9, 2.9, 3.0],
    border: { type: 'solid', color: C.rule, pt: 0.75 },
    fontFace: 'Arial', fontSize: 11, color: 'C9C3B6', valign: 'middle', rowH: 0.42,
  });

  /* ── 11 why us */
  s = slide();
  eyebrow(s, 'Why it holds together');
  display(s, 'One set, many pictures.', M, 1.0, 34, { w: 11 });
  body(s, 'Every KILN build starts as a real Blender scene. That single decision pays three times: the site is lit correctly, the launch film is rendered from the same geometry, and the ad stills are photographs rather than illustrations. One asset, one invoice, three channels.', M, 3.2, 5.9, 13);
  ['site', 'film', 'ads'].forEach((t, i) => {
    const x = 7.2 + (i % 2) * 2.4;
    const y = 2.2 + i * 1.75;
    s.addImage({
      path: IMG('brand', 'renders', ['work-atelier.png', 'work-kinetic.png', 'square-1600x1600.png'][i]),
      x, y, w: 2.2, h: 2.2, sizing: { type: 'cover', w: 2.2, h: 2.2 },
    });
    s.addText(t, { x, y: y + 2.24, w: 2.2, h: 0.24, fontSize: 8.5, color: C.smoke, fontFace: 'Consolas', charSpacing: 1.4 });
  });

  /* ── 12 next */
  s = slide();
  s.addImage({
    path: IMG('brand', 'renders', 'work-meridian.png'), x: 7.9, y: 0, w: W - 7.9, h: H,
    sizing: { type: 'cover', w: W - 7.9, h: H },
  });
  eyebrow(s, 'Next step', M, 1.2);
  display(s, 'Send the product.\nWe’ll send the room.', M, 1.7, 34, { w: 6.2 });
  body(s, 'Within two working days: a fixed price, a camera path and a load budget. No discovery invoice, no retainer to start.', M, 3.9, 5.7, 13);
  s.addText('studio@kiln.studio', { x: M, y: 5.3, w: 6, h: 0.4, fontSize: 17, color: C.emberLit, fontFace: 'Consolas' });
  s.addText('kiln.studio · showroom at /showroom', { x: M, y: 5.78, w: 6, h: 0.3, fontSize: 10, color: C.smoke, fontFace: 'Consolas' });

  const out = path.join(ROOT, 'deck', 'KILN-pitch-deck.pptx');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  await pptx.writeFile({ fileName: out });
  console.log('deck:', out, (fs.statSync(out).size / 1024).toFixed(0) + ' KB', pptx.slides.length, 'slides');
}

main().catch((e) => { console.error(e); process.exit(1); });
