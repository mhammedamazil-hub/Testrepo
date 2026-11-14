# KILN — build scripts

Every asset in this repo is generated. Nothing is hand-drawn, and nothing is a mock-up.

| script | produces | how |
|---|---|---|
| `wordmark.js` | mark, wordmark, lockups, favicons, construction sheet | resvg + true vector geometry |
| `kiln_render.py` | hero plate, key art, square, detail | Blender / Cycles via `bpy` |
| `kiln_work.py` | three case-study plates (1400 × 1750) | same, importing the helpers above |
| `kiln_posters.py` | manifesto + hiring posters, 1:1 / 4:5 / 16:9 social set | Cycles plates composited with PIL + the real type faces |
| `kiln_motion.py` | the 6 s identity sting (mp4, webm, gif, poster) | frame-by-frame from the same plate and geometry |
| `portfolio.js` | `portfolio/KILN-portfolio.pdf` (9 pp, A4 landscape) | pdf-lib + embedded fonts |
| `onepager.js` | `docs/KILN-one-pager.pdf` | same |
| `deck.js` | `deck/KILN-pitch-deck.pdf` + an editable `.pptx` (12 slides) | pdf-lib, then pptxgenjs |
| `lib.js` | shared palette and font paths | — |

## Running

```bash
# Blender work needs the bpy stub libs on the library path
LD_LIBRARY_PATH=/tmp/xstub python3 -u scripts/kiln_work.py atelier meridian kinetic

# Node work needs sharp, pdf-lib, resvg, pptxgenjs
NODE_PATH=/tmp/build/node_modules node scripts/portfolio.js
```

`bpy` renders at ~4.5 min per 2400 px plate on two cores. A full re-render of the set is
about twenty minutes; the scripts are deterministic apart from Cycles sampling.

## Retired

`brand.js`, `ads.js`, `creative.js`, `plates.js`, `renderer.js` and `site/app.js` built the
previous identity: a JS raytracer faking 3D, gradients, and a letterform badge. They were
deleted rather than left to rot — anything they produced has been superseded by the Cycles
set, and keeping them would mean the repo contains two contradictory stories about how the
work is made.
