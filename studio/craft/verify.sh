#!/usr/bin/env bash
# Mechanical verification for everything craft.yml builds.
#
# `pi-craft verify` returns 0 = pass, 1 = fail, 2 = usage, 3 = a probe tool is
# missing. Exit 3 (no ffprobe on the runner before apt) is reported as a skip, not
# a pass: a check that could not run has not passed.
set -uo pipefail

OUT=studio/craft/out
pass=0; fail=0; skip=0

v() {
  local label=$1; shift
  npx pi-craft verify "$@" >/tmp/verify.log 2>&1
  local rc=$?
  case $rc in
    0) echo "  PASS  $label"; pass=$((pass + 1));;
    3) echo "  SKIP  $label (probe tool missing)"; sed -n '1,3p' /tmp/verify.log | sed 's/^/        /'; skip=$((skip + 1));;
    *) echo "  FAIL  $label (rc=$rc)"; sed -n '1,6p' /tmp/verify.log | sed 's/^/        /'; fail=$((fail + 1));;
  esac
}

echo "── DeckCraft"
[ -f "$OUT/kiln-deckcraft.pdf" ] && v "deck pdf · 12 pages" "$OUT/kiln-deckcraft.pdf" --pages 12 \
  --text-contains "Rooms," --text-contains "Meridian Towers" --text-contains "Fixed scope. Fixed number."
[ -f "$OUT/kiln-deckcraft.pptx" ] && echo "  INFO  deck pptx $(du -h "$OUT/kiln-deckcraft.pptx" | cut -f1)"

echo "── EffectCraft"
if [ -f "$OUT/kiln-sting-alpha.mov" ]; then
  v "sting alpha · 1080², 6 s, has alpha" "$OUT/kiln-sting-alpha.mov" --alpha --size 1080x1080 --duration 6 --has-video
fi
if [ -f "$OUT/kiln-sting.mp4" ]; then
  v "sting mp4 · 1080², 6 s" "$OUT/kiln-sting.mp4" --size 1080x1080 --duration 6 --has-video
fi
if [ -f "$OUT/kiln-sting-poster.png" ]; then
  v "sting poster · 1080²" "$OUT/kiln-sting-poster.png" --size 1080x1080
fi

echo "── FigCraft"
for f in "$OUT"/figcraft-*.png; do
  [ -f "$f" ] || continue
  case "$f" in
    *Home-Desktop*) v "$(basename "$f") · 2880x1800" "$f" --size 2880x1800;;
    *Home-Mobile*)  v "$(basename "$f") · 780x1688" "$f" --size 780x1688;;
    *)              echo "  INFO  $(basename "$f") (no assertion)";;
  esac
done

echo
echo "verify: $pass passed, $fail failed, $skip skipped"
[ "$fail" -eq 0 ]
