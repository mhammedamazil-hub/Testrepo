# Exception Playbooks

Severity model is the ECC `logistics-exception-management` three-axis rule: score financial
impact, customer impact, and time sensitivity separately, then take the **highest** severity.
A $400 delay on a launch-critical restaurant order outranks a $3,000 delay on a stock order.

------------------------------------------------------------------------

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

------------------------------------------------------------------------

## Claims windows to put in the calendar at booking

| Mode | Damage | Delay | Authority |
|---|---|---|---|
| US domestic surface | 9 months from delivery | 9 months | 49 USC § 14706 (Carmack) |
| Air | 14 days | 21 days | Montreal Convention |
| Ocean (to EU/US) | Per B/L terms; check COGSA/Hague-Visby | Per B/L terms | Carrier's bill |
| Concealed damage, any mode | 5 days from delivery | — | Industry standard |
