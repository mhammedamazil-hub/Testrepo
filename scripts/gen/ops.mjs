import { usd, int, pct, computePlan } from '../lib/model.mjs';
import { lotRef, lotRefLong, hasLot } from '../lib/lotref.mjs';

const line = '-'.repeat(72);

export function salesAssets(t, model = computePlan(t)) {
  const Y = model.years;
  const eu = t.compliance.destination_specs.eu;

  // ---------- 1. trade one-pager (what a buyer receives) ----------
  const tradeSheet = `# Kollam Pepper Co — Trade Lot Sheet

**Product:** Whole black pepper (*Piper nigrum*), MG-1 and TGSEB grades
**Origin:** ${t.company.origin_hub}
**Classification:** HS 0904 11 00 (EU / UK commodity code) · HTS 0904.11.00.20 (US)
  — pepper of the genus *Piper*, **neither crushed nor ground**. Classification follows
  GRI 1 on the terms of the heading: no GRI 2-6 analysis is required. Crushed or ground
  pepper moves to 0904 12 and a different test obligation. **State the form on every order.**

${line}

## What a lot ships with

| Document | Issued by | Notes |
|---|---|---|
| Commercial invoice | Kollam | Conforms to 19 CFR § 141.86 for US entries |
| Packing list | Kollam | Bag count, net/gross, marks |
| Certificate of Origin | Chamber of commerce | Needed for preferential claims and buyer files |
| Phytosanitary certificate | PPQS | Plant-health clearance |
| Certificate of Analysis | NABL / FSSAI-approved lab | Per lot, not per shipment |
| Spices Board CRES reference | Spices Board of India | No scheduled spice leaves India without it |

## Specification

| Parameter | MG-1 | TGSEB |
|---|---|---|
| Sieve | 3.5–4.5 mm | 5.0 mm+ |
| Piperine | 4.0–6.0% | 5.0–7.0% |
| Moisture | ${t.compliance.quality_specs.moisture_pct_max}% max | ${t.compliance.quality_specs.moisture_pct_max}% max |
| Total ash | ${t.compliance.quality_specs.total_ash_pct_max}% max | ${t.compliance.quality_specs.total_ash_pct_max}% max |
| Acid insoluble ash | ${t.compliance.quality_specs.acid_insoluble_ash_pct_max}% max | ${t.compliance.quality_specs.acid_insoluble_ash_pct_max}% max |
| Bulk density | ${t.compliance.quality_specs.bulk_density_g_per_l_min} g/l min | ${t.compliance.quality_specs.bulk_density_g_per_l_min} g/l min |
| Volatile oil | ${t.compliance.quality_specs.volatile_oil_ml_per_100g_min} ml/100 g min | ${t.compliance.quality_specs.volatile_oil_ml_per_100g_min} ml/100 g min |
| Foreign matter | ${t.compliance.quality_specs.foreign_matter_pct_max}% max | ${t.compliance.quality_specs.foreign_matter_pct_max}% max |

## Residue and contaminant panel, every lot

- Aflatoxin B1 ≤ 5.0 µg/kg; total aflatoxins ≤ 10.0 µg/kg (Reg (EU) 2023/915)
- Ochratoxin A ≤ 15 µg/kg for pepper
- Salmonella absent in 25 g (Reg (EC) 2073/2005)
- Ethylene oxide + 2-chloroethanol: measured as a sum. **We treat any detection as a
  rejection.** EtO is not permitted for food use in the EU. No US tolerance for spices exists
  either. Steam treatment is the only sterilisation we use.
- Heavy metals: lead ≤ 0.6 mg/kg for fruit spices (EU, since 2021)
- Pesticide multi-residue against Reg (EC) 396/2005 MRLs for the destination

## Commercial

- **Price:** ${usd(t.unit_economics.b2b_micro_lot.revenue_usd)} per 25 kg bag, FOB Kochi.
  CIF quoted on request. No hidden re-packing charge.
- **Duty:** 0% into the EU (0904 11 00) and 0% into the US (0904.11.00 general rate).
  VAT/sales tax applies at destination and is the buyer's account.
- **MOQ:** one 25 kg bag for a first order, four bags (100 kg) for forward-contract pricing.
- **Lead time:** 45–60 days door to door. Test panel takes 7–10 days and is the long pole.
- **Payment:** 50% on order, 50% against scanned documents. LC at buyer's cost for new accounts.
- **Forward contracts:** two grower clusters, 90-day maximum inventory. We do not sell volume
  we have not secured.

## What we will not do

- Ship a lot before its panel clears
- Re-bag pepper of unverified origin
- Accept an EtO-positive lot under any tolerance argument
- Quote a fixed retail price for longer than six months on a crop this volatile

${line}

*Planning document. Prices illustrative. Verify current border-control frequency and MRL
values for your destination before contracting.*
`;

  // ---------- 2. B2B outreach sequence ----------
  const outreach = `# B2B Outreach Sequence

Voice rules from \`brand-voice\`: name the grade, the lot, the test result. No "exotic",
no "authentic", no superlatives without a comparison. Short sentences, one idea each.

Target list shape: restaurant groups (8–40 covers per site, 3+ sites), meal-kit operators,
specialty grocers with an import desk, and hotel groups with a central kitchen. Buyer title:
Executive Chef, Head of Sourcing, or Procurement Manager.

${line}

## Email 1 — the lot sheet

**Subject:** Lot ${lotRefLong(t)}

> [First name],
>
> We ship whole Malabar pepper from two grower clusters near Kochi. Every lot gets a full
> panel before it leaves: aflatoxin, ochratoxin, Salmonella, heavy metals, pesticide residues,
> and ethylene oxide.
>
> Lot ${lotRef(t)}: ${t.siteLot?.grade ?? 'graded'}, ${t.siteLot?.panel?.sieve_mm ?? '—'} mm sieve, ${t.siteLot?.panel?.piperine_pct ?? '—'}% piperine, ${t.siteLot?.panel?.moisture_pct ?? '—'}% moisture, EtO not detected.
> ${usd(t.unit_economics.b2b_micro_lot.revenue_usd)} per 25 kg bag FOB Kochi. Duty is 0% into the EU
> and the US.
>
> Sheet attached. If the panel is useful, I will send a sample of the next lot.
>
> [Name], Kollam Pepper Co

**Why this works:** the subject line *is* the proof. A buyer who has been burned by a rejected
container reads a specific number and knows the sender tests.

## Email 2 — day 4, the objection we actually get

**Subject:** Re: the price

> Price is the easy objection, so let me answer it before you ask.
>
> Our bag is more expensive than a spot quote because 6% of the lots we see get rejected and
> we eat that cost rather than pass the risk to you. A rejected container at your end costs
> more than the difference.
>
> If you want the cheaper route, I will tell you honestly that we are not it. If you want a
> panel with every bag, we should talk Thursday.

## Email 3 — day 9, the sample offer

**Subject:** 500 g of ${lotRef(t)}, no strings

> I would rather you cook with it than read about it.
>
> 500 g of the current lot, sent to your kitchen. If it does not earn shelf space, tell me why —
> the answer is useful either way.

## Email 4 — day 16, close or drop

**Subject:** Closing the file

> I am closing this thread so it does not sit in your inbox.
>
> If whole peppercorns are not a line you buy directly, say so and I will stop. If they are,
> reply "sample" and I will ship this week.

**Rule:** four touches, then stop. Re-open only on a new harvest or a new lot number.

${line}

## Call script — 90 seconds

1. "You buy whole pepper today. Do you know the lot number of the bag in your dry store?"
2. *Wait. Most say no.*
3. "We put one on every bag, with a panel. That is the entire difference between us and a
   spot quote."
4. Grade, price, MOQ, lead time. One sentence each.
5. Ask for the sample address, not for a meeting.

## Objection handling

| Objection | Answer |
|---|---|
| "Too expensive." | "It is. 6% of lots get rejected and we absorb that instead of shipping it to you. What does a rejected container cost your kitchen?" |
| "We already have a supplier." | "Keep them for volume. Use us for the line you put your name on." |
| "Never heard of you." | "Here is the panel and the CRES reference. Verify the lab." |
| "Send a sample." | Send it the same week, with the lot sheet, and ask for a one-line verdict. |
| "Can you do 500 kg at the 25 kg price?" | "Yes, on a forward contract with two clusters. That is what the contract is for." |
`;

  // ---------- 3. customer service playbooks ----------
  const playbooks = `# Exception Playbooks

Severity model is the ECC \`logistics-exception-management\` three-axis rule: score financial
impact, customer impact, and time sensitivity separately, then take the **highest** severity.
A $400 delay on a launch-critical restaurant order outranks a $3,000 delay on a stock order.

${line}

## EX-01 · Customs hold at destination

**Trigger:** shipment flagged at BCP or held by CBP/FDA for examination.

| Step | Owner | Within | Action |
|---|---|---|---|
| 1 | Commercial | 2 h | Confirm the exact hold reason in writing. Never act on a phone call. |
| 2 | Commercial | 4 h | Send the buyer the hold notice and the full document pack unprompted |
| 3 | Sourcing | 24 h | Pull the retained sample and the original CoA for that lot |
| 4 | Commercial | 24 h | Decide: supply documents, request re-test, or accept re-export |
| 5 | Founder | 48 h | If EtO or aflatoxin is the cause, open an NCR against the supplier |

**Never do this:** argue the tolerance, offer to "blend it down", or ask the buyer to
re-classify the goods. A contaminated lot is destroyed or re-exported, not negotiated.

## EX-02 · Salmonella or mycotoxin failure on arrival

1. Stop. Do not release, re-pack, or re-sell any part of the lot.
2. Retain the original CoA and the buyer's result side by side. If the numbers disagree, the
   sampling plan is the first suspect, not the lab.
3. Commission an independent referee lab at our cost.
4. If confirmed: full credit or replacement, freight at our account, and an 8D against the
   supplier within 10 days.
5. If not confirmed: the buyer's sampling is the issue. Send the referee result with the
   sampling method, not with an argument.

## EX-03 · Ethylene oxide positive

**Severity: critical, always.** EtO is not permitted for food use in the EU; a positive result
destroys the shipment and can trigger a RASFF notification that follows the exporter.

1. Quarantine the lot and everything from the same supplier in the same season.
2. Notify the supplier that shipments are suspended pending an audit.
3. Do not attempt re-treatment. EtO and 2-chloroethanol are measured as a sum and both persist.
4. File the prior-disclosure equivalent in the destination market before a regulator asks.
5. Root cause is almost always a fumigation contractor, not the grower. Audit the contractor.

## EX-03a · Rejection letter to a supplier

The letter is the quality system, not a courtesy. A supplier who is not told the code will
assume the buyer haggled.

**Subject:** Lot sample refused at intake — [FINDING CODE] at [VALUE]

> [Supplier],
>
> We tested the [GRADE] sample you offered on [DATE]. Result: **rejected**, one finding.
>
> - [FINDING CODE]: [VALUE]. Limit is [LIMIT]. [ONE LINE ON WHY IT CANNOT BE NEGOTIATED]
>
> Everything else on the panel was within spec. That is the point: one number decided it.
>
> We are not buying this lot and we are not blending it down. Two conditions for the next one:
> a signed no-EtO declaration naming your treatment contractor, and a re-test at our lab
> before we discuss price. The letter is attached to your file either way.
>
> [Name], Kollam Pepper Co

**Never do this:** never put a KL number in a rejection letter. A lot number is issued *only*
on release, so a rejected lot has none — and writing one into the letter tells the supplier
that the number is decorative. It is the one thing we sell.

## EX-04 · Transit delay past the promise date

- Under 3 days and the customer is not launch-critical: notify, do not escalate, offer a credit
  on the next bag.
- Over 5 days, or any launch-critical order: this scores Level 4 on time sensitivity alone.
  Call the buyer before they call us.
- Carrier-fault vs force majeure is decided on evidence, not on the carrier's first email.
  Weather and port congestion need a dated notice, not a claim.

## EX-05 · Shortage or damage at delivery

- **Under $500 with a strong carrier relationship: absorb it.** The paperwork costs more than
  the loss and it pollutes the carrier scorecard with noise. Log it.
- **$500–$2,500: file, do not escalate.** Accept anything above 70% of value.
- **Over $10,000: founder-level, independent inspection, reject settlements below 90%.**
- Concealed damage: 5 days from delivery, industry standard. Photograph everything at the
  tailgate, and never sign a clean BOL when the count is off.

## EX-06 · Grower delivers off-spec at intake

This is the most common exception in the business and the one with the least drama if handled
early.

1. Reject at intake, before payment. The lot never becomes ours.
2. Send the lab result to the cluster with the specific failing parameter — not a verdict.
3. Offer the fix: drying protocol, harvest timing, storage, or a different contractor.
4. Second failure in a season: reduced allocation, not removal.
5. Third failure: exit the cluster. Write the reason down; the next cluster will ask.

${line}

## Claims windows to put in the calendar at booking

| Mode | Damage | Delay | Authority |
|---|---|---|---|
| US domestic surface | 9 months from delivery | 9 months | 49 USC § 14706 (Carmack) |
| Air | 14 days | 21 days | Montreal Convention |
| Ocean (to EU/US) | Per B/L terms; check COGSA/Hague-Visby | Per B/L terms | Carrier's bill |
| Concealed damage, any mode | 5 days from delivery | — | Industry standard |
`;

  // ---------- 4. lot gate SOP ----------
  const sop = `# SOP-01 · Lot Intake and Release

**Owner:** Founder, Sourcing & Quality
**Applies to:** every lot of whole pepper, without exception
**Authority:** only this SOP can create a KL-YYYY-NNN lot number. No number, no sale.

${line}

## 0. Before the lot exists

A supplier must already be on the Approved Supplier List, which requires:

- [ ] Signed declaration: no ethylene-oxide fumigation, ever
- [ ] Named grower cluster or estate, with district
- [ ] Prior season sample that passed a full panel
- [ ] Storage description: covered, off-floor, no animal access
- [ ] Two references from buyers who took delivery

## 1. Offer and sample

| Field | Rule |
|---|---|
| Sample size | 2 kg minimum, drawn from the lot, not from a display bag |
| Grade claimed | MG-1 or TGSEB, with sieve |
| Moisture claimed | Must be ≤ ${t.compliance.quality_specs.moisture_pct_max}% |
| Price | In ₹/kg, FOB equivalent, with the weighbridge basis stated |

## 2. Intake measurement (same day)

- [ ] Moisture and water activity. Over ${t.compliance.quality_specs.moisture_pct_max}% → hold for
      re-drying, do not pay
- [ ] Visual grade: colour, size distribution, foreign matter
- [ ] Sieve check against the claimed grade
- [ ] Bulk density ≥ ${t.compliance.quality_specs.bulk_density_g_per_l_min} g/l
- [ ] Odour check: musty = reject, no further testing, saves the lab fee

## 3. Laboratory panel (7–10 days)

Send to a NABL-accredited or FSSAI-approved lab. The panel is fixed — it is not reduced because
a supplier has been reliable.

| Test | Limit | Method note |
|---|---|---|
| Aflatoxin B1 | ≤ 5.0 µg/kg | EU Reg 2023/915 |
| Total aflatoxins | ≤ 10.0 µg/kg | B1+B2+G1+G2 |
| Ochratoxin A | ≤ 15 µg/kg | Pepper |
| Salmonella | Absent in 25 g | Reg (EC) 2073/2005 |
| Total plate count, yeast, mould | To spec | Buyer's spec governs |
| Ethylene oxide + 2-chloroethanol | Not detected | Indicates fumigation. Non-negotiable. |
| Lead | ≤ 0.6 mg/kg | EU fruit-spice limit |
| Pesticide multi-residue | Against destination MRLs | Reg (EC) 396/2005 |
| Piperine | 4–7% by grade | COA value to the buyer |

## 4. Disposition

Use the ECC \`quality-nonconformance\` disposition sequence, first applicable path wins:

1. **Safety or regulatory failure** → reject. No use-as-is. No blend-down. No exception.
2. **Customer-spec tighter than design spec** → ask the customer for a concession in writing
   before disposing. Never assume.
3. **No functional impact and within authority** → use-as-is with documented engineering
   justification *and* a price adjustment to the buyer.
4. **Reworkable** → rework only if the rework cost is under 60% of replacement value.
5. **Supplier-caused** → return to vendor with a SCAR, and recover the lab cost.

## 5. Release

- [ ] Assign KL-YYYY-NNN. The number is never reused.
- [ ] Attach the CoA to the lot record and to the trade sheet.
- [ ] Print the lot number on the bag liner, not only the outer bag.
- [ ] Retain a 500 g sample for 12 months.

## 6. CAPA

A CAPA closes only on evidence: implementation proof, 90 days of production data or three
consecutive accepted lots, and zero recurrence of that failure mode. A recurrence reopens the
CAPA — it does not create a new one.

${line}

*This SOP is the company. If a shipment needs an exception to this SOP, the answer is no.*
`;

  // ---------- 5. investor update template ----------
  const update = `# Investor Update — [Month Year]

Send on the 5th of every month whether or not there is good news. Investors forgive bad
months; they do not forgive finding out late.

${line}

## Headline

One sentence. Revenue vs plan, and whether runway changed.

## Numbers

| Metric | Plan | Actual | Variance |
|---|---:|---:|---:|
| Revenue MTD | | | |
| Gross margin % | ${pct(model.years[0].gmPct)} FY1 plan | | |
| D2C orders | | | |
| B2B micro-lots shipped | | | |
| Cash at bank | | | |
| Runway (months) | | | |

## What worked

Two or three things, specific, with a number attached. "Trade show produced 14 qualified
leads, 3 samples sent" beats "good traction".

## What did not

One thing minimum. If a month has no miss, the reporting is not honest.

## Lot and quality

Lots received, lots rejected, rejection reasons. This section exists because quality is the
company's whole claim — an investor should be able to see it degrade before the P&L does.

## Ask

One specific ask. An introduction, a hire, a buyer, a term. If there is no ask, say so.

${line}

*Every figure in this update must come from the same source as the deck and the model.
If they disagree, the update is wrong.*
`;

  // ---------- 6. content calendar ----------
  const content = `# 90-Day Content Plan

Voice: name the grade, the lot, the test result. No "exotic", no "authentic",
no claims about health.

${line}

## Cadence

| Channel | Frequency | Purpose | Owner |
|---|---|---|---|
| Product page + lot page | per lot | The proof surface. Every other channel links here. | Founder, Sourcing |
| Email, D2C list | every 2 weeks | Recipes that require a specific grade, not generic content | Growth |
| Trade email | per lot cycle | Lot sheet to the 40-account list | Founder, Commercial |
| Instagram / short video | 3× per week | Process, test results, the rejection story | Growth |
| Trade show follow-up | within 48 h | Sample offer, not a brochure | Commercial |

## The 12 pieces that carry the first quarter

1. **Why we reject 6% of the lots we see** — the number is the brand
2. **What a lab panel actually tests** — one panel, annotated, no jargon
3. **Tellicherry vs MG-1** — same plant, different sieve, different job
4. **The EtO story** — why we steam-treat and what fumigation does to a shipment
5. **How to read a lot number** — makes the buyer feel competent, not lectured
6. **A kilo of pepper, four kitchens** — one SKU, four uses, four chefs
7. **What 12% moisture means in a kitchen** — practical, not technical
8. **The freight calendar** — when to order for a December menu
9. **A rejection, written up honestly** — the post nobody else publishes
10. **Our two grower clusters** — names, districts, what they grow
11. **Why Indian pepper got scarce in 2025** — the crop story with numbers
12. **How to store whole pepper** — the most-searched, least-answered question

## Rules

- Every claim links to a lot or a test
- No health claims. Pepper is food.
- No "premium quality". Say the grade.
- Photograph the actual product. No stock images.
- If a number is old, date it.

${line}

## 10 launch-week post captions

1. Lot ${lotRef(t)}. ${t.siteLot?.panel?.sieve_mm ?? '—'} mm sieve, ${t.siteLot?.panel?.piperine_pct ?? '—'}% piperine, EtO not detected.
2. We reject about six lots in a hundred. This is why.
3. The bag has a number on it. Ask any other pepper what its number is.
4. Four spices, two clusters, one district.
5. Steam-treated. Not fumigated. There is a difference and it is on the panel.
6. 0% duty into the EU and the US. The cost is in the testing, not the tariff.
7. Tellicherry is not a variety. It is a size grade. Here is the sieve.
8. Our 500 g bag is more expensive per kilo than a bulk sack. Here is where it goes.
9. A restaurant kitchen buys 25 kg at a time. Same lot as your jar.
10. Pepper does not need a story. It needs a test result.
`;

  return [
    { path: 'ops/trade-lot-sheet.md', body: tradeSheet },
    { path: 'ops/b2b-outreach.md', body: outreach },
    { path: 'ops/exception-playbooks.md', body: playbooks },
    { path: 'ops/SOP-01-lot-intake-and-release.md', body: sop },
    { path: 'ops/investor-update-template.md', body: update },
    { path: 'ops/content-calendar.md', body: content },
  ];
}

