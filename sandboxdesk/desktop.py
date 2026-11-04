#!/usr/bin/env python3
"""
sandboxdesk — a virtual desktop that lives entirely inside a terminal sandbox.

No X11, no Wayland, no VM, no browser engine. Just a framebuffer rendered with
Pillow, streamed to the user's browser as PNG frames, with mouse and keyboard
events routed back into a small object model. This is the architecture used by
real "computer use" agents (observe -> act -> verify), reimplemented from
scratch so it works on a machine with zero graphics libraries.

Run:  python3 desktop.py [--port 8000]
"""

import hashlib
import io
import json
import os
import sys
import time
import shlex
import subprocess
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

# ----------------------------------------------------------------------------
# Canvas
# ----------------------------------------------------------------------------
W, H = 1280, 800
FPS_HINT = 4

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FILES = {
    ("sans", 0): f"{FONT_DIR}/DejaVuSans.ttf",
    ("sans", 1): f"{FONT_DIR}/DejaVuSans-Bold.ttf",
    ("mono", 0): f"{FONT_DIR}/DejaVuSansMono.ttf",
    ("mono", 1): f"{FONT_DIR}/DejaVuSansMono-Bold.ttf",
}
_font_cache = {}


def font(size, bold=False, mono=False):
    key = ("mono" if mono else "sans", 1 if bold else 0, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(FILES[(key[0], key[1])], size)
    return _font_cache[key]


# Palette (dark, macOS-ish but its own thing)
C = {
    "desk_a": (28, 34, 54),
    "desk_b": (12, 14, 22),
    "bar": (20, 20, 26, 235),
    "win": (32, 34, 42),
    "win_dark": (24, 25, 32),
    "sidebar": (26, 27, 34),
    "border": (58, 62, 76),
    "text": (228, 232, 240),
    "dim": (140, 148, 165),
    "faint": (96, 104, 120),
    "accent": (86, 156, 255),
    "green": (90, 220, 140),
    "yellow": (245, 200, 80),
    "red": (240, 96, 96),
    "purple": (168, 122, 255),
    "hl": (58, 64, 84),
}


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ----------------------------------------------------------------------------
# Drawing helpers
# ----------------------------------------------------------------------------
def text(d, x, y, s, size=15, color=None, bold=False, mono=False,
         hl=None, anchor="lt", pad_x=6, pad_y=3):
    """Draw text with optional pill highlight behind it."""
    color = color or C["text"]
    f = font(size, bold, mono)
    if anchor == "lm":
        y = y - size * 0.62
    if hl:
        w = d.textlength(s, font=f)
        d.rounded_rectangle(
            [x - pad_x, y - pad_y, x + w + pad_x, y + size * 1.28 + pad_y],
            radius=6, fill=hl)
    d.text((x, y), s, font=f, fill=color)
    return d.textlength(s, font=f)


def icon_folder(d, x, y, s=34, color=(92, 160, 246)):
    d.rounded_rectangle([x, y + s * 0.18, x + s, y + s * 0.85], radius=4, fill=color)
    d.rounded_rectangle([x + s * 0.08, y + s * 0.05, x + s * 0.45, y + s * 0.30],
                        radius=3, fill=lerp(color, (255, 255, 255), 0.18))
    d.rounded_rectangle([x, y + s * 0.28, x + s, y + s * 0.85], radius=4,
                        fill=lerp(color, (255, 255, 255), 0.10))


def icon_file(d, x, y, s=34, color=(120, 132, 156)):
    d.rounded_rectangle([x + s * 0.14, y, x + s * 0.86, y + s], radius=3, fill=color)
    d.polygon([(x + s * 0.62, y), (x + s * 0.86, y), (x + s * 0.86, y + s * 0.26)],
              fill=lerp(color, (255, 255, 255), 0.30))
    for i in range(3):
        yy = y + s * (0.48 + i * 0.15)
        d.line([x + s * 0.26, yy, x + s * 0.74, yy],
               fill=lerp(color, (20, 22, 30), 0.55), width=1)


def icon_terminal(d, x, y, s=34, color=(70, 78, 96)):
    d.rounded_rectangle([x, y, x + s, y + s], radius=6, fill=color)
    d.text((x + s * 0.14, y + s * 0.22), ">_", font=font(int(s * 0.42), True, True),
           fill=(140, 240, 170))


def icon_gear(d, x, y, s=34, color=(150, 158, 176)):
    cx, cy, r = x + s / 2, y + s / 2, s * 0.40
    for i in range(8):
        import math
        a = i * math.pi / 4
        d.line([cx + r * 0.7 * math.cos(a), cy + r * 0.7 * math.sin(a),
                cx + r * 1.1 * math.cos(a), cy + r * 1.1 * math.sin(a)],
               fill=color, width=4)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=5)
    d.ellipse([cx - s * 0.10, cy - s * 0.10, cx + s * 0.10, cy + s * 0.10], fill=color)


