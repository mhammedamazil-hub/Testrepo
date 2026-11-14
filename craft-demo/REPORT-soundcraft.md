# SoundCraft 0.20.1 — headless audio pipeline
```
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
$ /tmp/sc/soundcraft-0.20.1-linux-x86_64/bin/soundcraft-cli convert /tmp/sc/tone.wav /tmp/sc/tone.flac
wrote /tmp/sc/tone.flac (1 ch, 44100 Hz, 2.00 s)
[exit 0]
$ /tmp/sc/soundcraft-0.20.1-linux-x86_64/bin/soundcraft-cli convert /tmp/sc/tone.wav /home/runner/work/Testrepo/Testrepo/craft-demo/soundcraft-tone.mp3
error: /home/runner/work/Testrepo/Testrepo/craft-demo/soundcraft-tone.mp3: cannot write `.mp3` files (supported: wav, wave, bwf, aif, aiff, aifc, flac)
