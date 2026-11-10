#!/usr/bin/env node
import { createApp } from './lib/app.mjs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const PORT = Number(process.env.PORT || 4173);
const QUEUE = process.env.KOLLAM_QUEUE || join(ROOT, 'data', 'lot-queue.json');

const app = createApp({ queuePath: QUEUE });

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Kollam Pepper Co on http://0.0.0.0:${PORT}`);
  console.log('  /        storefront');
  console.log('  /desk    live lot intake (queue: ' + QUEUE + ')');
  console.log('  /deck    investor deck');
});
