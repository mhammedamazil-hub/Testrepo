#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SDK=${ANDROID_HOME:?Set ANDROID_HOME}
NDK="$SDK/ndk/28.2.13676358"
LLVM="$NDK/toolchains/llvm/prebuilt/linux-x86_64"
BUILD="$ROOT/android/build-offline"
LLAMA_SOURCE=${LLAMA_SOURCE:-"$ROOT/.tools/llama-cpp"}
test -f "$LLAMA_SOURCE/include/llama.h"
mkdir -p "$BUILD/native" "$BUILD/libs" "$BUILD/classes" "$BUILD/generated" "$BUILD/dex" "$BUILD/assets/web" "$BUILD/lib/arm64-v8a"
cmake -S "$ROOT/android/native" -B "$BUILD/native" -G Ninja \
 -DCMAKE_TOOLCHAIN_FILE="$NDK/build/cmake/android.toolchain.cmake" \
 -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-28 -DANDROID_STL=c++_shared \
 -DCMAKE_BUILD_TYPE=Release -DLLAMA_SOURCE="$LLAMA_SOURCE"
cmake --build "$BUILD/native" --target sourcebook_llama --parallel 2
find "$BUILD/native" -name '*.a' -exec cp {} "$BUILD/libs/" \;
export PATH="$LLVM/bin:$PATH"
export CC_aarch64_linux_android=aarch64-linux-android28-clang
export CXX_aarch64_linux_android=aarch64-linux-android28-clang++
export AR_aarch64_linux_android=llvm-ar
export CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER=aarch64-linux-android28-clang
export CARGO_TARGET_AARCH64_LINUX_ANDROID_RUSTFLAGS='-C link-arg=-Wl,-z,max-page-size=16384'
export SOURCEBOOK_NATIVE_LIBS="$BUILD/libs"
(cd "$ROOT" && cargo build --release --lib --target aarch64-linux-android --features android-offline)
cp "$ROOT/target/aarch64-linux-android/release/libsourcebook.so" "$BUILD/lib/arm64-v8a/"
cp "$LLVM/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so" "$BUILD/lib/arm64-v8a/"
llvm-strip --strip-unneeded "$BUILD/lib/arm64-v8a/"*.so
cp "$ROOT/web/"{index.html,style.css,app.js,offline.js,astryx.js,astryx.css,UI-LICENSES.txt} "$BUILD/assets/web/"
cp "$LLAMA_SOURCE/LICENSE" "$BUILD/assets/llama-cpp-LICENSE.txt"
TOOLS="$SDK/build-tools/35.0.0"; ANDROID_JAR="$SDK/platforms/android-35/android.jar"
"$TOOLS/aapt2" compile --dir "$ROOT/android/app/src/main/res" -o "$BUILD/resources.zip"
"$TOOLS/aapt2" link -o "$BUILD/app-unsigned.apk" -I "$ANDROID_JAR" --manifest "$ROOT/android/offline/AndroidManifest.xml" --java "$BUILD/generated" --min-sdk-version 28 --target-sdk-version 35 --version-code 8 --version-name 0.7.0 "$BUILD/resources.zip" -A "$BUILD/assets"
find "$ROOT/android/offline/java" "$BUILD/generated" -name '*.java' > "$BUILD/sources.txt"
echo "$ROOT/android/app/src/main/java/app/sourcebook/mobile/OriginPolicy.java" >> "$BUILD/sources.txt"
javac -encoding UTF-8 -source 8 -target 8 -classpath "$ANDROID_JAR" -d "$BUILD/classes" @"$BUILD/sources.txt"
mapfile -t CLASSES < <(find "$BUILD/classes" -name '*.class')
"$TOOLS/d8" --release --min-api 28 --lib "$ANDROID_JAR" --output "$BUILD/dex" "${CLASSES[@]}"
(cd "$BUILD/dex" && zip -q -j "$BUILD/app-unsigned.apk" ./*.dex)
(cd "$BUILD" && zip -q "$BUILD/app-unsigned.apk" lib/arm64-v8a/*.so)
"$TOOLS/zipalign" -f -P 16 4 "$BUILD/app-unsigned.apk" "$BUILD/app-aligned.apk"
KEYSTORE="$ROOT/android/.signing/debug.keystore";mkdir -p "$(dirname "$KEYSTORE")"
if [ ! -f "$KEYSTORE" ];then keytool -genkeypair -keystore "$KEYSTORE" -storepass android -alias androiddebugkey -keypass android -dname 'CN=Android Debug,O=Android,C=US' -keyalg RSA -keysize 2048 -validity 10000 -noprompt;fi
"$TOOLS/apksigner" sign --ks "$KEYSTORE" --ks-key-alias androiddebugkey --ks-pass pass:android --key-pass pass:android --out "$BUILD/sourcebook-offline-arm64.apk" "$BUILD/app-aligned.apk"
"$TOOLS/apksigner" verify --verbose "$BUILD/sourcebook-offline-arm64.apk"
"$TOOLS/aapt2" dump permissions "$BUILD/sourcebook-offline-arm64.apk" > "$BUILD/permissions.txt"
grep -q 'android.permission.INTERNET' "$BUILD/permissions.txt"
unzip -l "$BUILD/sourcebook-offline-arm64.apk" | grep -E 'libsourcebook.so|libc\+\+_shared.so|offline.js|index.html'
(cd "$BUILD" && sha256sum sourcebook-offline-arm64.apk > sourcebook-offline-arm64.apk.sha256)
cp "$ROOT/docs/OFFLINE-ANDROID.md" "$BUILD/OFFLINE-README.md"