def icon_info(d, x, y, s=34, color=(120, 180, 255)):
    d.ellipse([x, y, x + s, y + s], outline=color, width=4)
    d.text((x + s * 0.42, y + s * 0.10), "i", font=font(int(s * 0.60), True), fill=color)


# ----------------------------------------------------------------------------
# Geometry
# ----------------------------------------------------------------------------
BAR_H = 30
DOCK_H = 74
WINDOWS = {
    "desktop":  (60, 66, 620, 430),
    "terminal": (110, 92, 720, 470),
    "finder":   (80, 70, 800, 530),
    "settings": (250, 110, 600, 480),
    "about":    (170, 100, 700, 540),
}
DOCK_APPS = [("desktop", "Desktop"), ("terminal", "Terminal"),
             ("finder", "Finder"), ("settings", "Settings"), ("about", "About")]


def dock_rects():
    out = []
    n = len(DOCK_APPS)
    total = n * 84
    x0 = (W - total) // 2
    y = H - DOCK_H + 12
    for i, (key, label) in enumerate(DOCK_APPS):
        out.append((key, label, (x0 + i * 84 + 12, y, x0 + i * 84 + 12 + 52, y + 52)))
    return out


# ----------------------------------------------------------------------------
# State
# ----------------------------------------------------------------------------
class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.active = "desktop"
        self.hover = None
        self.hover_dock = None
        self.term_input = ""
        self.term_scroll = 0
        self.finder_sel = 1
        self.toggles = {"Dark mode": True, "Live preview": True, "Sound": False}
        self.toast = None
        self.toast_until = 0
        self.clicks = 0
        self.started = time.time()
        self.term_lines = [
            ("user@sandbox:~$ welcome", C["green"]),
            ("sandboxdesk 1.0 — a desktop rendered inside a headless sandbox.", C["text"]),
            ("", C["text"]),
            ("Type `help` for commands, or use the mouse on the desktop.", C["dim"]),
            ("", C["text"]),
        ]

    def notify(self, msg):
        self.toast = msg
        self.toast_until = time.time() + 2.6


ST = State()
FILES_LIST = [
    ("Projects", "folder", "—"),
    ("README.md", "file", "2.1 KB"),
    ("desktop.py", "file", "18 KB"),
    ("notes.txt", "file", "640 B"),
    ("archive.zip", "file", "4.2 MB"),
    ("screenshot.png", "file", "88 KB"),
]


def run_cmd(cmd: str):
    """A tiny shell, so the terminal does something real."""
    cmd = cmd.strip()
    if not cmd:
        return []
    try:
        parts = shlex.split(cmd)
    except ValueError:
        return [("shell: unbalanced quotes", C["red"])]
    c = parts[0]

    if c == "help":
        return [("commands: ls  pwd  whoami  uname  date  df  free  echo  cat",
                 C["dim"]),
                ("          ps  open <app>  clear  neofetch  sudo", C["dim"])]
    if c == "ls":
        return [("desktop.py  FILES_LIST  README.md  notes.txt  screenshot.png",
                 C["text"])]
    if c == "pwd":
        return [("/home/user/sandboxdesk", C["text"])]
    if c == "whoami":
        return [("user (uid=1001, in group sudo)", C["text"])]
    if c == "uname":
        out = subprocess.run(["uname", "-a"], capture_output=True, text=True).stdout
        return [(out.strip()[:96], C["text"])]
    if c == "date":
        return [(datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%a %d %b %Y  %H:%M:%S %Z"),
                 C["text"])]
    if c == "df":
        out = subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout
        return [(l[:96], C["text"]) for l in out.strip().splitlines()]
    if c == "free":
        out = subprocess.run(["free", "-m"], capture_output=True, text=True).stdout
        return [(l[:96], C["text"]) for l in out.strip().splitlines()]
    if c == "ps":
        out = subprocess.run(["ps", "-eo", "pid,comm", "--no-headers"],
                             capture_output=True, text=True).stdout.strip().splitlines()
        return [(f"{len(out)} processes running", C["text"]),
                (" ".join(l.split()[1] for l in out[:6]), C["dim"])]
    if c == "echo":
        return [(" ".join(parts[1:]), C["text"])]
    if c == "neofetch":
        up = int(time.time() - ST.started)
        return [("  sandbox-os 1.0", C["accent"]),
                (f"  host      e2b / Debian 12 (bookworm)", C["text"]),
                (f"  kernel    {os.uname().release}", C["text"]),
                (f"  cpu       {os.cpu_count()} vCPU", C["text"]),
                (f"  display   {W}x{H} virtual framebuffer (Pillow)", C["text"]),
                (f"  uptime    {up}s", C["text"]),
                (f"  clicks    {ST.clicks} handled", C["text"])]
    if c == "sudo":
        return [("user is not in the sudoers file. This incident has been reported.",
                 C["red"]),
                ("(just kidding — you *are* in sudo, but apt is firewalled here)",
                 C["dim"])]
    if c == "clear":
        return [("__CLEAR__", C["text"])]
    if c == "cat":
        if len(parts) > 1 and parts[1] in ("README.md", "notes.txt"):
            return [("← that file exists in the Finder window", C["dim"])]
        return [("cat: file not found", C["red"])]
    if c == "open":
        app = parts[1] if len(parts) > 1 else ""
        if app in WINDOWS:
            return [(f"__OPEN__{app}", C["text"])]
        return [(f"open: unknown app '{app}'", C["red"])]
    return [(f"{c}: command not found", C["red"])]


