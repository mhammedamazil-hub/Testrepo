import test from 'node:test';
import assert from 'node:assert/strict';

import { panelDigest, buildPassport, verifyCode, PASSPORT_RE } from '../scripts/lib/passport.mjs';

const ENTRY = {
  at: '2026-11-10T03:00:00.000Z',
  supplier: 'Idukki cluster A',
  lot: 'KL-2026-001',
  disposition: 'RELEASE',
  grade: 'TGSEB',
  panel: {
    grade: 'TGSEB',
    sieve_mm: 5.2,
    moisture_pct: 10.8,
    piperine_pct: 6.1,
    aflatoxin_b1_ugkg: 0.4,
    aflatoxin_total_ugkg: 1.1,
    ochratoxin_a_ugkg: 1.8,
    salmonella_25g: 'absent',
    ethylene_oxide: 'not detected',
    lead_mgkg: 0.08,
    foreign_matter_pct: 0.1,
  },
  reasons: [],
};

/** Same lot, panel keys in a different insertion order. */
const REORDERED = {
  ...ENTRY,
  panel: Object.fromEntries(Object.entries(ENTRY.panel).reverse()),
};

test('the digest is stable regardless of panel key order', () => {
  assert.equal(panelDigest(ENTRY), panelDigest(REORDERED));
});

test('the digest is shaped like something a human can read off a bag', () => {
  assert.match(panelDigest(ENTRY), PASSPORT_RE);
});

test('changing one measured value changes the digest', () => {
  const tampered = { ...ENTRY, panel: { ...ENTRY.panel, piperine_pct: 6.2 } };
  assert.notEqual(panelDigest(ENTRY), panelDigest(tampered));
});

test('changing a value by one character changes the digest', () => {
  // the whole point: "not detected" and "0.05" must not hash the same
  const tampered = { ...ENTRY, panel: { ...ENTRY.panel, ethylene_oxide: '0.05' } };
  assert.notEqual(panelDigest(ENTRY), panelDigest(tampered));
});

test('the digest binds the supplier, not only the pepper', () => {
  const other = { ...ENTRY, supplier: 'Kasaragod trader' };
  assert.notEqual(panelDigest(ENTRY), panelDigest(other));
});

test('the digest binds the lot number', () => {
  const other = { ...ENTRY, lot: 'KL-2026-002' };
  assert.notEqual(panelDigest(ENTRY), panelDigest(other));
});

test('a lot that was never released cannot have a passport', () => {
  assert.throws(() => buildPassport({ ...ENTRY, lot: null, disposition: 'REJECT' }), /released lot/i);
  assert.throws(() => buildPassport({ ...ENTRY, disposition: 'HOLD' }), /released lot/i);
});

test('the passport carries the panel, the verdict and the digest', () => {
  const p = buildPassport(ENTRY);
  assert.equal(p.lot, 'KL-2026-001');
  assert.equal(p.code, panelDigest(ENTRY));
  assert.equal(p.disposition, 'RELEASE');
  assert.equal(p.panel.piperine_pct, 6.1);
  assert.equal(p.findings, 0);
  assert.equal(p.supplier, 'Idukki cluster A');
});

test('the passport states what the code does and does not prove', () => {
  const p = buildPassport(ENTRY);
  assert.match(p.claim, /panel the gate evaluated/i);
  assert.match(p.limit, /does not prove the laboratory was honest|not prove.*laborator/i);
});

test('a matching code verifies', () => {
  assert.equal(verifyCode(ENTRY, panelDigest(ENTRY)), true);
});

test('a code from a different lot does not verify', () => {
  const other = { ...ENTRY, lot: 'KL-2026-002' };
  assert.equal(verifyCode(ENTRY, panelDigest(other)), false);
});

test('verification accepts lower case and surrounding whitespace, and never throws', () => {
  const code = panelDigest(ENTRY);
  assert.equal(verifyCode(ENTRY, `  ${code.toLowerCase()} `), true);
  assert.equal(verifyCode(ENTRY, ''), false);
  assert.equal(verifyCode(ENTRY, null), false);
  assert.equal(verifyCode(ENTRY, { code }), false);
});

test('the digest is a fixed length, so a truncated copy fails loudly rather than loosely', () => {
  const code = panelDigest(ENTRY);
  assert.equal(verifyCode(ENTRY, code.slice(0, 4)), false);
});
