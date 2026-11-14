# Headless Crafting App demo — produced by CI (no GUI, no DISPLAY)

runner: Linux 7.0.0-1019-azure x86_64 · 4 vCPU · 15983 MB

## PhotoCraft 0.23.1 — provision + real edits
```

$ photocraft-cli --version
$ /tmp/pc/photocraft-0.23.1-linux-x86_64/bin/photocraft-cli --version
photocraft-cli 0.23.1 (45066c482, 2026-11-12)
[exit 0]
$ photocraft-cli run --help
$ /tmp/pc/photocraft-0.23.1-linux-x86_64/bin/photocraft-cli run --help
Open a file (or start a new document), run engine commands in order, save the result

Prints each command's JSON result. Give exactly one of <FILE> or --new, and at least one --cmd or --out. An --out that is the <FILE> is refused, as the result would replace the original; --in-place allows it.

Usage: photocraft-cli run [OPTIONS] <FILE|--new <JSON>> <--cmd <ID>|--out <FILE>>

Arguments:
  [FILE]
          The document to open

Options:
      --new <JSON>
          Start from a new document with these JSON parameters instead of opening a file

      --cmd <ID>
          An engine command to run; repeat for several, run in order

      --params <JSON>
          JSON parameters for the --cmd before it (default {})

      --out <FILE>
          Save the result to this file

      --in-place
          Allow an --out that is the <FILE>, replacing the original

      --approve-high-memory
          Explicitly approve high-memory PSD/PSB imports within the hard memory budget

      --gpu
          Prefer GPU rendering, falling back to CPU when unavailable or unsupported

      --no-gpu
          Use CPU rendering, overriding PHOTOCRAFT_GPU

      --format <EXT>
          Output format, overriding the output's extension (png, jpg, tif, webp, …)

      --quality <1-100>
          JPEG or WebP quality, 1-100. A WebP written with a quality is lossy, without one lossless

      --tiff-layers
          Keep the layers in TIFF output (Photoshop layer data); TIFF output is flat without it

      --tiff-compression <none|lzw|zip>
          Compress TIFF output: none (the default), lzw or zip

      --tiff-transparency <on|off>
          TIFF Save Transparency: on keeps the transparency (ahead of any alpha or spot channels), off composites the image over white. Without it: kept unless the document has alpha or spot channels

      --tiff-pyramid
          Also write a TIFF image pyramid: half-size copies after the full image

      --tga-bits <24|32>
          A TGA's bits per pixel: 32 writes the alpha channel (or else the transparency) as its alpha, 24 none. Without it: 32 with an alpha channel or transparency, else 24

      --dpx-bits <8|10|12|16>
          A DPX's bits per sample. Without it: 8 for an 8-bit document, else 16

      --dds-compression <none|bc1|bc2|bc3>
          A DDS texture's compression: none (uncompressed, the default), bc1 (DXT1: alpha on or off), bc2 (DXT3) or bc3 (DXT5)

      --dds-mipmaps
          Also write a DDS texture's full mip chain

      --jpeg-format <baseline|optimized|progressive>
          A JPEG's scans, as JPEG Options picks them: baseline (the default), optimized (Huffman tables fitted to the image; RGB is written 4:2:0 and keeps the standard tables, so only Gray and CMYK shrink) or progressive

      --pcraft-full-composite
          Request the flattened document at its canvas size in .pcraft output as composite/full.png; it may be omitted. Check the manifest's full_composite member

      --no-maximize-compatibility
          A layered PSD/PSB stores Photoshop's white placeholder instead of the merged image (Maximize Compatibility off): a smaller file and a faster save, but readers that show only the merged image see white. Bitmap, Indexed Color and Duotone documents still write the real image

      --metadata <none|all>
          The document metadata a flat export embeds: all (the default) keeps the document's XMP packet and free-form text where the format holds them, as Save As does; none leaves them out, as Export As's Metadata: None. Nothing else changes: the ICC profile, EXIF and resolution are written as they are without it. PSD, PSB and .pcraft always keep the XMP

  -h, --help
          Print help (see a summary with '-h')
[exit 0]
$ /tmp/pc/photocraft-0.23.1-linux-x86_64/bin/photocraft-cli info /tmp/pc/test.ppm
{
  "activeLayer": 2,
  "channels": {
    "alpha": [],
    "colors": [
      {
        "name": "Red",
        "visible": true
      },
      {
        "name": "Green",
        "visible": true
      },
      {
        "name": "Blue",
        "visible": true
      }
    ],
    "composite": "RGB",
    "compositeVisible": true,
    "layerMaskView": null,
    "quickMask": null,
    "selectedColors": null,
    "target": {
      "kind": "composite"
    }
  },
  "depth": 8,
  "file": "/tmp/pc/test.ppm",
  "hasSelection": false,
  "height": 300,
  "historySource": {
    "label": "Open",
    "state": 0
  },
  "isolatedLayers": [],
  "lastAppliedComp": null,
  "layerComps": [],
  "layerMaskView": null,
  "layers": [
    {
      "blend": "Normal",
      "bounds": [
        0,
        0,
        480,
        300
      ],
      "clipped": false,
      "fill": 1.0,
      "hasMask": false,
      "hasVectorMask": false,
      "hasXmp": false,
      "id": 2,
      "kind": "Pixel",
      "labelColor": "none",
      "linkGroup": null,
      "name": "Background",
      "opacity": 1.0,
      "selected": true,
      "vectorMaskEnabled": null,
      "visible": true
    }
  ],
  "measurement": {
    "count": 0,
    "countGroups": 0,
    "ruler": null,
    "scale": "1 pixels = 1.0000 pixels"
  },
  "mode": "Rgb",
  "name": "test.ppm",
  "notes": [],
  "path": "/tmp/pc/test.ppm",
  "quickMask": false,
  "resolution": 72.0,
  "selectedLayers": [
    2
  ],
  "selectionBounds": null,
  "snapshots": [
    {
      "id": 0,
      "name": "test.ppm"
    }
  ],
  "symmetry": null,
  "timeline": null,
  "variables": null,
  "warnings": [],
  "width": 480
}
[exit 0]
$ /tmp/pc/photocraft-0.23.1-linux-x86_64/bin/photocraft-cli convert /tmp/pc/test.ppm /tmp/pc/step1.png
[exit 0]
$ /tmp/pc/photocraft-0.23.1-linux-x86_64/bin/photocraft-cli convert /tmp/pc/step1.png /tmp/pc/step2.psd
[exit 0]
$ /tmp/pc/photocraft-0.23.1-linux-x86_64/bin/photocraft-cli convert /tmp/pc/step2.psd /home/runner/work/Testrepo/Testrepo/craft-demo/photocraft-psd-roundtrip.png
[exit 0]
$ /tmp/pc/photocraft-0.23.1-linux-x86_64/bin/photocraft-cli convert /tmp/pc/step1.png /home/runner/work/Testrepo/Testrepo/craft-demo/photocraft-out.webp
[exit 0]
$ /tmp/pc/photocraft-0.23.1-linux-x86_64/bin/photocraft-cli convert /tmp/pc/step1.png /home/runner/work/Testrepo/Testrepo/craft-demo/photocraft-out.jpg
warning: lossy compression
[exit 0]
```

## GridCraft 0.19.1 — provision + formula engine + real XLSX/PDF
```
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli version
gridcraft-cli 0.19.1
[exit 0]
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli eval =SUM(1,2,3,4,5)
15
[exit 0]
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli eval =ROUND(2.675,2)
2.68
[exit 0]
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli eval =IFERROR(1/0,"guarded")
guarded
[exit 0]
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli eval =TEXT(1234.5,"#,##0.00")
1,234.50
[exit 0]
$ /tmp/gc/gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli run --in /tmp/gc/book.xlsx --cmd set={"range":"A1:D3","values":[["item","qty","price","total"],["bolt",12,0.5,"=B2*C2"],["nut",7,0.25,"=B3*C3"]]} --cmd set={"range":"A5","values":[["grand total"]]} --cmd set={"range":"B5","values":[["=SUM(D2:D3)"]]} --print A1:D5
gridcraft-cli: /tmp/gc/book.xlsx: No such file or directory (os error 2)
