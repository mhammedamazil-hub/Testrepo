// KILN — identity construction.
//
// The mark is a kiln door: a solid block with one arch cut through it, open at the
// foot. It is built from the same arch module the renders and the site use, so the
// identity is literally a section through the studio's own architecture. No gradient,
// no isometric cube, no letterform forced into a badge — a single silhouette that
// survives at 16 px and embosses at 300 mm.
//
// Geometry is defined once, in a 1000-unit box, and every export scales from it.
const fs = require('fs');
const path = require('path');
const { Resvg } = require('@resvg/resvg-js');
const { ROOT, ensureDir } = require('./lib');

const F = path.join(ROOT, 'fonts');
const FONTS = {
  serif: `${F}/instrument-serif.ttf`,
  sans: `${F}/inter-tight-500.ttf`,
  mono: `${F}/jetbrains-mono.ttf`,
};
const FAM = { serif: 'Instrument Serif', sans: 'Inter Tight', mono: 'JetBrains Mono' };

const C = {
  ink: '#0B0C0E',
  inkSoft: '#141518',
  paper: '#F2EDE4',
  ember: '#D8542A',
  emberLit: '#EE7541',
  kiln: '#8A8578',
  smoke: '#55544F',
};

/* ── geometry ─────────────────────────────────────────────────────────────
   Box: 1000×1000. Door: 300 wide, springing line 120 above centre, radius 150,
   legs running to the foot of the block. Radius = half the opening, so the arch
   is a true semicircle — the proportion of a real kiln mouth.
*/
const G = {
  box: 1000,
  block: 1000,
  radius: 150,
  spring: -120,   // y of the springing line (negative = up)
  foot: 500,      // arch legs run past the bottom edge
  corner: 0,      // sharp: it is a section, not an app tile
};

const door = (s = 1, { ox = 0, oy = 0 } = {}) => {
  const r = G.radius * s;
  const y = G.spring * s + oy;
  const foot = G.foot * s + oy;
  const x0 = ox - r;
  const x1 = ox + r;
  return `M ${x0} ${foot} L ${x0} ${y} A ${r} ${r} 0 0 1 ${x1} ${y} L ${x1} ${foot} Z`;
};

// strip the outer <svg> wrapper so compositions can nest
const inner = (markup) => markup.replace(/^[\s\S]*?<svg[^>]*>/, '').replace(/<\/svg>\s*$/, '');

