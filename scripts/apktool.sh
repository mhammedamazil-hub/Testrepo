#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
JAVA_HOME=${JAVA_HOME:-"$ROOT/.tools/jdk-21.0.13+9"}
exec "$JAVA_HOME/bin/java" -jar "$ROOT/.tools/downloads/apktool_3.0.3.jar" "$@"
