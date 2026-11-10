import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';

import { openQueue } from '../scripts/lib/queue.mjs';
import { parsePanel } from '../scripts/lib/rules.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const truth = JSON.parse(readFileSync(join(ROOT, 'company', 'source-of-truth.json'), 'utf8'));

const CLEAN = `grade: TGSEB
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

const BAD = CLEAN.replace('ethylene_oxide: not detected', 'ethylene_oxide: 0.05');

function fresh() {
  const dir = mkdtempSync(join(tmpdir(), 'kollam-'));
  return { dir, q: openQueue(join(dir, 'queue.json')) };
}

test('queue starts empty', () => {
  const { q } = fresh();
  assert.deepEqual(q.list(), []);
});

test('submitting a clean lot releases it and assigns a lot number', () => {
  const { q } = fresh();
  const r = q.submit({ supplier: 'Idukki cluster A', panel: parsePanel(CLEAN) }, truth);
  assert.equal(r.disposition, 'RELEASE');
  assert.match(r.lot, /^KL-\d{4}-\d{3}$/);
  assert.equal(q.list().length, 1);
});

test('submitting an EtO-positive lot rejects it and assigns no number', () => {
  const { q } = fresh();
  const r = q.submit({ supplier: 'Kasaragod trader', panel: parsePanel(BAD) }, truth);
  assert.equal(r.disposition, 'REJECT');
  assert.equal(r.lot, null);
});

test('lot numbers increment and are never reused after a rejection', () => {
  const { q } = fresh();
  const a = q.submit({ supplier: 'A', panel: parsePanel(CLEAN) }, truth);
  const rejected = q.submit({ supplier: 'B', panel: parsePanel(BAD) }, truth);
  const c = q.submit({ supplier: 'C', panel: parsePanel(CLEAN) }, truth);
  assert.equal(a.lot, 'KL-2026-001');
  assert.equal(rejected.lot, null);
  assert.equal(c.lot, 'KL-2026-002', 'a rejected lot must not consume a number');
});

test('the same supplier cannot resubmit an identical rejected panel as a new lot', () => {
  const { q } = fresh();
  q.submit({ supplier: 'B', panel: parsePanel(BAD) }, truth);
  assert.throws(() => q.submit({ supplier: 'B', panel: parsePanel(BAD) }, truth), /duplicate/i);
});

test('history survives reopening the file', () => {
  const { dir, q } = fresh();
  q.submit({ supplier: 'A', panel: parsePanel(CLEAN) }, truth);
  const reopened = openQueue(join(dir, 'queue.json'));
  assert.equal(reopened.list().length, 1);
  assert.equal(reopened.list()[0].supplier, 'A');
});

test('every entry records a timestamp and the reasons, not just the verdict', () => {
  const { q } = fresh();
  q.submit({ supplier: 'B', panel: parsePanel(BAD) }, truth);
  const [entry] = q.list();
  assert.ok(!Number.isNaN(Date.parse(entry.at)));
  assert.ok(entry.reasons.length > 0);
  assert.ok(entry.reasons.some(r => r.code === 'ETO'));
});

test('stats sum to the queue', () => {
  const { q } = fresh();
  q.submit({ supplier: 'A', panel: parsePanel(CLEAN) }, truth);
  q.submit({ supplier: 'B', panel: parsePanel(BAD) }, truth);
  q.submit({ supplier: 'C', panel: parsePanel(CLEAN.replace('moisture_pct: 10.8', 'moisture_pct: 13')) }, truth);
  const s = q.stats();
  assert.equal(s.total, 3);
  assert.equal(s.release, 1);
  assert.equal(s.reject, 1);
  assert.equal(s.hold, 1);
  assert.equal(s.release + s.hold + s.reject, s.total);
});

test('a corrupt queue file fails loudly rather than silently starting fresh', () => {
  const { dir } = fresh();
  const p = join(dir, 'queue.json');
  writeFileSync(p, '{ not json');
  assert.throws(() => openQueue(p), /corrupt|invalid/i);
});

test('a released lot stores the panel it was released on', () => {
  const { q } = fresh();
  q.submit({ supplier: 'A', panel: parsePanel(CLEAN) }, truth);
  const [entry] = q.list();
  assert.equal(entry.panel.piperine_pct, 6.1);
  assert.equal(entry.panel.ethylene_oxide, 'not detected');
  assert.equal(entry.panel.aflatoxin_b1_ugkg, 0.4);
});
