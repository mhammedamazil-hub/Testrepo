// KILN — shared build helpers
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const ROOT = path.resolve(__dirname, '..');
const FONTS = '/tmp/build/node_modules/@fontsource';
const FONT_FILES = {
  serif: `${FONTS}/instrument-serif/files/instrument-serif-latin-400-normal.woff`,
  text: `${FONTS}/inter-tight/files/inter-tight-latin-400-normal.woff`,
  text500: `${FONTS}/inter-tight/files/inter-tight-latin-500-normal.woff`,
  mono: `${FONTS}/jetbrains-mono/files/jetbrains-mono-latin-400-normal.woff`,
};

// KILN palette — warm ink, paper, ember. No cool greys, no cyan, no violet.
const C = {
  ink: '#0B0C0E',
  ink2: '#121316',
  panel: '#141518',
  paper: '#F2EDE4',
  bone: '#F2EDE4',
  ember: '#D8542A',
  emberLit: '#EE7541',
  forge: '#D8542A',   // legacy alias
  kiln: '#8A8578',
  arc: '#8A8578',     // legacy alias, now a warm neutral
  muted: '#9A9488',
  smoke: '#55544F',
  rule: '#26272B',
};

const P = (...names) => names.map((n) => path.join(ROOT, n));

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

function write(rel, contents) {
  const p = path.join(ROOT, rel);
  ensureDir(path.dirname(p));
  fs.writeFileSync(p, contents);
  return p;
}

/** Render an SVG string to PNG / JPG / WEBP at a scale factor. */
async function raster(svg, outRel, { scale = 1, width, format } = {}) {
  const p = path.join(ROOT, outRel);
  ensureDir(path.dirname(p));
  const target = width ? sharp(Buffer.from(svg), { density: 384 }).resize({ width }) : sharp(Buffer.from(svg), { density: 96 * scale * 4 });
  let img = target;
  const ext = (format || path.extname(p).slice(1)).toLowerCase();
  if (ext === 'jpg' || ext === 'jpeg') img = img.jpeg({ quality: 92, mozjpeg: true });
  else if (ext === 'webp') img = img.webp({ quality: 92 });
  else img = img.png({ compressionLevel: 9 });
  await img.toFile(p);
  return p;
}

const svgOpen = (w, h, extra = '') =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" ${extra}>`;

function defs({ grain = true } = {}) {
  return `<defs>
    <linearGradient id="forge" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FF8A4C"/><stop offset=".55" stop-color="${C.forge}"/><stop offset="1" stop-color="#D93A0B"/>
    </linearGradient>
    <linearGradient id="arc" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0" stop-color="#0FB39B"/><stop offset="1" stop-color="${C.arc}"/>
    </linearGradient>
    <linearGradient id="bone" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#C9C2B2"/>
    </linearGradient>
    <radialGradient id="glow" cx=".5" cy=".5" r=".5">
      <stop offset="0" stop-color="${C.forge}" stop-opacity=".55"/>
      <stop offset=".6" stop-color="${C.arc}" stop-opacity=".12"/>
      <stop offset="1" stop-color="${C.arc}" stop-opacity="0"/>
    </radialGradient>
    ${grain ? `<filter id="noise"><feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="linear" slope=".06"/></feComponentTransfer></filter>` : ''}
  </defs>`;
}

module.exports = { ROOT, C, FONT_FILES, ensureDir, write, raster, svgOpen, defs, P };
