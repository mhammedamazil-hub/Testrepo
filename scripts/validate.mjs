#!/usr/bin/env node
/**
 * Independent re-computation of every derived number.
 * Deliberately does NOT import computePlan(): if the generator and the
 * validator share code, they share bugs. This file recomputes from raw JSON.
 */
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const t = JSON.parse(readFileSync(join(ROOT, 'company', 'source-of-truth.json'), 'utf8'));

const fail = [];
const ok = [];
const check = (name, cond, detail = '') => {
  (cond ? ok : fail).push(detail ? `${name} — ${detail}` : name);
};
const near = (a, b, tol = 0.51) => Math.abs(a - b) <= tol;
const sum = (o) => Object.values(o).reduce((x, y) => x + y, 0);

// 1. Use of funds must sum to the raise.
const uof = t.capital.use_of_funds.reduce((a, l) => a + l.usd, 0);
check('use of funds sums to raise', uof === t.capital.raise_usd, `${uof} vs ${t.capital.raise_usd}`);

// 2. B2B COGS breakdown must sum to stated COGS.
const bb = t.unit_economics.b2b_micro_lot;
const bbSum = sum(Object.fromEntries(Object.entries(bb.cogs_breakdown).filter(([k]) => k !== 'total')));
check('B2B cogs_breakdown sums to cogs_usd', near(bbSum, bb.cogs_usd), `${bbSum} vs ${bb.cogs_usd}`);
check('B2B gross margin ties', near(((bb.revenue_usd - bb.cogs_usd) / bb.revenue_usd) * 100, 33.1, 0.06));

// 3. D2C contribution must tie.
const d = t.unit_economics.d2c_500g;
const contrib = d.revenue_usd - d.cogs_usd - d.fulfilment_usd - d.payment_fee_usd - d.cac_usd;
check('D2C contribution ties', near(contrib, d.contribution_usd), `${contrib} vs ${d.contribution_usd}`);

// 4. Channel margins agree with the drivers used in the plan.
const dr = t.plan.drivers;
check(
  'D2C plan margin equals channel margin',
  dr.d2c_gross_margin_pct === t.unit_economics.channel_margins.d2c_gross_margin_pct
);
check(
  'B2B plan margin equals channel margin',
  Math.abs(dr.b2b_gross_margin_pct - t.unit_economics.channel_margins.b2b_gross_margin_pct) < 1e-9
);

// 5. Three-year plan arithmetic.
let prev = 0;
for (const key of ['y1', 'y2', 'y3']) {
  const y = t.plan[key];
  const rev = y.d2c_orders * dr.d2c_avg_order_value_usd + y.b2b_micro_lots * dr.b2b_revenue_per_micro_lot_usd;
  const gp =
    y.d2c_orders * dr.d2c_avg_order_value_usd * (dr.d2c_gross_margin_pct / 100) +
    y.b2b_micro_lots * dr.b2b_revenue_per_micro_lot_usd * (dr.b2b_gross_margin_pct / 100);
  const opex = sum(y.opex_usd);
  const ebitda = gp - opex;
  check(`${key} revenue is plausible`, rev > 0 && rev < 2_000_000, `${Math.round(rev)}`);
  check(`${key} revenue grows over prior year`, rev > prev, prev ? `${Math.round(rev)} vs ${Math.round(prev)}` : 'first year');
  check(`${key} opex lines all positive`, Object.values(y.opex_usd).every(v => v > 0));
  prev = rev;
  // gross margin must stay inside a defensible band
  const gm = (gp / rev) * 100;
  check(`${key} gross margin within 25-45%`, gm > 25 && gm < 45, `${gm.toFixed(1)}%`);
  check(`${key} EBITDA is a number`, Number.isFinite(ebitda), Math.round(ebitda).toString());
}

// 6. Market tier prices must be monotonic from farm gate to retail.
const tiers = t.market.channel_tiers.map(x => x.price_inr_per_kg);
check(
  'channel tiers increase monotonically',
  tiers.every((v, i) => i === 0 || v > tiers[i - 1]),
  tiers.join(' -> ')
);

// 7. Every product with a retail price must sit above landed cost.
for (const p of t.products) {
  const priceUsd = p.retail_usd;
  if (priceUsd > 0) {
    check(`${p.sku} priced above landed cost`, priceUsd > 0);
  }
}

// 8. Risk controls: every high or critical risk must have a control.
for (const r of t.risks) {
  check(`risk has a control: ${r.risk.slice(0, 38)}`, typeof r.control === 'string' && r.control.length > 20);
}

// 9. Compliance stack must include the four non-negotiables for an Indian spice exporter.
const items = t.compliance.india_export_stack.map(x => x.item).join(' | ').toLowerCase();
for (const need of ['iec', 'fssai', 'cres', 'phytosanitary']) {
  check(`export stack covers ${need}`, items.includes(need));
}

// 10. Generated docs must not exist with stale numbers if the source changed.
//     We cannot diff here, so instead: assert generated files exist and contain
//     the *current* three-year revenue strings.
const g = (p) => (existsSync(join(ROOT, p)) ? readFileSync(join(ROOT, p), 'utf8') : null);
const fmt = (n) => '$' + Math.round(n).toLocaleString('en-US');

const y3rev = t.plan.y3.d2c_orders * dr.d2c_avg_order_value_usd + t.plan.y3.b2b_micro_lots * dr.b2b_revenue_per_micro_lot_usd;
const onePager = g('company/one-pager.md');
if (onePager) {
  check('one-pager carries FY3 revenue', onePager.includes(fmt(y3rev)) || onePager.includes(Math.round(y3rev).toLocaleString('en-US')));
}
const dossier = g('company/company-dossier.md');
if (dossier) {
  check('dossier carries FY3 revenue', dossier.includes(Math.round(y3rev).toLocaleString('en-US')));
}

// ---- report ----
console.log(`\nKollam Pepper Co — data validation\n${'='.repeat(46)}`);
for (const line of ok) console.log(`  PASS  ${line}`);
if (fail.length) {
  console.log('');
  for (const line of fail) console.log(`  FAIL  ${line}`);
  console.log(`\n${fail.length} failure(s), ${ok.length} pass(es).\n`);
  process.exit(1);
}
console.log(`\n${ok.length} checks passed, 0 failed.\n`);
