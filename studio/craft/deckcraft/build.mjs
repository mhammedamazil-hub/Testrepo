// DeckCraft build for the KILN deck.
//
// Runs in CI. Two reasons it is written this way:
//
//  1. DeckCraft's parameter schema changes between releases, and one unknown key
//     aborts the whole `run` (exit 1, no file written). So we ask the CLI for its
//     own command schema first and drop any parameter it does not advertise. The
//     build reports what it dropped rather than failing silently.
//  2. A failing slide should not take the other eleven with it: each slide is its
//     own `run --in --save`, so a bad slide is skipped and named in the log.
//
// Output: studio/craft/out/kiln-deckcraft.pptx + .pdf, plus a JSON report.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

process.on('uncaughtException', (e) => {
  console.error('FATAL', e && e.stack || e);
  if (e && e.stderr) console.error('stderr:', String(e.stderr).slice(0, 4000));
  process.exit(1);
});

const OUT = 'studio/craft/out';
const PPTX = path.join(OUT, 'kiln-deckcraft.pptx');
const PDF = path.join(OUT, 'kiln-deckcraft.pdf');
const report = { dropped: {}, skippedSlides: [], failures: {}, commands: 0 };

fs.mkdirSync(OUT, { recursive: true });

const craft = (args) => execFileSync('npx', ['pi-craft', 'deckcraft', 'exec', ...args], {
  encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 64 * 1024 * 1024,
});

/* ── the CLI's own schema ─────────────────────────────────────────────────── */
let schema = {};
try {
  const raw = craft(['commands']).trim();
  const at = raw.lastIndexOf('[\n');            // the JSON array, not the prose above it
  const arr = JSON.parse(at >= 0 ? raw.slice(at) : raw);
  for (const c of arr) {
    const keys = new Set(Object.keys(c.params || c.parameters || {}));
    schema[c.id] = keys.size ? keys : null; // null = schema unknown, pass through
  }
} catch (e) {
  console.warn('schema lookup failed, passing parameters through:', e.message);
}

const WARNED = new Set();
function cmd(id, params = {}) {
  const allowed = schema[id];
  if (allowed) {
    for (const k of Object.keys(params)) {
      if (!allowed.has(k)) {
        (report.dropped[id] ||= new Set()).add(k);
        if (!WARNED.has(id + k)) { WARNED.add(id + k); console.warn(`  ${id}: dropping unsupported "${k}"`); }
        delete params[k];
      }
    }
  }
  return `${id}=${JSON.stringify(params)}`;
}

/* ── preset discovery ─────────────────────────────────────────────────────── */
// shape.insert takes a preset name from a fixed list, and the list is not stable
// across releases. Ask the CLI before drawing anything.
let RECT = 'rect';
try {
  console.log('--- describe shape.insert ---');
  try { console.log(craft(['describe', 'shape.insert'])); } catch (e) { console.log('describe failed'); }
  const out = craft(['run', '--cmd', 'slide.new={"layout":"blank"}', '--cmd', 'shape.presets={}', '--print']);
  const names = [...out.matchAll(/"([a-zA-Z0-9 _-]+)"/g)].map((m) => m[1]);
  console.log('shape presets seen:', names.slice(0, 40).join(', '));
  const pick = names.find((n) => /^(rect|rectangle|square|box)$/i.test(n))
    || names.find((n) => /rect|square|box/i.test(n));
  if (pick) RECT = pick;
} catch (e) {
  console.warn('preset discovery failed, using', RECT, String(e.stderr || e.message).slice(0, 300));
}
console.log('using preset:', RECT);

const C = {
  ink: '0B0C0E', paper: 'F2EDE4', ember: 'D8542A', emberLit: 'EE7541',
  kiln: '8A8578', smoke: '55544F', body: 'A9A398',
};

const box = (text, rect, o = {}) => cmd('insert.textBox', {
  text, rect,
  fontSize: o.size || 11,
  color: o.color || C.body,
  font: o.font || 'Arial',
  bold: !!o.bold,
  ...(o.track ? { charSpacing: o.track } : {}),
});
const head = (text, x, y, w, size, h = 60) => box(text, [x, y, w, h], { size, color: C.paper, font: 'Georgia' });
const kick = (text, x, y, w = 400) => box(text.toUpperCase(), [x, y, w, 14], { size: 8, color: C.ember, font: 'Consolas', track: 2 });
const bodyT = (text, x, y, w, h, size = 11, color = C.body) => box(text, [x, y, w, h], { size, color });
const foot = (t) => box(t.toUpperCase(), [72, 506, 500, 12], { size: 7, color: C.smoke, font: 'Consolas', track: 1.5 });
const num = (n) => box(String(n).padStart(2, '0'), [888, 506, 30, 12], { size: 7, color: C.smoke, font: 'Consolas' });
const slideNew = (name) => cmd('slide.new', { layout: 'blank', ...(name ? { title: name } : {}) });
const ink = () => cmd('shape.insert', { preset: RECT, rect: [0, 0, 960, 540], fill: `#${C.ink}` });
const rule = (y) => cmd('shape.insert', { preset: RECT, rect: [72, y, 816, 1], fill: '#26272B' });
const pic = (p, rect) => (schema['insert.picture'] === undefined ? null
  : cmd('insert.picture', { path: p, rect }));

