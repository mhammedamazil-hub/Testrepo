/**
 * The lot gate, as executable rules.
 * Every threshold here traces to company/source-of-truth.json -> compliance.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  parsePanel,
  evaluateLot,
  assignLotNumber,
  validateLotNumber,
  DISPOSITION,
} from '../scripts/lib/rules.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const truth = JSON.parse(readFileSync(join(ROOT, 'company', 'source-of-truth.json'), 'utf8'));

const CLEAN = `fixture: clean TGSEB lot
grade: TGSEB
sieve_mm: 5.2
moisture_pct: 10.8
piperine_pct: 6.1
aflatoxin_b1_ugkg: 0.4
aflatoxin_total_ugkg: 1.1
ochratoxin_a_ugkg: 1.8
salmonella_25g: absent
ethylene_oxide: not detected
lead_mgkg: 0.08
foreign_matter_pct: 0.1
`;

// ---------------------------------------------------------------- parsing
test('parsePanel reads key: value lines and ignores comments', () => {
  const p = parsePanel(CLEAN);
  assert.equal(p.grade, 'TGSEB');
  assert.equal(p.sieve_mm, 5.2);
  assert.equal(p.moisture_pct, 10.8);
  assert.equal(p.salmonella_25g, 'absent');
  assert.equal(p.ethylene_oxide, 'not detected');
});

test('parsePanel rejects a panel with no recognised fields', () => {
  assert.throws(() => parsePanel('hello world'), /no panel fields/i);
});

test('parsePanel rejects duplicate keys, because the second one is a lie', () => {
  assert.throws(() => parsePanel('moisture_pct: 10\nmoisture_pct: 14\n'), /duplicate/i);
});

test('parsePanel rejects non-numeric values on numeric fields', () => {
  assert.throws(() => parsePanel('aflatoxin_b1_ugkg: trace\n'), /numeric/i);
});

// ---------------------------------------------------------------- the gate
test('a clean lot is RELEASED', () => {
  const r = evaluateLot(parsePanel(CLEAN), truth);
  assert.equal(r.disposition, DISPOSITION.RELEASE);
  assert.equal(r.reasons.length, 0);
});

test('ethylene oxide at any detection is a hard REJECT, not a threshold', () => {
  const p = parsePanel(CLEAN.replace('ethylene_oxide: not detected', 'ethylene_oxide: 0.05'));
  const r = evaluateLot(p, truth);
  assert.equal(r.disposition, DISPOSITION.REJECT);
  assert.ok(r.reasons.some(x => x.code === 'ETO'));
});

test('ethylene oxide "detected at LOQ" is still a reject', () => {
  const p = parsePanel(CLEAN.replace('ethylene_oxide: not detected', 'ethylene_oxide: detected at LOQ'));
  const r = evaluateLot(p, truth);
  assert.equal(r.disposition, DISPOSITION.REJECT);
});

test('aflatoxin B1 above 5.0 µg/kg rejects', () => {
  const p = parsePanel(CLEAN.replace('aflatoxin_b1_ugkg: 0.4', 'aflatoxin_b1_ugkg: 5.1'));
  const r = evaluateLot(p, truth);
  assert.equal(r.disposition, DISPOSITION.REJECT);
  assert.ok(r.reasons.some(x => x.code === 'AFLATOXIN_B1'));
});

test('aflatoxin B1 exactly at the limit passes — the limit is the limit', () => {
  const p = parsePanel(CLEAN.replace('aflatoxin_b1_ugkg: 0.4', 'aflatoxin_b1_ugkg: 5.0'));
  assert.equal(evaluateLot(p, truth).disposition, DISPOSITION.RELEASE);
});

test('total aflatoxins above 10.0 rejects', () => {
  const p = parsePanel(CLEAN.replace('aflatoxin_total_ugkg: 1.1', 'aflatoxin_total_ugkg: 10.4'));
  assert.equal(evaluateLot(p, truth).disposition, DISPOSITION.REJECT);
});

test('ochratoxin A above 15 rejects', () => {
  const p = parsePanel(CLEAN.replace('ochratoxin_a_ugkg: 1.8', 'ochratoxin_a_ugkg: 16'));
  assert.equal(evaluateLot(p, truth).disposition, DISPOSITION.REJECT);
});

test('salmonella present rejects; "absent" and "not detected" both pass', () => {
  const bad = parsePanel(CLEAN.replace('salmonella_25g: absent', 'salmonella_25g: present'));
  assert.equal(evaluateLot(bad, truth).disposition, DISPOSITION.REJECT);
  const nd = parsePanel(CLEAN.replace('salmonella_25g: absent', 'salmonella_25g: not detected'));
  assert.equal(evaluateLot(nd, truth).disposition, DISPOSITION.RELEASE);
});

test('lead above 0.6 mg/kg rejects', () => {
  const p = parsePanel(CLEAN.replace('lead_mgkg: 0.08', 'lead_mgkg: 0.7'));
  assert.equal(evaluateLot(p, truth).disposition, DISPOSITION.REJECT);
});

test('moisture above 12% is a HOLD, not a reject — it can be re-dried', () => {
  const p = parsePanel(CLEAN.replace('moisture_pct: 10.8', 'moisture_pct: 13.4'));
  const r = evaluateLot(p, truth);
  assert.equal(r.disposition, DISPOSITION.HOLD);
  assert.ok(r.reasons.some(x => x.code === 'MOISTURE'));
});

test('a hold plus a reject resolves to reject — the worst finding wins', () => {
  const p = parsePanel(
    CLEAN.replace('moisture_pct: 10.8', 'moisture_pct: 13.4').replace('aflatoxin_b1_ugkg: 0.4', 'aflatoxin_b1_ugkg: 9')
  );
  assert.equal(evaluateLot(p, truth).disposition, DISPOSITION.REJECT);
});

test('foreign matter above 0.5% is a HOLD', () => {
  const p = parsePanel(CLEAN.replace('foreign_matter_pct: 0.1', 'foreign_matter_pct: 0.9'));
  assert.equal(evaluateLot(p, truth).disposition, DISPOSITION.HOLD);
});

test('MG-1 graded below its sieve is a HOLD for re-grade; TGSEB below 5.0 is the same', () => {
  const p = parsePanel(CLEAN.replace('sieve_mm: 5.2', 'sieve_mm: 4.4'));
  const r = evaluateLot(p, truth);
  assert.equal(r.disposition, DISPOSITION.HOLD);
  assert.ok(r.reasons.some(x => x.code === 'SIEVE'));
});

test('piperine outside the grade band is a HOLD', () => {
  const p = parsePanel(CLEAN.replace('piperine_pct: 6.1', 'piperine_pct: 3.1'));
  assert.equal(evaluateLot(p, truth).disposition, DISPOSITION.HOLD);
});

test('an unknown grade cannot be released', () => {
  const p = parsePanel(CLEAN.replace('grade: TGSEB', 'grade: AAA-PLUS'));
  const r = evaluateLot(p, truth);
  assert.equal(r.disposition, DISPOSITION.HOLD);
  assert.ok(r.reasons.some(x => x.code === 'GRADE_UNKNOWN'));
});

test('a missing critical test is a HOLD — an untested lot is not a clean lot', () => {
  const p = parsePanel(CLEAN.replace('ethylene_oxide: not detected\n', ''));
  const r = evaluateLot(p, truth);
  assert.equal(r.disposition, DISPOSITION.HOLD);
  assert.ok(r.reasons.some(x => x.code === 'MISSING_TEST' && x.field === 'ethylene_oxide'));
});

test('every reason carries a code, a field, and a human sentence', () => {
  const p = parsePanel(CLEAN.replace('aflatoxin_b1_ugkg: 0.4', 'aflatoxin_b1_ugkg: 9'));
  const r = evaluateLot(p, truth);
  for (const reason of r.reasons) {
    assert.match(reason.code, /^[A-Z][A-Z0-9_]*$/);
    assert.equal(typeof reason.field, 'string');
    assert.ok(reason.message.length > 15);
  }
});

// ---------------------------------------------------------------- lot numbers
test('a released lot gets a KL-YYYY-NNN number', () => {
  const n = assignLotNumber({ year: 2026, sequence: 14 });
  assert.equal(n, 'KL-2026-014');
  assert.equal(validateLotNumber(n), true);
});

test('lot numbers are rejected if malformed', () => {
  for (const bad of ['KL-26-14', 'kl-2026-014', 'KL-2026-14', 'KL-2026-0000', '']) {
    assert.equal(validateLotNumber(bad), false, bad);
  }
});

test('a rejected lot can never be assigned a number', () => {
  const p = parsePanel(CLEAN.replace('ethylene_oxide: not detected', 'ethylene_oxide: 0.2'));
  assert.throws(() => {
    const r = evaluateLot(p, truth);
    return assignLotNumber({ year: 2026, sequence: 15, disposition: r.disposition });
  }, /cannot assign/i);
});
