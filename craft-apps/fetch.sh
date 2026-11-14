#!/usr/bin/env bash
# Fetch the Crafting App headless CLIs (Linux x86_64) from this repo's release assets.
#   ./craft-apps/fetch.sh            # all apps  -> ~/.local/opt/craft-apps/bin
#   ./craft-apps/fetch.sh photocraft # one app
set -euo pipefail
REL="${CRAFT_RELEASE:-craft-apps-x86_64}"
DEST="${CRAFT_DEST:-$HOME/.local/opt/craft-apps/bin}"
REPO="${CRAFT_REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "${GITHUB_REPOSITORY:-owner/repo}")}"
APPS=("${@:-photocraft vectorcraft filmcraft lightcraft pdfcraft effectcraft designcraft figcraft wordcraft soundcraft deckcraft cadcraft gridcraft}")
mkdir -p "$DEST"; tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
gh release download "$REL" -R "$REPO" --pattern '*.gz' -D "$tmp"
gh release download "$REL" -R "$REPO" --pattern '*.gz.sha256' -D "$tmp"
( cd "$tmp" && sha256sum -c ./*.sha256 )
for app in $APPS; do
  gz=$(ls "$tmp"/"$app"-*.gz 2>/dev/null | head -1) || { echo "skip $app"; continue; }
  gunzip -c "$gz" > "$DEST/$app-cli"; chmod +x "$DEST/$app-cli"
  echo "installed $DEST/$app-cli  ($("$DEST/$app-cli" --version 2>&1 | head -1))"
done
echo; echo "add to PATH:  export PATH=\"$DEST:\$PATH\""