const R = 'studio/brand/renders';
const slides = [];

/* 01 cover */
slides.push({
  name: 'cover',
  cmds: [
    slideNew('Cover'),
    ink(),
    kick('KILN · INTERACTIVE ARCHITECTURE', 72, 72),
    head('Rooms,', 72, 286, 620, 62, 76),
    head('not pages.', 72, 350, 620, 62, 76),
    bodyT('An interactive architecture studio. We model the space in Blender, light it with bpy automation and ship it in React — under two megabytes, sixty frames on a phone.', 72, 442, 430, 70),
    foot('studio@kiln.studio · kiln.studio · +44 20 7946 0812'), num(1),
  ],
});

/* 02 problem */
slides.push({
  name: 'problem',
  cmds: [
    slideNew('The problem'),
    ink(), kick('01 · the problem', 72, 72),
    head('A page is a photograph', 72, 104, 760, 38, 46),
    head('of a place.', 72, 146, 760, 38, 46),
    bodyT('Customers do not read a spec sheet. They want to know what the room feels like at four in the afternoon, whether the sofa fits, how the light lands on the plaster. Every product site we are asked to fix has the same failure: it describes the object and withholds the room.', 72, 216, 520, 110),
    bodyT('We build the room first and photograph nothing.', 72, 344, 520, 24, 12, C.paper),
    foot('the problem'), num(2),
  ],
});

/* 03 what we make */
const offers = [
  ['commerce', 'A gallery you can shop', 'Every piece is a real object: turn it, place it, buy it.', 'work-atelier.png'],
  ['property', 'Every unit walkable', 'Sun studies baked in Blender, forty-eight apartments on one link.', 'work-meridian.png'],
  ['launch', 'A moment, not a page', 'A scroll-driven reveal that turns a spec sheet into something people forward.', 'work-kinetic.png'],
];
slides.push({
  name: 'work',
  cmds: [
    slideNew('What we build'),
    ink(), kick('the work', 72, 72),
    head('Three rooms, three trades.', 72, 104, 816, 34, 44),
    rule(170),
    ...offers.flatMap(([k, h, t, img], i) => {
      const x = 72 + i * 272;
      return [
        pic(`${R}/${img}`, [x, 196, 248, 186]),
        kick(k, x, 398, 220), head(h, x, 414, 248, 18, 40),
        bodyT(t, x, 458, 230, 40, 9.5),
      ].filter(Boolean);
    }),
    foot('what we build'), num(3),
  ],
});

/* 04 method */
const method = [
  ['01', 'Blockout', 'Camera path, scale and light direction locked before a single texture exists.'],
  ['02', 'Forge', 'bpy builds the hero geometry, bakes lighting to lightmaps and exports gLTF with LOD chains.'],
  ['03', 'Budget', 'Draco and KTX2 compression against a first-load ceiling you sign off before modelling starts.'],
  ['04', 'Wire', 'React Three Fiber scenes, scroll timelines and a CMS your team can edit without a deploy.'],
  ['05', 'Harden', 'GPU tiers, WebGL fallbacks, SEO-safe HTML and a Lighthouse gate in continuous integration.'],
];
slides.push({
  name: 'method',
  cmds: [
    slideNew('Method'),
    ink(), kick('method', 72, 72),
    head('Blockout · Forge · Budget · Wire · Harden', 72, 104, 816, 32, 42),
    bodyT('Five stages, each with an artefact you can open and a number it has to hit. If a scene cannot hold the budget, it does not ship.', 72, 158, 700, 30, 10.5),
    ...method.flatMap(([n, name, copy], i) => {
      const y = 214 + i * 52;
      return [
        box(n, [72, y, 30, 14], { size: 8, color: C.ember, font: 'Consolas' }),
        head(name, 110, y - 2, 160, 14, 20),
        bodyT(copy, 270, y, 630, 44, 9.5),
      ];
    }),
    pic(`${R}/hero-2400x1600.png`, [72, 470, 816, 0.1]),
    foot('how it is made'), num(4),
  ].filter(Boolean),
});

