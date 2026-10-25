#!/usr/bin/env bash
# Validate the proposed version-matched libX11 development solution for
# libxkbfile at two independent levels:
#
#   1. Normal pkg-config/Meson integration using honest upstream metadata.
#   2. Direct ABI compilation/link/runtime checks using the pristine
#      libX11 1.8.4 headers and the actual installed Debian 1.8.4 library.
#
# The libX11 development overlay is isolated from the main prefix.  Its
# headers and x11.pc are expanded from immutable files in the pinned
# upstream source.  No system directory is modified and no dependency field
# is removed to hide a missing package.
set -Eeuo pipefail

ARENA=${ARENA:-/tmp/arena-xvfb}
PREFIX=${PREFIX:-$ARENA/prefix}
LIBX11_SRC=${LIBX11_SRC:-$ARENA/src/libX11-1.8.4}
LIBXKBFILE_SRC=${LIBXKBFILE_SRC:-$ARENA/src/libxkbfile}
OVERLAY=${OVERLAY:-$ARENA/validation/libX11-1.8.4-dev}
PROBE_BUILD=${PROBE_BUILD:-$ARENA/build/libxkbfile-probe}
MANUAL_BUILD=${MANUAL_BUILD:-$ARENA/validation/libxkbfile-manual}
TEST_SRC=${TEST_SRC:-$ARENA/tests/libxkbfile-x11-runtime-test.c}
TEST_BIN=${TEST_BIN:-$ARENA/validation/libxkbfile-x11-runtime-test}
HEADER_PROBE=${HEADER_PROBE:-$ARENA/validation/libX11-header-probe.c}
HEADER_PROBE_BIN=${HEADER_PROBE_BIN:-$ARENA/validation/libX11-header-probe}
SYSTEM_X11=${SYSTEM_X11:-/usr/lib/x86_64-linux-gnu/libX11.so.6}
EXPECTED_LIBX11_COMMIT=fc5ec8edda1efdf5d66db4e76796e3c407527b3b
EXPECTED_LIBXKBFILE_COMMIT=6289ef997918cafdaae5ddc17a7442e30dede994
LOG=${LOG:-$ARENA/logs/libx11-libxkbfile-validation.log}

mkdir -p "$ARENA/logs" "$(dirname "$PROBE_BUILD")" "$(dirname "$OVERLAY")"
exec > >(tee "$LOG") 2>&1

export PATH="$PREFIX/bin:$PATH"
export PKG_CONFIG="$PREFIX/bin/pkg-config"
export PKG_CONFIG_SYSTEM_INCLUDE_PATH=/usr/include
export PKG_CONFIG_SYSTEM_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu
export GIT_TERMINAL_PROMPT=0

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

libx11_commit=$(git -C "$LIBX11_SRC" rev-parse HEAD^{commit})
libxkbfile_commit=$(git -C "$LIBXKBFILE_SRC" rev-parse HEAD)
[ "$libx11_commit" = "$EXPECTED_LIBX11_COMMIT" ] ||
  fail "libX11 source commit $libx11_commit != $EXPECTED_LIBX11_COMMIT"
[ "$libxkbfile_commit" = "$EXPECTED_LIBXKBFILE_COMMIT" ] ||
  fail "libxkbfile source commit $libxkbfile_commit != $EXPECTED_LIBXKBFILE_COMMIT"

system_x11_real=$(readlink -f "$SYSTEM_X11")
system_package_version=$(dpkg-query -W -f='${Version}' libx11-6)
case "$system_package_version" in
  *1.8.4*) ;;
  *) fail "installed libx11-6 is version $system_package_version, expected upstream 1.8.4" ;;
esac
[ "$(objdump -p "$system_x11_real" | awk '$1 == "SONAME" {print $2}')" = "libX11.so.6" ] ||
  fail "$system_x11_real does not have SONAME libX11.so.6"

echo "libX11 source pin:       $libx11_commit"
echo "libxkbfile source pin:   $libxkbfile_commit"
echo "runtime package:         libx11-6 $system_package_version"
echo "runtime library:         $system_x11_real"
echo "runtime library sha256:   $(sha256sum "$system_x11_real" | awk '{print $1}')"

# The two XlibConf.h values follow defaults in the pinned configure.ac:
# xthreads defaults to yes, and XUSE_MTSAFE_API follows when getpwuid_r is
# available.  Prove those host/library facts before generating the header.
if ! nm -D /lib/x86_64-linux-gnu/libc.so.6 | grep ' getpwuid_r@@' >/dev/null; then
  fail "getpwuid_r not found in libc; XUSE_MTSAFE_API=1 would not be justified"
