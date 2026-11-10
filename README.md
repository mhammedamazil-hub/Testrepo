# Kollam Pepper Co

A Kerala pepper house that owns the grade, the test panel, and the story — instead of exporting
anonymous bulk.

**Everything in `company/`, `deck/`, `site/` and `ops/` is generated.** The only file you edit
by hand is `company/source-of-truth.json`.

```bash
npm install
npm run build      # regenerate every document, deck, and page from the JSON
npm run validate   # re-derive all financials independently; fails on any mismatch
npm start          # preview: / storefront  ·  /deck investor deck
```

## What is here

| Path | What it is |
|---|---|
| `company/source-of-truth.json` | Every input number, assumption, risk, and limit. The only hand-edited file. |
| `company/company-dossier.md` | The full company: wedge, market, unit economics, 3-year plan, compliance, ops, team, risks |
| `company/one-pager.md` | One page for a buyer or an angel |
| `company/model-output.json` | Derived financials, machine-readable, for diffing |
| `deck/deck.html` / `deck/deck.md` | 15-slide investor deck, self-contained, printable |
| `site/index.html` | Storefront for the brand |
| `ops/SOP-01-lot-intake-and-release.md` | The lot gate. No lot number, no sale. |
| `ops/trade-lot-sheet.md` | What a B2B buyer receives with a shipment |
| `ops/b2b-outreach.md` | Four-touch sequence, call script, objection table |
| `ops/exception-playbooks.md` | Customs hold, lab failure, EtO positive, delay, damage, supplier off-spec |
| `ops/investor-update-template.md` | Monthly update with the quality section investors never get |
| `ops/content-calendar.md` | 90-day plan, 12 pieces, 10 captions |

## The company in four lines

1. Buy from named grower clusters in the Western Ghats.
2. Grade to Tellicherry / Malabar Garbled and test every lot to the destination's limits.
3. Assign a lot number — only after the panel clears.
4. Sell it two ways: retail packs under our own mark, and 25 kg micro-lots to kitchens.

## The numbers

| | FY1 | FY2 | FY3 |
|---|---:|---:|---:|
| Revenue | $157,660 | $486,800 | $895,200 |
| Gross margin | 44.5% | 44.6% | 44.4% |
| EBITDA | -$21,884 | $36,915 | $78,854 |

Bear case on FY3 (60% of revenue, 4 points off margin, flat opex): **-$101,532**.
That is the number the raise has to survive.

Ask: **$150,000**.

## Why this is defensible

Verified Indian origin is the scarce input, not pepper. The 2024/25 crop fell to ~48,000 t
against ~81,000 t of domestic consumption — India net-imported. Specialty retail sells
Tellicherry at GBP 27.95/kg and EUR 36.93/kg while the Kochi terminal prints around
Rs 670–685/kg. A 3.9× ladder that is climbed with paperwork and grading, not freight.

Duty is 0% on whole pepper into the EU (0904 11 00) and the US (0904.11.00), so the constraint
is the contaminant panel: aflatoxin B1 ≤ 5.0 µg/kg, total aflatoxins ≤ 10.0 µg/kg, ochratoxin A
≤ 15 µg/kg, Salmonella absent in 25 g, and ethylene oxide at zero tolerance in the EU.

## Built with ECC

The [ECC (everything-claude-code)](https://github.com/affaan-m/ECC) harness is installed in this
repo at `.claude/` — 68 agents, 293 skills, rules, and an install-state file.

```bash
npx ecc-universal@2.2.3 install --profile full --target claude-project --no-hooks
npx ecc list-installed
npx ecc doctor
npx ecc memory search "lot gate"
```

- `npx ecc doctor` → `status: OK, issues: none`
- Durable decisions are in the ECC memory vault at `.ecc/memory/project/`
  (why this company, why the model is driver-based, what the lot gate is)
- Skills actually exercised: `customs-trade-compliance`, `logistics-exception-management`,
  `quality-nonconformance`, `inventory-demand-planning`, `market-research`,
  `investor-materials`, `brand-voice`, `finance-billing-ops`, `seo`
- Agents mapped to work: `chief-of-staff`, `marketing-agent`, `seo-specialist`,
  `code-reviewer`, `security-reviewer`, `doc-updater`, `planner`, `performance-optimizer`

## What this is not

Pre-revenue planning material. Prices, freight, and retail observations are point-in-time.
The lot `KL-2026-014` on the site is illustrative. Regulatory limits are quoted from EU Reg
2023/915 and Reg (EC) 2073/2005 to explain the quality gate — verify destination requirements
before shipping anything real.
