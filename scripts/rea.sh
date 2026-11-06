#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
if [ -d "$ROOT/.tools/jdk-21.0.13+9" ]; then
    export JAVA_HOME="$ROOT/.tools/jdk-21.0.13+9"
    export PATH="$JAVA_HOME/bin:$PATH"
fi
if [ -f "$ROOT/.tools/downloads/jadx-headless-mcp-0.7.1-all.jar" ]; then
    export REA_JADX_MCP_JAR="$ROOT/.tools/downloads/jadx-headless-mcp-0.7.1-all.jar"
fi
if [ -d "$ROOT/.tools/ghidra_12.1.4_PUBLIC" ]; then
    export GHIDRA_INSTALL_DIR="$ROOT/.tools/ghidra_12.1.4_PUBLIC"
fi
if [ -f "$ROOT/.tools/downloads/apktool_3.0.3.jar" ]; then
    export REA_APKTOOL_COMMAND="$ROOT/scripts/apktool.sh"
fi
exec "$ROOT/node_modules/node/bin/node" "$ROOT/node_modules/rea-agents/scripts/rea.mjs" "$@"
