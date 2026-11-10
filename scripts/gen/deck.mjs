import { usd, int, pct, computePlan, cashRunway } from '../lib/model.mjs';

export function deckMarkdown(t, model = computePlan(t)) {
  const Y = model.years;
  const runway = cashRunway(t, model);
  const n = (i) => `${i + 1}`;
  const slides = [];

  slides.push({
    kicker: 'The ask',
    title: `${usd(t.capital.raise_usd)}`,
    body: `To ship two container cycles, clear the full EU/US compliance stack, and turn a price ladder into a brand.\n\n${t.company.hq} · ${t.company.founded}`,
  });

  slides.push({
    kicker: 'The problem',
    title: 'India grows the most storied pepper in the world and exports almost none of it',
    body: `The 2024/25 crop fell to a record-low ~48,000 t while domestic consumption ran ~81,000 t. India net-imported pepper.\n\nWhat does leave the country leaves as anonymous bulk. A buyer in Rotterdam cannot prove the bag they bought came from Kerala at all — and the market's default answer to that is cheaper pepper from somewhere else, re-bagged.`,
  });

  slides.push({
    kicker: 'The wedge',
    title: 'Verified provenance at lot level is the scarce input — not pepper',
    body: `Growers sell ungraded at ${'₹'}${int(t.market.channel_tiers[0].price_inr_per_kg)}/kg. Specialty retail sells at ${'₹'}${int(t.market.channel_tiers[3].price_inr_per_kg)}/kg.\n\nThat is a ${model.tierSpread.multiple.toFixed(1)}× ladder. It is not climbed by being better at freight. It is climbed by owning the grade, the test panel, and the mark.`,
  });

  slides.push({
    kicker: 'The product',
    title: 'Two channels, one lot gate',
    body: `**D2C — retail under our own mark.**\n100 g and 500 g Tellicherry Bold packs, plus a four-spice Malabar Line gift box.\n\n**B2B — 25 kg kitchen-grade micro-lots.**\nMG-1 to restaurant groups and meal-kit kitchens who need a named origin and a printed test panel, not a commodity quote.\n\nEvery SKU carries a KL-YYYY-NNN lot number. No number, no sale.`,
  });

  slides.push({
    kicker: 'How it works',
    title: 'The lot gate',
    body: `A lot cannot be sold until all of this is true:\n\n1. Signed supplier declaration: no ethylene-oxide fumigation\n2. Moisture and water activity measured at intake\n3. Full panel — mycotoxins, microbiology, heavy metals, pesticide multi-residue, EtO\n4. Grade verified by sieve and density\n\nOnly then does it get a lot number.\n\nThis is the whole company in four lines. Everything else is logistics.`,
  });

  slides.push({
    kicker: 'Unit economics',
    title: `B2B micro-lot: ${pct(model.b2b.gmPct)} gross margin`,
    body: `One 25 kg bag of MG-1.\n\nRevenue ${usd(model.b2b.revenue)} · COGS ${usd(model.b2b.cogs)} · **gross profit ${usd(model.b2b.gp)}**\n\nDuty into the EU and the US on whole pepper is 0%. Tariff is not the constraint. The test panel is: one rejected container costs more than a year of freight.`,
  });

  slides.push({
    kicker: 'Unit economics',
    title: `D2C pack: ${pct(model.d2c.contributionPct)} contribution`,
    body: `${usd(model.d2c.revenue)} revenue · ${usd(model.d2c.goods)} goods · ${usd(model.d2c.fulfilment)} fulfilment · ${usd(model.d2c.payment)} payment · ${usd(model.d2c.cac)} CAC → **${usd(model.d2c.contribution)}**\n\nGross margin before CAC is ${pct(model.d2c.grossBeforeCacPct)}. We plan D2C at ${pct(model.marginBlend.d2c, 0)} and B2B at ${pct(model.marginBlend.b2b)} — both midpoints, not best cases.`,
  });

  slides.push({
    kicker: 'Plan',
    title: `${usd(Y[0].revenue)} → ${usd(Y[2].revenue)} in three years`,
    body: `| | FY1 | FY2 | FY3 |\n|---|---:|---:|---:|\n| Revenue | ${usd(Y[0].revenue)} | ${usd(Y[1].revenue)} | ${usd(Y[2].revenue)} |\n| Gross margin | ${pct(Y[0].gmPct)} | ${pct(Y[1].gmPct)} | ${pct(Y[2].gmPct)} |\n| EBITDA | ${usd(Y[0].ebitda)} | ${usd(Y[1].ebitda)} | ${usd(Y[2].ebitda)} |\n\nDrivers: D2C orders and AOV, B2B micro-lot count, and two channel gross margins. Nothing else moves.`,
  });

  slides.push({
    kicker: 'Downside',
    title: `Bear case FY3: ${usd(model.bear.ebitda)} EBITDA`,
    body: `${pct(t.plan.bear_case.revenue_multiplier * 100, 0)} of planned revenue at ${pct(model.bear.gmPct)} gross margin with opex held flat.\n\nThat is the number to survive. It is survivable only if the raise covers the FY1 operating loss of ${usd(runway.firstYearBurn)} and no fixed headcount is added before FY3 route density exists.`,
  });

  slides.push({
    kicker: 'Compliance',
    title: 'The four numbers that decide whether a shipment lives',
    body: `**Aflatoxin B1** 5.0 µg/kg max in the EU · **total aflatoxins** 10.0 µg/kg\n**Ochratoxin A** 15 µg/kg for pepper\n**Salmonella** absent in 25 g\n**Ethylene oxide** — banned for food use in the EU, measured with 2-chloroethanol, effectively zero tolerance\n\nWe test every lot in India before it ships. The US has no EtO tolerance for spices either. There is no market where a positive result is negotiable.`,
  });

  slides.push({
    kicker: 'Moat',
    title: 'Why this is defensible and not just trading',
    body: `- **Lot-level chain of custody** with named grower clusters — expensive to build, boring to copy\n- **Rejection data looped back to clusters**, so our supply improves and the spot market's does not\n- **A brand that prints its own test results**, which is a liability for anyone selling on price alone\n- **Two channels on one lot gate** — D2C carries margin, B2B carries volume predictability\n\nA trader can undercut our price. A trader cannot undercut our paperwork without doing the work.`,
  });

  slides.push({
    kicker: 'Team',
    title: 'Two founders, one advisor, and a deliberate absence of staff',
    body: `${t.org.roles.slice(0, 2).map(r => `**${r.role}** — ${r.owns}`).join('\n\n')}\n\nNo sales team before month 15. No warehouse. No owned processing line. Co-packing and third-party processing until route density justifies capital.`,
  });

  slides.push({
    kicker: 'Use of funds',
    title: `${usd(model.useOfFundsTotal)}`,
    body: t.capital.use_of_funds.map(l => `- ${l.line} — ${usd(l.usd)}`).join('\n') +
      `\n\nMilestone at month 12: repeat-order rate above 25% D2C and two multi-lot B2B accounts.`,
  });

  slides.push({
    kicker: 'Risks',
    title: 'What actually kills this company',
    body: t.risks
      .filter(r => r.severity === 'critical' || r.severity === 'high')
      .map(r => `**${r.risk}** — ${r.control}`)
      .join('\n\n'),
  });

  slides.push({
    kicker: 'Why now',
    title: 'Zero duty, a depleted crop, and an under-built premium story',
    body: `- Whole pepper enters the EU and the US at **0% duty**\n- India's FY 2024-25 spice exports hit a record ${'$'}4.72 B, but pepper is only ~3% of that basket by value\n- The 2024/25 crop collapse pushed domestic prices up and made provenance a buying criterion, not a nice-to-have\n\nBuyers with budget have started asking for the test panel. Most suppliers cannot produce one on demand.`,
  });

  return slides
    .map(
      (s, i) =>
        `---\n\n## ${n(i)} / ${slides.length} — ${s.kicker}\n\n# ${s.title}\n\n${s.body}\n`
    )
    .join('\n');
}