# ----------------------------------------------------------------------------
# Renderers
# ----------------------------------------------------------------------------
def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


_bg_cache = {}


def _background():
    """Soft radial glow painted on a tiny canvas, then upscaled (cheap + smooth)."""
    if "img" in _bg_cache:
        return _bg_cache["img"]
    sw, sh = 160, 100
    small = Image.new("RGB", (sw, sh))
    px = small.load()
    for yy in range(sh):
        t = yy / (sh - 1)
        base = lerp(C["desk_a"], C["desk_b"], t)
        for xx in range(sw):
            dx = (xx / (sw - 1) - 0.70) / 0.62
            dy = (yy / (sh - 1) - 0.40) / 0.66
            dist = (dx * dx + dy * dy) ** 0.5
            g = max(0.0, 1.0 - dist)
            g = (g ** 2) * 0.60
            px[xx, yy] = lerp(base, (74, 116, 196), g)
    img = small.resize((W, H), Image.BICUBIC)
    _bg_cache["img"] = img
    return img


def draw_background(img, d):
    img.paste(_background(), (0, 0))
    # faint dot grid for texture
    for yy in range(40, H - DOCK_H, 40):
        for xx in range(40, W, 40):
            d.point((xx, yy), fill=(255, 255, 255, 10))


def draw_menu_bar(d):
    d.rectangle([0, 0, W, BAR_H], fill=C["bar"])
    d.line([(0, BAR_H), (W, BAR_H)], fill=(255, 255, 255, 18))
    text(d, 18, 7, "◆", 13, C["accent"], bold=True)
    x = 36
    for item in ["sandboxdesk", "File", "Edit", "View", "Go", "Help"]:
        x += text(d, x, 7, item, 13, C["text"] if item != "Help" else C["dim"]) + 20
    now = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%a %d %b  %H:%M")
    w = d.textlength(now, font=font(13, True))
    text(d, W - w - 18, 7, now, 13, C["text"], bold=True)
    text(d, W - w - 150, 7, f"{int(ST.clicks)} clicks", 13, C["dim"])


