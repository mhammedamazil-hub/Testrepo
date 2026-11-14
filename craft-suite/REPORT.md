# Headless Crafting App suite — real files, no GUI, no DISPLAY
runner: Linux 7.0.0-1019-azure x86_64 · 4 vCPU
asset: soundcraft-0.20.1-linux-x86_64.tar.gz

$ /tmp/sc/soundcraft-0.20.1-linux-x86_64/bin/soundcraft-cli --version
soundcraft-cli 0.20.1 (linux x86_64)
[exit 0]

$ /tmp/sc/soundcraft-0.20.1-linux-x86_64/bin/soundcraft-cli info /tmp/sc/tone.wav
{
  "bwf": null,
  "channels": 1,
  "format": "Wav",
  "frames": 88200,
  "sample_format": "Int16",
  "sample_rate": 44100,
  "seconds": 2.0
}
[exit 0]

$ /tmp/sc/soundcraft-0.20.1-linux-x86_64/bin/soundcraft-cli convert /tmp/sc/tone.wav /home/runner/work/Testrepo/Testrepo/craft-suite/soundcraft-tone.flac
wrote /home/runner/work/Testrepo/Testrepo/craft-suite/soundcraft-tone.flac (1 ch, 44100 Hz, 2.00 s)
[exit 0]

$ /tmp/sc/soundcraft-0.20.1-linux-x86_64/bin/soundcraft-cli convert /tmp/sc/tone.wav /home/runner/work/Testrepo/Testrepo/craft-suite/soundcraft-tone-48k.wav
wrote /home/runner/work/Testrepo/Testrepo/craft-suite/soundcraft-tone-48k.wav (1 ch, 44100 Hz, 2.00 s)
[exit 0]

$ /tmp/sc/soundcraft-0.20.1-linux-x86_64/bin/soundcraft-cli info /home/runner/work/Testrepo/Testrepo/craft-suite/soundcraft-tone.flac
{
  "bwf": null,
  "channels": 1,
  "format": "Flac",
  "frames": 88200,
  "sample_format": "Int24",
  "sample_rate": 44100,
  "seconds": 2.0
}
[exit 0]
asset: figcraft-0.18.1-linux-x86_64.tar.gz
asset: figcraft-server-0.18.1-linux-x86_64.tar.gz

$ /tmp/fg/figcraft-0.18.1-linux-x86_64/bin/figcraft-cli --version
figcraft-cli 0.18.1
[exit 0]

$ /tmp/fg/figcraft-0.18.1-linux-x86_64/bin/figcraft-cli info /tmp/fg/card.svg
/tmp/fg/card.svg — card (5 nodes, 0 styles, 0 variables, 0 images)
page 1 "Page 1": 4 nodes, 1 top-level
  2 FRAME "card" 480.0×300.0
[exit 0]

$ /tmp/fg/figcraft-0.18.1-linux-x86_64/bin/figcraft-cli convert /tmp/fg/card.svg /home/runner/work/Testrepo/Testrepo/craft-suite/figcraft-card.png
/home/runner/work/Testrepo/Testrepo/craft-suite/figcraft-card.png
[exit 0]

$ /tmp/fg/figcraft-0.18.1-linux-x86_64/bin/figcraft-cli convert /tmp/fg/card.svg /home/runner/work/Testrepo/Testrepo/craft-suite/figcraft-card.pdf
/home/runner/work/Testrepo/Testrepo/craft-suite/figcraft-card.pdf
[exit 0]
asset: pdfcraft-0.21.1-linux-x86_64.tar.gz
asset: pdfcraft-cli-0.21.1-linux-x86_64.tar.gz
/tmp/pd/pdfcraft-0.21.1-linux-x86_64/bin/pdfcraft
/tmp/pd/pdfcraft-0.21.1-linux-x86_64/bin/pdfcraft-cli
/tmp/pd/pdfcraft-cli-0.21.1-linux-x86_64/pdfcraft-cli
pdfcraft binary: /tmp/pd/pdfcraft-0.21.1-linux-x86_64/bin/pdfcraft

$ /tmp/pd/pdfcraft-0.21.1-linux-x86_64/bin/pdfcraft --version
pdfcraft 0.21.1
[exit 0]

$ /tmp/pd/pdfcraft-0.21.1-linux-x86_64/bin/pdfcraft info /home/runner/work/Testrepo/Testrepo/craft-suite/figcraft-card.pdf --json
2026-11-14T07:17:55.280Z INFO  [main] pdfcraft: PdfCraft 0.21.1, log file /home/runner/.local/share/pdfcraft/logs/pdfcraft.log
Error: WinitEventLoop(Os(OsError { line: 777, file: "/home/runner/.cargo/git/checkouts/winit-0b02aa607dc0343f/a517b38/src/platform_impl/linux/mod.rs", error: Misc("neither WAYLAND_DISPLAY nor WAYLAND_SOCKET nor DISPLAY is set.") }))
