# Headless Crafting App demo — produced by CI (no GUI, no DISPLAY)
runner: Linux 7.0.0-1019-azure x86_64 · 4 vCPU · 15983 MB
fetched gridcraft -> /tmp/gc

## GridCraft 0.19.1 — formula engine, CSV→XLSX→PDF
```
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli version
gridcraft-cli 0.19.1
[exit 0]
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli eval =SUM(1,2,3,4,5)
15
[exit 0]
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli eval =TEXT(1234.5,"#,##0.00")
1,234.50
[exit 0]
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli convert /tmp/gc/ledger.csv /tmp/gc/ledger.xlsx
wrote /tmp/gc/ledger.xlsx (4185 bytes)
[exit 0]
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli info /tmp/gc/ledger.xlsx --json
{
  "activeCell": "A1",
  "activeSheet": 0,
  "calcMode": "Automatic",
  "dirty": false,
  "mode": "Ready",
  "names": [],
  "path": "/tmp/gc/ledger.xlsx",
  "redo": [],
  "selection": "A1",
  "sheets": [
    {
      "autofilter": null,
      "cells": 14,
      "charts": [],
      "comments": 0,
      "conditionalFormats": 0,
      "freeze": null,
      "images": 0,
      "merges": [],
      "name": "ledger",
      "protected": false,
      "shapes": 0,
      "tabColor": null,
      "tables": [],
      "usedRange": "A1:D6",
      "validations": 0,
      "visibility": "Visible",
      "zoom": 100
    }
  ],
  "theme": "Craft",
  "title": "ledger.xlsx",
  "trust": "fromFile",
  "undo": []
}
[exit 0]
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli cat /tmp/gc/ledger.xlsx --csv
item,qty,price,total
bolt,12,0.5,=B2*C2
nut,7,0.25,=B3*C3
,,,
,,,
grand total,,,=SUM(D2:D3)
[exit 0]
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli check /tmp/gc/ledger.xlsx
== /tmp/gc/ledger.xlsx
  formulas 0: 0 checked, 0 matched, 0 mismatched, 0 no oracle, 0 volatile
  round trip: all equal

file                 formulas   checked   matched  mismatch  no-oracle  volatile  round trip
/tmp/gc/ledger.xlsx         0         0         0         0          0         0  ok

files: 1 (1 opened, 0 failed to open)
formula cells: 0 (0 checked: 0 matched, 0 mismatched; 0 no oracle; 0 volatile)
round trip: 0 of 1 files differ
[exit 0]
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli convert /tmp/gc/ledger.xlsx /home/runner/work/Testrepo/Testrepo/craft-demo/gridcraft-ledger.pdf
wrote /home/runner/work/Testrepo/Testrepo/craft-demo/gridcraft-ledger.pdf (2005 bytes, 1 pages)
[exit 0]
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli cat /home/runner/work/Testrepo/Testrepo/craft-demo/gridcraft-ledger.xlsx --range A1:D5 --formulas
item  qty  price  total
bolt  12   0.5    =B2*C2
nut   7    0.25   =B3*C3


[exit 0]
```
fetched vectorcraft -> /tmp/vc

