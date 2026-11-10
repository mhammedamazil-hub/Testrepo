/**
 * Lot passports.
 *
 * The storefront claims every bag carries a lot number and a test panel. Until a buyer
 * can check that claim against the bag in their hand, it is a slogan. This module turns
 * a released lot into a short code that is derived from the panel the gate actually
 * evaluated, so changing one measured value changes the code.
 *
 * What it is: an integrity check. A clerk with the bag and the code can tell whether the
 * page they were shown is the record behind that bag.
 *
 * What it is not: proof of origin, proof of laboratory honesty, or a signature. Those are
 * chain of custody and accreditation, and pretending a hash solved them would be worse
 * than not having a hash. The passport says so in plain words on the page.
 */
import { createHash } from 'node:crypto';

export const PASSPORT_RE = /^KP-[0-9A-F]{8}$/;

/** Fixed, explicit field order — the digest must not depend on JS key insertion order. */
const DIGESTED_FIELDS = Object.freeze([
  'grade',
  'sieve_mm',
  'moisture_pct',
  'piperine_pct',
  'aflatoxin_b1_ugkg',
  'aflatoxin_total_ugkg',
  'ochratoxin_a_ugkg',
  'lead_mgkg',
  'foreign_matter_pct',
  'bulk_density_g_per_l',
  'salmonella_25g',
  'ethylene_oxide',
]);

function canonical(value) {
  // Normalise only the things a lab writes inconsistently. Never normalise a number.
  if (typeof value === 'string') return value.trim().toLowerCase().replace(/\s+/g, ' ');
  if (typeof value === 'number') return String(value);
  return String(value ?? '');
}

/**
 * @param {{supplier: string, lot: string|null, panel: object}} entry
 * @returns {string} e.g. KP-4A9C21F0
 */
export function panelDigest(entry) {
  const panel = entry.panel ?? {};
  const rows = DIGESTED_FIELDS.map(f => `${f}=${canonical(panel[f])}`).join('\n');
  // the supplier and the lot number are part of the record: a panel alone does not
  // say which bag it is describing, and a lot number alone does not say what is in it
  const body = ['kollam.passport.v1', `supplier=${canonical(entry.supplier)}`, `lot=${canonical(entry.lot)}`, rows].join('\n');
  const hex = createHash('sha256').update(body, 'utf8').digest('hex');
  return `KP-${hex.slice(0, 8).toUpperCase()}`;
}

/**
 * Only a released lot has a passport. A held lot has a panel and a problem; a rejected
 * lot has neither a number nor a claim to make. This mirrors assignLotNumber(), which
 * also refuses anything that is not a release.
 */
export function buildPassport(entry) {
  if (!entry || entry.disposition !== 'RELEASE' || !entry.lot) {
    throw new Error('Only a released lot with a lot number can carry a passport.');
  }
  const panel = { ...(entry.panel ?? {}) };
  return {
    lot: entry.lot,
    code: panelDigest(entry),
    disposition: entry.disposition,
    grade: entry.grade ?? panel.grade ?? null,
    supplier: entry.supplier,
    released_at: entry.at,
    findings: (entry.reasons ?? []).length,
    panel,
    claim:
      'This code is derived from the exact panel the gate evaluated. If the code on the bag and the code on this page differ, the panel has been altered since release.',
    limit:
      'It does not prove the laboratory was honest or that the pepper in the bag is the pepper in the sample. That is what accreditation, sealed samples and chain of custody are for.',
  };
}

/**
 * Compare a code read off a bag with a lot record. Never throws — a customer typing a
 * code into a form must get "no" rather than a stack trace.
 */
export function verifyCode(entry, code) {
  if (typeof code !== 'string') return false;
  const clean = code.trim().toLowerCase();
  if (!clean) return false;
  const expected = panelDigest(entry ?? {}).toLowerCase();
  // length check first so a truncated paste fails cleanly rather than by prefix luck
  if (clean.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i += 1) diff |= clean.charCodeAt(i) ^ expected.charCodeAt(i);
  return diff === 0;
}
