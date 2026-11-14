// LUMENFORGE — one-pager PDF (A4 portrait) for email attachments & print
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const { PDFDocument, rgb } = require('pdf-lib');
const fontkit = require('@pdf-lib/fontkit');
const { ROOT, C } = require('./lib');

const W = 595, H = 842;
const FONT = {
  bold: 'space-grotesk-700-normal.ttf',
  sans: 'space-grotesk-400-normal.ttf',
  body: 'inter-400-normal.ttf',
  mono: 'jetbrains-mono-400-normal.ttf',
};

const hex = (h) => {
  const s = h.replace('#', '');
  return rgb(parseInt(s.slice(0, 2), 16) / 255, parseInt(s.slice(2, 4), 16) / 255, parseInt(s.slice(4, 6), 16) / 255);
};

async function main() {
  const pdf = await PDFDocument.create();
  pdf.setTitle('LUMENFORGE — one-pager');
  pdf.setAuthor('LUMENFORGE');
  pdf.setSubject('Interactive 3D websites — Blender (bpy), Three.js, React');
  pdf.registerFontkit(fontkit);
  const f = (file) => pdf.embedFont(fs.readFileSync(path.join(ROOT, 'fonts', file)), { subset: true });
  const bold = await f(FONT.bold);
  const body = await f(FONT.body);
  const mono = await f(FONT.mono);

  const p = pdf.addPage([W, H]);
  p.drawRectangle({ x: 0, y: 0, width: W, height: H, color: hex(C.ink) });

  // header band: clean plate crop, no baked type
  const plate = await sharp(path.join(ROOT, 'portfolio/plates/cover.png'))
    .resize({ width: W, height: 236, fit: 'cover', position: 'right' })
    .modulate({ brightness: 1.12 })
    .png()
    .toBuffer();
  const img = await pdf.embedPng(plate);
  p.drawImage(img, { x: 0, y: H - 236, width: W, height: 236 });
  for (const [y, h, o] of [[H - 236, 236, 0.15], [H - 130, 130, 0.4]]) {
    p.drawRectangle({ x: 0, y, width: W, height: h, color: hex(C.ink), opacity: o });
  }
  const mark = await pdf.embedPng(await sharp(path.join(ROOT, 'brand/exports/logo-mark-512.png')).resize(256).png().toBuffer());

  const text = (t, x, y, size, font, color, opts = {}) =>
    p.drawText(t, { x, y, size, font, color: hex(color), lineHeight: size * 1.45, ...opts });
  const kicker = (t, x, y, color = C.arc) => text(t.toUpperCase(), x, y, 7.5, mono, color, { characterSpacing: 1.8 });

  p.drawImage(mark, { x: 44, y: H - 74, width: 30, height: 30 });
  text('LUMENFORGE', 80, H - 64, 16, bold, C.bone, { characterSpacing: 1.6 });
  kicker('interactive 3d studio', 80, H - 78);

  let y = H - 288;
  text('Websites you can', 44, y, 30, bold, C.bone);
  y -= 34;
  text('walk through.', 44, y, 30, bold, C.forge);

  y -= 30;
  text(
    'We model your product in Blender, bake the geometry with bpy, and ship it as a',
    44, y, 8.6, body, C.muted
  );
  text('Three.js + React site that loads under two seconds on a mid-range phone.', 44, y - 13, 8.6, body, C.muted);
  text('Not a video. Not a slideshow. A place.', 44, y - 26, 8.6, body, C.muted);

  // three columns: problem / offer / proof (fixed baseline so nothing drifts)
  const colW = 158;
  const colsKickerY = 408;
  p.drawLine({ start: { x: 44, y: colsKickerY + 14 }, end: { x: W - 44, y: colsKickerY + 14 }, thickness: 0.6, color: hex('#1B2130') });
  const cy = colsKickerY;
  const cols = [
    ['the problem', ['Customers judge size, material', 'and finish from a flat photo —', 'and guess wrong at the exact', 'moment they would have bought.', '', 'Video cannot be explored, and', 'most 3D sites are 40 MB', 'showreels that melt a phone.']],
    ['what we build', ['3D commerce — every piece is an', 'object you rotate, place, buy.', '', '3D real estate — every unit', 'walkable, sun studies baked', 'in Blender.', '', 'Product launches — a scroll reveal', 'worth forwarding.']],
    ['proof', ['Atelier Nova', '   +38% add-to-cart, 1.9 MB', '', 'Meridian Towers', '   3.1x longer sessions', '', 'Kinetic Labs', '   2.4M campaign views', '', '<= 8 draw calls · 60 fps']],
  ];
  cols.forEach(([head, lines], i) => {
    const x = 44 + i * (colW + 14);
    kicker(head, x, cy);
    lines.forEach((l, j) => {
      const clean = l.trim();
      const isName = l === clean && /^[A-Z]/.test(clean) && !/^[A-Z ]+$/.test(clean) && clean.length < 22;
      text(clean, x, cy - 18 - j * 11.4, 7.3, body, isName ? C.bone : C.muted);
    });
  });

  // pricing strip — anchored, not cumulative, so nothing can collide
  const tierKickerY = 268;
  p.drawLine({ start: { x: 44, y: tierKickerY + 12 }, end: { x: W - 44, y: tierKickerY + 12 }, thickness: 0.6, color: hex('#1B2130') });
  kicker('fixed scope, fixed number', 44, tierKickerY - 4);
  const tiers = [
    ['SPARK', '$4,800', '2 weeks', '1 walkthrough scene + 3 stills'],
    ['FORGE', '$12,500', '3-5 weeks', 'up to 5 rooms, CMS, launch kit'],
    ['FOUNDRY', '$3,900/mo', 'rolling', '2 scenes per sprint + monitoring'],
  ];
  const cardTop = tierKickerY - 26;
  tiers.forEach(([n, price, when, what], i) => {
    const x = 44 + i * (colW + 14);
    p.drawRectangle({
      x, y: cardTop - 62, width: colW, height: 78,
      color: hex(i === 1 ? '#140E0B' : C.panel),
      borderColor: hex(i === 1 ? C.forge : '#1B2130'), borderWidth: i === 1 ? 1 : 0.5,
    });
    text(n, x + 10, cardTop - 10, 7, mono, i === 1 ? C.forge : C.arc, { characterSpacing: 1.4 });
    text(price, x + 10, cardTop - 32, 15, bold, C.bone);
    text(when, x + 10, cardTop - 45, 6.8, mono, C.muted);
    text(what, x + 10, cardTop - 56, 6.8, body, C.muted, { maxWidth: colW - 20 });
  });

  // process strip
  const procY = 136;
  kicker('the forge', 44, procY);
  text('Blockout  ·  Forge  ·  Budget  ·  Wire  ·  Harden', 44, procY - 20, 11, bold, C.bone);

  // footer band
  p.drawLine({ start: { x: 44, y: 96 }, end: { x: W - 44, y: 96 }, thickness: 0.6, color: hex('#1B2130') });
  text('Send us your product. We send back a room.', 44, 72, 10.5, bold, C.bone);
  const email = 'forge@lumenforge.studio';
  const emailW = bold.widthOfTextAtSize(email, 9.5);
  text(email, W - 44 - emailW, 72, 9.5, bold, C.arc);
  text('fixed price, camera path and load budget within 48 hours  ·  lumenforge.studio  ·  live showroom at /showroom', 44, 50, 6.6, mono, '#5F6878');
  text('Blender · bpy · Three.js · React Three Fiber · GSAP · Draco · KTX2', 44, 32, 6.4, mono, '#4C5566');

  const out = path.join(ROOT, 'docs', 'LUMENFORGE-one-pager.pdf');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, await pdf.save());
  console.log('one-pager:', out, (fs.statSync(out).size / 1024).toFixed(0) + ' KB');
}

main().catch((e) => { console.error(e); process.exit(1); });
