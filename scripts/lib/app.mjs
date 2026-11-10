/**
 * HTTP surface for the company: the storefront, the deck, and the live lot desk.
 *
 * Deliberately dependency-free. A pepper company's intake desk should not need a
 * node_modules tree to answer "can I sell this lot".
 */
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import { join, extname, normalize, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

import { openQueue } from './queue.mjs';
import { parsePanel } from './rules.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.md': 'text/plain; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.webp': 'image/webp',
  '.woff2': 'font/woff2',
};

const ROUTES = {
  '/': 'site/index.html',
  '/site': 'site/index.html',
  '/deck': 'deck/deck.html',
  '/deck/': 'deck/deck.html',
  '/one-pager': 'company/one-pager.md',
  '/dossier': 'company/company-dossier.md',
  '/model': 'company/model-output.json',
};

function json(res, status, body) {
  const payload = JSON.stringify(body, null, 2);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(payload),
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff',
  });
  res.end(payload);
}

async function readBody(req, limit = 64 * 1024) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > limit) throw Object.assign(new Error('Body too large'), { status: 413 });
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString('utf8');
}

/**
 * @param {{queuePath: string, truth: object}} opts
 */
export function createApp({ queuePath, truth = null }) {
  if (!queuePath) throw new Error('createApp requires a queuePath');
  if (!truth) {
    // read synchronously once; the spec file is small and must not change mid-request
    truth = JSON.parse(readFileSync(join(ROOT, 'company', 'source-of-truth.json'), 'utf8'));
  }

  const queue = () => openQueue(queuePath);

  const server = createServer(async (req, res) => {
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    const path = decodeURIComponent(url.pathname);
    const method = req.method || 'GET';

    try {
      // ---------------- API ----------------
      if (path === '/api/lots' && method === 'GET') {
        const q = queue();
        return json(res, 200, { stats: q.stats(), entries: q.list(), rejectionBreakdown: q.rejectionBreakdown() });
      }

      if (path === '/api/lots' && method === 'POST') {
        let body;
        try {
          body = JSON.parse(await readBody(req));
        } catch (err) {
          return json(res, 400, { error: 'Invalid JSON body', detail: err.message });
        }
        if (!body || typeof body.panel !== 'string') {
          return json(res, 400, { error: 'A "panel" string is required — paste the lab panel text.' });
        }

        let panel;
        try {
          panel = parsePanel(body.panel);
        } catch (err) {
          return json(res, 400, { error: 'Panel could not be parsed', detail: err.message });
        }

        let result;
        try {
          result = queue().submit({ supplier: body.supplier || 'unnamed', panel }, truth);
        } catch (err) {
          if (/duplicate/i.test(err.message)) {
            return json(res, 409, { error: err.message });
          }
          return json(res, 500, { error: err.message });
        }

        const status = result.disposition === 'RELEASE' ? 201 : 422;
        return json(res, status, result);
      }

      if (path === '/api/rules' && method === 'GET') {
        return json(res, 200, {
          compliance: truth.compliance,
          dispositions: ['RELEASE', 'HOLD', 'REJECT'],
        });
      }

      if (path.startsWith('/api/') && method !== 'GET' && !['/api/lots'].includes(path)) {
        return json(res, 405, { error: 'Method not allowed' });
      }
      if (path.startsWith('/api/')) {
        return json(res, 404, { error: `No API route ${path}` });
      }

      // ---------------- static ----------------
      if (method !== 'GET' && method !== 'HEAD') {
        res.writeHead(405, { allow: 'GET, HEAD, POST' }).end('Method not allowed');
        return;
      }

      let target = ROUTES[path] ? '/' + ROUTES[path] : path;
      if (path === '/desk') target = '/site/desk.html';

      const rel = normalize(target).replace(/^(\.\.[/\\])+/, '').replace(/^[/\\]+/, '');
      const file = join(ROOT, rel);
      if (!file.startsWith(ROOT + sep) && file !== ROOT) {
        res.writeHead(403).end('Forbidden');
        return;
      }

      const s = await stat(file).catch(() => null);
      if (!s || !s.isFile()) {
        res.writeHead(404, { 'content-type': 'text/html; charset=utf-8' });
        res.end(`<!doctype html><meta charset=utf-8><title>Not found</title>
<body style="font:16px system-ui;padding:48px;background:#f4efe6;color:#1c211c">
<h1 style="letter-spacing:.2em">KOLLAM·</h1>
<p>No file at <code>${rel.replace(/[<>&]/g, '')}</code>.</p>
<p>Try <a href="/">the storefront</a>, <a href="/desk">the lot desk</a>, or <a href="/deck">the deck</a>.</p>
</body>`);
        return;
      }

      const body = await readFile(file);
      res.writeHead(200, {
        'content-type': TYPES[extname(file)] || 'application/octet-stream',
        'content-length': body.length,
        'cache-control': 'no-store',
        'x-content-type-options': 'nosniff',
        'content-security-policy': "frame-ancestors *",
      });
      res.end(method === 'HEAD' ? undefined : body);
    } catch (err) {
      if (!res.headersSent) json(res, err.status || 500, { error: String(err.message || err) });
      else res.end();
    }
  });

  server.locals = { queuePath, root: ROOT };
  return server;
}