/* 05–07 cases */
const cases = [
  ['case 01 · commerce', 'Atelier Nova', 'A gallery where every piece is a real object you turn, place and buy. Product photography replaced by a room you can walk into.', 'work-atelier.png', 5,
    [['+38%', 'add to cart'], ['1.9 MB', 'first load'], ['7', 'draw calls']]],
  ['case 02 · property', 'Meridian Towers', 'Forty-eight apartments, each lit for its real orientation. Sun studies computed in Blender and baked to a lightmap, so a phone draws the floor plan in one pass.', 'work-meridian.png', 6,
    [['3.1×', 'session length'], ['48', 'units walkable'], ['0', 'render farm']]],
  ['case 03 · launch', 'Kinetic Labs', 'A scroll-driven reveal that turns a spec sheet into something people forward. The launch film is rendered from the same geometry, so the ad and the site are the same object.', 'work-kinetic.png', 7,
    [['2.4M', 'launch film views'], ['6', 'weeks to ship'], ['1', 'source of truth']]],
];
for (const [k, title, copy, img, n, stats] of cases) {
  slides.push({
    name: `case-${n}`,
    cmds: [
      slideNew(title),
      ink(),
      pic(`${R}/${img}`, [520, 0, 440, 540]),
      kick(k, 72, 72), head(title, 72, 104, 420, 34, 44),
      bodyT(copy, 72, 170, 410, 90, 10.5),
      ...stats.flatMap(([v, label], i) => {
        const y = 330 + i * 50;
        return [
          head(v, 72, y, 120, 24, 34),
          box(label.toUpperCase(), [200, y + 10, 220, 14], { size: 7, color: C.kiln, font: 'Consolas', track: 1.5 }),
        ];
      }),
      foot('rendered in Blender · shipped in React'), num(n),
    ].filter(Boolean),
  });
}

/* 08 engineering */
slides.push({
  name: 'engineering',
  cmds: [
    slideNew('Engineering'),
    ink(), kick('engineering', 72, 72),
    head('Beauty that survives', 72, 104, 600, 36, 44),
    head('a mid-range phone.', 72, 144, 600, 36, 44),
    bodyT('Every build is measured on a Moto G, not a MacBook. The numbers below are the gate, not the aspiration.', 72, 208, 440, 50, 10.5),
    head('<2.0 MB', 72, 288, 200, 28, 36),
    box('FIRST LOAD, COMPRESSED', [72, 324, 280, 12], { size: 7, color: C.kiln, font: 'Consolas', track: 1.4 }),
    head('60 fps', 344, 288, 200, 28, 36),
    box('SUSTAINED, MID-TIER GPU', [344, 324, 280, 12], { size: 7, color: C.kiln, font: 'Consolas', track: 1.4 }),
    head('≤8', 72, 380, 200, 28, 36),
    box('DRAW CALLS IN THE HERO SCENE', [72, 416, 280, 12], { size: 7, color: C.kiln, font: 'Consolas', track: 1.4 }),
    head('95+', 344, 380, 200, 28, 36),
    box('LIGHTHOUSE, MOBILE', [344, 416, 280, 12], { size: 7, color: C.kiln, font: 'Consolas', track: 1.4 }),
    pic(`${R}/detail-2400x1350.png`, [560, 288, 328, 185]),
    foot('the budget'), num(8),
  ].filter(Boolean),
});

/* 09 studio */
slides.push({
  name: 'studio',
  cmds: [
    slideNew('The studio'),
    ink(), kick('the studio', 72, 72),
    head('Blender hands,', 72, 104, 480, 36, 44),
    head('browser discipline.', 72, 144, 480, 36, 44),
    bodyT('KILN is three people on purpose: an asset engineer writing bpy automation, a creative developer owning the WebGL layer, and a motion designer who ships the campaign with every build. One pipeline, no hand-off to a render farm.', 72, 208, 410, 100, 10.5),
    bodyT('Blender · bpy · Cycles', 72, 322, 320, 18, 10.5),
    bodyT('Three.js · React Three Fiber · gLTF', 72, 348, 320, 18, 10.5),
    bodyT('Draco · KTX2 · Playwright', 72, 374, 320, 18, 10.5),
    pic(`${R}/square-1600x1600.png`, [540, 250, 348, 348]),
    foot('three people, one pipeline'), num(9),
  ].filter(Boolean),
});

