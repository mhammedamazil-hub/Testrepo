/**
 * Referring to a lot in generated documents.
 *
 * The rule: a document may only print a lot number that the gate actually issued. Before
 * this module existed, the brand-voice sample sentence and the sales emails quoted a
 * hard-coded "KL-2026-014" — a number that no lot ever received. That is the exact
 * fabrication this company sells against, committed in its own collateral.
 *
 * So: templates carry {lot}, {grade}, {sieve}, {piperine}; they are filled from the queue
 * at build time. When no lot has been released, the caller gets an honest sentence about
 * the absence instead of a plausible-looking number.
 */
import { buildPassport } from './passport.mjs';

export function hasLot(t) {
  return Boolean(t && t.siteLot && t.siteLot.lot);
}

/** Fill a template from the most recent released lot. */
export function fillLot(t, template) {
  const lot = t?.siteLot;
  if (!lot) return null;
  const p = lot.panel ?? {};
  return String(template)
    .replaceAll('{lot}', lot.lot)
    .replaceAll('{code}', t.siteLotCode ?? buildPassport(lot).code)
    .replaceAll('{grade}', lot.grade ?? p.grade ?? '—')
    .replaceAll('{sieve}', p.sieve_mm ?? '—')
    .replaceAll('{piperine}', p.piperine_pct ?? '—')
    .replaceAll('{moisture}', p.moisture_pct ?? '—');
}

/**
 * A lot reference for a document a human will send. Falls back to an obvious placeholder
 * rather than a number, because a wrong number in a buyer's inbox is worse than a bracket.
 */
export function lotRef(t) {
  return hasLot(t) ? t.siteLot.lot : '[current lot]';
}

/** Subject-line reference: lot number plus its distinguishing panel figure. */
export function lotRefLong(t) {
  if (!hasLot(t)) return '[current lot] — panel attached';
  const p = t.siteLot.panel ?? {};
  return `${t.siteLot.lot} — ${t.siteLot.grade ?? p.grade ?? 'graded'}, ${p.piperine_pct ?? '—'}% piperine, EtO not detected`;
}
