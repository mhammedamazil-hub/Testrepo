// LUMENFORGE — brand kit generator (mark, lockups, exports, stationery)
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const { ROOT, C, FONT_FILES, ensureDir, write, raster, svgOpen, defs } = require('./lib');

const css = () => {
  const f = (p, n, extra = '') =>
    `@font-face{font-family:'${n}';src:url(data:font/woff;base64,${fs.readFileSync(p).toString('base64')}) format('woff');${extra}}`;
  return `<style>
    ${f(FONT_FILES.grotesk400, 'g4')}
    ${f(FONT_FILES.grotesk, 'g5')}
    ${f(FONT_FILES.grotesk700, 'g7')}
    ${f(FONT_FILES.inter, 'i4')}
    ${f(FONT_FILES.mono, 'm4')}
  </style>`;
};

/* ---------- isometric geometry ---------- */
const K = 0.8660254;
const iso = (x, y, z, u = 1, ox = 0, oy = 0) => [ox + (x - z) * K * u, oy + ((x + z) * 0.5 - y) * u];
const pt = (p) => p.map((q) => `${q[0].toFixed(2)},${q[1].toFixed(2)}`).join(' ');

/** A box in isometric space -> visible top / right(+x) / left(+z) faces. */
function box(x0, x1, z0, z1, y0, y1, u, ox, oy) {
  const top = [iso(x0, y1, z0, u, ox, oy), iso(x1, y1, z0, u, ox, oy), iso(x1, y1, z1, u, ox, oy), iso(x0, y1, z1, u, ox, oy)];
  const right = [iso(x1, y1, z0, u, ox, oy), iso(x1, y1, z1, u, ox, oy), iso(x1, y0, z1, u, ox, oy), iso(x1, y0, z0, u, ox, oy)];
  const left = [iso(x0, y1, z1, u, ox, oy), iso(x1, y1, z1, u, ox, oy), iso(x1, y0, z1, u, ox, oy), iso(x0, y0, z1, u, ox, oy)];
  return { top, right, left };
}

/** The LUMENFORGE mark: an isometric "L" forged from light-bearing beams. */
function mark({ size = 512, glow = true, mono = null, pad = 0.16 } = {}) {
  const u = (size * (1 - pad * 2)) / 11.4; // beam span ~11.4u wide
  const ox = size * 0.5;
  const oy = size * 0.5 - 1.15 * u;
  const W = 2.5; // beam thickness / foot height
  const H = 8.2; // total height
  const FU = 7.0; // foot length
  const FZ = 2.5; // depth

  // foot on the ground, vertical beam standing on the foot's heel
  const foot = box(0, FU, 0, FZ, 0, W, u, ox, oy);
  const beam = box(0, W, 0, FZ, W, H, u, ox, oy);

  const grad = (id, a, b, c) =>
    `<linearGradient id="${id}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${a}"/><stop offset=".6" stop-color="${b}"/><stop offset="1" stop-color="${c}"/></linearGradient>`;

  const topFill = mono ? mono : 'url(#mTop)';
  const rightFill = mono ? mono : 'url(#mRight)';
  const leftFill = mono ? mono : 'url(#mLeft)';

  const ember = iso(FU, W, FZ * 0.5, u, ox, oy);
  const ember2 = iso(W, H, FZ * 0.5, u, ox, oy);
  const glowC = iso(FU * 0.52, W * 0.9, FZ * 0.5, u, ox, oy);

  return `${svgOpen(size, size)}
  <defs>
    ${grad('mTop', '#FFFFFF', '#EDE7DA', '#BFB7A6')}
    ${grad('mRight', '#FFB07A', C.forge, '#C9340A')}
    ${grad('mLeft', '#3A2A20', '#1B1512', '#100C0A')}
    <radialGradient id="mGlow" cx=".5" cy=".5" r=".5">
      <stop offset="0" stop-color="#FFD9A8" stop-opacity=".95"/>
      <stop offset=".35" stop-color="${C.forge}" stop-opacity=".55"/>
      <stop offset="1" stop-color="${C.forge}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  ${glow && !mono ? `<circle cx="${glowC[0]}" cy="${glowC[1]}" r="${size * 0.34}" fill="url(#mGlow)" opacity=".55"/>` : ''}
  <polygon points="${pt(foot.left)}" fill="${leftFill}"/>
  <polygon points="${pt(foot.right)}" fill="${rightFill}"/>
  <polygon points="${pt(foot.top)}" fill="${topFill}"/>
  <polygon points="${pt(beam.left)}" fill="${leftFill}"/>
  <polygon points="${pt(beam.right)}" fill="${rightFill}"/>
  <polygon points="${pt(beam.top)}" fill="${topFill}"/>
  ${glow && !mono ? `<circle cx="${ember[0]}" cy="${ember[1]}" r="${size * 0.013}" fill="#FFF3E2"/>
  <circle cx="${ember2[0]}" cy="${ember2[1]}" r="${size * 0.007}" fill="${C.arc}" opacity=".9"/>` : ''}
  </svg>`;
}

