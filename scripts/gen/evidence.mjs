/**
 * Turn the real lot queue into evidence.
 *
 * The rule: any panel shown in a customer-facing document must have been produced by
 * the gate in scripts/lib/rules.mjs and recorded in data/lot-queue.json. If the queue is
 * empty, the documents say so rather than printing a convincing fabrication.
 */
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const QUEUE = join(ROOT, 'data', 'lot-queue.json');

export function loadEvidence() {
  const entries = [];
  if (existsSync(QUEUE)) {
    try {
      const parsed = JSON.parse(readFileSync(QUEUE, 'utf8'));
      if (Array.isArray(parsed.entries)) entries.push(...parsed.entries);
    } catch {
      // a corrupt queue must not silently become an empty one in the evidence log
      throw new Error(`data/lot-queue.json is corrupt; refusing to generate evidence from it.`);
    }
  }

  const released = entries.filter(e => e.disposition === 'RELEASE');
  const held = entries.filter(e => e.disposition === 'HOLD');
  const rejected = entries.filter(e => e.disposition === 'REJECT');

  const latestReleased = released.at(-1) ?? null;

  const tally = new Map();
  for (const e of [...held, ...rejected]) {
    for (const r of e.reasons) tally.set(r.code, (tally.get(r.code) ?? 0) + 1);
  }
  const breakdown = [...tally.entries()].sort((a, b) => b[1] - a[1]).map(([code, count]) => ({ code, count }));

  const json = {
    generated_at: new Date().toISOString(),
    source: 'data/lot-queue.json',
    enforced_by: 'scripts/lib/rules.mjs',
    totals: { submitted: entries.length, released: released.length, held: held.length, rejected: rejected.length },
    rejection_breakdown: breakdown,
    lots: entries.map(e => ({
      at: e.at, supplier: e.supplier, lot: e.lot, disposition: e.disposition,
      grade: e.grade, codes: e.reasons.map(r => r.code),
    })),
  };

  const pctOf = (n) => (entries.length ? `${((n / entries.length) * 100).toFixed(0)}%` : '—');

  const markdown = `# Lot gate evidence log

**Generated:** ${new Date().toISOString().slice(0, 10)} · **Source:** \`data/lot-queue.json\`
**Enforced by:** \`scripts/lib/rules.mjs\` (24 unit tests) via \`scripts/lib/queue.mjs\` (9 unit tests)

> This file is produced by the build from the actual queue. It is not a mock-up. If the
> numbers below look bad, the company looks bad, and that is the point.

## Headline

| | Count | Share |
|---|---:|---:|
| Lots submitted | ${entries.length} | 100% |
| **Released** with a KL number | ${released.length} | ${pctOf(released.length)} |
| Held for rework | ${held.length} | ${pctOf(held.length)} |
| **Rejected** | ${rejected.length} | ${pctOf(rejected.length)} |

${entries.length === 0 ? '_No lots have been submitted to the gate yet. Every panel shown in our marketing would be fabricated until this table has a row in it._' : ''}

## Findings that stopped a lot

${breakdown.length === 0 ? '_None. No lot has been held or rejected._' : breakdown.map(b => `- **${b.code}** — ${b.count} occurrence${b.count === 1 ? '' : 's'}`).join('\n')}

## Every lot, in order

${entries.length === 0 ? '_Empty._' : `| When | Supplier | Lot | Disposition | Findings |
|---|---|---|---|---|
${entries.map(e => `| ${e.at.slice(0, 16).replace('T', ' ')} | ${e.supplier} | ${e.lot ?? '—'} | ${e.disposition} | ${e.reasons.length ? e.reasons.map(r => r.code).join(', ') : 'clear'} |`).join('\n')}`}

## Why this log exists

The ECC \`quality-nonconformance\` skill is blunt about this: a CAPA closes on evidence, not
on a promise. The same applies to a lot. A document that says "every lot is tested" is
marketing. A document that lists which lots failed, and why, is a quality system.

The gate cannot be talked out of a rejection. There is no override flag, no "accept anyway"
button, and no path where a lot without a panel receives a number.
`;

  return { markdown, json, latestReleased };
}