## VectorCraft 0.24.1 — SVG in, PNG/PDF/SVG out
```
$ /tmp/vc/vectorcraft-0.24.1-linux-x86_64/bin/vectorcraft-cli --version
vectorcraft-cli 0.24.1
[exit 0]
$ /tmp/vc/vectorcraft-0.24.1-linux-x86_64/bin/vectorcraft-cli --help
vectorcraft-cli — VectorCraft automation

USAGE:
  vectorcraft-cli --safe-mode SUBCOMMAND ...
      Run any subcommand without plug-ins: none loads or runs, and plug-in commands report that
      Safe Mode is on. Plug-ins stay installed. `--safe-mode mcp` serves a headless session and
      does not take --connect.

  vectorcraft-cli mcp [--connect ADDR | --headless] [--automation-read-root DIR]... [--automation-write-root DIR]... [--allow-plugin-grants]
      Run the MCP server on stdio. Default: connect to a running app at 127.0.0.1:7979
      (vectorcraft --control 7979), falling back to a headless in-process session.
      --automation-read-root / --automation-write-root confine the files the agent's commands read
      (open, place, relink, library loads…) and write (save, export, package, library saves…) to
      DIR, links followed; each may be given more than once, a path inside any of its folders being
      allowed, and a kind left out grants none of its access. They imply --headless: a running app
      enforces its own (vectorcraft --control PORT --automation-read-root DIR …).
      --allow-plugin-grants lets plugin.install's grant and allowHeavy take effect in this session,
      so whoever sends the commands can give a plug-in the permissions it lists, and a heavy budget,
      with nobody approving them. Without it they are refused, and a plug-in that lists permissions
      installs only when its hash is already recorded in grants.json, by a person's approval in the
      desktop app or by a grant accepted under this flag. A grant accepted under this flag stays
      recorded and counts as approved in later sessions. It implies --headless. It can't be used
      with --automation-read-root or --automation-write-root: a server confined to folders has no
      plug-in store, so it reads no grants.json, and a plug-in that lists permissions or asks for a
      heavy budget does not install there. With VECTORCRAFT_NO_PREFS set there is no store either,
      and a grant accepted under this flag lasts for that session only.

  vectorcraft-cli run [--in FILE] [--cmd ID [--params JSON] | --commands FILE|-]... [--export FILE]... [--scale N] [--ppi N] [--allow-plugin-grants]
      Headless batch: open FILE (any readable format) or start a new document, run commands in
      order, export each FILE in the format its extension picks (see Writable formats; a .ait FILE
      is a template, written as file.saveAsTemplate writes it). Raster exports use the document's
      raster effects resolution unless --scale (pixels per point) or --ppi (pixels per inch, wins
      over --scale) is given; other formats leave them out. Prints one JSON result per step.
      --commands reads steps from FILE, or from standard input for -, where it stands among the
      --cmd and --export steps: a JSON array of {"command": ID, "params": {...}} (or "id" for
      "command"), or one such object per line (JSON Lines), at most 64 MiB and 100000 steps.
      Errors name the step, counting from 0 as "$N" references do.
      --allow-plugin-grants lets plugin.install's grant and allowHeavy take effect in this run, as
      for mcp.

  vectorcraft-cli commands
      Print the command catalogue as JSON.

  vectorcraft-cli convert IN OUT [--scale N] [--ppi N] [--artboard I | --range R] [--outline-text] [--decimals N] [--replace-lossy] [--editing-data] [--legacy-name-encoding ENC] [--preserve-editing] [--ai-version 7|pdf] [--hidden-objects layer|omit|visible] [--transparent-images flatten|omit]
      Open IN (any readable format) and export OUT in the format its extension picks (see Writable
      formats). Raster resolution: --ppi, else 72 times --scale, else the document's raster effects
      resolution; other formats leave them out. --artboard is 0-based, --range 1-based ("1-3,5"); a PDF gets every artboard
      unless one of them is given, EPS the bounds of the art, the other formats the first artboard.
      A .ait OUT is a template of every artboard, written as file.saveAsTemplate writes it (not with
      --artboard or --range).
      Live effects are kept, and hidden layers and objects (written hidden in SVG and PSD), with
      SVG's data-* attributes; --outline-text writes SVG text as paths, --decimals sets SVG's coordinate
      precision (1–7, default 3). OUT may not be IN when reading
      IN left things out (hidden text, art or layers it could not read; the notes say which) unless
      --replace-lossy is given. --editing-data opens a .ai or an EPS with editing data from its editing copy
      even where that draws differently from its PDF part or page (which can be older), as long as
      it can be read. --legacy-name-encoding reads the names in a .ai's or an EPS's editing data
      that aren't UTF-8 (layers, objects, artboards, colors, gradients, patterns, graphic styles,
      swatches, brushes, symbols, variables and data sets, and data sets' text values) in
      windows-1252 (the default), macintosh, windows-949, shift_jis, gbk or big5. A PDF OUT omits the embedded native document unless --preserve-editing is
      given (the app's Save As PDF still defaults to keeping it). With --preserve-editing, when the
      attachment is written the result's warnings say so (it is left out, with its own warning, for
      --artboard or a --range without every artboard).
      The result has the export's warnings, and importWarnings for what reading IN left out.
      --ai-version 7 writes a .ai as the legacy version 7 (layers, groups and type kept; one file
      per artboard, OUT-<artboard>.ai when there are several; default pdf, PDF-compatible), with
      --hidden-objects (default layer: a hidden layer above each layer's hidden objects; omit;
      visible), --transparent-images (default flatten, with the art under them; omit) and
      --outline-text (type as outlines instead of text).

  vectorcraft-cli info FILE
      Print a JSON summary: the import warnings (what didn't come in as it was, such as an EPS
      read from its preview and why), title, colour mode, units, artboards, object counts by
      kind, fonts.

  vectorcraft-cli bench FILE [--size WxH] [--iters N]
      Render FILE (any readable format) fitted to WxH (default 2880x1800) and print ms per frame
      (warm), multithreaded and single-threaded.

  vectorcraft-cli perf [--paths N] [--deep] [--native-io [--artboards 1..4]]
      Check the performance budgets (render, pan, hit test, save/load, SVG, Pathfinder, handle
      and segment drags) on a synthetic N-path document (default 50000). Exits non-zero if a
      budget is exceeded, unless the report says the machine is busy. --deep also times work with
      no budget yet and prints memory use (the working set on Windows), with the peak so far on
      Windows and Linux.
      --native-io instead measures the application's native save/open commands (one warmup,
      five samples, no disk I/O), including preview, PDF, compression and API base64 costs.
      It reports the default and explicit PDF opt-out, with and without preview/compression;
      --artboards repeats the same artwork
      on 1 to 4 overlapping artboards. This mode allows at most 50000 paths.

Readable formats: .vectorcraft, .drawcraft, .svg, .svgz, .pdf, .ai, .ait, .png, .pns, .jpg, .jpeg, .gif, .webp, .tif, .tiff, .bmp, .dib, .rle, .tga, .vda, .icb, .vst, .pcx, .pxr, .jpf, .jpx, .jp2, .j2k, .j2c, .jpc, .heic, .heif, .psd, .pdd, .psb, .jxl, .vctemplate, .dxf, .emf, .wmf, .eps, .epsf, .ps, .af, .afdesign, .afpub
Writable formats: .vectorcraft, .svg, .svgz, .pdf, .ai, .png, .jpg, .gif, .webp, .tif, .bmp, .vctemplate, .txt, .dxf, .eps, .emf, .wmf, .tga, .psd
[exit 0]
$ /tmp/vc/vectorcraft-0.24.1-linux-x86_64/bin/vectorcraft-cli info /tmp/vc/badge.svg
{
  "artboards": [
    {
      "name": "Artboard 1",
      "rect": [
        0.0,
        0.0,
        800.0,
        480.0
      ]
    }
  ],
  "file": "/tmp/vc/badge.svg",
  "fonts": [
    {
      "family": "DejaVu Sans",
      "missing": false,
      "missingGlyphs": 0,
      "objects": 2,
      "resolved": {
        "family": "DejaVu Sans",
        "style": "Book"
      },
      "runs": 2,
      "status": "substitute",
      "style": "Regular"
    }
  ],
  "info": {
    "artboards": 1,
    "author": "",
    "authorTitle": "",
    "colorMode": "rgb",
    "copyrightNotice": "",
    "copyrightStatus": "unknown",
    "copyrightUrl": "",
    "created": null,
    "description": "",
    "keywords": [],
    "modified": null,
    "objects": 5,
    "rating": 0,
    "title": "badge.svg",
    "units": "Pixels"
  },
  "kinds": {
    "Layer": 1,
    "Path": 2,
    "Type": 2
  },
  "warnings": []
}
[exit 0]
$ /tmp/vc/vectorcraft-0.24.1-linux-x86_64/bin/vectorcraft-cli convert /tmp/vc/badge.svg /home/runner/work/Testrepo/Testrepo/craft-demo/vectorcraft-badge.png
{"bytes":13732,"format":"png","path":"/home/runner/work/Testrepo/Testrepo/craft-demo/vectorcraft-badge.png","warnings":["font styles that aren't available were written in the closest style: DejaVu Sans Regular was drawn in DejaVu Sans Book (pick a style the family has)"]}
[exit 0]
$ /tmp/vc/vectorcraft-0.24.1-linux-x86_64/bin/vectorcraft-cli convert /tmp/vc/badge.svg /home/runner/work/Testrepo/Testrepo/craft-demo/vectorcraft-badge.pdf
{"bytes":10554,"format":"pdf","path":"/home/runner/work/Testrepo/Testrepo/craft-demo/vectorcraft-badge.pdf","warnings":["font styles that aren't available were written in the closest style: DejaVu Sans Regular was drawn in DejaVu Sans Book (pick a style the family has)"]}
[exit 0]
$ /tmp/vc/vectorcraft-0.24.1-linux-x86_64/bin/vectorcraft-cli convert /tmp/vc/badge.svg /tmp/vc/roundtrip.svg
{"bytes":851,"format":"svg","path":"/tmp/vc/roundtrip.svg","warnings":[]}
[exit 0]
```
pdfcraft tag: v0.21.1
tar: ./pdfcraft-cli-0.21.1-linux-x86_64.tar.gz: Not found in archive
tar: Exiting with failure status due to previous errors
