# Lot gate evidence log

**Generated:** 2026-11-10 · **Source:** `data/lot-queue.json`
**Enforced by:** `scripts/lib/rules.mjs` (24 unit tests) via `scripts/lib/queue.mjs` (9 unit tests)

> This file is produced by the build from the actual queue. It is not a mock-up. If the
> numbers below look bad, the company looks bad, and that is the point.

## Headline

| | Count | Share |
|---|---:|---:|
| Lots submitted | 2 | 100% |
| **Released** with a KL number | 1 | 50% |
| Held for rework | 0 | 0% |
| **Rejected** | 1 | 50% |



## Findings that stopped a lot

- **ETO** — 1 occurrence

## Every lot, in order

| When | Supplier | Lot | Disposition | Findings | Passport |
|---|---|---|---|---|
| 2026-11-10 02:58 | Idukki cluster A | KL-2026-001 | RELEASE | clear | KP-CD719E6B |
| 2026-11-10 02:58 | Kasaragod trader | — | REJECT | ETO | — |

A passport code is a digest of the panel above plus the supplier and the lot number. Change one
measured value and the code changes, which is the only useful property it has. It is not a
signature and it is not proof of origin; the page says so where a buyer will read it.

## Why this log exists

The ECC `quality-nonconformance` skill is blunt about this: a CAPA closes on evidence, not
on a promise. The same applies to a lot. A document that says "every lot is tested" is
marketing. A document that lists which lots failed, and why, is a quality system.

The gate cannot be talked out of a rejection. There is no override flag, no "accept anyway"
button, and no path where a lot without a panel receives a number.
