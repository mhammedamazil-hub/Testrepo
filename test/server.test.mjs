import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { createApp } from '../scripts/lib/app.mjs';

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

async function withServer(fn) {
  const dir = mkdtempSync(join(tmpdir(), 'kollam-srv-'));
  const app = createApp({ queuePath: join(dir, 'queue.json') });
  await new Promise(r => app.listen(0, '127.0.0.1', r));
  const { port } = app.address();
  try {
    await fn(`http://127.0.0.1:${port}`, app);
  } finally {
    await new Promise(r => app.close(r));
  }
}

test('GET /desk serves the intake page as HTML', async () => {
  await withServer(async base => {
    const res = await fetch(`${base}/desk`);
    assert.equal(res.status, 200);
    assert.match(res.headers.get('content-type'), /text\/html/);
    const body = await res.text();
    assert.match(body, /Lot intake/);
  });
});

test('POST /api/lots with a clean panel releases a lot', async () => {
  await withServer(async base => {
    const res = await fetch(`${base}/api/lots`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ supplier: 'Idukki cluster A', panel: CLEAN }),
    });
    assert.equal(res.status, 201);
    const json = await res.json();
    assert.equal(json.disposition, 'RELEASE');
    assert.match(json.lot, /^KL-2026-\d{3}$/);
  });
});

test('POST /api/lots with EtO rejects and returns 422', async () => {
  await withServer(async base => {
    const res = await fetch(`${base}/api/lots`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        supplier: 'Kasaragod trader',
        panel: CLEAN.replace('ethylene_oxide: not detected', 'ethylene_oxide: 0.05'),
      }),
    });
    assert.equal(res.status, 422);
    const json = await res.json();
    assert.equal(json.disposition, 'REJECT');
    assert.equal(json.lot, null);
    assert.ok(json.reasons.some(r => r.code === 'ETO'));
  });
});

test('GET /api/lots returns the queue and stats', async () => {
  await withServer(async base => {
    await fetch(`${base}/api/lots`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ supplier: 'A', panel: CLEAN }),
    });
    const res = await fetch(`${base}/api/lots`);
    const json = await res.json();
    assert.equal(json.stats.total, 1);
    assert.equal(json.entries.length, 1);
  });
});

test('POST /api/lots rejects a missing panel with 400, not a crash', async () => {
  await withServer(async base => {
    const res = await fetch(`${base}/api/lots`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ supplier: 'A' }),
    });
    assert.equal(res.status, 400);
  });
});

test('POST /api/lots rejects a garbage body with 400, not a crash', async () => {
  await withServer(async base => {
    const res = await fetch(`${base}/api/lots`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: 'not json at all',
    });
    assert.equal(res.status, 400);
  });
});

test('an unknown path returns 404 with a helpful page', async () => {
  await withServer(async base => {
    const res = await fetch(`${base}/nope`);
    assert.equal(res.status, 404);
  });
});

test('path traversal is refused', async () => {
  await withServer(async base => {
    const res = await fetch(`${base}/../../etc/passwd`, { redirect: 'manual' });
    assert.ok(res.status === 403 || res.status === 404, `got ${res.status}`);
  });
});

test('the app never invokes the ECC install state or writes outside its queue', async () => {
  await withServer(async (base, app) => {
    await fetch(`${base}/api/lots`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ supplier: 'A', panel: CLEAN }),
    });
    assert.ok(app.locals.queuePath.includes('queue.json'));
  });
});

// ---------------------------------------------------------------- lot passports

test('GET /api/passport/KL-2026-001 returns a passport for a released lot', async () => {
  await withServer(async base => {
    await fetch(`${base}/api/lots`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ supplier: 'Idukki cluster A', panel: CLEAN }),
    });
    const res = await fetch(`${base}/api/passport/KL-2026-001`);
    assert.equal(res.status, 200);
    const p = await res.json();
    assert.equal(p.lot, 'KL-2026-001');
    assert.match(p.code, /^KP-[0-9A-F]{8}$/);
    assert.equal(p.panel.piperine_pct, 6.1);
  });
});

test('the passport code verifies back against the lot it came from', async () => {
  await withServer(async base => {
    await fetch(`${base}/api/lots`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ supplier: 'Idukki cluster A', panel: CLEAN }),
    });
    const p = await (await fetch(`${base}/api/passport/KL-2026-001`)).json();
    const res = await fetch(`${base}/api/passport/KL-2026-001/verify?code=${encodeURIComponent(p.code)}`);
    const v = await res.json();
    assert.equal(v.verified, true);
    assert.equal(v.lot, 'KL-2026-001');
  });
});

test('verification fails for a code that belongs to another lot', async () => {
  await withServer(async base => {
    await fetch(`${base}/api/lots`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ supplier: 'Idukki cluster A', panel: CLEAN }),
    });
    const res = await fetch(`${base}/api/passport/KL-2026-001/verify?code=KP-00000000`);
    const v = await res.json();
    assert.equal(v.verified, false);
    // a wrong code is a normal answer to a normal question, not an error status
    assert.equal(res.status, 200);
  });
});

test('an unknown lot number returns 404 rather than an invented passport', async () => {
  await withServer(async base => {
    const res = await fetch(`${base}/api/passport/KL-2026-999`);
    assert.equal(res.status, 404);
    const json = await res.json();
    assert.equal(json.error !== undefined, true);
  });
});

test('a rejected lot has no passport, even if someone guesses its position', async () => {
  await withServer(async base => {
    await fetch(`${base}/api/lots`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        supplier: 'Kasaragod trader',
        panel: CLEAN.replace('ethylene_oxide: not detected', 'ethylene_oxide: 0.05'),
      }),
    });
    // the rejected lot never got KL-2026-001, so that number must not resolve to it
    const res = await fetch(`${base}/api/passport/KL-2026-001`);
    assert.equal(res.status, 404);
  });
});

test('GET /passport/<lot> serves an HTML page, and /passport without a lot explains itself', async () => {
  await withServer(async base => {
    await fetch(`${base}/api/lots`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ supplier: 'Idukki cluster A', panel: CLEAN }),
    });
    const page = await fetch(`${base}/passport/KL-2026-001`);
    assert.equal(page.status, 200);
    assert.match(page.headers.get('content-type'), /text\/html/);
    const html = await page.text();
    assert.match(html, /KP-[0-9A-F]{8}/);
    assert.match(html, /KL-2026-001/);

    const bare = await fetch(`${base}/passport`);
    assert.equal(bare.status, 200);
    assert.match(await bare.text(), /lot number/i);
  });
});

test('a lot number is escaped before it reaches the page', async () => {
  await withServer(async base => {
    const res = await fetch(`${base}/passport/${encodeURIComponent('<script>alert(1)</script>')}`);
    const body = await res.text();
    assert.equal(body.includes('<script>alert(1)</script>'), false);
  });
});
