// LUMENFORGE — pitch deck (pptxgenjs)
const path = require('path');
const fs = require('fs');
const PptxGenJS = require('pptxgenjs');

const ROOT = path.resolve(__dirname, '..');
const IMG = (...p) => path.join(ROOT, ...p);

const C = {
  ink: '06070B',
  panel: '0C0F17',
  bone: 'EDE7DA',
  forge: 'FF6B2C',
  arc: '22E8C8',
  muted: '8A93A6',
  line: '1B2130',
};

const W = 13.333, H = 7.5;

async function main() {
  const pptx = new PptxGenJS();
  pptx.layout = 'LAYOUT_16x9';
  pptx.author = 'LUMENFORGE';
  pptx.company = 'LUMENFORGE Interactive 3D Studio';
  pptx.title = 'LUMENFORGE — interactive 3D websites';

  const bg = (slide, color = C.ink) => {
    slide.background = { color };
  };

  const kicker = (slide, text, x = 0.7, y = 0.55) =>
    slide.addText(text.toUpperCase(), {
      x, y, w: 8, h: 0.34, fontSize: 10, color: C.arc, charSpacing: 3, bold: true, fontFace: 'Consolas',
    });

  const title = (slide, text, x = 0.7, y = 0.95, size = 40, w = 11.6, color = C.bone) =>
    slide.addText(text, { x, y, w, h: 1.5, fontSize: size, bold: true, color, fontFace: 'Arial', lineSpacingMultiple: 0.92 });

  const body = (slide, text, x, y, w = 5.6, size = 13, color = C.muted) =>
    slide.addText(text, { x, y, w, fontSize: size, color, fontFace: 'Arial', lineSpacingMultiple: 1.35 });

  const rule = (slide, x, y, w = 11.9) =>
    slide.addShape(pptx.ShapeType.line, { x, y, w, h: 0, line: { color: C.line, width: 1 } });

  // clean 3D plates (no baked type) so slides can carry their own typography
  const plate = (slide, name, x, y, w, h) =>
    slide.addImage({ path: IMG('portfolio', 'plates', `${name}.png`), x, y, w, h, sizing: { type: 'cover', w, h } });

  const chip = (slide, text, x, y, color = C.arc) =>
    slide.addText(text.toUpperCase(), {
      x, y, w: text.length * 0.095 + 0.3, h: 0.32, fontSize: 9, color, fontFace: 'Consolas', charSpacing: 2,
      align: 'center', shape: pptx.ShapeType.roundRect, rectRadius: 0.16, line: { color, width: 0.75 }, fill: { color: C.ink },
    });

  /* ---------- 1. cover ---------- */
  let s = pptx.addSlide();
  bg(s);
  plate(s, 'cover', 6.6, 0, 6.73, 7.5);
  s.addImage({ path: IMG('brand', 'exports', 'logo-mark-512.png'), x: 0.7, y: 0.7, w: 0.95, h: 0.95 });
  s.addText('LUMENFORGE', { x: 0.7, y: 2.05, w: 6.4, h: 0.9, fontSize: 40, bold: true, color: C.bone, charSpacing: 3 });
  s.addText('WEBSITES YOU CAN WALK THROUGH', { x: 0.72, y: 2.95, w: 6.2, h: 0.4, fontSize: 12, color: C.arc, charSpacing: 4 });
  rule(s, 0.7, 3.55, 5.9);
  body(s, 'An interactive 3D studio building launch-ready 3D commerce, real-estate and product sites with Blender (bpy), Three.js and React.', 0.7, 3.8, 5.9, 14, C.muted);
  s.addText('Pitch deck · 2026 · forge@lumenforge.studio', { x: 0.7, y: 6.65, w: 6, h: 0.3, fontSize: 10, color: '5F6878', fontFace: 'Consolas' });

  /* ---------- 2. problem ---------- */
  s = pptx.addSlide();
  bg(s);
  kicker(s, 'The problem');
  title(s, 'The web is still flat, and flat is expensive.', 0.7, 1.0, 38, 11.5);
  const probs = [
    ['Visitors cannot imagine scale', 'Static product shots force customers to guess size, material and finish. Guessing is where carts die.'],
    ['Video is a dead end', 'A 4 MB hero video looks expensive, costs LCP, and cannot be explored. It is a billboard, not a room.'],
    ['WebGL got a bad name', 'Most 3D sites are 40 MB showreels built by studios who never had to ship on a mid-range Android.'],
  ];
  probs.forEach(([h, t], i) => {
    const y = 2.55 + i * 1.5;
    s.addText(`0${i + 1}`, { x: 0.7, y, w: 0.6, h: 0.4, fontSize: 13, color: C.forge, fontFace: 'Consolas' });
    s.addText(h, { x: 1.35, y: y - 0.08, w: 5.0, h: 0.4, fontSize: 17, bold: true, color: C.bone });
    body(s, t, 1.35, y + 0.38, 5.0, 12);
  });
  plate(s, 'nova', 6.9, 1.5, 5.9, 4.43);

  /* ---------- 3. offer ---------- */
  s = pptx.addSlide();
  bg(s);
  kicker(s, 'The offer');
  title(s, 'One studio, three ways in.', 0.7, 1.0, 38);
  const offers = [
    ['Spark', '$4,800', 'One hero scene, art-directed stills, mobile fallback. Two weeks.'],
    ['Forge', '$12,500', 'Full 3D site: up to five rooms or products, CMS, analytics, launch kit.'],
    ['Foundry', '$3,900 / mo', 'Retainer: new scenes each sprint, perf monitoring, asset library upkeep.'],
  ];
  offers.forEach(([n, p, t], i) => {
    const x = 0.7 + i * 4.05;
    s.addShape(pptx.ShapeType.roundRect, { x, y: 2.25, w: 3.7, h: 3.4, rectRadius: 0.12, fill: { color: i === 1 ? '141017' : C.panel }, line: { color: i === 1 ? C.forge : C.line, width: 1 } });
    s.addText(n.toUpperCase(), { x: x + 0.28, y: 2.5, w: 3.1, h: 0.4, fontSize: 12, color: i === 1 ? C.forge : C.arc, charSpacing: 3, fontFace: 'Consolas' });
    s.addText(p, { x: x + 0.28, y: 2.9, w: 3.1, h: 0.6, fontSize: 26, bold: true, color: C.bone });
    body(s, t, x + 0.28, 3.6, 3.15, 12);
  });
  body(s, 'All tiers include a written first-load budget, a Lighthouse gate in CI, and WebGL fallbacks for low-tier phones.', 0.7, 6.1, 11.5, 12);

  /* ---------- 4. process ---------- */
  s = pptx.addSlide();
  bg(s);
  kicker(s, 'The forge');
  title(s, 'Blockout → Forge → Budget → Wire → Harden', 0.7, 0.95, 30);
  const steps = [
    ['Blockout', 'Camera path, scale and light locked in Blender before any texture exists.'],
    ['Forge', 'bpy scripts build hero assets, bake lightmaps, export GLTF with LODs.'],
    ['Budget', 'Draco + KTX2 compression against a signed-off first-load ceiling.'],
    ['Wire', 'React Three Fiber scenes, scroll timelines, CMS so marketing can edit copy.'],
    ['Harden', 'GPU tiers, fallbacks, SEO-safe HTML and a perf gate in CI.'],
  ];
  steps.forEach(([h, t], i) => {
    const x = 0.7 + i * 2.42;
    s.addShape(pptx.ShapeType.line, { x, y: 2.5, w: 2.2, h: 0, line: { color: C.line, width: 1 } });
    s.addShape(pptx.ShapeType.ellipse, { x: x - 0.07, y: 2.44, w: 0.13, h: 0.13, fill: { color: C.forge } });
    s.addText(`0${i + 1}`, { x, y: 2.7, w: 1.2, h: 0.3, fontSize: 10, color: C.forge, fontFace: 'Consolas' });
    s.addText(h, { x, y: 3.0, w: 2.1, h: 0.4, fontSize: 15, bold: true, color: C.bone });
    body(s, t, x, 3.45, 2.05, 10.5);
  });
  plate(s, 'process', 0.7, 5.05, 11.9, 1.95);

  /* ---------- 5-7. case studies ---------- */
  const cases = [
    ['CASE 01 · 3D COMMERCE', 'Atelier Nova', 'A flagship store where every piece is a real object: rotate, place, buy.',
      ['1.9 MB first load', '+38% add-to-cart', 'bpy asset pipeline', 'Three.js + R3F'], 'nova'],
    ['CASE 02 · REAL ESTATE', 'Meridian Towers', '48 unit interiors and sun studies computed in Blender, walkable on a phone.',
      ['3.1× longer sessions', 'KTX2 + Draco', 'Sun study in bpy', 'WebGL 2 fallback'], 'meridian'],
    ['CASE 03 · PRODUCT LAUNCH', 'Kinetic Labs', 'A scroll-driven reveal that turns a spec sheet into a launch moment.',
      ['2.4M campaign views', 'GLTF + Draco', 'GSAP + R3F', 'Launch ad kit'], 'kinetic'],
  ];
  for (const [k, n, d, tags, img] of cases) {
    s = pptx.addSlide();
    bg(s);
    plate(s, img, 3.2, 0, W - 3.2, H);
    s.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 6.9, h: H, fill: { color: C.ink, transparency: 12 } });
    kicker(s, k, 0.7, 1.5);
    title(s, n, 0.7, 1.95, 44, 7);
    body(s, d, 0.7, 3.5, 5.6, 14);
    tags.forEach((t, i) => chip(s, t, 0.7 + i * 1.85, 5.4, i % 2 ? C.forge : C.arc));
  }

  /* ---------- 8. perf budget ---------- */
  s = pptx.addSlide();
  bg(s);
  kicker(s, 'Engineering');
  title(s, 'Beauty that survives a mid-range phone.', 0.7, 1.0, 36);
  const nums = [
    ['< 2.0 MB', 'first load, including fonts and JS'],
    ['60 fps', 'on a Pixel 6a / iPhone 12 tier GPU'],
    ['95+', 'Lighthouse performance gate in CI'],
    ['≤ 8', 'draw calls in the hero scene'],
  ];
  nums.forEach(([n, t], i) => {
    const x = 0.7 + (i % 2) * 5.95;
    const y = 2.3 + Math.floor(i / 2) * 1.9;
    s.addText(n, { x, y, w: 3.2, h: 0.7, fontSize: 34, bold: true, color: i % 2 ? C.forge : C.arc });
    body(s, t, x, y + 0.75, 4.8, 12);
  });
  s.addImage({ path: IMG('brand', 'exports', 'logo-mark-1024.png'), x: 9.9, y: 3.6, w: 2.7, h: 2.7 });

  /* ---------- 9. who we are ---------- */
  s = pptx.addSlide();
  bg(s);
  kicker(s, 'The studio');
  title(s, 'Blender hands, browser discipline.', 0.7, 1.0, 36);
  body(s, 'LUMENFORGE is a small, senior team: an asset pipeline engineer writing bpy automation, a creative developer owning the WebGL layer, and a motion designer who ships the launch campaign with every build.', 0.7, 2.2, 6.0, 14);
  const stack = ['Blender', 'bpy', 'Three.js', 'React Three Fiber', 'React / Next', 'GSAP', 'Draco', 'KTX2', 'Playwright', 'Figma'];
  stack.forEach((t, i) => chip(s, t, 0.7 + (i % 5) * 1.55, 4.4 + Math.floor(i / 5) * 0.52, C.arc));
  s.addImage({ path: IMG('ads', 'posters', 'poster-hiring-1200x1600.png'), x: 7.4, y: 0.9, w: 3.9, h: 5.2, rounding: true });
  s.addImage({ path: IMG('ads', 'posters', 'poster-manifesto-1200x1600.png'), x: 8.9, y: 3.2, w: 3.4, h: 4.5, rounding: true });

  /* ---------- 10. pricing table ---------- */
  s = pptx.addSlide();
  bg(s);
  kicker(s, 'Commercials');
  title(s, 'Fixed scope, fixed number, fixed date.', 0.7, 1.0, 34);
  const rows = [
    [{ text: ' ', options: { fill: { color: C.panel } } }, { text: 'Spark', options: { bold: true, color: C.bone, fill: { color: C.panel } } }, { text: 'Forge', options: { bold: true, color: C.forge, fill: { color: C.panel } } }, { text: 'Foundry', options: { bold: true, color: C.bone, fill: { color: C.panel } } }],
    ['Price', '$4,800', '$12,500', '$3,900 / mo'],
    ['Scenes', '1', 'up to 5', '2 per sprint'],
    ['bpy pipeline', '—', 'included', 'included'],
    ['CMS + analytics', '—', 'included', 'included'],
    ['Launch ad kit', 'stills', 'stills + video', 'monthly'],
    ['Delivery', '2 weeks', '3–5 weeks', 'rolling'],
  ];
  s.addTable(rows, {
    x: 0.7, y: 2.2, w: 11.9, colW: [2.9, 3.0, 3.0, 3.0],
    border: { type: 'solid', color: C.line, pt: 1 },
    fontFace: 'Arial', fontSize: 12, color: C.muted, valign: 'middle', rowH: 0.46,
  });

  /* ---------- 11. next steps ---------- */
  s = pptx.addSlide();
  bg(s);
  plate(s, 'contact', 8.6, 0, 4.73, 7.5);
  kicker(s, 'Next step');
  title(s, 'Send us your product.\nWe send back a room.', 0.7, 1.4, 36, 7);
  body(s, 'Within 48 hours you get a fixed price, a camera path and a load budget. No retainer to start, no discovery invoice.', 0.7, 3.6, 6.2, 14);
  s.addText('forge@lumenforge.studio', { x: 0.7, y: 5.2, w: 6.2, h: 0.4, fontSize: 18, bold: true, color: C.arc });
  s.addText('lumenforge.studio · live showroom at /showroom', { x: 0.7, y: 5.65, w: 6.2, h: 0.3, fontSize: 11, color: C.muted, fontFace: 'Consolas' });

  const out = path.join(ROOT, 'deck', 'LUMENFORGE-pitch-deck.pptx');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  await pptx.writeFile({ fileName: out });
  console.log('deck written:', out, (fs.statSync(out).size / 1024).toFixed(0) + ' KB');
}

main().catch((e) => { console.error(e); process.exit(1); });