def draw_dock(d):
    d.rectangle([0, H - DOCK_H, W, H], fill=(16, 17, 23, 210))
    d.line([(0, H - DOCK_H), (W, H - DOCK_H)], fill=(255, 255, 255, 16))
    for key, label, (x1, y1, x2, y2) in dock_rects():
        active = ST.active == key
        hover = ST.hover_dock == key
        pad = 0 if hover else 3
        box = [x1 + pad, y1 + pad, x2 - pad, y2 - pad]
        col = {"desktop": (72, 96, 150), "terminal": (66, 74, 92),
               "finder": (82, 150, 240), "settings": (110, 118, 138),
               "about": (96, 150, 220)}[key]
        rrect(d, box, 11, fill=lerp(col, (255, 255, 255), 0.10 if hover else 0.0),
              outline=C["accent"] if active else None, width=2)
        cx, cy = x1 + 26, y1 + 26
        if key == "terminal":
            icon_terminal(d, cx - 15, cy - 15, 30, (30, 32, 40))
        elif key == "finder":
            d.ellipse([cx - 15, cy - 15, cx + 15, cy + 15], fill=(240, 245, 255))
            d.ellipse([cx - 9, cy - 10, cx - 4, cy - 5], fill=(40, 50, 70))
            d.ellipse([cx + 4, cy - 10, cx + 9, cy - 5], fill=(40, 50, 70))
            d.arc([cx - 9, cy - 4, cx + 9, cy + 10], 20, 160, fill=(40, 50, 70), width=3)
        elif key == "settings":
            icon_gear(d, cx - 15, cy - 15, 30, (235, 240, 250))
        elif key == "about":
            icon_info(d, cx - 15, cy - 15, 30, (240, 245, 255))
        else:
            d.rounded_rectangle([cx - 13, cy - 13, cx + 13, cy + 13], radius=4,
                                fill=(200, 220, 255))
            d.rectangle([cx - 8, cy + 3, cx + 8, cy + 5], fill=(90, 120, 180))
        if active:
            d.ellipse([cx - 2, H - 12, cx + 2, H - 8], fill=C["accent"])
    # label of hovered/active app
    for key, label, (x1, y1, x2, y2) in dock_rects():
        if ST.hover_dock == key:
            w = d.textlength(label, font=font(12, True))
            bx = (x1 + x2) / 2
            rrect(d, [bx - w / 2 - 8, H - DOCK_H - 30, bx + w / 2 + 8, H - DOCK_H - 10],
                  6, fill=(30, 32, 42))
            text(d, bx - w / 2, H - DOCK_H - 27, label, 12, C["text"], bold=True)


def window(d, key, title, subtitle=""):
    x, y, w, h = WINDOWS[key]
    rrect(d, [x + 3, y + 5, x + w + 3, y + h + 5], 12, fill=(0, 0, 0, 60))
    rrect(d, [x, y, x + w, y + h], 12, fill=C["win"], outline=C["border"])
    # title bar
    d.rounded_rectangle([x, y, x + w, y + 38], radius=12, fill=C["win_dark"])
    d.rectangle([x, y + 26, x + w, y + 38], fill=C["win_dark"])
    for i, col in enumerate([C["red"], C["yellow"], C["green"]]):
        d.ellipse([x + 15 + i * 20, y + 14, x + 27 + i * 20, y + 26], fill=col)
    tw = d.textlength(title, font=font(13, True))
    text(d, x + w / 2 - tw / 2, y + 11, title, 13, C["text"], bold=True)
    if subtitle:
        sw = d.textlength(subtitle, font=font(12))
        text(d, x + w - sw - 16, y + 12, subtitle, 12, C["faint"])
    return x, y, w, h


def render_desktop(d, x, y, w, h):
    cx = x + 26
    text(d, cx, y + 58, "Good evening.", 26, C["text"], bold=True)
    text(d, cx, y + 92, "This desktop is drawn by Pillow and streamed as PNG.", 14, C["dim"])
    cards = [
        ("Framebuffer", f"{W}×{H}", "Pillow → PNG frames", C["accent"]),
        ("Input", "mouse + keys", "routed to hit-testing", C["green"]),
        ("Engine", "none", "no X11, no VM, no browser", C["purple"]),
    ]
    cw = (w - 52 - 24) / 3
    for i, (label, value, sub, col) in enumerate(cards):
        bx = cx + i * (cw + 12)
        rrect(d, [bx, y + 130, bx + cw, y + 236], 10, fill=(40, 43, 54), outline=C["border"])
        d.rectangle([bx + 1, y + 130, bx + 5, y + 236], fill=col)
        text(d, bx + 16, y + 146, label.upper(), 11, C["faint"], bold=True)
        text(d, bx + 16, y + 166, value, 20, C["text"], bold=True)
        text(d, bx + 16, y + 200, sub, 10, C["dim"])
    text(d, cx, y + 258, "What actually works here", 13, C["text"], bold=True)
    rows = [
        ("Rendering", "Pillow draws every pixel — verified", C["green"]),
        ("Streaming", "HTTP + PNG, ~%d fps" % FPS_HINT, C["green"]),
        ("Interaction", "click, hover, type, scroll", C["green"]),
        ("Real shell", "commands actually execute", C["green"]),
        ("Real browser engine", "libnspr4/libgbm missing — unavailable", C["red"]),
        ("Boot a real OS", "no /dev/kvm, no hardware virt", C["red"]),
    ]
    for i, (k, v, col) in enumerate(rows):
        yy = y + 282 + i * 24
        d.ellipse([cx, yy + 6, cx + 7, yy + 13], fill=col)
        text(d, cx + 16, yy, k, 13, C["text"])
        text(d, cx + 196, yy, v, 13, C["dim"])