fi
for sym in XInitThreads XLockDisplay XUnlockDisplay; do
  nm -D "$system_x11_real" | grep " T $sym$" >/dev/null ||
    fail "runtime libX11 does not export expected thread API symbol $sym"
done

rm -rf "$OVERLAY"
mkdir -p "$OVERLAY/include/X11/extensions" "$OVERLAY/lib/pkgconfig"

# Exact installed-header list from include/Makefile.am in libX11 1.8.4.
for header in \
  XKBlib.h Xcms.h Xlib.h Xlibint.h Xlocale.h Xresource.h Xutil.h \
  cursorfont.h Xregion.h ImUtil.h Xlib-xcb.h
do
  install -m 0644 "$LIBX11_SRC/include/X11/$header" "$OVERLAY/include/X11/$header"
done
install -m 0644 \
  "$LIBX11_SRC/include/X11/extensions/XKBgeom.h" \
  "$OVERLAY/include/X11/extensions/XKBgeom.h"

sed \
  -e 's|^#undef XTHREADS$|#define XTHREADS 1|' \
  -e 's|^#undef XUSE_MTSAFE_API$|#define XUSE_MTSAFE_API 1|' \
  "$LIBX11_SRC/include/X11/XlibConf.h.in" > "$OVERLAY/include/X11/XlibConf.h"
grep -q '^#define XTHREADS 1$' "$OVERLAY/include/X11/XlibConf.h"
grep -q '^#define XUSE_MTSAFE_API 1$' "$OVERLAY/include/X11/XlibConf.h"

ln -s "$system_x11_real" "$OVERLAY/lib/libX11.so"
ln -s "$system_x11_real" "$OVERLAY/lib/libX11.so.6"

# Generate x11.pc from the upstream template.  In particular, the honest
# Requires.private entry for libxcb is retained.
python3 - "$LIBX11_SRC/x11.pc.in" "$OVERLAY/lib/pkgconfig/x11.pc" "$OVERLAY" <<'PY'
import pathlib
import sys

source, dest, prefix = map(pathlib.Path, sys.argv[1:])
text = source.read_text()
replacements = {
    "@prefix@": str(prefix),
    "@exec_prefix@": "${prefix}",
    "@libdir@": "${exec_prefix}/lib",
    "@includedir@": "${prefix}/include",
    "@XTHREADLIB@": "-lpthread",
    "@PACKAGE_VERSION@": "1.8.4",
    "@XKBPROTO_REQUIRES@": "kbproto",
    "@X11_EXTRA_DEPS@": "xcb >= 1.11.1",
    "@XTHREAD_CFLAGS@": "",
}
for old, new in replacements.items():
    text = text.replace(old, new)
if "@" in text:
    raise SystemExit("unexpanded @TOKEN@ left in generated x11.pc")
dest.write_text(text)
PY

cat > "$OVERLAY/PROVENANCE.txt" <<EOF
Purpose: isolated validation of a version-matched libX11 development overlay.
Source: X11Libre/mirror.fdo.libX11 tag libX11-1.8.4
Source commit: $EXPECTED_LIBX11_COMMIT
Runtime: Debian libx11-6 $system_package_version at $system_x11_real
Runtime sha256: $(sha256sum "$system_x11_real" | awk '{print $1}')
Generated include/X11/XlibConf.h: XTHREADS=1, XUSE_MTSAFE_API=1
Generated lib/pkgconfig/x11.pc: expanded from upstream x11.pc.in
Known integration requirement: a genuine xcb development package for the
upstream x11.pc Requires.private entry.
EOF
(
  cd "$OVERLAY"
  find include lib/pkgconfig -type f -print0 | sort -z | xargs -0 sha256sum
) > "$OVERLAY/SHA256SUMS"

export PKG_CONFIG_PATH="$OVERLAY/lib/pkgconfig:$PREFIX/lib/pkgconfig:$PREFIX/share/pkgconfig"

echo "--- generated x11.pc ---"
cat "$OVERLAY/lib/pkgconfig/x11.pc"
echo "--- pkg-config module/version check ---"
pkg-config --modversion x11

