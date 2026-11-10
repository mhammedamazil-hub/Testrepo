# SOP-01 · Lot Intake and Release

**Owner:** Founder, Sourcing & Quality
**Applies to:** every lot of whole pepper, without exception
**Authority:** only this SOP can create a KL-YYYY-NNN lot number. No number, no sale.

------------------------------------------------------------------------

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
| Moisture claimed | Must be ≤ 12% |
| Price | In ₹/kg, FOB equivalent, with the weighbridge basis stated |

## 2. Intake measurement (same day)

- [ ] Moisture and water activity. Over 12% → hold for
      re-drying, do not pay
- [ ] Visual grade: colour, size distribution, foreign matter
- [ ] Sieve check against the claimed grade
- [ ] Bulk density ≥ 500 g/l
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

Use the ECC `quality-nonconformance` disposition sequence, first applicable path wins:

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

------------------------------------------------------------------------

*This SOP is the company. If a shipment needs an exception to this SOP, the answer is no.*
