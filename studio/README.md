# LUMENFORGE — studio assets

Everything for the LUMENFORGE brand, launch campaign, pitch deck, portfolio and website, generated from source scripts in this folder. Nothing here is stock or hand-drawn in a GUI: the 3D art is ray-cast frame-by-frame by `scripts/renderer.js`, the type is set in SVG, and the deliverables are encoded in Node.

**Brand:** LUMENFORGE — *websites you can walk through.*
Ink `#06070B` · panel `#0C0F17` · bone `#EDE7DA` · forge `#FF6B2C` · arc `#22E8C8` · violet `#7C5CFF` · muted `#8A93A6`
Type: Space Grotesk (display), Inter (body), JetBrains Mono (labels).

## Tree

```
brand/logo/          mark, mono mark, icon, wordmark, lockups (SVG)
brand/exports/       PNG exports + favicons
ads/keyart/          hero key art 1600x2000
ads/set/             social ad set 1:1, 9:16, 16:9
ads/posters/         manifesto, case-study, hiring posters (1200x1600)
ads/video/           motion ad masters: webm, mp4, gif, poster
ads/avatars/         profile avatars + cover banner
portfolio/           three case-study plates 1800x1200
portfolio/plates/    caption-free 3D plates used by the deck + PDF
portfolio/LUMENFORGE-portfolio.pdf   8-page A4 landscape portfolio
deck/                LUMENFORGE-pitch-deck.pptx (11 slides, 16:9)
site/                static site: index + showroom (three.js), self-contained
site/shots/          real-browser screenshots, captured in CI (Playwright)
docs/                offers, pricing model, one-pager, 90-day launch plan
copy/                brand book + launch copy (ads, email, social, social kit)
fonts/               subset TTFs for the PDF (converted from the site woff2)
scripts/             all generators
```

## Scripts

Node 22, dependencies from npm (installed to a scratch `node_modules`, referenced via `NODE_PATH`):

```
NODE_PATH=/tmp/build/node_modules node scripts/brand.js       # logo, marks, favicons
NODE_PATH=/tmp/build/node_modules node scripts/ads.js         # key art, ad set, posters, case plates
NODE_PATH=/tmp/build/node_modules node scripts/plates.js      # caption-free plates for deck/PDF
NODE_PATH=/tmp/build/node_modules node scripts/creative.js all # poster + looping GIF + WebM ad
python3 scripts/encode-mp4.py                                 # H.264 1080 delivery cut
NODE_PATH=/tmp/build/node_modules node scripts/deck.js        # pitch deck .pptx
NODE_PATH=/tmp/build/node_modules node scripts/portfolio.js   # 8-page portfolio PDF
```

Deps: `sharp`, `gifenc`, `webm-writer`, `pptxgenjs`, `pdf-lib` + `@pdf-lib/fontkit`; `av` (PyAV) for the MP4 remux.

Notes worth keeping:

- `scripts/renderer.js` is a small CPU rasteriser (boxes, tori, spheres, points, grid, fog, rim light, vignette) writing raw RGB. `render(w, h, ss)` supersamples 2×.
- The motion ad is 120 frames at 20 fps; captions are SVG composites with a bottom scrim, plus a hold-and-fade end lockup.
- The PDF sets its own type (Space Grotesk / Inter / JetBrains Mono embedded and subset with fontkit), so PDF art uses the clean plates, never the captioned ad art.
- `webm-writer` is browser-only; `scripts/creative.js` shims `window.atob` and feeds it a fake canvas that returns a WebP data URL from sharp.

## The site

`site/` is fully static and offline-safe — three.js 0.160 is vendored, fonts are local woff2, no CDN calls.

- `index.html` — hero (live WebGL forge), three case studies with WebP `<picture>`, "the spot" video section, five-step process, three tiers, mailto contact form.
- `showroom.html` — live product showroom: orbit / pinch / wheel camera, four finish swatches, FPS + draw-call + triangle readout.
- Serve locally: `python3 -m http.server 4173 --bind 0.0.0.0` from `site/`.

## Verification

No browser can be downloaded in the agent sandbox, so `.github/workflows/site-shots.yml` serves
`studio/site`, screenshots it with Playwright at 1440 and 390 wide plus the showroom, logs the live
three.js render stats (frames / draw calls / triangles) and commits the PNGs to `site/shots/`.
Re-run it after any `site/` change: `gh workflow run site-shots.yml`.

## Contacts / facts used consistently everywhere

`forge@lumenforge.studio` · lumenforge.studio · Spark $4,800 · Forge $12,500 · Foundry $3,900/mo · < 2.0 MB first load · 60 fps · Lighthouse 95+ · ≤ 8 draw calls.
