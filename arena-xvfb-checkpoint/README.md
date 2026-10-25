# Arena Xvfb checkpoint — libXfont2 and libX11/libxkbfile validation

Checkpoint date: 2026-10-25

This directory preserves the reproducible scripts, Meson port, test programs,
source pins, generated metadata, and logs for the two tasks performed in
`/tmp/arena-xvfb/`. It was added on this session's dedicated checkpoint branch,
`arena/bac94189-testrepo`; the repository's original top-level `README.md` was
not modified.

No Xvfb/X server, window manager, VNC server, browser, or Blender work was
started in this checkpoint.

## Preserved layout

- `scripts/build-libxfont2.sh` — builds/tests/installs libXfont2.
- `scripts/validate-libx11-libxkbfile.sh` — validates the version-matched
  libX11 solution at pkg-config/Meson and direct ABI levels. It intentionally
  exits with status 3 for the current partial result described below.
- `scripts/env.sh` — the shell environment used for the prefix.
- `meson-ports/libXfont2/meson.build` — the minimal libXfont2 Meson port.
- `tests/` — installed-library and runtime test programs.
- `pins.txt` and `logs/pins.txt` — preserved source-pin log.
- `logs/` — build, test, symbol-audit, and blocker logs.
- `metadata/xfont2.pc` — installed libXfont2 pkg-config output.
- `metadata/libX11-overlay/` — generated `x11.pc`, `XlibConf.h`,
  provenance note, and header hashes for the validation overlay.

The note `(INSPECT ONLY)` beside libXfont in the older preserved pin log was
from the previous checkpoint. In this checkpoint that same commit was built.
The libX11 entry is for header/metadata validation only; libX11 itself was not
compiled.

## Objective 1: libXfont2 — PASS

Source:

- Repository: `https://github.com/X11Libre/mirror.fdo.libXfont.git`
- Ref used: `master`
- Exact commit: `1531de719edf74ad76f21f0afcd94db450c65cce`
- Upstream version: 2.0.9
- Existing checkout: `/tmp/arena-xvfb/src/libXfont`
- Meson port: `/tmp/arena-xvfb/meson-ports/libXfont2/meson.build`
- Install prefix: `/tmp/arena-xvfb/prefix`

Build/test command:

```sh
/tmp/arena-xvfb/scripts/build-libxfont2.sh
```

That script performs:

```sh
meson setup /tmp/arena-xvfb/build/libXfont2 /tmp/arena-xvfb/src/libXfont \
  --prefix=/tmp/arena-xvfb/prefix --libdir=lib --buildtype=release
ninja -C /tmp/arena-xvfb/build/libXfont2
meson test -C /tmp/arena-xvfb/build/libXfont2 --print-errorlogs
ninja -C /tmp/arena-xvfb/build/libXfont2 install
```

Port configuration follows the upstream `configure.ac` and `Makefile.am` for:

- enabled: fontfile, bitmap, PCF, BDF, built-ins, gzip;
- disabled: FreeType, font-server client (`fc`), SNF, bzip2;
- 41 C sources including feature-detected replacements;
- on this glibc, `strlcpy` and `strlcat` were absent, so
  `src/util/strlcpy.c` and `src/util/strlcat.c` were selected;
- hidden visibility, Linux `_XOPEN_SOURCE`, `_GNU_SOURCE`, and
  `-Wl,--no-undefined` (matching upstream `-no-undefined`).

Results:

- Build and install: **PASS**.
- Upstream Meson test suite in the port: **6 passed, 0 failed**:
  - `lsfontdir-built-ins`
  - `test-pcf-repad`
  - `test-pcf-props`
  - `test-pcf-bitmapscale`
  - `test-pcf-encoding`
  - `test-pcf-norepad`
- Separate installed-tree consumer test: **PASS**. It exercised font-name
  records, the pattern cache, and allocation of a font private index against
  the installed header/library.
- Installed library:
  `/tmp/arena-xvfb/prefix/lib/libXfont2.so.2.0.0`
- Installed library SHA-256:
  `2c04daee84154f67f4fdf005bb1f80b87fa3fb679db5cc6606d1379df11f78bd`
- `pkg-config --modversion xfont2`: `2.0.9`

Detailed evidence is in `logs/libXfont2-build.log` and
`logs/libXfont2-consumer-test.log`. Meson's raw `testlog.txt` was not copied
to Git because Meson embeds the process environment in that file; its test
summary is included in the build log.

## Objective 2: libX11 solution for libxkbfile — PARTIAL

### Sources and runtime validated

- libX11 headers/metadata source:
  `https://github.com/X11Libre/mirror.fdo.libX11.git`
- Tag: `libX11-1.8.4`
- Exact commit: `fc5ec8edda1efdf5d66db4e76796e3c407527b3b`
- Runtime library: Debian `libx11-6 2:1.8.4-2+deb12u2`
- Runtime file: `/usr/lib/x86_64-linux-gnu/libX11.so.6.4.0`
- Runtime SHA-256:
  `688d7edc1a02a0e7993722d57a42821b22435e249071554625a5ec4784787d3d`
- libxkbfile source:
  `https://github.com/X11Libre/mirror.fdo.libxkbfile.git`
- libxkbfile exact commit:
  `6289ef997918cafdaae5ddc17a7442e30dede994`