/* 10 rates */
const tiers = [
  ['spar', '$4,800', 'two weeks', 'One walkthrough scene · three art-directed stills · mobile and no-WebGL fallback · source handover', false],
  ['kiln · most commissioned', '$12,500', 'three to five weeks', 'Up to five rooms or products · bpy asset pipeline and lightmaps · launch kit: stills, loop, cuts', true],
  ['firing', '$3,900 / mo', 'rolling', 'Two new scenes per sprint · asset library upkeep · performance monitoring · monthly ad creative', false],
];
slides.push({
  name: 'rates',
  cmds: [
    slideNew('Rates'),
    ink(), kick('rates', 72, 72),
    head('Fixed scope. Fixed number.', 72, 104, 816, 34, 44),
    bodyT('Every tier includes a written load budget, a Lighthouse gate in CI, source handover and a WebGL fallback.', 72, 158, 700, 24, 10.5),
    ...tiers.flatMap(([k, price, term, what, hot], i) => {
      const x = 72 + i * 272;
      return [
        kick(k, x, 212, 240),
        head(price, x, 228, 248, 26, 34),
        box(term.toUpperCase(), [x, 266, 240, 12], { size: 7, color: hot ? C.emberLit : C.smoke, font: 'Consolas', track: 1.4 }),
        bodyT(what, x, 290, 240, 70, 9.5),
      ];
    }),
    foot('pricing'), num(10),
  ],
});

/* 11 provenance */
slides.push({
  name: 'provenance',
  cmds: [
    slideNew('Provenance'),
    ink(), kick('how it holds together', 72, 72),
    head('One set,', 72, 104, 480, 36, 44),
    head('many pictures.', 72, 144, 480, 36, 44),
    bodyT('Every KILN build starts as a real Blender scene. That single decision pays three times: the site is built correctly, the launch film is rendered from the same geometry, and the ad stills are photographs rather than illustrations. One asset, one invoice, three channels.', 72, 208, 410, 110, 10.5),
    bodyT('No stock imagery. No mock-ups. No lorem ipsum in the delivered build.', 72, 336, 410, 30, 10.5, C.paper),
    pic(`${R}/keyart-1600x2000.png`, [540, 0, 420, 540]),
    foot('provenance'), num(11),
  ].filter(Boolean),
});

/* 12 next */
slides.push({
  name: 'next',
  cmds: [
    slideNew('Next step'),
    ink(), kick('next step', 72, 72),
    head('Send the product.', 72, 140, 700, 44, 54),
    head("We'll send the room.", 72, 194, 700, 44, 54),
    bodyT('Within two working days you get a fixed price, a camera path and a load budget — no discovery invoice, no retainer to start.', 72, 288, 460, 60, 12),
    head('studio@kiln.studio', 72, 392, 400, 20, 30),
    kick('+44 20 7946 0812 · kiln.studio', 72, 424),
    foot('kiln · interactive architecture'), num(12),
  ],
});

/* ── build ────────────────────────────────────────────────────────────────── */
function run(args, label) {
  try {
    craft(args);
    return true;
  } catch (e) {
    const detail = String(e.stderr || e.message || '').split('\n').filter(Boolean).slice(0, 6).join(' | ');
    console.error(`  ✗ ${label}: ${detail}`);
    (report.failures[label] ||= []).push(detail);
    return false;
  }
}

// start with a truly empty presentation (plain file.new still yields an empty slide)
run(['run', '--cmd', 'file.new={"blank":true}', '--save', PPTX], 'init');

for (const s of slides) {
  const args = ['run', '--in', PPTX, '--save', PPTX, ...s.cmds.flatMap((c) => ['--cmd', c])];
  report.commands += s.cmds.length;
  if (!run(args, s.name)) {
    report.failures[s.name] ||= [];
    if (report.failures[s.name].length === 0) report.failures[s.name].push('see log');
    report.skippedSlides.push(s.name);
    // rebuild the reference file if the failed run corrupted it
    if (!fs.existsSync(PPTX)) run(['run', '--cmd', 'file.new={"blank":true}', '--save', PPTX], 're-init');
  } else {
    console.log(`  ✓ ${s.name} (${s.cmds.length} commands)`);
  }
}

run(['info', PPTX], 'info');
run(['convert', PPTX, PDF], 'convert');

for (const k of Object.keys(report.dropped)) report.dropped[k] = [...report.dropped[k]];
report.slides = slides.length;
report.hasDeck = fs.existsSync(PPTX);
report.hasPdf = fs.existsSync(PDF);
fs.writeFileSync(path.join(OUT, 'deckcraft-report.json'), JSON.stringify(report, null, 2));
console.log('deckcraft report:', JSON.stringify({ ...report, commands: report.commands }, null, 1));
if (report.skippedSlides.length) process.exitCode = 2;
