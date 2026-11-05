#!/usr/bin/env python3
"""Synthesise the game's four sounds. Nothing is downloaded and nothing is sampled.

    python tools/game_audio.py android/game/app/src/main/res/raw

Wind (8 s, seamless), a footstep on gravel-ish lawn, a pickup chime and a soft click. All
mono 16-bit 22 050 Hz, which is plenty for ambience and keeps the whole set under 300 kB.
"""
import os
import struct
import sys
import wave

import numpy as np

SR = 22050


def _noise(n, rng):
    return rng.standard_normal(n)


def lowpass(x, fc, order=2):
    """Zero-phase low pass in the frequency domain: H(f) = 1 / (1 + (f/fc)^(2*order)).

    An FFT filter rather than a recursive one: it is exact, it is fast for these lengths,
    and it cannot drift into the numerical trouble an IIR cascade hits on 8 s of noise.
    """
    n = len(x)
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    h = 1.0 / (1.0 + (f / max(1e-6, fc)) ** (2 * order))
    return np.fft.irfft(spec * h, n=n)


def write_wav(path, x, sr=SR):
    x = np.clip(x, -1.0, 1.0)
    pcm = (x * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def wind(dur=8.0, seed=7):
    """Filtered noise with a slow swell, plus a little 'air' band on top."""
    rng = np.random.default_rng(seed)
    n = int(SR * dur)
    base = lowpass(_noise(n, rng), 190.0, 2)          # the body of the gust
    mid = lowpass(_noise(n, rng), 900.0, 2)           # leaves moving, not a jet engine
    # slow amplitude modulation, and make it loop by cross-fading the ends
    t = np.arange(n) / SR
    swell = 0.55 + 0.30 * np.sin(2 * np.pi * t / dur * 2.0) + 0.15 * np.sin(2 * np.pi * t / dur * 5.0)
    x = (base * 1.0 + mid * 0.22) * swell
    x /= max(1e-9, np.abs(x).max())
    # crossfade the tail into the head so the loop is seamless
    fade = int(SR * 0.75)
    head = x[:fade].copy()
    tail = x[-fade:].copy()
    w = np.linspace(0, 1, fade)
    x[:fade] = head * w + tail * (1 - w)
    x = x[:-fade]
    return x * 0.55


def step(seed=3):
    """A foot on lawn: a short noise burst with a low thump under it."""
    rng = np.random.default_rng(seed)
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    burst = lowpass(_noise(n, rng) * np.exp(-t * 42.0), 1200.0, 2)
    thump = np.sin(2 * np.pi * 68.0 * t) * np.exp(-t * 26.0) * 0.6
    crunch = lowpass(_noise(n, rng) * np.exp(-t * 70.0), 2600.0, 1) * 0.30
    x = burst * 0.55 + thump + crunch
    x /= max(1e-9, np.abs(x).max())
    return x * 0.75


def chime(seed=11):
    """Two rising partials, like a wind chime being struck once."""
    n = int(SR * 0.9)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f, a, d in ((880.0, 0.50, 3.4), (1320.0, 0.30, 4.6), (1760.0, 0.16, 6.0)):
        x += a * np.sin(2 * np.pi * f * t) * np.exp(-t * d)
    x *= np.minimum(1.0, t * 220.0)      # tiny attack so it does not click
    x /= max(1e-9, np.abs(x).max())
    return x * 0.6


def main(argv):
    out = argv[1] if len(argv) > 1 else "android/game/app/src/main/res/raw"
    os.makedirs(out, exist_ok=True)
    items = {"wind": wind(), "step": step(), "chime": chime()}
    for name, x in items.items():
        p = os.path.join(out, name + ".wav")
        write_wav(p, x)
        print(f"{p}: {len(x) / SR:.2f} s, {os.path.getsize(p) / 1024:.0f} kB")
    # a second, quieter variant so repeated footsteps do not sound like a machine gun
    write_wav(os.path.join(out, "step.wav"), items["step"])
    print("done")


if __name__ == "__main__":
    main(sys.argv)