meson_blocked_by_xcb=0
set +e
pkg-config --cflags --libs x11 >"$ARENA/logs/libX11-pkgconfig-flags.txt" 2>&1
pkgconfig_flags_status=$?
set -e
cat "$ARENA/logs/libX11-pkgconfig-flags.txt"
if [ "$pkgconfig_flags_status" -ne 0 ]; then
  grep -q "Package 'xcb', required by 'x11', not found" \
    "$ARENA/logs/libX11-pkgconfig-flags.txt" ||
    fail "pkg-config x11 failed for an unexpected reason"
  meson_blocked_by_xcb=1
  echo "EXPECTED BLOCKER: honest x11.pc cannot resolve flags until a genuine xcb.pc/development package exists."
fi

rm -rf "$PROBE_BUILD"
set +e
meson setup "$PROBE_BUILD" "$LIBXKBFILE_SRC" \
  --prefix="$PREFIX" --libdir=lib --buildtype=release \
  >"$ARENA/logs/libxkbfile-meson-probe.log" 2>&1
meson_status=$?
set -e
cat "$ARENA/logs/libxkbfile-meson-probe.log"
if [ "$meson_status" -ne 0 ]; then
  grep -q "Package 'xcb', required by 'x11', not found" \
    "$ARENA/logs/libxkbfile-meson-probe.log" ||
    fail "Meson libxkbfile probe failed for an unexpected reason"
  meson_blocked_by_xcb=1
  echo "EXPECTED BLOCKER: Meson correctly rejected the incomplete x11 dependency graph."
else
  echo "Meson configured libxkbfile; continuing with full Meson build/install."
  ninja -C "$PROBE_BUILD"
  ninja -C "$PROBE_BUILD" install
fi

# Direct ABI validation.  These compiler flags come from the actual fields in
# the upstream x11.pc.in after expansion, rather than modifying that file to
# erase xcb.  libxkbfile does not include Xlib-xcb.h or any xcb header; its
# shared-library link needs the libX11 ABI directly.  The private libxcb
# runtime dependency is then exercised through libX11's own DT_NEEDED.
cat > "$HEADER_PROBE" <<'EOF'
#include <stdio.h>
#include <X11/Xlib.h>
#include <X11/XKBlib.h>

int main(void)
{
    const char *name = XDisplayName(NULL);
    if (XInitThreads() == 0)
        return 2;
    printf("libX11 header/link probe: PASS (XDisplayName='%s', SupportsLocale=%d)\n",
           name ? name : "", (int) XSupportsLocale());
    return 0;
}
EOF

echo "+ gcc header probe with explicit flags from generated x11.pc"
gcc -Wall -Wextra -Werror -O2 \
  -I"$OVERLAY/include" -I"$PREFIX/include" \
  -o "$HEADER_PROBE_BIN" "$HEADER_PROBE" \
  -L"$OVERLAY/lib" -lX11 -lpthread
"$HEADER_PROBE_BIN"

[ -f "$PROBE_BUILD/config.h" ] ||
  fail "Meson probe did not generate libxkbfile config.h before dependency resolution"

rm -rf "$MANUAL_BUILD"
mkdir -p "$MANUAL_BUILD/obj"
cp "$PROBE_BUILD/config.h" "$MANUAL_BUILD/config.h"

manual_sources="
cout.c maprules.c srvmisc.c xkbatom.c xkbbells.c xkbconfig.c xkbdraw.c
xkberrs.c xkbmisc.c xkbout.c xkbtext.c xkmout.c xkmread.c
"
manual_objects=""
for source in $manual_sources; do
  object="$MANUAL_BUILD/obj/${source%.c}.o"
  echo "+ gcc -c $LIBXKBFILE_SRC/src/$source"
  gcc -fPIC -O2 -DHAVE_CONFIG_H \
    -I"$MANUAL_BUILD" \
    -I"$LIBXKBFILE_SRC" \
    -I"$LIBXKBFILE_SRC/include" \
    -I"$LIBXKBFILE_SRC/include/X11/extensions" \
    -I"$OVERLAY/include" \
    -I"$PREFIX/include" \
    -c "$LIBXKBFILE_SRC/src/$source" -o "$object"
  manual_objects="$manual_objects $object"
done

manual_library="$MANUAL_BUILD/libxkbfile.so.1.0.2"
echo "+ gcc -shared -Wl,--no-undefined manual libxkbfile validation library"
# shellcheck disable=SC2086
gcc -shared -Wl,-soname,libxkbfile.so.1 -Wl,--no-undefined \
  -o "$manual_library" $manual_objects \
  -L"$OVERLAY/lib" -lX11 -lpthread
