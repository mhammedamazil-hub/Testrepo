#!/bin/sh
# Build the pinned libXfont2 2.0.9 checkout with the Arena Meson port.
set -eu

ARENA=${ARENA:-/tmp/arena-xvfb}
PREFIX=${PREFIX:-$ARENA/prefix}
SRC=${SRC:-$ARENA/src/libXfont}
BUILD=${BUILD:-$ARENA/build/libXfont2}
PORT=${PORT:-$ARENA/meson-ports/libXfont2/meson.build}
EXPECTED_COMMIT=1531de719edf74ad76f21f0afcd94db450c65cce

export PATH="$PREFIX/bin:$PATH"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/share/pkgconfig"
export PKG_CONFIG="$PREFIX/bin/pkg-config"
export PKG_CONFIG_SYSTEM_INCLUDE_PATH=/usr/include
export PKG_CONFIG_SYSTEM_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu
export LD_LIBRARY_PATH="$PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

actual_commit=$(git -C "$SRC" rev-parse HEAD)
if [ "$actual_commit" != "$EXPECTED_COMMIT" ]; then
  echo "error: libXfont checkout is $actual_commit, expected $EXPECTED_COMMIT" >&2
  exit 1
fi

mkdir -p "$ARENA/logs" "$(dirname "$BUILD")"
cp "$PORT" "$SRC/meson.build"

rm -rf "$BUILD"
set +e
{
  echo "+ meson setup $BUILD $SRC --prefix=$PREFIX --libdir=lib --buildtype=release"
  meson setup "$BUILD" "$SRC" --prefix="$PREFIX" --libdir=lib --buildtype=release &&
  echo "+ ninja -C $BUILD" &&
  ninja -C "$BUILD" &&
  echo "+ meson test -C $BUILD --print-errorlogs" &&
  meson test -C "$BUILD" --print-errorlogs &&
  echo "+ ninja -C $BUILD install" &&
  ninja -C "$BUILD" install
} >"$ARENA/logs/libXfont2-build.log" 2>&1
build_status=$?
set -e

cat "$ARENA/logs/libXfont2-build.log"
exit "$build_status"
