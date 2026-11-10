# ECC memory vault — exported copy
This is a tracked export of the memos written through `npx ecc memory save`.
ECC's vault at `.ecc/memory/project/` gitignores itself (`*`), so the source of record is
local and machine-specific. This file is the durable copy that travels with the repo.
Regenerate with `npm run memory:export` if the vault changes.

---

## Kollam Pepper Co: why this company was chosen
`mem_20261110_3995ef09c658426fb916` · kind **decision** · scope project · trust unreviewed · tags strategy, provenance · written 2026-11-10T02:49:00.432Z

```text
Chosen wedge: verified Indian-origin pepper at lot level, not pepper volume.

Evidence: FY2024/25 Indian crop ~48,000 t vs ~81,000 t domestic consumption (India net-imported);
pepper is ~3% of India's USD 4.72 B spice export basket by value; retail Tellicherry sells at
GBP 27.95/kg and EUR 36.93/kg while Kochi terminal indicative print was INR 670-685/kg in mid-2025.

Rejected alternatives: commodity trading (no defensible margin), private label for EU grocers
(buyer owns the brand, we own the risk), oleoresin extraction (capex-heavy, different business).

Decision sits in company/source-of-truth.json -> wedge.
```

## Kollam Pepper Co: financial model must be driver-based
`mem_20261110_ccfba78e390d41b4a12e` · kind **lesson** · scope project · trust unreviewed · tags finance, validation · written 2026-11-10T02:49:00.811Z

```text
First draft hard-coded revenue and EBITDA alongside unit economics, and the numbers contradicted
each other (B2B margin printed as 42% in one place and 33.1% in another; blended margin 44.5%
against a stated "~37%").

Fix: source-of-truth.json stores only drivers (orders, AOV, micro-lot count, two channel margins,
opex lines). scripts/build.mjs derives revenue/gross profit/EBITDA. scripts/validate.mjs
re-derives them without importing the generator and fails the build on mismatch. 39 checks.

Lesson: if a document states a number twice, the second statement is a bug waiting to happen.
```

## Kollam Pepper Co: the lot gate is the company
`mem_20261110_85a46b4f232e443cbc13` · kind **runbook** · scope project · trust unreviewed · tags quality, compliance · written 2026-11-10T02:49:01.194Z

```text
No lot receives a KL-YYYY-NNN number until: signed no-EtO supplier declaration, intake moisture
and water activity, full lab panel (aflatoxin B1 <=5.0 ug/kg, total aflatoxins <=10.0 ug/kg,
ochratoxin A <=15 ug/kg, Salmonella absent in 25 g, EtO not detected, lead <=0.6 mg/kg,
pesticide MRR), grade verified by sieve and density.

Any EtO detection is a rejection, not a threshold negotiation - EtO is banned for food use in
the EU and measured with 2-chloroethanol. Duty is 0% into EU (0904 11 00) and US
(0904.11.00.20), so the panel is the actual cost centre, not tariff.
```