const svg = (w, h, body) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${body}</svg>`;

/** The mark: block with the door knocked out. `inverse` swaps field and cutting. */
function markSvg(size = 1000, { field = C.ink, cut = C.paper, pad = 0 } = {}) {
  const s = (size - pad * 2) / G.box;
  return svg(size, size, `
    <g transform="translate(${pad},${pad}) scale(${s})">
      <path fill="${field}" fill-rule="evenodd"
        d="M 0 0 H ${G.box} V ${G.box} H 0 Z ${door(1, { ox: G.box / 2, oy: G.box / 2 })}"/>
      <path fill="${cut}" d="${door(1, { ox: G.box / 2, oy: G.box / 2 })}"/>
    </g>`);
}

/** Solid door only — for use inside other compositions. */
function doorOnly(size = 1000, fill = C.ember, pad = 0) {
  const s = (size - pad * 2) / G.box;
  return svg(size, size, `<g transform="translate(${pad},${pad}) scale(${s})"><path fill="${fill}" d="${door(1, { ox: G.box / 2, oy: G.box / 2 })}"/></g>`);
}

/* ── wordmark ─────────────────────────────────────────────────────────────
   Instrument Serif, tracked to +0.06em. At display sizes the serif carries the
   warmth; the tracking keeps it from reading as a book title.
   Real metrics (fontTools): upem 1000, cap 0.72, "KILN" = 1.698 em.
*/
const M_ = {
  serifCap: 0.72,
  kiln: 1.698,        // advance of KILN at 1 em
  kilnTrack: 0.06,    // em, applied after each glyph
  sansCap: 0.7275,
  monoCap: 0.73,
};

function wordmark(width = 2400, { dark = true, color } = {}) {
  const fg = color || (dark ? C.paper : C.ink);
  const size = width / (M_.kiln + M_.kilnTrack * 4);
  const cap = size * M_.serifCap;
  const h = Math.round(cap * 1.5);
  const baseline = h * 0.5 + cap * 0.5;
  return svg(Math.round(width), h, `
    <text x="0" y="${baseline}" font-family="${FAM.serif}" font-size="${size}"
      letter-spacing="${size * M_.kilnTrack}" fill="${fg}">KILN</text>`);
}

/* ── lockup ───────────────────────────────────────────────────────────────
   Mark sits on the baseline, its block exactly cap height. Clear space between
   block and wordmark = 0.55 cap. Wordmark baseline = mark foot. Ember rule, then
   the descriptor stack, optically centred on the cap height of KILN.
*/
function lockup(width = 2400, { dark = true, desc = 'INTERACTIVE ARCHITECTURE', sub = 'BLENDER · BPY · THREE.JS' } = {}) {
  const fg = dark ? C.paper : C.ink;
  const subCol = dark ? C.kiln : '#6E6A60';

  // proportions are all in cap heights, so the lockup scales without re-drawing
  const K = {
    mark: 1.0,
    gap: 0.55,
    wordmark: (M_.kiln + M_.kilnTrack * 4) / M_.serifCap, // 2.692
    gapRule: 0.42,
    rule: 0.035,
    gapDesc: 0.30,
    sans: 0.245,
    mono: 0.185,
  };
  const descAdv = 13.5405;   // Inter Tight 500, "INTERACTIVE ARCHITECTURE", em
  const descTrack = 0.14;    // em of the sans size, applied after each glyph
  const descEm = descAdv * K.sans + descTrack * K.sans * (desc.length - 1);
  const total = K.mark + K.gap + K.wordmark + K.gapRule + K.rule + K.gapDesc + descEm;

  const cap = width / total;
  const size = cap / M_.serifCap;
  const sansSize = cap * K.sans;
  const monoSize = cap * K.mono;

  const markX = 0;
  const tx = cap * (K.mark + K.gap);
  const ruleX = cap * (K.mark + K.gap + K.wordmark + K.gapRule);
  const descX = ruleX + cap * (K.rule + K.gapDesc);

  const h = Math.round(cap * 1.86);
  const baseline = Math.round(h * 0.5 + cap * 0.5);

  return svg(Math.round(width), h, `
    <g transform="translate(${markX},${baseline - cap})">
      ${inner(markSvg(cap, { field: fg, cut: dark ? C.ink : C.paper }))}
    </g>
    <text x="${tx}" y="${baseline}" font-family="${FAM.serif}" font-size="${size}"
      letter-spacing="${size * M_.kilnTrack}" fill="${fg}">KILN</text>
    <rect x="${ruleX}" y="${baseline - cap * 1.12}" width="${Math.max(1.4, cap * K.rule)}"
      height="${cap * 1.34}" fill="${C.ember}"/>
    <text x="${descX}" y="${baseline - cap * 0.40}" font-family="${FAM.sans}"
      font-size="${sansSize}" letter-spacing="${sansSize * descTrack}" fill="${fg}">${desc}</text>
    <text x="${descX}" y="${baseline + cap * 0.04}" font-family="${FAM.mono}"
      font-size="${monoSize}" letter-spacing="${monoSize * 0.10}" fill="${subCol}">${sub}</text>`);
}

/* ── favicon ──────────────────────────────────────────────────────────────
   16 px budget: the door has to be at least 5 px wide or it fills in, so the
   small sizes use a wider opening and a lighter block.
*/
function favicon(px = 64) {
  const r = px * 0.5 * 0.62;
  return svg(px, px, `
    <rect width="${px}" height="${px}" fill="${C.ink}"/>
    <path fill="${C.paper}" d="M ${px / 2 - r} ${px} L ${px / 2 - r} ${px * 0.42}
      A ${r} ${r} 0 0 1 ${px / 2 + r} ${px * 0.42} L ${px / 2 + r} ${px} Z"/>`);
}

