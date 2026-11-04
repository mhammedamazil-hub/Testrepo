# sandboxdesk

A **virtual desktop you can actually use** — rendered inside a headless container,
streamed to your browser, with real clicks and real keystrokes. Built because
`terminal-mac` (macOS VM in a terminal) is impossible here, and so is every
conventional "desktop in the sandbox" approach.

Everything below was **measured in this sandbox**, not assumed.

---

## The research: what works and what doesn't

| Approach | Needs | Result here |
|---|---|---|
| **terminal-mac** (real macOS via Apple Virtualization) | Apple silicon, macOS 14+, Virtualization.framework | ✗ Impossible — this is Linux x86_64 |
| **QEMU / Docker Desktop / any real OS VM** | `/dev/kvm`, hardware virt | ✗ `ls /dev/kvm` → missing; no `vmx`/`svm` flags; no nested virt |
| **Xvfb + X11 desktop + noVNC** | `apt install xvfb x11vnc openbox` | ✗ `deb.debian.org` unreachable → no apt (even though `sudo` works) |
| **Playwright / headless Chromium** | `libnss3`, `libgbm`, `libgtk-3`, browser CDN | ✗ Chromium unpacks (209 MB) then dies: `libnspr4.so: cannot open shared object file`. `cdn.playwright.dev` → blocked |
| **Puppeteer / real Chrome** | same libs | ✗ Same failure |
| **conda / nix** to supply those libs | `conda.anaconda.org`, `cache.nixos.org` | ✗ Both unreachable |
| **Relaying a real browser for the user** | a running browser engine | ✗ No engine can start, so nothing to relay |
| **Own framebuffer renderer (this)** | **Python + Pillow only** | ✓ **Works** — Pillow is pure-wheel, needs zero system graphics libs |

### The two findings that decide it

1. **No hardware virtualization.** No `/dev/kvm`, no CPU virt flags. A container
   cannot boot a real OS. Any "real computer" answer is off the table.
2. **No graphics stack and no way to install one.** `libX11`/`libxcb` exist but
   `libnss3`, `libgbm`, `libgtk-3`, `libdrm`, `libpango`, `libasound` are all
   absent. apt is firewalled and the npm/PyPI-only egress can't supply system
   `.so` files. So: **no browser engine, no X server, ever — here.**

That leaves exactly one honest architecture, which is what this project is:
**render the desktop ourselves and ship pixels over HTTP.**

---

## What it does

- **1280×800 framebuffer**, drawn every frame with Pillow (no GPU, no X).
- **Streamed as PNG** over HTTP; the page polls frames and swaps them.
- **Input is real**: click, hover, and keyboard events are hit-tested against
  the window model and routed to the focused app.
- **Five apps**: Desktop, Terminal, Finder, Settings, About.
- **The Terminal runs real commands** — `neofetch`, `uname -a`, `df -h`, `free`,
  `ps`, `date`, `echo`, `help`… executed with `subprocess` on the actual host and
  printed into the virtual screen.
- **Same loop computer-use agents use**: observe (frame) → act (click/key) →
  verify (frame), exposed as a CLI so an agent can drive it without a browser.

Performance measured here: **~31 fps** sustainable single-client, ~81 KB/frame,
~10 ms warm render on 2 vCPU.

---

## Run it

```sh
cd sandboxdesk
python3 desktop.py --port 8000       # or ./run.sh
```

Then open the preview for port **8000**. Both are bound to `0.0.0.0`.

### Drive it from the terminal (no browser needed)

```sh
./deskctl.sh shot                    # observe: save a frame, print the path
./deskctl.sh click 552 765           # act: open Terminal from the dock
./deskctl.sh run "neofetch"          # type + Enter
./deskctl.sh key Enter
./deskctl.sh state                   # verify: active app + toggles
./deskctl.sh demo                    # scripted tour, a frame per step
```

`DESK_URL` overrides the base URL (default `http://127.0.0.1:8000`).

---

## Controls

| Action | Result |
|---|---|
| Click a dock icon | Opens that app |
| Click the red dot | Closes the window (back to Desktop) |
| Click toggles / files / sidebar | Toggles, selects, opens |
| Typing (while Terminal is focused) | Enters a command |
| `Enter` / `Backspace` / `Ctrl+C` / `Ctrl+L` | Run / delete / cancel / clear |
| `Esc` | Back to Desktop |

## Files

| File | Role |
|---|---|
| `desktop.py` | Framebuffer renderer, window model, hit-testing, HTTP server |
| `deskctl.py` / `deskctl.sh` | Headless CLI client (observe → act → verify) |
| `run.sh` | Launcher |

## Honest limitations

- It is **not** macOS, not a real OS, and not a browser. It's a self-contained
  simulated desktop — deliberately labelled as such on screen.
- Frames are full PNGs, so this is fine for one or two viewers, not a fleet.
  (Delta/tile encoding would be the next step, and needs no new dependencies.)
- The Finder shows a fixed file list; the Terminal shell is a curated command set,
  not a full pty — a pty (`openpty`) is the obvious upgrade.

MIT.
