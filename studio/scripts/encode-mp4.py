#!/usr/bin/env python3
"""Encode the LUMENFORGE ad masters.

The motion ads are rendered frame-by-frame in Node (scripts/creative.js), which can only
emit GIF and VP8/WebM on this machine (no WebCodecs, no ffmpeg). This script remuxes the
VP8 master into delivery formats with PyAV:

    ads/video/lumenforge-ad-1080.mp4    H.264, 1080x1080, 20 fps  (paid social / Meta / IG feed)
    ads/video/lumenforge-ad-720.webm    VP8,   720x720,  20 fps  (web embed, kept as rendered)
    ads/video/lumenforge-loop-720.gif   looping 5 s GIF         (email / Slack / deck)
    ads/video/lumenforge-video-poster.png  1:1 still frame, used as <video poster>

Usage:  python3 scripts/encode-mp4.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VID = os.path.join(ROOT, 'ads', 'video')
SRC = os.path.join(VID, 'lumenforge-ad-720.webm')
TMP = os.path.join('/tmp', 'lumenforge-ad-1080.tmp.mp4')
DST = os.path.join(VID, 'lumenforge-ad-1080.mp4')


def main():
    try:
        import av
    except ImportError:
        sys.exit('pip install av  # PyAV is only needed for the mp4 delivery cut')

    if not os.path.exists(SRC):
        sys.exit(f'missing {SRC} — run: NODE_PATH=... node scripts/creative.js video')

    src = av.open(SRC)
    out = av.open(TMP, 'w')
    st = out.add_stream('libx264', rate=20)
    st.width, st.height, st.pix_fmt = 1080, 1080, 'yuv420p'
    st.bit_rate = 4_000_000
    st.options = {'crf': '20', 'preset': 'medium'}

    n = 0
    for frame in src.decode(video=0):
        frame = frame.reformat(width=1080, height=1080, format='yuv420p')
        for pkt in st.encode(frame):
            out.mux(pkt)
        n += 1
    for pkt in st.encode():
        out.mux(pkt)
    out.close()
    src.close()

    os.replace(TMP, DST)
    print(f'{os.path.relpath(DST, ROOT)}  {n} frames  {os.path.getsize(DST) / 1024:.0f} KB')


if __name__ == '__main__':
    main()
