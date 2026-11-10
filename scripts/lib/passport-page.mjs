/**
 * The customer-facing lot passport page and the verification page.
 *
 * Kept out of gen/ because these are responses, not build artifacts: a passport has to
 * resolve against the live queue, otherwise it is a static page that will drift from the
 * record it claims to describe.
 */
import { buildPassport, verifyCode } from './passport.mjs';

const esc = s =>
  String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const SHELL = (title, body) => `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)} — Kollam Pepper Co</title>
<style>
  :root{--ink:#1c211c;--green:#2e4a3b;--accent:#c05a2e;--paper:#f4efe6;--sand:#e0d6c4;--muted:#6b7268;--ok:#2f7d4f;--bad:#a83232}
  *{box-sizing:border-box}
  body{margin:0;background:var(--paper);color:var(--ink);
       font-family:ui-sans-serif,-apple-system,"Segoe UI",Inter,Helvetica,Arial,sans-serif;line-height:1.6}
  .wrap{width:min(760px,94vw);margin:0 auto}
  header{border-bottom:1px solid var(--sand);background:#fffdf8}
  header .wrap{display:flex;align-items:center;justify-content:space-between;padding:16px 0}
  .brand{font-weight:800;letter-spacing:.22em;font-size:14px}
  .brand span{color:var(--accent)}
  header a{font-size:13px;color:var(--muted);text-decoration:none}
  header a:hover{color:var(--ink)}
  h1{font-size:30px;letter-spacing:-.02em;margin:34px 0 4px}
  .lotno{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:15px;color:var(--muted);margin:0 0 26px}
  .code{background:var(--green);color:var(--paper);padding:20px 22px;margin:0 0 8px}
  .code span{display:block;font-size:10px;letter-spacing:.16em;text-transform:uppercase;opacity:.75;margin-bottom:6px}
  .code b{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:30px;letter-spacing:.08em;font-weight:700}
  table{width:100%;border-collapse:collapse;font-size:14px;background:#fffdf8;margin:18px 0 0}
  th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--sand)}
  th{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:600}
  td.v{font-family:ui-monospace,monospace;text-align:right}
  .ok{color:var(--ok);font-weight:600}
  .note{font-size:12px;color:var(--muted);line-height:1.6;margin:10px 0 0}
  .box{background:#fffdf8;border:1px solid var(--sand);border-left:5px solid var(--green);padding:16px 18px;margin:24px 0;font-size:13px}
  .box.bad{border-left-color:var(--bad)}
  .box.good{border-left-color:var(--ok)}
  footer{font-size:11px;color:var(--muted);padding:40px 0 60px;line-height:1.7}
  input{width:100%;font-family:ui-monospace,monospace;font-size:16px;padding:12px;border:1px solid var(--sand);background:#fff}
  button{background:var(--green);color:var(--paper);border:0;padding:13px 20px;font-size:12px;
         letter-spacing:.1em;text-transform:uppercase;font-weight:700;cursor:pointer;margin-top:10px}
  button:hover{background:var(--accent)}
</style>
</head>
<body>
<header><div class="wrap"><div class="brand">KOLLAM<span>·</span></div>
<div><a href="/">Storefront</a> &nbsp;·&nbsp; <a href="/passport">Check a lot</a></div></div></header>
<div class="wrap">${body}</div>
<footer><div class="wrap">
  Planning prototype. A passport proves that this page is the record behind the code on a bag;
  it does not by itself prove the laboratory was honest or that the sample came from the bag.
  Accreditation, sealed samples and chain of custody are what do that.
</div></footer>
</body></html>`;

/** What each panel field is, and the limit it is measured against. */
const ROWS = [
  ['grade', 'Grade', null],
  ['sieve_mm', 'Sieve', 'mm'],
  ['piperine_pct', 'Piperine', '%'],
  ['moisture_pct', 'Moisture', '%'],
  ['bulk_density_g_per_l', 'Bulk density', 'g/l'],
  ['aflatoxin_b1_ugkg', 'Aflatoxin B1', 'µg/kg · max 5.0'],
  ['aflatoxin_total_ugkg', 'Total aflatoxins', 'µg/kg · max 10.0'],
  ['ochratoxin_a_ugkg', 'Ochratoxin A', 'µg/kg · max 15'],
  ['lead_mgkg', 'Lead', 'mg/kg · max 0.6'],
  ['salmonella_25g', 'Salmonella', 'absent in 25 g'],
  ['ethylene_oxide', 'Ethylene oxide', 'not detected'],
  ['foreign_matter_pct', 'Foreign matter', '%'],
];

const NEGATIVE = /^(absent|not detected|notdetected|nd|none|< ?loq|< ?lod|negative|n\/d)$/i;

function isSafetyRow(field) {
  return ['aflatoxin_b1_ugkg', 'aflatoxin_total_ugkg', 'ochratoxin_a_ugkg', 'lead_mgkg', 'salmonella_25g', 'ethylene_oxide'].includes(field);
}