- Isolated validation overlay:
  `/tmp/arena-xvfb/validation/libX11-1.8.4-dev`

The overlay contains the exact public headers listed by upstream
`include/Makefile.am`, `XlibConf.h` generated from the upstream template with
`XTHREADS=1` and `XUSE_MTSAFE_API=1`, and `x11.pc` expanded from upstream
`x11.pc.in`. Its linker names point to the actual installed Debian 1.8.4
runtime. No system directory was modified.

Validation command:

```sh
/tmp/arena-xvfb/scripts/validate-libx11-libxkbfile.sh
# Current expected exit status: 3 (direct ABI passed; Meson blocked)
```

### Checks that passed

- `pkg-config --modversion x11` against the isolated overlay: `1.8.4`.
- Strict header/link probe using upstream 1.8.4 headers: **PASS**.
- Direct compilation of all 13 libxkbfile library sources: **PASS**.
- Direct shared-library link with `-Wl,--no-undefined`: **PASS**.
- The resulting validation library had SONAME `libxkbfile.so.1` and
  `DT_NEEDED libX11.so.6`.
- Symbol audit: **40** undefined libxkbfile symbols are exported by the
  installed libX11, including `XGetAtomName`, `XInternAtom`,
  `XkbAllocKeyboard`, `XkbAllocClientMap`, `XkbGetMap`, and `XkbSetMap`.
  The complete intersection is in
  `logs/libxkbfile-symbols-provided-by-libX11.txt`.
- `ldd -r`: **PASS**, with no undefined-symbol or not-found diagnostics.
- Runtime consumer: **PASS** via both the overlay path and the normal system
  libX11 path. It exercised a libxkbfile atom round trip and libX11's
  `XkbAllocKeyboard`, `XkbAllocClientMap`, and `XkbFreeKeyboard` functions.

The manual libxkbfile validation library was deliberately left only under
`/tmp/arena-xvfb/validation/libxkbfile-manual/`; it was **not** installed into
the main prefix. After this checkpoint, `xkbfile`, `x11`, and `xcb` remain
missing from the main prefix's default pkg-config view.

### Exact blocker

Normal pkg-config/Meson integration is **blocked** because the honest
upstream `x11.pc` contains:

```text
Requires.private: xcb >= 1.11.1
```

The sandbox has Debian `libxcb1 1.15-1` as a runtime library, but no genuine
libxcb development package: no `xcb.pc`, linker name, or xcb headers.
Consequently both of these correctly fail:

```text
pkg-config --cflags --libs x11
Package 'xcb', required by 'x11', not found

meson setup ... /tmp/arena-xvfb/src/libxkbfile
src/meson.build:20:4: ERROR: Dependency lookup for x11 with method
'pkg-config' failed: ... Package 'xcb', required by 'x11', not found
```

See `logs/libX11-pkgconfig-flags.txt`,
`logs/libxkbfile-meson-probe.log`, and
`logs/libx11-libxkbfile-validation.log`.

`PKG_CONFIG_MAXIMUM_TRAVERSE_DEPTH=1` was investigated and rejected: Meson
reported `x11` as found, but the generated build rules contained no include
or library flags from the overlay. That would hide, rather than satisfy, the
dependency and would not be a valid validation.

## Smallest next fix

Provide a genuine libxcb development state before attempting the Meson build
of libxkbfile again. Either:

1. source-build the real `xcb-proto`, `libXdmcp`, and `libxcb` chain into the
   prefix; or
2. construct a complete version-matched libxcb 1.15 development overlay from
   official sources, including all generated protocol headers, the upstream
   `xcb.pc` template expanded truthfully, and the actual installed runtime.

Do not solve this by deleting `Requires.private: xcb` from `x11.pc`, creating
an empty `xcb.pc`, or truncating pkg-config traversal. Once a real `xcb`
module is present, rerun `scripts/validate-libx11-libxkbfile.sh`; its success
path will configure, build, and install libxkbfile through Meson, followed by
the same direct ABI checks.

## Restoring these checkpoint files into `/tmp`

If `/tmp/arena-xvfb` resets but the existing source checkouts and prefix are
recreated from `pins.txt` and the earlier logs, restore this checkpoint's
working files with:

```sh
mkdir -p /tmp/arena-xvfb/scripts /tmp/arena-xvfb/meson-ports/libXfont2 \
  /tmp/arena-xvfb/tests /tmp/arena-xvfb/logs
cp arena-xvfb-checkpoint/scripts/build-libxfont2.sh /tmp/arena-xvfb/scripts/
cp arena-xvfb-checkpoint/scripts/validate-libx11-libxkbfile.sh /tmp/arena-xvfb/scripts/
cp arena-xvfb-checkpoint/scripts/env.sh /tmp/arena-xvfb/env.sh
cp arena-xvfb-checkpoint/meson-ports/libXfont2/meson.build \
  /tmp/arena-xvfb/meson-ports/libXfont2/
cp arena-xvfb-checkpoint/tests/libxkbfile-x11-runtime-test.c /tmp/arena-xvfb/tests/
cp arena-xvfb-checkpoint/tests/libXfont2-consumer-test.c /tmp/arena-xvfb/
chmod +x /tmp/arena-xvfb/scripts/*.sh
```

The scripts assert the exact libXfont, libX11, and libxkbfile commits above
and fail rather than silently building different sources.
