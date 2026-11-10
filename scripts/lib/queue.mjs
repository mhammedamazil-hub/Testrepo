/**
 * Append-only lot queue.
 *
 * A JSON file on purpose: it can be read by a human, diffed in git, and audited.
 * The queue is the company's evidence trail — if it is corrupt, we stop, because a
 * quietly-forgotten lot is worse than a broken build.
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { evaluateLot, assignLotNumber, DISPOSITION } from './rules.mjs';

const CURRENT_YEAR = 2026;

export function openQueue(path) {
  let entries = [];

  if (existsSync(path)) {
    const raw = readFileSync(path, 'utf8');
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed.entries)) throw new Error('missing entries array');
      entries = parsed.entries;
    } catch (err) {
      throw new Error(`Queue file is corrupt or invalid: ${path} (${err.message})`);
    }
  }

  const persist = () => {
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, JSON.stringify({ schema: 'kollam.lot-queue.v1', entries }, null, 2) + '\n', 'utf8');
  };

  const maxSequence = () =>
    entries.reduce((max, e) => {
      if (!e.lot) return max;
      const m = e.lot.match(/^KL-\d{4}-(\d{3})$/);
      return m ? Math.max(max, Number(m[1])) : max;
    }, 0);

  const fingerprint = (supplier, panel) =>
    `${supplier}|${JSON.stringify(
      Object.keys(panel)
        .sort()
        .map(k => [k, panel[k]])
    )}`;

  return {
    list() {
      return entries.map(e => ({ ...e }));
    },

    submit({ supplier, panel }, truth, opts = {}) {
      if (!supplier || typeof supplier !== 'string') throw new Error('A supplier name is required.');
      if (!panel) throw new Error('A parsed panel is required.');

      const fp = fingerprint(supplier, panel);
      if (entries.some(e => e.fingerprint === fp)) {
        throw new Error('Duplicate submission: this supplier already filed an identical panel.');
      }

      const { disposition, reasons } = evaluateLot(panel, truth);

      let lot = null;
      if (disposition === DISPOSITION.RELEASE) {
        lot = assignLotNumber({
          year: opts.year ?? CURRENT_YEAR,
          sequence: maxSequence() + 1,
          disposition,
        });
      }

      const entry = {
        at: new Date().toISOString(),
        supplier,
        lot,
        disposition,
        grade: panel.grade ?? null,
        // the measured values travel with the lot: a lot number that does not resolve
        // to a panel is a label, not evidence
        panel: { ...panel },
        reasons,
        fingerprint: fp,
      };
      entries.push(entry);
      persist();
      return { ...entry };
    },

    stats() {
      const out = { total: entries.length, release: 0, hold: 0, reject: 0 };
      for (const e of entries) {
        if (e.disposition === DISPOSITION.RELEASE) out.release += 1;
        else if (e.disposition === DISPOSITION.HOLD) out.hold += 1;
        else out.reject += 1;
      }
      return out;
    },

    /** Rejection reasons ranked, so a supplier review has a starting point. */
    rejectionBreakdown() {
      const tally = new Map();
      for (const e of entries) {
        if (e.disposition === DISPOSITION.RELEASE) continue;
        for (const r of e.reasons) tally.set(r.code, (tally.get(r.code) ?? 0) + 1);
      }
      return [...tally.entries()].sort((a, b) => b[1] - a[1]).map(([code, count]) => ({ code, count }));
    },
  };
}
