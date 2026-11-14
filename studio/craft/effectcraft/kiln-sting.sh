#!/usr/bin/env bash
# EffectCraft — the KILN identity sting, built as a real motion-graphics comp.
#
# Runs in CI. Produces three things:
#   kiln-sting-alpha.mov   ProRes 4444 with rgba channels — a real overlay with
#                          transparency, for cutting over footage elsewhere
#   kiln-sting.mp4         h264, the same comp over the studio's ink field
#   kiln-sting-poster.png  a still, for the site's poster attribute
#
# The comp is 1080x1080, 6 s at 24 fps, to match ads/video/kiln-sting-1080.mp4.
#
# One difference from the Blender-rendered master worth stating: the runner has no
# Instrument Serif, so this build draws the wordmark in a system grotesque. The
# geometry, timing and colour are the brand's; the face is not. The Blender master
# (ads/video/kiln-sting-1080.mp4) remains the version with the real typography.
set -euo pipefail

OUT=studio/craft/out
mkdir -p "$OUT"
EC=studio/craft/out/kiln-sting.ecproj
rm -f "$EC" "$OUT/kiln-sting-alpha.mov" "$OUT/kiln-sting.mp4" "$OUT/kiln-sting-poster.png"

# A comp with the brand's ink field, an ember rule that draws, the wordmark, and
# the descriptor. --empty is mandatory: without it EffectCraft opens its demo
# project and demo items end up in the render.
npx pi-craft effectcraft exec --empty --save-as "$EC" run \
  comp.new '{"name":"KILN Sting","width":1080,"height":1080,"frameRate":24,"duration":6,"background":"#0B0C0E"}' \
  layer.newText '{"text":"KILN","name":"Wordmark","size":150,"position":[540,560],"fill":"#F2EDE4","font":"Georgia"}' \
  layer.newText '{"text":"INTERACTIVE ARCHITECTURE","name":"Descriptor","size":22,"position":[540,690],"fill":"#8A8578","font":"Consolas"}' \
  layer.newShape '{"kind":"rect","name":"Rule","size":[360,3],"position":[360,646],"fill":"#D8542A"}' \
  prop.addKey '{"layer":"Wordmark","path":"transform/opacity","time":0,"value":0}' \
  prop.addKey '{"layer":"Wordmark","path":"transform/opacity","time":1.0,"value":100}' \
  prop.addKey '{"layer":"Descriptor","path":"transform/opacity","time":1.0,"value":0}' \
  prop.addKey '{"layer":"Descriptor","path":"transform/opacity","time":2.2,"value":100}' \
  prop.addKey '{"layer":"Rule","path":"contents/group/transform/anchor","time":0,"value":[0,0]}' \
  prop.addKey '{"layer":"Rule","path":"contents/group/contents/rect/size","time":0,"value":[0,3]}' \
  prop.addKey '{"layer":"Rule","path":"contents/group/contents/rect/size","time":1.4,"value":[360,3]}' \
  prop.addKey '{"layer":"Rule","path":"contents/group/contents/rect/size","time":4.6,"value":[360,3]}' \
  prop.addKey '{"layer":"Rule","path":"contents/group/contents/rect/size","time":6.0,"value":[360,3]}' \

npx pi-craft effectcraft exec --project "$EC" info > "$OUT/kiln-sting.info.json" || true
# property paths are not guessable; they are recorded below. A shape's live width is
# contents/group/contents/rect/size, so the rule can draw on from its left anchor
# rather than fading in.
npx pi-craft effectcraft exec --project "$EC" props - Rule --flat > "$OUT/kiln-sting-props.txt" 2>&1 || true
cat "$OUT/kiln-sting-props.txt" || true

# The alpha overlay: both flags are required or the mov is yuv444p12le and opaque.
npx pi-craft effectcraft exec --project "$EC" render \
  --out "$OUT/kiln-sting-alpha.mov" --format prores --prores 4444 --channels rgba

# The deliverable: over the comp's own ink field.
npx pi-craft effectcraft exec --project "$EC" render \
  --out "$OUT/kiln-sting.mp4" --format h264

npx pi-craft effectcraft exec --project "$EC" render-frame \
  --time 3.0 --out "$OUT/kiln-sting-poster.png"

echo "effectcraft: done"