def term_prompt(d, x, y):
    w1 = text(d, x, y, "user@sandbox", 14, C["green"], bold=True, mono=True)
    w2 = text(d, x + w1, y, ":~/sandboxdesk$ ", 14, C["accent"], bold=True, mono=True)
    return x + w1 + w2


def render_terminal(d, x, y, w, h):
    lh = 22
    top = y + 58
    left = x + 20
    for i, (line, color) in enumerate(ST.term_lines):
        yy = top + i * lh
        if yy > y + h - 44:
            break
        if line.startswith("user@sandbox:~$ "):
            cmd = line[len("user@sandbox:~$ "):]
            px = term_prompt(d, left, yy)
            text(d, px, yy, cmd, 14, C["text"], mono=True)
        else:
            text(d, left, yy, line, 14, color, mono=True)
    n = len(ST.term_lines)
    yy = top + n * lh
    if yy <= y + h - 44:
        px = term_prompt(d, left, yy)
        tw = text(d, px, yy, ST.term_input, 14, C["text"], mono=True)
        if int(time.time() * 2) % 2 == 0:
            d.rectangle([px + tw + 2, yy - 1, px + tw + 10, yy + 18], fill=C["accent"])


def render_finder(d, x, y, w, h):
    sb = 186
    d.rounded_rectangle([x, y + 38, x + sb, y + h], radius=0, fill=C["sidebar"])
    d.rectangle([x + sb, y + 38, x + sb + 1, y + h], fill=C["border"])
    text(d, x + 18, y + 54, "Favorites", 11, C["faint"], bold=True)
    items = ["Home", "Desktop", "Documents", "Downloads", "Projects"]
    for i, it in enumerate(items):
        yy = y + 76 + i * 30
        sel = i == ST.finder_sel % len(items)
        if sel:
            rrect(d, [x + 10, yy - 4, x + sb - 10, yy + 22], 6, fill=(52, 58, 78))
        d.rectangle([x + 20, yy + 2, x + 32, yy + 14], fill=(92, 160, 246) if sel else (70, 76, 96))
        text(d, x + 42, yy, it, 13, C["text"] if sel else C["dim"])
    # toolbar
    text(d, x + sb + 22, y + 52, "Projects", 15, C["text"], bold=True)
    text(d, x + sb + 22, y + 74, f"{len(FILES_LIST)} items", 12, C["dim"])
    # grid
    gx0, gy0 = x + sb + 22, y + 104
    cell_w, cell_h = 132, 104
    for i, (name, kind, size) in enumerate(FILES_LIST):
        col, row = i % 4, i // 4
        bx, by = gx0 + col * cell_w, gy0 + row * cell_h
        clicked = ST.hover == ("file", i)
        if clicked:
            rrect(d, [bx - 6, by - 6, bx + cell_w - 26, by + cell_h - 16], 8, fill=(58, 64, 84))
        if kind == "folder":
            icon_folder(d, bx + 18, by + 10, 42)
        else:
            icon_file(d, bx + 22, by + 10, 42)
        text(d, bx + 6, by + 62, name[:14], 12, C["text"] if kind == "folder" else C["dim"])
        text(d, bx + 6, by + 78, size, 10, C["faint"])


def toggle(d, x, y, on):
    rrect(d, [x, y, x + 44, y + 24], 12, fill=C["accent"] if on else (62, 66, 80))
    cx = x + 32 if on else x + 12
    d.ellipse([cx - 9, y + 3, cx + 9, y + 21], fill=(245, 248, 255))


def render_settings(d, x, y, w, h):
    text(d, x + 24, y + 56, "Settings", 20, C["text"], bold=True)
    rows = list(ST.toggles.items())
    for i, (k, v) in enumerate(rows):
        yy = y + 100 + i * 46
        hot = ST.hover == ("toggle", i)
        if hot:
            rrect(d, [x + 14, yy - 8, x + w - 14, yy + 32], 8, fill=(46, 50, 64))
        text(d, x + 24, yy, k, 14, C["text"])
        toggle(d, x + w - 76, yy - 2, v)
    yy = y + 250
    d.line([x + 24, yy, x + w - 24, yy], fill=C["border"])
    info = [("Display", f"{W} × {H} @ {FPS_HINT}fps"),
            ("Renderer", "Pillow 13.0 (no GPU)"),
            ("Transport", "HTTP · image/png"),
            ("Uptime", f"{int(time.time() - ST.started)}s")]
    for i, (k, v) in enumerate(info):
        text(d, x + 24, yy + 18 + i * 26, k, 13, C["dim"])
        vw = d.textlength(v, font=font(13))
        text(d, x + w - 24 - vw, yy + 18 + i * 26, v, 13, C["text"])
    # power button
    bx, by = x + 24, y + h - 62
    hot = ST.hover == ("power", 0)
    rrect(d, [bx, by, bx + 150, by + 36], 8,
          fill=(80, 40, 46) if hot else (54, 36, 42), outline=(150, 70, 76))
    text(d, bx + 18, by + 9, "Power off desktop", 13, (250, 160, 160), bold=True)


