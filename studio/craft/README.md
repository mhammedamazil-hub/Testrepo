# craft/ — the real Craft toolchain, run in CI

The agent sandbox has no egress to `release-assets.githubusercontent.com`, so
`pi-craft` cannot provision FigCraft, DeckCraft or EffectCraft there. GitHub Actions
runners can. `.github/workflows/craft.yml` provisions all three, runs the scripts in
this folder, asserts the outputs with `pi-craft verify`, and commits them back.

Nothing here is a stub. If a binary fails to provision the job fails.

## What the job builds

| App | Script | Artefact |
|---|---|---|
| FigCraft | `figcraft/site-desktop.jsonl`, `figcraft/site-mobile.jsonl` | `craft/out/figcraft-*.png` — 2880×1800 and 780×1688 frames, 2× |
| DeckCraft | `deckcraft/build.mjs` | `craft/out/kiln-deckcraft.pptx` + `.pdf` (DeckCraft's own composition) |
| DeckWriter | `console/DeckWriter.java` | `craft/out/kiln-deck.pptx` + `.pdf` — **the deck that gets sent** |
| EffectCraft | `effectcraft/kiln-sting.sh` | `craft/out/kiln-sting.mp4`, `kiln-sting-alpha.mov` (ProRes 4444, rgba), poster |

Verified in `verify.sh`: 12 PDF pages with the right copy, 1080² · 6 s mp4, and a
ProRes master that actually reports an alpha channel (`--alpha` reads the pixel
format, so a yuv file cannot pass by accident). A check whose probe tool is missing
(exit 3) counts as a skip, never a pass.

## Why DeckWriter exists

DeckCraft 0.21.1 composes slides, shapes, text boxes and pictures, and exports them.
It has **no command for setting a run's font, size or colour**: `describe
insert.textBox` lists `rect` and `text` only, and the formatting commands it does
expose are transparency, highlight, outline and anchor. So every slide it produced
came out in the theme's default face on the theme's accent colour.

`deckcraft/build.mjs` therefore emits two things from the same coordinates:

1. the `--cmd` sequence DeckCraft runs, and
2. `craft/out/kiln-deck.script.txt`, a line-per-element layout script

`console/DeckWriter.java` (JDK only — the ubuntu runner ships one) turns that script
into a real `.pptx` with per-run type, colour and tracking, and pictures at exact
placements. DeckCraft then reads that file back to render the slides and export the
PDF, so the images on the site are of the deck that ships.

The split is uncomfortable and worth naming: the tool that lays out the deck is not
the tool that sets its type. The alternative was shipping a deck in the wrong face.

## Hard-won details

- **`sz` is hundredths of a point.** `sz="62000"` is a 620 pt headline, not 62.
- **A zip entry with no bytes is a crossed placeholder.** Media has to be written,
  not just declared.
- **`wrap='none'`** on every text box means body copy runs off the slide as one line.
  `DeckWriter` wraps by default and takes an `N` flag to opt out for labels.
- **DeckCraft's presets are ids, not labels.** `rect`, not `Rectangle`. The build
  reads the enum from `describe shape.insert`.
- **`design.background` is refused on an empty deck** ("no slides"), and does not
  paint every slide unless you pass `all: true`.
- **`slide.new` does not advance the current slide**, so the build places each one by
  index instead of trusting order.
- **EffectCraft rejects unknown parameters before it runs anything.** `layer.newText`
  takes `fill`, not `color`; `layer.newShape` takes `kind`, not `type`.
- **A property path is not guessable.** A shape's live width is
  `contents/group/contents/rect/size`; `props --flat` is the only reliable source.
  The build dumps it to `craft/out/kiln-sting-props.txt`.
- **Actions logs and artefact blobs are both unreachable from the sandbox.** Every
  step tees to `craft/out/*.log` or `craft/logs/*.log` and those get committed, which
  is how each of the bugs above was actually found.
- **`bash -e` kills a step at the first non-zero exit**, so a failed build's log never
  got copied anywhere. Build steps now disable errexit and `exit 0` on purpose; the
  verification gate is what fails the job, not the build.

## Fonts

The runner has none of the studio's faces. FigCraft says so in its log ("missing
font Instrument Serif: 3 text layers"); DeckCraft and EffectCraft fall back silently.
The **shipped** deck is the PDF in `deck/`, set in Instrument Serif / Inter Tight /
JetBrains Mono; the `.pptx` here is the editable working copy and names Georgia,
Arial and Consolas honestly rather than pretending otherwise.

## Running it

Push anything under `studio/craft/**`, or dispatch `craft-assets` by hand. The job
takes about two minutes and commits its own outputs, so `git log` is the audit trail.
