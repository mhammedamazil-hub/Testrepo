#!/usr/bin/env node
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { join, extname, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const PORT = Number(process.env.PORT || 4173);

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.md': 'text/plain; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
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

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    let path = decodeURIComponent(url.pathname);

    if (ROUTES[path]) path = '/' + ROUTES[path];

    // normalise and confine to ROOT
    const rel = normalize(path).replace(/^(\.\.[/\\])+/, '').replace(/^[/\\]+/, '');
    const file = join(ROOT, rel);
    if (!file.startsWith(ROOT)) {
      res.writeHead(403).end('Forbidden');
      return;
    }

    const s = await stat(file).catch(() => null);
    if (!s || !s.isFile()) {
      res.writeHead(404, { 'content-type': 'text/html; charset=utf-8' });
      res.end(`<!doctype html><meta charset=utf-8><title>Not found</title>
        <body style="font:16px system-ui;padding:48px;background:#f4efe6;color:#1c211c">
        <h1 style="letter-spacing:.2em">KOLLAM·</h1>
        <p>No file at <code>${rel || '/'}</code>.</p>
        <p>Try <a href="/">the storefront</a> or <a href="/deck">the deck</a>.</p></body>`);
      return;
    }

    const type = TYPES[extname(file)] || 'application/octet-stream';
    const body = await readFile(file);
    res.writeHead(200, {
      'content-type': type,
      'cache-control': 'no-store',
      'x-content-type-options': 'nosniff',
      // explicitly allow embedding in the Arena preview iframe
      'content-security-policy': "frame-ancestors *",
    });
    res.end(body);
  } catch (err) {
    res.writeHead(500, { 'content-type': 'text/plain' }).end(String(err));
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Kollam Pepper Co preview on http://0.0.0.0:${PORT}`);
  console.log(`  /        storefront`);
  console.log(`  /deck    investor deck`);
});