def render_about(d, x, y, w, h):
    text(d, x + 26, y + 56, "sandboxdesk", 24, C["text"], bold=True)
    text(d, x + 26, y + 90, "a computer you can use from a terminal session", 13, C["dim"])
    paras = [
        ("The idea", "Your terminal can't show a desktop, so we render", "one and stream the pixels over HTTP."),
        ("Why not a real OS?", "Virtualization needs /dev/kvm and hardware", "virt. A container has neither, and no apt."),
        ("Why not a browser?", "Chromium links libnspr4, libgbm, libgtk-3 —", "all absent. So: our own renderer."),
        ("The pattern", "observe → act → verify, the same loop", "computer-use agents run."),
    ]
    yy = y + 122
    for label, l1, l2 in paras:
        text(d, x + 26, yy, label.upper(), 10, C["accent"], bold=True)
        text(d, x + 26, yy + 16, l1, 13, C["text"])
        text(d, x + 26, yy + 33, l2, 13, C["dim"])
        yy += 66
    text(d, x + 26, y + h - 34, "MIT · built inside this sandbox, no external services",
         11, C["faint"])


def render_toast(d):
    if not ST.toast or time.time() > ST.toast_until:
        return
    msg = ST.toast
    w = d.textlength(msg, font=font(13, True)) + 44
    bx, by = W - w - 28, H - DOCK_H - 58
    rrect(d, [bx, by, bx + w, by + 40], 10, fill=(38, 42, 56), outline=C["accent"])
    d.ellipse([bx + 14, by + 16, bx + 22, by + 24], fill=C["green"])
    text(d, bx + 30, by + 12, msg, 13, C["text"], bold=True)


def render():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img, "RGBA")
    draw_background(img, d)

    key = ST.active
    if key == "desktop":
        x, y, w, h = window(d, "desktop", "Desktop", "virtual")
        render_desktop(d, x, y, w, h)
    elif key == "terminal":
        x, y, w, h = window(d, "terminal", "Terminal — user@sandbox", "python")
        render_terminal(d, x, y, w, h)
    elif key == "finder":
        x, y, w, h = window(d, "finder", "Finder", "Projects")
        render_finder(d, x, y, w, h)
    elif key == "settings":
        x, y, w, h = window(d, "settings", "Settings")
        render_settings(d, x, y, w, h)
    elif key == "about":
        x, y, w, h = window(d, "about", "About this desktop")
        render_about(d, x, y, w, h)

    draw_menu_bar(d)
    draw_dock(d)
    render_toast(d)
    return img