/* ── construction sheet ───────────────────────────────────────────────────
   Every studio has one: the geometry, the clear space, the minimum size.
*/
function construction(W = 2000) {
  const H = W * 0.755;
  const s = W / 2000;
  const box = 470 * s;
  const x0 = 150 * s;
  const y0 = 250 * s;
  const gx = (n) => x0 + box * n;
  const gy = (n) => y0 + box * n;
  const grid = [];
  for (let i = 1; i < 8; i++) {
    grid.push(`<line x1="${gx(i / 8)}" y1="${y0}" x2="${gx(i / 8)}" y2="${y0 + box}" stroke="${C.kiln}" stroke-opacity=".28" stroke-width="${1 * s}"/>`);
    grid.push(`<line x1="${x0}" y1="${gy(i / 8)}" x2="${x0 + box}" y2="${gy(i / 8)}" stroke="${C.kiln}" stroke-opacity=".28" stroke-width="${1 * s}"/>`);
  }
  const clr = box * 0.16;
  return svg(W, H, `
    <rect width="${W}" height="${H}" fill="${C.ink}"/>
    <text x="${x0}" y="${y0 - 150 * s}" font-family="${FAM.mono}" font-size="${17 * s}"
      letter-spacing="${5 * s}" fill="${C.ember}">MARK · CONSTRUCTION</text>
    <text x="${x0}" y="${y0 - 104 * s}" font-family="${FAM.serif}" font-size="${46 * s}"
      fill="${C.paper}">The kiln door</text>

    <g transform="translate(${x0},${y0}) scale(${box / 1000})">
      <rect width="1000" height="1000" fill="none" stroke="${C.kiln}" stroke-width="${1.4 * s * 1000 / box}"/>
      <path fill="${C.paper}" fill-rule="evenodd"
        d="M 0 0 H 1000 V 1000 H 0 Z ${door(1, { ox: 500, oy: 500 })}"/>
      <path fill="none" stroke="${C.ember}" stroke-width="${3 * s * 1000 / box}"
        d="${door(1, { ox: 500, oy: 500 })}"/>
      <circle cx="500" cy="${500 + G.spring}" r="4.5" fill="${C.ember}"/>
      <line x1="0" y1="${500 + G.spring}" x2="1000" y2="${500 + G.spring}" stroke="${C.ember}" stroke-width="${1.6 * s * 1000 / box}" stroke-dasharray="${9 * s * 1000 / box} ${7 * s * 1000 / box}"/>
      <line x1="500" y1="0" x2="500" y2="1000" stroke="${C.kiln}" stroke-opacity=".45" stroke-width="${1.2 * s * 1000 / box}"/>
    </g>
    ${grid.join('')}
    <rect x="${x0 - clr}" y="${y0 - clr}" width="${box + clr * 2}" height="${box + clr * 2}"
      fill="none" stroke="${C.kiln}" stroke-opacity=".55" stroke-dasharray="${8 * s} ${8 * s}" stroke-width="${1.2 * s}"/>

    ${[
      ['01 · GEOMETRY', ['Field: full square, no radius.', 'Door: 300 units wide, semicircular head.', 'Radius = ½ opening — a true arch.', 'Springing line: 120 above centre.', 'Legs run past the foot: it is a passage.']],
      ['02 · CLEAR SPACE', ['Keep 0.16 × block on all sides.', 'No type, rule or image inside.', 'The mark may bleed only at the foot.']],
      ['03 · COLOUR', ['Ink field, paper door. That is the mark.', 'Paper field inverts it exactly.', 'Ember is a signal, never a field.']],
      ['04 · MINIMUM SIZE', ['32 px digital, door widened below that.', '8 mm print, at which the door closes.', 'Never outline, glow or bevel it.']],
    ].map(([head, lines], i) => {
      const cx = W * 0.415 + (i % 2) * W * 0.30;
      const cy = 250 * s + Math.floor(i / 2) * 240 * s;
      return `
      <text x="${cx}" y="${cy}" font-family="${FAM.mono}" font-size="${14 * s}" letter-spacing="${4 * s}" fill="${C.ember}">${head}</text>
      ${lines.map((l, j) => `<text x="${cx}" y="${cy + 34 * s + j * 26 * s}" font-family="${FAM.sans}" font-size="${15.5 * s}" fill="${C.paper}" fill-opacity=".82">${l}</text>`).join('')}`;
    }).join('')}

    <g transform="translate(${x0},${y0 + box + 168 * s})">
      <text font-family="${FAM.mono}" font-size="${13 * s}" letter-spacing="${4 * s}" fill="${C.kiln}">SCALE TEST</text>
      ${[128, 64, 32, 16].map((px, i) => `
        <g transform="translate(${i * 118 * s},${30 * s}) scale(0.62)">
          ${inner(markSvg(px, { field: C.paper, cut: C.ink }))}
        </g>
        <text x="${i * 118 * s}" y="${126 * s}" font-family="${FAM.mono}" font-size="${11.5 * s}" fill="${C.smoke}">${px} px</text>`).join('')}
    </g>

    <g transform="translate(${W * 0.415},${y0 + box + 40 * s})">
      <text font-family="${FAM.mono}" font-size="${13 * s}" letter-spacing="${4 * s}" fill="${C.kiln}">LOCKUPS · DARK</text>
      <g transform="translate(0,${40 * s})">
        ${inner(lockup(880 * s, { dark: true }))}
      </g>
      <g transform="translate(0,${360 * s})">
        <text font-family="${FAM.mono}" font-size="${13 * s}" letter-spacing="${4 * s}" fill="${C.kiln}">LOCKUPS · PAPER</text>
        <rect x="0" y="${40 * s}" width="${1010 * s}" height="${230 * s}" fill="${C.paper}"/>
        <g transform="translate(${40 * s},${78 * s})">
          ${inner(lockup(800 * s, { dark: false }))}
        </g>
      </g>
    </g>`);
}

