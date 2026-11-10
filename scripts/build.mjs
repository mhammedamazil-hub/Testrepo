#!/usr/bin/env node
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { loadTruth, computePlan, ROOT } from './lib/model.mjs';
import { dossier, onePager } from './gen/docs.mjs';
import { deckMarkdown, deckHtml } from './gen/deck.mjs';
import { site } from './gen/site.mjs';
import { salesAssets } from './gen/ops.mjs';

const t = loadTruth();
const model = computePlan(t);

const out = [];
function write(rel, body) {
  const p = join(ROOT, rel);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, body, 'utf8');
  out.push([rel, body.length]);
}

write('company/company-dossier.md', dossier(t, model));
write('company/one-pager.md', onePager(t, model));
write('deck/deck.md', deckMarkdown(t, model));
write('deck/deck.html', deckHtml(t, model));
write('site/index.html', site(t, model));
for (const a of salesAssets(t, model)) write(a.path, a.body);

// machine-readable model output, so a human or an agent can diff it
write('company/model-output.json', JSON.stringify({
  generated_at: new Date().toISOString(),
  source: 'company/source-of-truth.json',
  years: model.years.map(y => ({
    label: y.label, revenue: Math.round(y.revenue), gross_profit: Math.round(y.gp),
    gross_margin_pct: +y.gmPct.toFixed(2), opex: y.opex, ebitda: Math.round(y.ebitda),
  })),
  three_year_revenue: Math.round(model.total.revenue),
  bear_fy3_ebitda: Math.round(model.bear.ebitda),
  unit_economics: {
    b2b_gross_margin_pct: +model.b2b.gmPct.toFixed(2),
    d2c_contribution_pct: +model.d2c.contributionPct.toFixed(2),
  },
  use_of_funds_total: model.useOfFundsTotal,
}, null, 2) + '\n');

console.log('\nKollam Pepper Co — build\n' + '='.repeat(46));
for (const [p, n] of out) console.log(`  wrote  ${p.padEnd(42)} ${String(n).padStart(7)} bytes`);
console.log('\nThree-year revenue: $' + Math.round(model.total.revenue).toLocaleString('en-US'));
console.log('FY3 EBITDA:        $' + Math.round(model.years[2].ebitda).toLocaleString('en-US'));
console.log('Bear FY3 EBITDA:   $' + Math.round(model.bear.ebitda).toLocaleString('en-US'));
console.log('');