export function passportPage(entry) {
  const p = buildPassport(entry);
  const rows = ROWS.filter(([f]) => p.panel[f] !== undefined)
    .map(([field, label, unit]) => {
      const raw = p.panel[field];
      const shown = NEGATIVE.test(String(raw)) ? 'not detected' : raw;
      return `<tr><th scope="row">${esc(label)}</th><td class="v">${esc(shown)}${unit && typeof raw === 'number' ? ' ' + esc(unit.split(' · ')[0]) : ''}</td>
        <td style="color:var(--muted);font-size:12px">${esc(unit && unit.includes('·') ? unit.split(' · ')[1] : '')}</td></tr>`;
    })
    .join('');

  return SHELL(
    `Lot ${p.lot}`,
    `<h1>Lot passport</h1>
  <p class="lotno">${esc(p.lot)} · ${esc(p.grade ?? 'grade not stated')} · released ${esc(String(p.released_at).slice(0, 10))}</p>

  <div class="code"><span>Code printed on the bag</span><b>${esc(p.code)}</b></div>
  <p class="note">Check it against the bag. If the two do not match, the panel was altered after release.</p>

  <table>
    <thead><tr><th>Test</th><th style="text-align:right">Result</th><th>Limit</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>

  <div class="box good">
    <b>${esc(p.disposition)}</b> — cleared every limit in the specification. ${p.findings === 0 ? 'No findings of any kind.' : `${p.findings} finding(s) recorded; see the evidence log.`}
    <br><span class="note">Grower cluster: ${esc(p.supplier)}</span>
  </div>

  <div class="box">
    <b>What this code proves.</b> ${esc(p.claim)}<br><br>
    <b>What it does not.</b> ${esc(p.limit)}
  </div>

  <p class="note">Verify: <a href="/passport/${encodeURIComponent(p.lot)}/verify">open the check</a> ·
  machine-readable: <code>/api/passport/${esc(p.lot)}</code> ·
  the whole gate: <a href="/desk">lot desk</a></p>`
  );
}

export function verifyPage(entry, code) {
  const p = buildPassport(entry);
  const ok = verifyCode(entry, code);

  return SHELL(
    ok ? `Code matches ${p.lot}` : `Code does not match ${p.lot}`,
    `<h1>${ok ? 'Code matches' : 'No match'}</h1>
  <p class="lotno">Lot ${esc(p.lot)}</p>

  <div class="box ${ok ? 'good' : 'bad'}">
    <b>${ok ? 'Verified.' : 'This code is not the code for this lot.'}</b><br>
    ${ok
      ? 'The code you entered is the one derived from the panel the gate evaluated for this lot.'
      : 'Either the code was mistyped, it belongs to a different lot, or the panel has been changed since release. Ask us to re-issue before you accept the bag.'}
  </div>

  <table>
    <thead><tr><th>Code on the bag</th><th>The code for ${esc(p.lot)}</th></tr></thead>
    <tbody><tr>
      <td class="v">${esc(code ? String(code).trim().toUpperCase() : '—')}</td>
      <td class="v">${esc(p.code)}</td>
    </tr></tbody>
  </table>

  <p class="note"><a href="/passport/${encodeURIComponent(p.lot)}">Back to the passport</a></p>`
  );
}

export function passportIndexPage(lots) {
  const released = lots.filter(e => e.disposition === 'RELEASE' && e.lot);
  return SHELL(
    'Check a lot',
    `<h1>Check a lot</h1>
  <p class="note" style="font-size:15px;max-width:60ch">Type the KL number off the bag. If you have only the
  short code, ask us for the lot — the code is a check on the panel, not a lookup key.</p>

  <form method="get" action="/passport" onsubmit="this.action='/passport/'+encodeURIComponent(this.lot.value.trim())">
    <input name="lot" placeholder="KL-2026-001" autocomplete="off" spellcheck="false" aria-label="Lot number">
    <button type="submit">Open the passport</button>
  </form>

  <h2 style="font-size:17px;margin:34px 0 0">Released lots</h2>
  ${released.length === 0
    ? `<p class="note">No lot has been released yet.</p>`
    : `<table><thead><tr><th>Lot</th><th>Grade</th><th>Released</th></tr></thead><tbody>
      ${released
        .map(e => `<tr><td><a href="/passport/${encodeURIComponent(e.lot)}">${esc(e.lot)}</a></td><td>${esc(e.grade ?? '—')}</td><td>${esc(String(e.at).slice(0, 10))}</td></tr>`)
        .join('')}
    </tbody></table>`}`
  );
}

export function notFoundPage(lot, releasedLots) {
  return SHELL(
    'No such lot',
    `<h1>No such lot</h1>
  <p class="note" style="font-size:15px">Nothing in the register matches <code>${esc(lot)}</code>.</p>
  <div class="box bad">
    <b>Why this is the answer you want.</b>
    A passport exists only for a lot that cleared the gate and was issued a number. If a number
    does not resolve, it was either mistyped or it was never issued — and a number that was never
    issued is exactly what a rejected lot does <em>not</em> get.
  </div>
  ${releasedLots.length
    ? `<p class="note">Released lots: ${releasedLots.map(e => `<a href="/passport/${encodeURIComponent(e.lot)}">${esc(e.lot)}</a>`).join(' · ')}</p>`
    : `<p class="note">No lots have been released yet.</p>`}
  <p class="note"><a href="/passport">Check another lot</a></p>`
  );
}
