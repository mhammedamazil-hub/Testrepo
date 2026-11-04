#!/usr/bin/env python3
"""
deskctl — drive the virtual desktop from the terminal (no browser).

This is the same observe -> act -> verify loop that computer-use agents use:
  observe : screenshot  (fetch a frame, write a PNG, optionally OCR-free summary)
  act     : click / move / type / key
  verify  : screenshot again, or `state`

Examples:
  ./deskctl.sh shot                 # save frame as PNG, print path
  ./deskctl.sh click 552 765        # open Terminal from the dock
  ./deskctl.sh type "neofetch"      # type into the focused app
  ./deskctl.sh key Enter
  ./deskctl.sh run "neofetch"       # type + Enter in one go
  ./deskctl.sh state
  ./deskctl.sh demo                 # scripted tour, saves a frame per step
"""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("DESK_URL", "http://127.0.0.1:8000")
OUT = os.environ.get("DESK_OUT", "/tmp")


def _post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode()


def shot(name="frame"):
    with urllib.request.urlopen(BASE + "/img", timeout=15) as r:
        data = r.read()
    path = os.path.join(OUT, f"{name}.png")
    with open(path, "wb") as f:
        f.write(data)
    print(path)
    return path


def state():
    with urllib.request.urlopen(BASE + "/state", timeout=10) as r:
        s = json.loads(r.read())
    msg = (f"active={s['active']}  clicks={s['clicks']}")
    toggles = ", ".join(f"{k}={'on' if v else 'off'}" for k, v in s["toggles"].items())
    print(msg + ("\n" + toggles if toggles else ""))


def click(x, y):
    _post("/click", {"x": int(x), "y": int(y)})
    print(f"clicked {x},{y}")


def move(x, y):
    _post("/hover", {"x": int(x), "y": int(y)})
    print(f"moved {x},{y}")


def type_text(t):
    _post("/text", {"t": t})
    print(f"typed {len(t)} chars")


def key(k):
    _post("/key", {"k": k})
    print(f"key {k}")


def run(cmd):
    type_text(cmd)
    key("Enter")


def demo():
    """A scripted tour: proves observe/act/verify without a browser."""
    steps = [
        ("open Terminal", lambda: click(552, 765)),
        ("neofetch", lambda: run("neofetch")),
        ("df", lambda: run("df -h /")),
        ("open Finder", lambda: click(636, 765)),
        ("open Settings", lambda: click(720, 765)),
        ("open About", lambda: click(804, 765)),
    ]
    for i, (label, fn) in enumerate(steps):
        fn()
        p = shot(f"demo_{i}_{label.split()[0].lower()}")
        print(f"  step {i}: {label} -> {p}")
    state()


HELP = __doc__

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(HELP)
        sys.exit(0)
    cmd, rest = args[0], args[1:]
    try:
        if cmd == "shot":
            shot(rest[0] if rest else "frame")
        elif cmd == "state":
            state()
        elif cmd == "click":
            click(rest[0], rest[1])
        elif cmd == "move":
            move(rest[0], rest[1])
        elif cmd == "type":
            type_text(" ".join(rest))
        elif cmd == "key":
            key(" ".join(rest))
        elif cmd == "run":
            run(" ".join(rest))
        elif cmd == "demo":
            demo()
        else:
            print(f"unknown command: {cmd}\n")
            print(HELP)
            sys.exit(1)
    except urllib.error.URLError as e:
        print(f"cannot reach {BASE}: {e.reason}", file=sys.stderr)
        print("start the desktop with: python3 desktop.py --port 8000", file=sys.stderr)
        sys.exit(2)