export function emails(t, model = computePlan(t)) {
  // D2C flows and B2B sequences as a machine-readable-ish markdown for handoff
  return `# Email Library

${line}

## FLOW 1 — Welcome (D2C, triggered on signup)

**Subject:** The number on your bag

> You are on the list for the next lot.
>
> Every bag we ship carries a lot number — KL-YYYY-NNN — and that number resolves to a test
> panel: aflatoxin, ochratoxin, Salmonella, heavy metals, pesticide residues, ethylene oxide.
>
> Nothing ships before its panel clears. That is the only promise we make.
>
> — Kollam Pepper Co, Kochi

## FLOW 2 — Abandoned cart (2 emails)

**Email A, 4 h**

**Subject:** Still on the shelf

> Your cart is holding a 500 g Tellicherry Bold. Current lot: ${lotRef(t)}, ${t.siteLot?.panel?.piperine_pct ?? '—'}% piperine.
> It will still be there tomorrow. The lot number will change when this one sells out.

**Email B, 48 h**

**Subject:** Last call on lot ${lotRef(t)}

> When this lot is gone, the next one gets a new number and a new panel. The price does not
> change. The proof does.

## FLOW 3 — Post-purchase (3 emails)

**Day 0 — Subject: Lot ${lotRef(t)}, panel inside**

> Your bag is on its way. The panel for this lot is attached and the number is printed on the
> liner. If the numbers and the bag ever disagree, that is our problem, not yours.

**Day 7 — Subject: One thing to try**

> Grind it at the last second. Pre-ground pepper loses the volatile oil that you paid for —
> our spec is ${t.compliance.quality_specs.volatile_oil_ml_per_100g_min} ml/100 g minimum, and most of it leaves within days of grinding.

**Day 21 — Subject: How was the lot?**

> One question: did it earn a second bag? Reply with a sentence either way. We read them.

${line}

## B2B — see ops/b2b-outreach.md

## Exception comms — see ops/exception-playbooks.md
`;
}
