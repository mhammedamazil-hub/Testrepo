/**
 * Export the local ECC memory vault to a tracked file.
 * The vault at .ecc/memory/project/ gitignores itself, so this is the durable copy.
 */
import { execFileSync } from 'node:child_process';
import { writeFileSync, readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const ids = process.argv.slice(2);

if (!ids.length) {
  console.error('usage: node scripts/memory-export.mjs <memory-id> [<memory-id> ...]');
  console.error('find ids with: npx ecc memory search ""');
  process.exit(1);
}

const memos = ids.map(id => {
  const raw = execFileSync('npx', ['ecc', 'memory', 'read', id, '--json'], { cwd: ROOT, encoding: 'utf8' });
  return JSON.parse(raw).memory;
});

const out = [
  '# ECC memory vault — exported copy\n',
  'This is a tracked export of the memos written through `npx ecc memory save`.\n',
  "ECC's vault at `.ecc/memory/project/` gitignores itself (`*`), so the source of record is\n",
  'local and machine-specific. This file is the durable copy that travels with the repo.\n',
  'Regenerate with `npm run memory:export` if the vault changes.\n',
  '\n---\n',
];

for (const m of memos.sort((a, b) => a.kind.localeCompare(b.kind))) {
  out.push(`\n## ${m.title}\n`);
  out.push(`\`${m.id}\` · kind **${m.kind}** · scope ${m.scope} · trust ${m.trust} · tags ${m.tags.join(', ')} · written ${m.createdAt}\n`);
  out.push('\n```text\n' + m.body.replace(/\s+$/, '') + '\n```\n');
}

const dest = join(ROOT, 'docs', 'ECC-MEMORY.md');
writeFileSync(dest, out.join(''), 'utf8');
const before = existsSync(dest) ? readFileSync(dest, 'utf8').length : 0;
console.log(`wrote docs/ECC-MEMORY.md (${memos.length} memos, ${before} bytes)`);
