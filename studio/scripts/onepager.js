// KILN — one-pager (A4 portrait). Email attachment + print leave-behind.
// Same three faces, same grid, same ember rule as the site. Nothing here is decorative.
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const { PDFDocument, rgb } = require('pdf-lib');
const fontkit = require('@pdf-lib/fontkit');
const { ROOT } = require('./lib');

const W = 595.28;
const H = 841.89;
const M = 44;

const C = {
  ink: '#0B0C0E', paper: '#F2EDE4', ember: '#D8542A', emberLit: '#EE7541',
  kiln: '#8A8578', smoke: '#55544F', body: '#C4BEB1', rule: '#26272B',
};

const hex = (h) => {
  const s = h.replace('#', '');
  return rgb(parseInt(s.slice(0, 2), 16) / 255, parseInt(s.slice(2, 4), 16) / 255, parseInt(s.slice(4, 6), 16) / 255);
};

async function main() {
  const pdf = await PDFDocument.create();
  pdf.setTitle('KILN — one-pager');
  pdf.setAuthor('KILN');
  pdf.setSubject('Interactive architecture: Blender-rendered rooms shipped as React sites');
  pdf.registerFontkit(fontkit);

  const F = (f) => pdf.embedFont(fs.readFileSync(path.join(ROOT, 'fonts', f)), { subset: true });
  const serif = await F('instrument-serif.ttf');
  const sans = await F('inter-tight-400.ttf');
  const sansM = await F('inter-tight-500.ttf');
  const mono = await F('jetbrains-mono.ttf');

  const p = pdf.addPage([W, H]);
  p.drawRectangle({ x: 0, y: 0, width: W, height: H, color: hex(C.ink) });

  // top plate: the house set, cropped wide, with an ink scrim into the headline
  const band = await sharp(path.join(ROOT, 'brand/renders/hero-2400x1600.png'))
    .resize({ width: Math.round(W * 2), height: 720, fit: 'cover', position: 'centre' })
    .png().toBuffer();
  p.drawImage(await pdf.embedPng(band), { x: 0, y: H - 236, width: W, height: 236 });
  // a real gradient, not stacked rectangles: one pass, no banding, no seam
  const scrim = await sharp(Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${Math.round(W)}" height="236">
    <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${C.ink}" stop-opacity="0.62"/>
      <stop offset="0.34" stop-color="${C.ink}" stop-opacity="0.34"/>
      <stop offset="0.72" stop-color="${C.ink}" stop-opacity="0.86"/>
      <stop offset="1" stop-color="${C.ink}" stop-opacity="1"/>
    </linearGradient></defs>
    <rect width="${Math.round(W)}" height="236" fill="url(#g)"/></svg>`)).png().toBuffer();
  p.drawImage(await pdf.embedPng(scrim), { x: 0, y: H - 236, width: W, height: 236 });

  const mark = await pdf.embedPng(await sharp(path.join(ROOT, 'brand/exports/mark-512.png')).resize(120).png().toBuffer());
  p.drawImage(mark, { x: M, y: H - 62, width: 22, height: 22 });
  p.drawText('KILN', { x: M + 32, y: H - 58, size: 13, font: serif, color: hex(C.paper), characterSpacing: 1.8 });
  p.drawText('INTERACTIVE ARCHITECTURE', {
    x: M + 32, y: H - 72, size: 5.2, font: mono, color: hex(C.kiln), characterSpacing: 1.4,
  });

  // headline block, sitting just under the plate
  let y = H - 300;
  p.drawText('Rooms,', { x: M, y, size: 40, font: serif, color: hex(C.paper) });
  p.drawText('not pages.', { x: M, y: y - 40, size: 40, font: serif, color: hex(C.emberLit) });
  y -= 62;
  p.drawRectangle({ x: M, y, width: 54, height: 1.6, color: hex(C.ember) });
  y -= 16;
  const lede = 'We model your space in Blender, light it with bpy, and ship it as a React site that\nloads in under two megabytes and holds sixty frames on a phone. Not a video.\nNot a slideshow. A place you can walk around.';
  p.drawText(lede, { x: M, y, size: 8.4, font: sans, color: hex(C.body), lineHeight: 13 });

  // three columns with a shared baseline
  const colTop = y - 52;
  p.drawLine({ start: { x: M, y: colTop + 10 }, end: { x: W - M, y: colTop + 10 }, thickness: 0.5, color: hex(C.rule) });
  const colW = (W - M * 2 - 2 * 16) / 3;
  const cols = [
    ['THE ARGUMENT', [
      'Customers judge scale, material',
      'and finish from a flat photograph —',
      'and guess wrong at the exact',
      'moment they would have bought.',
      '',
      'Video cannot be explored, and most',
      '3D sites are forty-megabyte',
      'showreels that melt a phone.',
    ]],
    ['WHAT WE BUILD', [
      'Commerce — every piece is an',
      'object you turn, place and buy.',
      '',
      'Property — every unit walkable,',
      'sun studies baked in Blender.',
      '',
      'Launch — a reveal worth',
      'forwarding, cut from the same scene.',
    ]],
    ['PROOF', [
      'Atelier Nova',
      '  +38% add-to-cart, 1.9 MB',
      '',
      'Meridian Towers',
      '  3.1× session length, 48 units',
      '',
      'Kinetic Labs',
      '  2.4M campaign views',
    ]],
  ];
  cols.forEach(([head, lines], i) => {
    const x = M + i * (colW + 16);
    p.drawText(head, { x, y: colTop - 8, size: 5.6, font: mono, color: hex(C.ember), characterSpacing: 1.3 });
    lines.forEach((l, j) => {
      const clean = l.trim();
      const name = l === clean && /^[A-Z]/.test(clean) && clean.length < 22 && !/^[A-Z ']+$/.test(clean);
      p.drawText(clean, {
        x, y: colTop - 24 - j * 10.4, size: 7.1, font: name ? sansM : sans,
        color: hex(name ? C.paper : C.body),
      });
    });
  });

  // rates strip
  const tierTop = 290;
  p.drawLine({ start: { x: M, y: tierTop + 12 }, end: { x: W - M, y: tierTop + 12 }, thickness: 0.5, color: hex(C.rule) });
  p.drawText('FIXED SCOPE, FIXED NUMBER', { x: M, y: tierTop, size: 5.6, font: mono, color: hex(C.ember), characterSpacing: 1.3 });
  const tiers = [
    ['SPAR', '$4,800', '2 weeks', 'One walkthrough scene, three stills'],
    ['KILN', '$12,500', '3–5 weeks', 'Up to five rooms, CMS, launch kit'],
    ['FIRING', '$3,900/mo', 'rolling', 'Two scenes per sprint, monitoring'],
  ];
  tiers.forEach(([n, price, when, what], i) => {
    const x = M + i * (colW + 16);
    const feat = i === 1;
    p.drawRectangle({
      x, y: tierTop - 74, width: colW, height: 70,
      color: hex(feat ? '#14100E' : '#101114'),
      borderColor: hex(feat ? C.ember : C.rule), borderWidth: feat ? 0.9 : 0.5,
    });
    p.drawText(n, { x: x + 9, y: tierTop - 22, size: 5.4, font: mono, color: hex(feat ? C.emberLit : C.kiln), characterSpacing: 1.2 });
    p.drawText(price, { x: x + 9, y: tierTop - 42, size: 13, font: serif, color: hex(C.paper) });
    p.drawText(when, { x: x + 9, y: tierTop - 52, size: 5.6, font: mono, color: hex(C.smoke) });
    p.drawText(what, { x: x + 9, y: tierTop - 64, size: 6.2, font: sans, color: hex(C.body), maxWidth: colW - 18 });
  });

  // method, as a single tracked line
  p.drawText('THE METHOD', { x: M, y: 214, size: 5.6, font: mono, color: hex(C.kiln), characterSpacing: 1.3 });
  p.drawText('Blockout  ·  Forge  ·  Budget  ·  Wire  ·  Harden', {
    x: M, y: 196, size: 11, font: serif, color: hex(C.paper),
  });
  p.drawText('Each stage has an artefact you can open and a number it has to hit.', {
    x: M, y: 180, size: 7, font: sans, color: hex(C.body),
  });

  // footer
  p.drawLine({ start: { x: M, y: 118 }, end: { x: W - M, y: 118 }, thickness: 0.5, color: hex(C.rule) });
  p.drawText('Send the product. We send the room.', { x: M, y: 96, size: 9.4, font: sansM, color: hex(C.paper) });
  const email = 'studio@kiln.studio';
  p.drawText(email, {
    x: W - M - sansM.widthOfTextAtSize(email, 8.6), y: 96, size: 8.6, font: sansM, color: hex(C.emberLit),
  });
  p.drawText('fixed price, camera path and load budget within two working days  ·  kiln.studio  ·  showroom at /showroom', {
    x: M, y: 74, size: 5.6, font: mono, color: hex(C.smoke),
  });
  p.drawText('Blender  ·  bpy  ·  Cycles  ·  Three.js  ·  React Three Fiber  ·  Draco  ·  KTX2', {
    x: M, y: 56, size: 5.4, font: mono, color: hex('#4C4B47'),
  });

  const out = path.join(ROOT, 'docs', 'KILN-one-pager.pdf');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, await pdf.save());
  console.log('one-pager:', out, (fs.statSync(out).size / 1024).toFixed(0) + ' KB');
}

main().catch((e) => { console.error(e); process.exit(1); });
