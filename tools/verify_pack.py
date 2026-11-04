#!/usr/bin/env python3
"""Sanity-check a packed .vpk so CI fails loudly instead of shipping a broken APK.

    python tools/verify_pack.py /tmp/pack.json --tris 500000 --max-mb 60
"""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stats")
    ap.add_argument("--tris", type=int, default=500000)
    ap.add_argument("--draws", type=int, default=50)
    ap.add_argument("--max-mb", type=float, default=60.0)
    ns = ap.parse_args()
    d = json.load(open(ns.stats))
    print(json.dumps(d, indent=1))
    bad = []
    if d["tris"] < ns.tris:
        bad.append("tris %d < %d" % (d["tris"], ns.tris))
    if d["draws"] < ns.draws:
        bad.append("draws %d < %d" % (d["draws"], ns.draws))
    if d["out_mb"] > ns.max_mb:
        bad.append("size %.1f MB > %.1f MB" % (d["out_mb"], ns.max_mb))
    if d["textures"] < 1:
        bad.append("no textures")
    if bad:
        print("FAIL: " + "; ".join(bad), file=sys.stderr)
        return 1
    print("PASS: %d tris, %d draws, %.2f MB" % (d["tris"], d["draws"], d["out_mb"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
