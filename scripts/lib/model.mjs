import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
export const ROOT = join(here, '..', '..');

export function loadTruth() {
  const raw = readFileSync(join(ROOT, 'company', 'source-of-truth.json'), 'utf8');
  return JSON.parse(raw);
}

export const usd = n =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
export const usd2 = n =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const inr = n =>
  '₹' + n.toLocaleString('en-IN', { maximumFractionDigits: 0 });
export const pct = (n, d = 1) => `${n.toFixed(d)}%`;
export const int = n => Math.round(n).toLocaleString('en-US');

export function sumValues(obj) {
  return Object.values(obj).reduce((a, b) => a + b, 0);
}

/**
 * Derive every financial figure from drivers.
 * Nothing in here is allowed to read a stored revenue or EBITDA number:
 * those do not exist in source-of-truth.json.
 */
export function computePlan(t) {
  const dr = t.plan.drivers;
  const years = ['y1', 'y2', 'y3'].map(key => {
    const y = t.plan[key];
    const d2cRevenue = y.d2c_orders * dr.d2c_avg_order_value_usd;
    const b2bRevenue = y.b2b_micro_lots * dr.b2b_revenue_per_micro_lot_usd;
    const revenue = d2cRevenue + b2bRevenue;
    const gp = d2cRevenue * (dr.d2c_gross_margin_pct / 100) + b2bRevenue * (dr.b2b_gross_margin_pct / 100);
    const opex = sumValues(y.opex_usd);
    const ebitda = gp - opex;
    return {
      key,
      label: y.label,
      d2cOrders: y.d2c_orders,
      b2bLots: y.b2b_micro_lots,
      d2cRevenue,
      b2bRevenue,
      revenue,
      gp,
      gmPct: (gp / revenue) * 100,
      opex,
      opexLines: y.opex_usd,
      ebitda,
      ebitdaPct: (ebitda / revenue) * 100,
      // cash to fund the operating loss; 0 once positive
      fundingNeed: Math.max(0, -ebitda),
    };
  });

  const bear = t.plan.bear_case;
  const base = years[2];
  const bearRevenue = base.revenue * bear.revenue_multiplier;
  const bearGm = Math.max(0, base.gmPct + bear.margin_delta_points) / 100;

  const ue = t.unit_economics;
  const b2bCogsBreakdownSum = sumValues(
    Object.fromEntries(Object.entries(ue.b2b_micro_lot.cogs_breakdown).filter(([k]) => k !== 'total'))
  );

  const d2c = ue.d2c_500g;
  const d2cContribution =
    d2c.revenue_usd - d2c.cogs_usd - d2c.fulfilment_usd - d2c.payment_fee_usd - d2c.cac_usd;

  const useOfFundsTotal = t.capital.use_of_funds.reduce((a, l) => a + l.usd, 0);

  return {
    years,
    total: {
      revenue: years.reduce((a, y) => a + y.revenue, 0),
      gp: years.reduce((a, y) => a + y.gp, 0),
      ebitda: years.reduce((a, y) => a + y.ebitda, 0),
      peakFundingNeed: Math.max(...years.map(y => y.fundingNeed)),
    },
    marginBlend: {
      d2c: t.unit_economics.channel_margins.d2c_gross_margin_pct,
      b2b: t.unit_economics.channel_margins.b2b_gross_margin_pct,
      blended: (dr.d2c_gross_margin_pct + dr.b2b_gross_margin_pct) / 2,
    },
    b2b: {
      revenue: ue.b2b_micro_lot.revenue_usd,
      cogs: ue.b2b_micro_lot.cogs_usd,
      cogsBreakdownSum: b2bCogsBreakdownSum,
      gp: ue.b2b_micro_lot.revenue_usd - ue.b2b_micro_lot.cogs_usd,
      gmPct:
        ((ue.b2b_micro_lot.revenue_usd - ue.b2b_micro_lot.cogs_usd) /
          ue.b2b_micro_lot.revenue_usd) *
        100,
      delivery: ue.b2b_micro_lot.delivery_cost_usd_assumption,
      contribution: ue.b2b_micro_lot.revenue_usd - ue.b2b_micro_lot.cogs_usd - ue.b2b_micro_lot.delivery_cost_usd_assumption,
    },
    d2c: {
      revenue: d2c.revenue_usd,
      goods: d2c.cogs_usd,
      fulfilment: d2c.fulfilment_usd,
      payment: d2c.payment_fee_usd,
      cac: d2c.cac_usd,
      contribution: d2cContribution,
      contributionPct: (d2cContribution / d2c.revenue_usd) * 100,
      grossBeforeCacPct:
        ((d2c.revenue_usd - d2c.cogs_usd - d2c.fulfilment_usd - d2c.payment_fee_usd) /
          d2c.revenue_usd) *
        100,
    },
    bear: {
      revenue: bearRevenue,
      gp: bearRevenue * bearGm,
      gmPct: bearGm * 100,
      ebitda: bearRevenue * bearGm - base.opex,
    },
    useOfFundsTotal,
    tierSpread: (() => {
      const tiers = t.market.channel_tiers;
      return {
        farmGate: tiers[0].price_inr_per_kg,
        retail: tiers[3].price_inr_per_kg,
        multiple: tiers[3].price_inr_per_kg / tiers[0].price_inr_per_kg,
      };
    })(),
  };
}

export function cashRunway(t, model) {
  const raise = t.capital.raise_usd;
  const firstYearBurn = model.years[0].fundingNeed;
  const months = firstYearBurn > 0 ? (raise / firstYearBurn) * 12 : Infinity;
  return { raise, firstYearBurn, months };
}