/* ---------- wordmark ---------- */
function wordmark({ width = 1600, dark = true, tag = true } = {}) {
  const h = width * 0.24;
  const fg = dark ? C.bone : '#0A0B0F';
  const s = width / 1600;
  return `${svgOpen(width, h)}${css()}
  <defs>
    <linearGradient id="wForge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#FFA36B"/><stop offset=".55" stop-color="${C.forge}"/><stop offset="1" stop-color="#FF4D0A"/>
    </linearGradient>
  </defs>
  <text x="${8 * s}" y="${128 * s}" font-family="g7" font-size="${104 * s}" letter-spacing="${7 * s}" fill="${fg}">LUMEN<tspan fill="url(#wForge)">FORGE</tspan></text>
  ${tag ? `<text x="${12 * s}" y="${186 * s}" font-family="m4" font-size="${25 * s}" letter-spacing="${11.5 * s}" fill="${dark ? C.arc : '#0E7C6B'}">INTERACTIVE 3D · WEB · MOTION</text>` : ''}
  </svg>`;
}

function lockup({ w = 2000, dark = true } = {}) {
  const h = w * 0.28;
  const m = 260;
  const fg = dark ? C.bone : '#0A0B0F';
  return `${svgOpen(w, h)}${css()}
  <defs>
    <linearGradient id="lForge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#FFA36B"/><stop offset=".55" stop-color="${C.forge}"/><stop offset="1" stop-color="#FF4D0A"/>
    </linearGradient>
  </defs>
  <g transform="translate(20,${(h - m) / 2})">${mark({ size: m, pad: 0.08 }).replace(/^<svg[^>]*>/, '').replace(/<\/svg>$/, '')}</g>
  <g transform="translate(${m + 44},${h * 0.34})">
    <text x="0" y="${86 * (w / 2000)}" font-family="g7" font-size="${92 * (w / 2000)}" letter-spacing="${6 * (w / 2000)}" fill="${fg}">LUMEN<tspan fill="url(#lForge)">FORGE</tspan></text>
    <text x="4" y="${140 * (w / 2000)}" font-family="m4" font-size="${22 * (w / 2000)}" letter-spacing="${9 * (w / 2000)}" fill="${dark ? C.arc : '#0E7C6B'}">WEBSITES YOU CAN WALK THROUGH</text>
  </g>
  </svg>`;
}

/* ---------- app icon with rounded plate ---------- */
function appIcon(size = 512, bg = C.ink) {
  const r = size * 0.225;
  return `${svgOpen(size, size)}<defs>
    <clipPath id="rr"><rect width="${size}" height="${size}" rx="${r}" ry="${r}"/></clipPath>
    <radialGradient id="plate" cx=".3" cy=".2" r="1">
      <stop offset="0" stop-color="#181C26"/><stop offset=".6" stop-color="#0A0C12"/><stop offset="1" stop-color="#05060A"/>
    </radialGradient>
  </defs>
  <g clip-path="url(#rr)">
    <rect width="${size}" height="${size}" fill="url(#plate)"/>
    <g transform="translate(${size * 0.5},${size * 0.5}) scale(0.94) translate(${-size * 0.5},${-size * 0.5})">
      ${mark({ size, pad: 0.2 }).replace(/^<svg[^>]*>/, '').replace(/<\/svg>$/, '')}
    </g>
  </g></svg>`;
}

async function main() {
  const out = [];
  // ---- master vectors ----
  out.push(write('brand/logo/lumenforge-mark.svg', mark({ size: 512 })));
  out.push(write('brand/logo/lumenforge-mark-mono.svg', mark({ size: 512, glow: false, mono: '#EDE7DA' })));
  out.push(write('brand/logo/lumenforge-icon.svg', appIcon(512)));
  out.push(write('brand/logo/lumenforge-wordmark.svg', wordmark({ width: 1600 })));
  out.push(write('brand/logo/lumenforge-wordmark-dark.svg', wordmark({ width: 1600, dark: false, tag: false })));
  out.push(write('brand/logo/lumenforge-lockup.svg', lockup({ w: 2000 })));
  out.push(write('brand/logo/lumenforge-lockup-dark.svg', lockup({ w: 2000, dark: false })));

  // ---- raster exports ----
  const jobs = [
    ['brand/exports/logo-mark-1024.png', mark({ size: 1024 })],
    ['brand/exports/logo-mark-512.png', mark({ size: 512 })],
    ['brand/exports/logo-mark-mono-512.png', mark({ size: 512, glow: false, mono: '#EDE7DA' })],
    ['brand/exports/icon-1024.png', appIcon(1024)],
    ['brand/exports/icon-512.png', appIcon(512)],
    ['brand/exports/wordmark-2400.png', wordmark({ width: 2400 })],
    ['brand/exports/wordmark-dark-2400.png', wordmark({ width: 2400, dark: false, tag: false })],
    ['brand/exports/lockup-2400.png', lockup({ w: 2400 })],
    ['brand/exports/lockup-dark-2400.png', lockup({ w: 2400, dark: false })],
  ];
  for (const [rel, svg] of jobs) {
    const p = path.join(ROOT, rel);
    ensureDir(path.dirname(p));
    await sharp(Buffer.from(svg), { density: 300 }).png({ compressionLevel: 9 }).toFile(p);
    out.push(p);
  }

  // favicons
  const fav = appIcon(64);
  await sharp(Buffer.from(appIcon(256)), { density: 300 }).resize(32).png().toFile(path.join(ROOT, 'brand/exports/favicon-32.png'));
  await sharp(Buffer.from(appIcon(256)), { density: 300 }).resize(180).png().toFile(path.join(ROOT, 'brand/exports/apple-touch-icon.png'));
  write('brand/exports/favicon.svg', fav);
  out.push(path.join(ROOT, 'brand/exports/favicon-32.png'));

  console.log(`brand: ${out.length} files`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

module.exports = { mark, wordmark, lockup, appIcon, css, iso, box };
