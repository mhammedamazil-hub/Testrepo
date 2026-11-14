# PdfCraft 0.21.1 headless: info, combine, extract, render, text
```
$ /tmp/pd/pdfcraft-cli-0.21.1-linux-x86_64/pdfcraft-cli info /home/runner/work/Testrepo/Testrepo/craft-demo/gridcraft-ledger.pdf
{
  "acroform_fields": 0,
  "annotations": 0,
  "attachments": 0,
  "author": null,
  "bookmarks": 0,
  "creator": "GridCraft",
  "custom_properties": 0,
  "encrypted": false,
  "fields": 0,
  "file": "/home/runner/work/Testrepo/Testrepo/craft-demo/gridcraft-ledger.pdf",
  "file_size": 2005,
  "first_page_pt": [
    612.0,
    792.0
  ],
  "javascript": false,
  "layers": 0,
  "links": 0,
  "output_intents": [],
  "page_labels": [
    "1"
  ],
  "pages": 1,
  "pdf_pages": 1,
  "pdf_version": "1.7",
  "pdfa": null,
  "pdfua": null,
  "producer": "GridCraft PDF",
  "repairs": [],
  "tagged": false,
  "title": "ledger.xlsx",
  "transitions": 0,
  "warnings": [],
  "xfa": null,
  "xfa_layout": null
}
[exit 0]
$ /tmp/pd/pdfcraft-cli-0.21.1-linux-x86_64/pdfcraft-cli info /home/runner/work/Testrepo/Testrepo/craft-suite/figcraft-card.pdf
{
  "acroform_fields": 0,
  "annotations": 0,
  "attachments": 0,
  "author": null,
  "bookmarks": 0,
  "creator": "FigCraft",
  "custom_properties": 0,
  "encrypted": false,
  "fields": 0,
  "file": "/home/runner/work/Testrepo/Testrepo/craft-suite/figcraft-card.pdf",
  "file_size": 7535,
  "first_page_pt": [
    480.0,
    300.0
  ],
  "javascript": false,
  "layers": 0,
  "links": 0,
  "output_intents": [],
  "page_labels": [
    "1"
  ],
  "pages": 1,
  "pdf_pages": 1,
  "pdf_version": "1.7",
  "pdfa": null,
  "pdfua": null,
  "producer": "FigCraft",
  "repairs": [],
  "tagged": false,
  "title": "card",
  "transitions": 0,
  "warnings": [],
  "xfa": null,
  "xfa_layout": null
}
[exit 0]
$ /tmp/pd/pdfcraft-cli-0.21.1-linux-x86_64/pdfcraft-cli combine /home/runner/work/Testrepo/Testrepo/craft-demo/gridcraft-ledger.pdf /home/runner/work/Testrepo/Testrepo/craft-suite/figcraft-card.pdf --out /home/runner/work/Testrepo/Testrepo/craft-suite/pdfcraft-combined.pdf
[exit 0]
$ /tmp/pd/pdfcraft-cli-0.21.1-linux-x86_64/pdfcraft-cli info /home/runner/work/Testrepo/Testrepo/craft-suite/pdfcraft-combined.pdf
{
  "acroform_fields": 0,
  "annotations": 0,
  "attachments": 0,
  "author": null,
  "bookmarks": 2,
  "creator": null,
  "custom_properties": 0,
  "encrypted": false,
  "fields": 0,
  "file": "/home/runner/work/Testrepo/Testrepo/craft-suite/pdfcraft-combined.pdf",
  "file_size": 7577,
  "first_page_pt": [
    612.0,
    792.0
  ],
  "javascript": false,
  "layers": 0,
  "links": 0,
  "output_intents": [],
  "page_labels": [
    "1",
    "2"
  ],
  "pages": 2,
  "pdf_pages": 2,
  "pdf_version": "1.7",
  "pdfa": null,
  "pdfua": null,
  "producer": null,
  "repairs": [],
  "tagged": false,
  "title": null,
  "transitions": 0,
  "warnings": [],
  "xfa": null,
  "xfa_layout": null
}
[exit 0]
$ /tmp/pd/pdfcraft-cli-0.21.1-linux-x86_64/pdfcraft-cli extract /home/runner/work/Testrepo/Testrepo/craft-suite/pdfcraft-combined.pdf --pages 2 --out /home/runner/work/Testrepo/Testrepo/craft-suite/pdfcraft-page2.pdf
[exit 0]
$ /tmp/pd/pdfcraft-cli-0.21.1-linux-x86_64/pdfcraft-cli render /home/runner/work/Testrepo/Testrepo/craft-suite/pdfcraft-page2.pdf --page 1 --dpi 96 --out /home/runner/work/Testrepo/Testrepo/craft-suite/pdfcraft-page2.png
rendered page 1 at 96 dpi: 640×400 px in 1 ms
[exit 0]
$ /tmp/pd/pdfcraft-cli-0.21.1-linux-x86_64/pdfcraft-cli text /home/runner/work/Testrepo/Testrepo/craft-suite/pdfcraft-page2.pdf
FIGCRAFT
[exit 0]
$ /tmp/pd/pdfcraft-cli-0.21.1-linux-x86_64/pdfcraft-cli audit /home/runner/work/Testrepo/Testrepo/craft-suite/pdfcraft-combined.pdf
{"count":0,"file":"/home/runner/work/Testrepo/Testrepo/craft-suite/pdfcraft-combined.pdf","findings":[]}
[exit 0]
```
total 348
-rw-r--r-- 1 runner runner   3752 Nov 14 07:24 REPORT-pdfcraft.md
-rw-r--r-- 1 runner runner   3086 Nov 14 07:24 REPORT.md
-rw-r--r-- 1 runner runner   7535 Nov 14 07:24 figcraft-card.pdf
-rw-r--r-- 1 runner runner  14285 Nov 14 07:24 figcraft-card.png
-rw-r--r-- 1 runner runner   7577 Nov 14 07:24 pdfcraft-combined.pdf
-rw-r--r-- 1 runner runner   6129 Nov 14 07:24 pdfcraft-page2.pdf
-rw-r--r-- 1 runner runner  16348 Nov 14 07:24 pdfcraft-page2.png
-rw-r--r-- 1 runner runner 264704 Nov 14 07:24 soundcraft-tone-48k.wav
-rw-r--r-- 1 runner runner  24145 Nov 14 07:24 soundcraft-tone.flac