/* ── exports ────────────────────────────────────────────────────────────── */
function raster(markup, width) {
  const r = new Resvg(markup, {
    fitTo: { mode: 'width', value: width },
    font: { fontFiles: [FONTS.serif, FONTS.sans, FONTS.mono], loadSystemFonts: false, defaultFontFamily: FAM.serif },
  });
  return r.render().asPng();
}

async function write(rel, markup, width, { png = true } = {}) {
  const out = path.join(ROOT, rel);
  if (!/^<svg/.test(markup.trim())) throw new Error('bad svg: '+rel+' :: '+markup.slice(0,200));
  ensureDir(path.dirname(out));
  fs.writeFileSync(out, markup);
  if (png) {
    try { fs.writeFileSync(out.replace(/\.svg$/, '.png'), raster(markup, width)); }
    catch (e) { console.error('RASTER FAIL', rel, e.message); throw e; }
  }
  return rel;
}

async function main() {
  const out = [];
  const L = 'brand/logo';
  const E = 'brand/exports';

  out.push(await write(`${L}/kiln-mark.svg`, markSvg(1000), 1000));
  out.push(await write(`${L}/kiln-mark-paper.svg`, markSvg(1000, { field: C.paper, cut: C.ink }), 1000));
  out.push(await write(`${L}/kiln-mark-ember.svg`, markSvg(1000, { field: C.ember, cut: C.ink }), 1000));
  out.push(await write(`${L}/kiln-door.svg`, doorOnly(1000, C.ember), 1000));
  out.push(await write(`${L}/kiln-wordmark.svg`, wordmark(2400), 2400));
  out.push(await write(`${L}/kiln-wordmark-ink.svg`, wordmark(2400, { dark: false }), 2400));
  out.push(await write(`${L}/kiln-lockup.svg`, lockup(2400), 2400));
  out.push(await write(`${L}/kiln-lockup-ink.svg`, lockup(2400, { dark: false }), 2400));
  out.push(await write(`${L}/kiln-favicon.svg`, favicon(64), 64, { png: false }));
  out.push(await write(`${L}/kiln-construction.svg`, construction(2000), 2000));

  // app / social exports
  out.push(await write(`${E}/mark-1024.png`, markSvg(1024), 1024, { png: true }) && `${E}/mark-1024.png`);
  fs.writeFileSync(path.join(ROOT, `${E}/mark-512.png`), raster(markSvg(512), 512));
  fs.writeFileSync(path.join(ROOT, `${E}/mark-mono-512.png`), raster(markSvg(512, { field: C.paper, cut: C.ink }), 512));
  fs.writeFileSync(path.join(ROOT, `${E}/icon-1024.png`), raster(markSvg(1024), 1024));
  fs.writeFileSync(path.join(ROOT, `${E}/wordmark-2400.png`), raster(wordmark(2400), 2400));
  fs.writeFileSync(path.join(ROOT, `${E}/lockup-2400.png`), raster(lockup(2400), 2400));
  fs.writeFileSync(path.join(ROOT, `${E}/lockup-ink-2400.png`), raster(lockup(2400, { dark: false }), 2400));
  fs.writeFileSync(path.join(ROOT, `${E}/favicon-32.png`), raster(favicon(64), 32));
  fs.writeFileSync(path.join(ROOT, `${E}/apple-touch-icon.png`), raster(favicon(180), 180));
  fs.writeFileSync(path.join(ROOT, `${E}/favicon.svg`), favicon(64));

  console.log('identity:'); out.forEach((f) => console.log('  ', f));
}

if (require.main === module) main().catch((e) => { console.error(e); process.exit(1); });
module.exports = { markSvg, wordmark, lockup, favicon, construction, doorOnly, C, G, door, FONTS };
