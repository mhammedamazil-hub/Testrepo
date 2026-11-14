# KILN — studio assets

Everything in this folder is generated from a script in `scripts/`. There is no stock
imagery, no hand-drawn mark and no mock-up: the plates are Cycles renders driven by `bpy`, the
type is set in the three licensed-for-web faces below, and the PDFs and deck are encoded from
the same geometry.

**KILN** — *Rooms, not pages.* An interactive architecture studio.

Ink `#0B0C0E` · paper `#F2EDE4` · ember `#D8542A` · ember-lit `#EE7541` · kiln `#8A8578` · smoke `#55544F`
Instrument Serif (display) · Inter Tight (text) · JetBrains Mono (labels).

## The mark

A section through a kiln wall: a 1000-unit block with a 300-unit opening cut through it, radius
equal to half the opening, springing 120 units above centre, legs running past the foot. It is
the same arch the studio renders and the same arch the studio sells, which is why the identity
does not need a second idea.

`brand/logo/kiln-construction.svg` is the sheet: grid, clear space, colour rules, minimum size
and a 128/64/32/16 scale test. The mark is never outlined, glowed or bevelled.

## Tree

```
brand/logo/          mark (ink/paper/ember), wordmark, lockups, construction sheet
brand/exports/       PNG exports, favicons, app icon
brand/renders/       Cycles plates: hero, key art, square, detail, three case studies
ads/posters/         manifesto + hiring posters (1200x1600)
ads/set/             social set 1:1, 4:5, 16:9
ads/video/           identity sting: mp4, webm, gif, poster
ads/avatars/         profile avatars + cover banner
portfolio/           KILN-portfolio.pdf (9 pp, A4 landscape)
deck/                KILN-pitch-deck.pdf (12 slides, 16:9)
docs/                KILN-one-pager.pdf · KILN-brand-guidelines.pdf, offers, pricing model, launch plan
copy/                brand book + launch copy
site/                static site: index + showroom, self-contained, no CDN
site/shots/          real-browser screenshots, captured in CI
fonts/               TTFs for the PDF and print generators
scripts/             every generator (see scripts/README.md)
```

## The site

`site/` is fully static and offline-safe: three.js is vendored, fonts are local woff2, and the
only external reference anywhere is a `mailto:`.

- `index.html` — hero, facts bar, three case plates, the identity film, five-step method,
  three tiers, contact.
- `showroom.html` — live scene: orbit / pinch / dolly, four finishes, draw-call and frame-rate
  readout. The geometry mirrors the Cycles house set, so the claim on the homepage can be
  checked by the visitor.
- `motion.js` — headline line reveals, scroll reveals with a 4-second failsafe, hero parallax,
  nav condense, film playback. One easing curve (`cubic-bezier(.16,1,.3,1)`), 3 KB, and inert
  under `prefers-reduced-motion`.

Serve locally: `python3 -m http.server 4173 --bind 0.0.0.0` from `site/`.

## Verification

No browser can be downloaded in the agent sandbox, so `.github/workflows/site-shots.yml` serves
`studio/site`, screenshots it with Playwright at 1440 and 390 wide plus the showroom, walks the
page so scroll reveals fire, logs layout overflow and the live three.js stats, and commits the
PNGs to `site/shots/`. Re-run after any `site/` change: `gh workflow run site-shots.yml`.

## Facts used consistently everywhere

`studio@kiln.studio` · +44 20 7946 0812 · kiln.studio
Spar $4,800 / 2 weeks · Kiln $12,500 / 3–5 weeks · Firing $3,900 per month
< 2.0 MB first load · 60 fps on a mid-range phone · ≤ 8 draw calls · Lighthouse 95+ gated in CI
