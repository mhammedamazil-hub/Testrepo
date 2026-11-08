#!/usr/bin/env bash
# Reproducible SDK-only Android build: no Gradle/dependency downloads after SDK installation.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SDK=${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}
: "${SDK:?Set ANDROID_HOME to your Android SDK}"
TOOLS="$SDK/build-tools/35.0.0"
ANDROID_JAR="$SDK/platforms/android-35/android.jar"
for tool in aapt2 d8 zipalign apksigner; do test -x "$TOOLS/$tool" || { echo "Missing build-tools/35.0.0/$tool" >&2; exit 1; }; done
test -f "$ANDROID_JAR"
BUILD="$ROOT/build"
mkdir -p "$BUILD/classes" "$BUILD/generated" "$BUILD/dex" "$BUILD/host-tests"
# This policy has no Android dependency and is executed before compiling the app.
javac -d "$BUILD/host-tests" "$ROOT/app/src/main/java/app/sourcebook/mobile/OriginPolicy.java" "$ROOT/tests/OriginPolicyTest.java"
java -cp "$BUILD/host-tests" app.sourcebook.mobile.OriginPolicyTest
"$TOOLS/aapt2" compile --dir "$ROOT/app/src/main/res" -o "$BUILD/resources.zip"
"$TOOLS/aapt2" link -o "$BUILD/app-unsigned.apk" -I "$ANDROID_JAR" --manifest "$ROOT/app/src/main/AndroidManifest.xml" --java "$BUILD/generated" --min-sdk-version 26 --target-sdk-version 35 --version-code 3 --version-name 0.3.0 "$BUILD/resources.zip"
find "$ROOT/app/src/main/java" "$BUILD/generated" -name '*.java' > "$BUILD/sources.txt"
javac -encoding UTF-8 -source 8 -target 8 -bootclasspath "$ANDROID_JAR" -d "$BUILD/classes" @"$BUILD/sources.txt"
mapfile -t CLASSES < <(find "$BUILD/classes" -name '*.class')
"$TOOLS/d8" --release --min-api 26 --lib "$ANDROID_JAR" --output "$BUILD/dex" "${CLASSES[@]}"
(cd "$BUILD/dex" && zip -q -j "$BUILD/app-unsigned.apk" ./*.dex)
"$TOOLS/zipalign" -f -p 4 "$BUILD/app-unsigned.apk" "$BUILD/app-aligned.apk"
# Debug signing is for personal sideloading, NOT Play Store production publishing.
KEYSTORE=${SOURCEBOOK_DEBUG_KEYSTORE:-"$ROOT/.signing/debug.keystore"}
mkdir -p "$(dirname "$KEYSTORE")"
if [ ! -f "$KEYSTORE" ]; then
 keytool -genkeypair -keystore "$KEYSTORE" -storepass android -alias androiddebugkey -keypass android -dname 'CN=Android Debug,O=Android,C=US' -keyalg RSA -keysize 2048 -validity 10000 -noprompt
fi
"$TOOLS/apksigner" sign --ks "$KEYSTORE" --ks-key-alias androiddebugkey --ks-pass pass:android --key-pass pass:android --out "$BUILD/sourcebook-debug.apk" "$BUILD/app-aligned.apk"
"$TOOLS/apksigner" verify --verbose "$BUILD/sourcebook-debug.apk"
"$TOOLS/aapt2" dump badging "$BUILD/sourcebook-debug.apk" > "$BUILD/apk-info.txt"
sed -n '1,20p' "$BUILD/apk-info.txt"
sha256sum "$BUILD/sourcebook-debug.apk" > "$BUILD/sourcebook-debug.apk.sha256"
echo "APK ready: $BUILD/sourcebook-debug.apk"
