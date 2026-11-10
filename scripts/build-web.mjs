import {build} from 'esbuild';
import {readFile, writeFile} from 'node:fs/promises';
// Commit these small built assets so cargo/NDK builds stay Rust-only and offline.
await build({entryPoints:['ui/astryx.jsx'],bundle:true,minify:true,format:'iife',target:['chrome109'],outfile:'web/astryx.js',loader:{'.css':'empty'},define:{'process.env.NODE_ENV':'"production"'},legalComments:'eof',charset:'utf8'});
await build({entryPoints:['ui/astryx.css'],bundle:true,minify:true,target:['chrome109'],outfile:'web/astryx.css',legalComments:'eof',charset:'utf8'});
const css=await readFile('web/astryx.css','utf8');
if(/@import\b|url\(\s*['"]?https?:/i.test(css))throw new Error('Offline UI must not import remote fonts or styles');
const notices=['@astryxdesign/core','@astryxdesign/theme-matcha','react','react-dom','@stylexjs/stylex'];
let text='Sourcebook bundles the following open-source UI packages locally. No CDN assets.\n\n';
for(const name of notices){const meta=JSON.parse(await readFile(`node_modules/${name}/package.json`,'utf8'));let license;for(const candidate of ['LICENSE','LICENSE.md'])try{license=await readFile(`node_modules/${name}/${candidate}`,'utf8');break;}catch{}text+=`--- ${name} ${meta.version} (${meta.license}) ---\n${license||'See package license in its published npm distribution.'}\n\n`;}
await writeFile('web/UI-LICENSES.txt',text);
console.log('Built local Astryx JS/CSS and license notices.');