export function deckHtml(t, model = computePlan(t)) {
  const Y = model.years;
  const slides = [];

  const S = (kicker, title, bodyHtml, cls = '') => slides.push({ kicker, title, bodyHtml, cls });

  S('Kollam Pepper Co · 2026', `${usd(t.capital.raise_usd)}`,
    `<p class="lede">To ship two container cycles, clear the full EU and US compliance stack,
     and turn a ${model.tierSpread.multiple.toFixed(1)}× price ladder into a brand.</p>
     <p class="meta">${t.company.hq} · Pre-seed</p>`, 'title-slide');

  S('01 · The problem', 'India grows the most storied pepper in the world and exports almost none of it',
    `<p>The 2024/25 crop fell to a record-low <b>~48,000 t</b> while domestic consumption ran
     <b>~81,000 t</b>. India net-imported pepper.</p>
     <p>What does leave the country leaves as anonymous bulk. A buyer in Rotterdam cannot prove the
     bag they bought came from Kerala at all — and the market's answer to that is cheaper pepper
     from somewhere else, re-bagged.</p>`);

  S('02 · The wedge', 'Verified provenance at lot level is the scarce input — not pepper',
    `<div class="ladder">
       <div><span>Farm gate</span><b>₹${int(t.market.channel_tiers[0].price_inr_per_kg)}/kg</b></div>
       <div><span>Exporter landed</span><b>₹${int(t.market.channel_tiers[2].price_inr_per_kg)}/kg</b></div>
       <div><span>Specialty retail</span><b>₹${int(t.market.channel_tiers[3].price_inr_per_kg)}/kg</b></div>
     </div>
     <p>That is a <b>${model.tierSpread.multiple.toFixed(1)}×</b> ladder. It is not climbed by being
     better at freight. It is climbed by owning the grade, the test panel, and the mark.</p>`);

  S('03 · The product', 'Two channels, one lot gate',
    `<div class="cols">
      <div><h4>D2C — our own mark</h4>
        ${t.products.filter(p => p.sku.startsWith('KP-T') || p.sku.startsWith('KP-BLEND')).map(p => `<p class="sku">${p.name}<br><small>${p.format} · ${p.grade}</small></p>`).join('')}
      </div>
      <div><h4>B2B — micro-lots</h4>
        ${t.products.filter(p => p.sku.startsWith('KP-MG1')).map(p => `<p class="sku">${p.name}<br><small>${p.format} · ${p.grade}</small></p>`).join('')}
        <p class="small">Restaurant groups and meal-kit kitchens who need a named origin and a printed test panel, not a commodity quote.</p>
      </div>
     </div>
     <p class="stamp">Every SKU carries a KL-YYYY-NNN lot number. No number, no sale.</p>`);

  S('04 · How it works', 'The lot gate',
    `<ol class="gate">
       <li>Signed supplier declaration — no ethylene-oxide fumigation</li>
       <li>Moisture and water activity measured at intake</li>
       <li>Full panel: mycotoxins, microbiology, heavy metals, pesticide residues, EtO</li>
       <li>Grade verified by sieve and density</li>
     </ol>
     <p>Only then does a lot receive a number and enter sellable stock.
     <b>This is the whole company.</b> Everything else is logistics.</p>`);

  S('05 · Unit economics', `B2B micro-lot — ${pct(model.b2b.gmPct)} gross margin`,
    `<table class="fin">
      <tr><td>Revenue, one 25 kg bag of MG-1</td><td class="num">${usd(model.b2b.revenue)}</td></tr>
      <tr><td>COGS</td><td class="num">${usd(model.b2b.cogs)}</td></tr>
      <tr class="total"><td>Gross profit</td><td class="num">${usd(model.b2b.gp)}</td></tr>
     </table>
     <p>Duty into the EU and the US on whole pepper is <b>0%</b>. Tariff is not the constraint.
     The test panel is: one rejected container costs more than a year of freight.</p>`);

  S('06 · Unit economics', `D2C pack — ${pct(model.d2c.contributionPct)} contribution`,
    `<table class="fin">
      <tr><td>Revenue, 500 g Tellicherry Bold</td><td class="num">${usd(model.d2c.revenue)}</td></tr>
      <tr><td>Goods</td><td class="num">${usd(model.d2c.goods)}</td></tr>
      <tr><td>Fulfilment</td><td class="num">${usd(model.d2c.fulfilment)}</td></tr>
      <tr><td>Payment</td><td class="num">${usd(model.d2c.payment)}</td></tr>
      <tr><td>Acquisition cost</td><td class="num">${usd(model.d2c.cac)}</td></tr>
      <tr class="total"><td>Contribution</td><td class="num">${usd(model.d2c.contribution)}</td></tr>
     </table>
     <p class="small">Planned at ${pct(model.marginBlend.d2c, 0)} D2C and ${pct(model.marginBlend.b2b)} B2B — both midpoints of observed tier spreads.</p>`);

  S('07 · The plan', `${usd(Y[0].revenue)} → ${usd(Y[2].revenue)}`,
    `<table class="fin wide">
      <tr><th></th><th class="num">FY1</th><th class="num">FY2</th><th class="num">FY3</th></tr>
      <tr><td>Revenue</td><td class="num">${usd(Y[0].revenue)}</td><td class="num">${usd(Y[1].revenue)}</td><td class="num">${usd(Y[2].revenue)}</td></tr>
      <tr><td>Gross margin</td><td class="num">${pct(Y[0].gmPct)}</td><td class="num">${pct(Y[1].gmPct)}</td><td class="num">${pct(Y[2].gmPct)}</td></tr>
      <tr class="total"><td>EBITDA</td><td class="num">${usd(Y[0].ebitda)}</td><td class="num">${usd(Y[1].ebitda)}</td><td class="num">${usd(Y[2].ebitda)}</td></tr>
     </table>
     <p class="small">Four drivers only: D2C orders, D2C average order value, B2B micro-lot count, and the two channel margins.</p>`);

  S('08 · Downside', `Bear case FY3 — ${usd(model.bear.ebitda)} EBITDA`,
    `<p>${pct(t.plan.bear_case.revenue_multiplier * 100, 0)} of planned revenue at
     ${pct(model.bear.gmPct)} gross margin, opex held flat at ${usd(Y[2].opex)}.</p>
     <p class="big-neg">${usd(model.bear.ebitda)}</p>
     <p>That is the number to survive. It is survivable only if the raise covers the
     ${usd(cashRunway(t, model).firstYearBurn)} FY1 operating loss and no fixed headcount
     is added before FY3 route density exists.</p>`);

  S('09 · Compliance', 'Four numbers decide whether a shipment lives',
    `<div class="limits">
      <div><b>5.0 <small>µg/kg</small></b><span>Aflatoxin B1, EU max</span></div>
      <div><b>10.0 <small>µg/kg</small></b><span>Total aflatoxins, EU max</span></div>
      <div><b>15 <small>µg/kg</small></b><span>Ochratoxin A, pepper</span></div>
      <div><b>25 <small>g</small></b><span>Salmonella absent in</span></div>
     </div>
     <p><b>Ethylene oxide</b> is banned for food use in the EU and measured with 2-chloroethanol.
     There is no market where a positive result is a negotiable threshold. We test in India
     before it ships.</p>`);

  S('10 · Moat', 'Why this is defensible and not just trading',
    `<ul class="moat">
       <li><b>Lot-level chain of custody</b> with named grower clusters — expensive to build, boring to copy</li>
       <li><b>Rejection data fed back</b> to clusters, so our supply improves and the spot market's does not</li>
       <li><b>A brand that prints its own test results</b> — a liability for anyone competing on price alone</li>
       <li><b>Two channels on one lot gate</b> — D2C carries margin, B2B carries predictable volume</li>
     </ul>
     <p class="stamp">A trader can undercut our price. A trader cannot undercut our paperwork without doing the work.</p>`);

  S('11 · Team', 'Two founders, one advisor, and a deliberate absence of staff',
    `<div class="cols">
       <div><h4>Founder — Sourcing &amp; Quality</h4><p>Grower relationships, lot intake, testing,
       rejections, Spices Board and FSSAI files.</p></div>
       <div><h4>Founder — Commercial</h4><p>B2B accounts, pricing, export documentation,
       importer relationships.</p></div>
     </div>
     <p>No sales team before month 15. No warehouse. No owned processing line. Co-packing and
     third-party processing until route density justifies capital.</p>`);

  S('12 · Use of funds', usd(model.useOfFundsTotal),
    `<table class="fin">
      ${t.capital.use_of_funds.map(l => `<tr><td>${l.line}</td><td class="num">${usd(l.usd)}</td></tr>`).join('')}
      <tr class="total"><td>Total</td><td class="num">${usd(model.useOfFundsTotal)}</td></tr>
     </table>
     <p class="small">Month-12 milestone: repeat-order rate above 25% on D2C and two multi-lot B2B accounts.</p>`);

  S('13 · Risk', 'What actually kills this company',
    `<div class="cols">
      ${t.risks.filter(r => r.severity === 'critical' || r.severity === 'high').slice(0, 4).map(r => `<div><h4>${r.risk}</h4><p>${r.control}</p></div>`).join('')}
     </div>`);

  S('14 · Why now', 'Zero duty, a depleted crop, an under-built premium story',
    `<ul class="moat">
       <li>Whole pepper enters the EU and the US at <b>0% duty</b></li>
       <li>India's FY 2024-25 spice exports hit a record <b>$4.72 B</b> — but pepper is only ~3% of that basket by value</li>
       <li>The 2024/25 crop collapse made provenance a buying criterion, not a nice-to-have</li>
     </ul>
     <p>Buyers with budget have started asking for the test panel. Most suppliers cannot produce
     one on demand.</p>`, 'closing');

  const css = `
:root{--ink:#1c211c;--paper:#f4efe6;--green:#2e4a3b;--accent:#c05a2e;--muted:#6b7268}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#0d0f0d;color:var(--ink);font-family:ui-sans-serif,-apple-system,"Segoe UI",Inter,Helvetica,Arial,sans-serif}
.deck{display:block}
.slide{position:relative;margin:0 auto 28px;width:min(1120px,94vw);min-height:630px;background:var(--paper);
  padding:54px 64px 64px;display:flex;flex-direction:column;justify-content:flex-start;overflow:hidden}
.slide::after{content:attr(data-n);position:absolute;right:34px;bottom:26px;font-size:12px;color:var(--muted);letter-spacing:.14em}
.kicker{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:26px}
h1{font-size:44px;line-height:1.1;margin:0 0 30px;font-weight:800;letter-spacing:-.02em;max-width:24ch}
.slide p{font-size:19px;line-height:1.55;margin:0 0 16px;max-width:62ch}
.small{font-size:16px;color:var(--muted)}
.meta{font-size:14px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.title-slide{background:var(--green);color:#f4efe6;justify-content:center}
.title-slide h1{font-size:120px;margin:0 0 18px;letter-spacing:-.04em;color:#f4efe6}
.title-slide .kicker{color:#d9c9a8}.title-slide .lede{font-size:24px;max-width:44ch;color:#e9e2d4}
.title-slide .meta{color:#b9c4b3}
.ladder{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:8px 0 22px}
.ladder div{background:#fff;border-left:4px solid var(--accent);padding:16px 18px}
.ladder span{display:block;font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.ladder b{font-size:30px;font-weight:800}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:34px}
h4{font-size:14px;letter-spacing:.12em;text-transform:uppercase;margin:0 0 10px;color:var(--accent)}
.sku{font-size:17px;font-weight:600;margin:0 0 14px}
.sku small{font-weight:400;color:var(--muted);font-size:13px}
.stamp{margin-top:auto;padding-top:18px;border-top:1px solid #cfc6b6;font-weight:700;font-size:17px}
ol.gate{counter-reset:g;list-style:none;padding:0;margin:0 0 24px}
ol.gate li{counter-increment:g;position:relative;padding:14px 0 14px 54px;border-bottom:1px solid #d8cfbf;font-size:19px}
ol.gate li::before{content:counter(g);position:absolute;left:0;top:12px;width:34px;height:34px;border-radius:50%;
  background:var(--green);color:var(--paper);display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700}
table.fin{width:100%;border-collapse:collapse;font-size:18px;margin:0 0 20px}
table.fin td,table.fin th{padding:11px 0;border-bottom:1px solid #d8cfbf;text-align:left}
table.fin .num{text-align:right;font-variant-numeric:tabular-nums}
table.fin .total td{border-top:2px solid var(--ink);border-bottom:none;font-weight:800;padding-top:14px}
table.fin.wide th{font-weight:700;font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.big-neg{font-size:52px;font-weight:800;color:var(--accent);margin:10px 0 18px!important}
.limits{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:0 0 24px}
.limits div{background:#fff;padding:18px 14px;border-top:4px solid var(--green)}
.limits b{display:block;font-size:32px;font-weight:800;line-height:1}
.limits small{font-size:13px;font-weight:600;color:var(--muted)}
.limits span{display:block;font-size:13px;color:var(--muted);margin-top:8px}
ul.moat{list-style:none;padding:0;margin:0 0 20px}
ul.moat li{position:relative;padding:12px 0 12px 26px;border-bottom:1px solid #d8cfbf;font-size:18px}
ul.moat li::before{content:"";position:absolute;left:0;top:21px;width:9px;height:9px;background:var(--accent)}
.closing{background:var(--green);color:#f4efe6}
.closing h1{color:#fff}.closing .kicker{color:#d9c9a8}.closing li{border-color:#46614f;color:#e9e2d4}
@media print{body{background:#fff}.slide{margin:0;width:100%;min-height:100vh;page-break-after:always}}
@media(max-width:820px){.slide{padding:34px 26px}h1{font-size:30px}.title-slide h1{font-size:58px}
  .cols,.ladder,.limits{grid-template-columns:1fr}.slide p{font-size:17px}}
`;

  const body = slides
    .map(
      (s, i) =>
        `<section class="slide ${s.cls}" data-n="${String(i + 1).padStart(2, '0')} / ${String(slides.length).padStart(2, '0')}">
           <div class="kicker">${s.kicker}</div>
           <h1>${s.title}</h1>
           ${s.bodyHtml}
         </section>`
    )
    .join('\n');

  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kollam Pepper Co — Investor Deck</title>
<style>${css}</style></head>
<body><main class="deck">${body}</main></body></html>`;
}