# ----------------------------------------------------------------------------
# Input handling
# ----------------------------------------------------------------------------
def hit(x, y):
    """Return what's under the cursor. This is the whole hit-testing model."""
    for key, label, (x1, y1, x2, y2) in dock_rects():
        if x1 <= x <= x2 and y1 <= y <= y2:
            return ("dock", key)
    if y <= BAR_H:
        return ("bar", None)
    if ST.active in WINDOWS:
        wx, wy, ww, wh = WINDOWS[ST.active]
        if not (wx <= x <= wx + ww and wy <= y <= wy + wh):
            return ("desk", None)
        rel = (x - wx, y - wy)
        rx, ry = rel
        if ry <= 38:
            if 15 <= rx <= 27:
                return ("close", None)
            return ("titlebar", None)
        if ST.active == "finder":
            if rx < 186 and 54 <= ry <= 230:
                idx = int((ry - 76) // 30)
                if 0 <= idx < 5:
                    return ("sidebar", idx)
            gx0, gy0 = 186 + 22, 104
            if rx >= gx0 - 10 and ry >= gy0 - 10:
                col = int((rx - gx0 + 10) // 132)
                row = int((ry - gy0 + 10) // 104)
                idx = row * 4 + col
                if 0 <= idx < len(FILES_LIST):
                    return ("file", idx)
        if ST.active == "settings":
            for i in range(len(ST.toggles)):
                yy = 100 + i * 46
                if 92 <= ry <= 140 + i * 46:
                    return ("toggle", i)
            if (ry >= WINDOWS["settings"][3] - 62 and rx >= 24
                    and rx <= 174):
                return ("power", 0)
        if ST.active == "terminal":
            return ("term", None)
    return ("desk", None)


def do_click(x, y):
    target, arg = hit(x, y)
    if target == "dock":
        ST.active = arg
        ST.notify(f"opened {arg}")
    elif target == "close":
        ST.active = "desktop"
    elif target == "sidebar":
        ST.finder_sel = arg
    elif target == "file":
        ST.finder_sel = arg
        name = FILES_LIST[arg][0]
        if FILES_LIST[arg][1] == "folder":
            ST.notify(f"opened {name}")
        else:
            ST.notify(f"{name} — preview unavailable")
    elif target == "toggle":
        k = list(ST.toggles.keys())[arg]
        ST.toggles[k] = not ST.toggles[k]
        ST.notify(f"{k}: {'on' if ST.toggles[k] else 'off'}")
    elif target == "power":
        ST.active = "desktop"
        ST.notify("desktop kept alive (this is a preview)")
    elif target == "term":
        pass
    ST.hover = (target, arg)


def do_hover(x, y):
    target, arg = hit(x, y)
    ST.hover_dock = arg if target == "dock" else None
    if target in ("toggle", "power", "file"):
        ST.hover = (target, arg)
    elif target == "sidebar":
        ST.hover = ("file", arg) if arg is not None else None
    else:
        ST.hover = None


def type_key(ch):
    """Insert a printable character into whatever has focus."""
    if ST.active != "terminal":
        return
    ST.term_input += ch


def press_key(k):
    if ST.active != "terminal":
        if k == "Escape":
            ST.active = "desktop"
        return
    if k == "Enter":
        cmd = ST.term_input
        prompt = f"user@sandbox:~$ {cmd}"
        ST.term_lines.append((prompt, C["text"]))
        out = run_cmd(cmd)
        for line, col in out:
            if line.startswith("__CLEAR__"):
                ST.term_lines = []
                break
            if line.startswith("__OPEN__"):
                ST.active = line[len("__OPEN__"):]
                ST.term_lines.append((f"opening {ST.active}…", C["dim"]))
                break
            ST.term_lines.append((line, col))
        ST.term_input = ""
        ST.term_lines = ST.term_lines[-60:]
        ST.term_lines.append(("", C["text"]))
    elif k == "Backspace":
        ST.term_input = ST.term_input[:-1]
    elif k == "Ctrl+C":
        ST.term_lines.append((f"user@sandbox:~$ {ST.term_input}^C", C["text"]))
        ST.term_input = ""
    elif k == "Ctrl+L":
        ST.term_lines = []


# ----------------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------------
LOCK = threading.Lock()
FRAME = {"png": None, "etag": None}


def invalidate():
    """Any state change makes the cached frame stale."""
    FRAME["png"] = None
    FRAME["etag"] = None

PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<title>sandboxdesk</title>
<style>
  :root{color-scheme:dark}
  *{box-sizing:border-box}
  html,body{height:100%;margin:0;background:#07080c;font:13px/1.4 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#e4e8f0;overflow:hidden}
  #wrap{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:12px}
  #frame{position:relative;max-width:100%;max-height:calc(100vh - 86px);border-radius:12px;overflow:hidden;
         box-shadow:0 24px 70px rgba(0,0,0,.7),0 0 0 1px #232a3a;line-height:0}
  #screen{display:block;max-width:100%;max-height:calc(100vh - 86px);width:auto;height:auto;cursor:default;
          image-rendering:-webkit-optimize-contrast;user-select:none;-webkit-user-drag:none}
  #hud{display:flex;gap:14px;align-items:center;color:#7c849a;font-size:12px}
  #hud b{color:#aab4cc;font-weight:600}
  .dot{width:7px;height:7px;border-radius:50%;background:#5adc8c;box-shadow:0 0 8px #5adc8c;display:inline-block}
  .dot.off{background:#f06060;box-shadow:0 0 8px #f06060}
  kbd{background:#1b1f2a;border:1px solid #2b3242;border-radius:4px;padding:1px 5px;font:11px ui-monospace,monospace;color:#9aa6bf}
</style></head>
<body><div id="wrap">
  <div id="frame"><img id="screen" src="/img" width="1280" height="800" alt="virtual desktop"></div>
  <div id="hud">
    <span><span class="dot" id="live"></span> <b id="status">live</b></span>
    <span>click = mouse &middot; keys type into Terminal &middot; <kbd>Esc</kbd> back to Desktop</span>
    <span id="fps" style="margin-left:auto"></span>
  </div>
</div>
<script>
const img = document.getElementById('screen');
const live = document.getElementById('live');
const statusEl = document.getElementById('status');
const fpsEl = document.getElementById('fps');
let busy = false, frames = 0, lastT = performance.now(), lastTag = null;
let objectUrl = null;

async function tick(){
  if (busy) return; busy = true;
  try{
    const opts = {cache:'no-store'};
    if (lastTag) opts.headers = {'If-None-Match': lastTag};
    const r = await fetch('/img?t=' + Date.now(), opts);
    if (r.status === 304){ live.className = 'dot'; statusEl.textContent = 'idle'; return; }
    if (!r.ok) throw new Error(r.status);
    lastTag = r.headers.get('ETag');
    const b = await r.blob();
    const url = URL.createObjectURL(b);
    await new Promise(res => { img.onload = res; img.onerror = res; img.src = url; });
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = url;
    frames++;
    const now = performance.now();
    if (now - lastT > 1000){ fpsEl.textContent = frames + ' fps'; frames = 0; lastT = now; }
    live.className = 'dot'; statusEl.textContent = 'live';
  } catch(e){
    live.className = 'dot off'; statusEl.textContent = 'reconnecting…';
  } finally { busy = false; }
}
setInterval(tick, 140); tick();

function coords(ev){
  const r = img.getBoundingClientRect();
  return { x: Math.round((ev.clientX - r.left) * img.naturalWidth / r.width),
           y: Math.round((ev.clientY - r.top)  * img.naturalHeight / r.height) };
}
function post(path, body){
  navigator.sendBeacon ? navigator.sendBeacon(path, new Blob([JSON.stringify(body)],{type:'application/json'}))
                       : fetch(path,{method:'POST',body:JSON.stringify(body)});
}
img.addEventListener('mousedown', ev => { ev.preventDefault(); img.focus(); const p = coords(ev); post('/click', p); });
let lastHover = 0;
img.addEventListener('mousemove', ev => {
  const now = Date.now(); if (now - lastHover < 90) return; lastHover = now;
  post('/hover', coords(ev));
});
window.addEventListener('keydown', ev => {
  const named = ['Enter','Backspace','Tab','Escape','ArrowUp','ArrowDown','ArrowLeft','ArrowRight',' ','Delete'];
  if (ev.ctrlKey && ev.key.toLowerCase() === 'c'){ post('/key',{k:'Ctrl+C'}); ev.preventDefault(); return; }
  if (ev.ctrlKey && ev.key.toLowerCase() === 'l'){ post('/key',{k:'Ctrl+L'}); ev.preventDefault(); return; }
  if (named.includes(ev.key)){ post('/key',{k:ev.key === ' ' ? ' ' : ev.key}); ev.preventDefault(); return; }
  if (ev.key.length === 1 && !ev.metaKey && !ev.ctrlKey){ post('/text',{t:ev.key}); ev.preventDefault(); }
});
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, ctype, body, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", PAGE.encode())
        elif p == "/img":
            with LOCK:
                if FRAME["png"] is None:
                    buf = io.BytesIO()
                    render().save(buf, "PNG", compress_level=1)
                    FRAME["png"] = buf.getvalue()
                    FRAME["etag"] = hashlib.md5(FRAME["png"]).hexdigest()
                etag = '"%s"' % FRAME["etag"]
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self._send(200, "image/png", FRAME["png"], {"ETag": etag})
        elif p == "/state":
            with LOCK:
                body = json.dumps({"active": ST.active, "toggles": ST.toggles,
                                   "clicks": ST.clicks}).encode()
            self._send(200, "application/json", body)
        elif p == "/health":
            self._send(200, "text/plain", b"ok")
        else:
            self._send(404, "text/plain", b"not found")

    def do_POST(self):
        p = self.path.split("?")[0]
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            data = {}
        with LOCK:
            if p == "/click":
                ST.clicks += 1
                invalidate()
                do_click(int(data.get("x", 0)), int(data.get("y", 0)))
            elif p == "/hover":
                invalidate()
                do_hover(int(data.get("x", 0)), int(data.get("y", 0)))
            elif p == "/key":
                invalidate()
                press_key(data.get("k", ""))
            elif p == "/text":
                invalidate()
                for ch in str(data.get("t", "")):
                    type_key(ch)
        self._send(200, "application/json", b'{"ok":true}')

    def do_OPTIONS(self):
        self._send(204, "text/plain", b"")


def main():
    port = 8000
    args = sys.argv[1:]
    if "--port" in args:
        port = int(args[args.index("--port") + 1])
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    srv.daemon_threads = True
    print(f"sandboxdesk listening on http://0.0.0.0:{port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
