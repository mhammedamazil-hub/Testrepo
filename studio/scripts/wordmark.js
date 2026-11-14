// KILN — typographic identity.
//
// The previous mark (an isometric "L" built from cubes) is exactly the kind of thing
// generated brands do. This one is type-led: an Instrument Serif wordmark with the
// counter of the K carrying the heat, set on a strict baseline. Serif wordmark +
// sans UI is the pairing a real studio would pick, not a gradient badge.
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const { Resvg } = require('@resvg/resvg-js');
const { ROOT, ensureDir } = require('./lib');

// resvg only embeds raw sfnt fonts, so the identity uses TTF copies of the woff2 files
const F = '/tmp/build/ttfs';
const FONTS = {
  serif: `${F}/instrument-serif.ttf`,
  sans: `${F}/inter-tight-500.ttf`,
  mono: `${F}/jetbrains-mono.ttf`,
};

const C = {
  ink: '#0B0C0E',
  paper: '#F2EDE4',
  ember: '#D8542A',
  emberHot: '#F0743A',
  kiln: '#8A8578',
  smoke: '#4A4A46',
};

const face = (file, family) =>
  `@font-face{font-family:'${family}';src:url(data:font/woff;base64,${fs
    .readFileSync(file)
    .toString('base64')}) format('woff');}`;

// No @font-face: pass the TTFs to resvg directly and reference their real family names.
const css = () => '';
const FAM = { serif: 'Instrument Serif', sans: 'Inter Tight', mono: 'JetBrains Mono' };

function raster(markup, width) {
  const r = new Resvg(markup, {
    fitTo: { mode: 'width', value: width },
    font: {
      fontFiles: [FONTS.serif, FONTS.sans, FONTS.mono],
      loadSystemFonts: false,
      defaultFontFamily: FAM.serif,
    },
  });
  return r.render().asPng();
}

const svg = (w, h, body, bg = null) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${
    bg ? `<rect width="${w}" height="${h}" fill="${bg}"/>` : ''
  }${body}</svg>`;

async function write(rel, markup, w, h, { png = true } = {}) {
  const out = path.join(ROOT, rel);
  ensureDir(path.dirname(out));
  fs.writeFileSync(out, markup);
  if (png) {
    fs.writeFileSync(out.replace(/\.svg$/, '.png'), raster(markup, w));
  }
  return rel;
}

/* ------------------------------------------------------------------ mark
   The icon is the wordmark's first letter, cut: a serif K whose upper arm is
   replaced by a filled ember wedge — reads as a maker's stamp at 16px.
*/
function iconMark(px = 1024, { bg = C.ink, fg = C.paper, accent = C.ember } = {}) {
  const s = px / 1024;
  return svg(
    px,
    px,
    `<g transform="translate(${px / 2},${px / 2})">
      <rect x="${-352 * s}" y="${-352 * s}" width="${704 * s}" height="${704 * s}" rx="${150 * s}" fill="${bg}"/>
      <text x="${-14 * s}" y="${228 * s}" font-family="Instrument Serif" font-size="${600 * s}" fill="${fg}" text-anchor="middle">K</text>
      <path d="M ${96 * s} ${-236 * s} L ${238 * s} ${-236 * s} L ${152 * s} ${-104 * s} Z" fill="${accent}"/>
    </g>`,
    null
  );
}

/* ------------------------------------------------------------------ wordmark */
function wordmark(width = 2400, { dark = true } = {}) {
  const h = Math.round(width * 0.3);
  const fg = dark ? C.paper : C.ink;
  return svg(
    width,
    h,
    `${css()}
    <text x="${width * 0.035}" y="${h * 0.70}" font-family="Instrument Serif" font-size="${width * 0.235}" letter-spacing="${width * 0.006}" fill="${fg}">KILN</text>
    <circle cx="${width * 0.905}" cy="${h * 0.245}" r="${width * 0.0085}" fill="${C.ember}"/>`,
    null
  );
}

/* ------------------------------------------------------------------ lockup */
function lockup(width = 2400, { dark = true } = {}) {
  const h = Math.round(width * 0.19);
  const fg = dark ? C.paper : C.ink;
  const sub = dark ? C.kiln : '#6E6A60';
  return svg(
    width,
    h,
    `${css()}
    <g transform="translate(${width * 0.045},${h * 0.5})">
      <text x="0" y="${h * 0.115}" font-family="Instrument Serif" font-size="${width * 0.098}" letter-spacing="${width * 0.004}" fill="${fg}">KILN</text>
      <rect x="${width * 0.305}" y="${-h * 0.22}" width="${width * 0.0016}" height="${h * 0.44}" fill="${C.ember}"/>
      <text x="${width * 0.33}" y="${-h * 0.005}" font-family="Inter Tight" font-size="${width * 0.0165}" letter-spacing="${width * 0.0022}" fill="${fg}">INTERACTIVE ARCHITECTURE</text>
      <text x="${width * 0.33}" y="${h * 0.055}" font-family="JetBrains Mono" font-size="${width * 0.0125}" letter-spacing="${width * 0.002}" fill="${sub}">blender · three.js · react</text>
    </g>`,
    null
  );
}

/* ------------------------------------------------------------------ favicon */
function favicon(px = 64) {
  return svg(
    px,
    px,
    `<rect width="${px}" height="${px}" rx="${px * 0.22}" fill="${C.ink}"/>
     <text x="${px * 0.5}" y="${px * 0.76}" font-family="Georgia, 'Times New Roman', serif" font-size="${px * 0.78}" fill="${C.paper}" text-anchor="middle">K</text>
     <path d="M ${px * 0.6} ${px * 0.14} L ${px * 0.84} ${px * 0.14} L ${px * 0.68} ${px * 0.38} Z" fill="${C.ember}"/>`
  );
}

async function main() {
  const log = [];
  log.push(await write('brand/logo/kiln-icon.svg', iconMark(1024), 1024));
  log.push(await write('brand/logo/kiln-icon-paper.svg', iconMark(1024, { bg: C.paper, fg: C.ink, accent: C.ember }), 1024));
  log.push(await write('brand/logo/kiln-wordmark.svg', wordmark(2400, { dark: true }), 2400));
  log.push(await write('brand/logo/kiln-wordmark-dark.svg', wordmark(2400, { dark: false }), 2400));
  log.push(await write('brand/logo/kiln-lockup.svg', lockup(2400, { dark: true }), 2400));
  log.push(await write('brand/logo/kiln-lockup-dark.svg', lockup(2400, { dark: false }), 2400));
  log.push(await write('brand/logo/kiln-favicon.svg', favicon(64), 64));
  console.log(log.join('\n'));
  for (const f of log) console.log(' -', f);
}

if (require.main === module) main().catch((e) => { console.error(e); process.exit(1); });
module.exports = { iconMark, wordmark, lockup, favicon, C, css, FONTS };