ln -sf "$(basename "$manual_library")" "$MANUAL_BUILD/libxkbfile.so.1"
ln -sf "$(basename "$manual_library")" "$MANUAL_BUILD/libxkbfile.so"

[ "$(objdump -p "$manual_library" | awk '$1 == "SONAME" {print $2}')" = "libxkbfile.so.1" ] ||
  fail "manual libxkbfile has unexpected SONAME"
echo "--- DT_NEEDED for manual libxkbfile validation library ---"
objdump -p "$manual_library" | awk '$1 == "NEEDED" || $1 == "SONAME" {print}'
objdump -p "$manual_library" | grep -q 'NEEDED.*libX11.so.6' ||
  fail "manual libxkbfile does not record DT_NEEDED libX11.so.6"

nm -D -u "$manual_library" | awk '$1 == "U" {sub(/@.*/, "", $2); print $2}' |
  sort -u > "$ARENA/logs/libxkbfile-undefined.txt"
nm -D --defined-only "$system_x11_real" | awk 'NF >= 3 {print $3}' |
  sort -u > "$ARENA/logs/libX11-defined.txt"
comm -12 "$ARENA/logs/libxkbfile-undefined.txt" "$ARENA/logs/libX11-defined.txt" \
  > "$ARENA/logs/libxkbfile-symbols-provided-by-libX11.txt"

echo "--- undefined libxkbfile symbols exported by installed libX11 ---"
cat "$ARENA/logs/libxkbfile-symbols-provided-by-libX11.txt"
for sym in XGetAtomName XInternAtom XkbAllocKeyboard XkbAllocClientMap XkbGetMap XkbSetMap; do
  grep -qx "$sym" "$ARENA/logs/libxkbfile-symbols-provided-by-libX11.txt" ||
    fail "expected libX11-provided libxkbfile symbol missing from audit: $sym"
done

set +e
LD_LIBRARY_PATH="$MANUAL_BUILD:$OVERLAY/lib" ldd -r "$manual_library" \
  > "$ARENA/logs/libxkbfile-ldd-r.txt" 2>&1
ldd_status=$?
set -e
cat "$ARENA/logs/libxkbfile-ldd-r.txt"
[ "$ldd_status" -eq 0 ] || fail "ldd -r failed for manual libxkbfile validation library"
if grep -q 'undefined symbol' "$ARENA/logs/libxkbfile-ldd-r.txt"; then
  fail "ldd -r found undefined symbols in manual libxkbfile library"
fi
if grep -q 'not found' "$ARENA/logs/libxkbfile-ldd-r.txt"; then
  fail "ldd -r found a missing runtime library for manual libxkbfile library"
fi

echo "+ gcc libxkbfile/libX11 runtime consumer"
gcc -Wall -Wextra -Werror -O2 \
  -I"$LIBXKBFILE_SRC/include" -I"$OVERLAY/include" -I"$PREFIX/include" \
  -o "$TEST_BIN" "$TEST_SRC" \
  -L"$MANUAL_BUILD" -lxkbfile -L"$OVERLAY/lib" -lX11 -lpthread

echo "--- runtime test via overlay lib path ---"
LD_LIBRARY_PATH="$MANUAL_BUILD:$OVERLAY/lib" ldd "$TEST_BIN"
LD_LIBRARY_PATH="$MANUAL_BUILD:$OVERLAY/lib" "$TEST_BIN"

echo "--- runtime test resolving libX11 from the normal system path ---"
LD_LIBRARY_PATH="$MANUAL_BUILD" ldd "$TEST_BIN"
LD_LIBRARY_PATH="$MANUAL_BUILD" "$TEST_BIN"

echo "--- validation hashes ---"
sha256sum "$manual_library" "$TEST_BIN" "$OVERLAY/lib/pkgconfig/x11.pc" \
  "$OVERLAY/include/X11/XlibConf.h"

echo "Direct libX11 ABI/header/link/runtime validation: PASS"
if [ "$meson_blocked_by_xcb" -ne 0 ]; then
  echo "Meson/pkg-config libxkbfile integration: BLOCKED by missing genuine xcb development package (xcb.pc)"
  echo "Validation result: PARTIAL (ABI passed; Meson integration blocked)"
  exit 3
fi

echo "libX11/libxkbfile validation: PASS"
