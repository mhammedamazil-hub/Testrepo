# Sourcebook for Android

## What this APK is

A lightweight native Android shell around your **running Rust Sourcebook server**, with a mobile layout and native file picking/saving/printing. Android 8.0+ (API 26), targeting Android 15 (API 35). No Google login, Gemini dependency, analytics SDK, camera/microphone permission, or broad storage permission.

**It is not an offline, all-in-one Rust server APK.** The Rust backend is unchanged and runs on your computer or hosted server. AI calls, ingestion, storage and media synthesis happen there. The native shell uses Java/Android WebView APIs; all existing server/business logic remains Rust. It needs a reasonably current Android System WebView. Unimplemented NotebookLM features are not added by packaging.

## Build/download

Workflow: **Build Sourcebook Android APK** (`.github/workflows/android.yml`). Successful runs publish the artifact **sourcebook-android-debug**, containing:

- `sourcebook-debug.apk` — debug-signed, installable APK for personal sideloading.
- `sourcebook-debug.apk.sha256` — integrity checksum.

A [verified successful build](https://github.com/mhammedamazil-hub/Testrepo/actions/runs/42487957011) is available; [download its APK artifact](https://github.com/mhammedamazil-hub/Testrepo/actions/runs/42487957011/artifacts/13619784791). For newer revisions, open the latest successful workflow run on GitHub. Download and extract that artifact, then transfer the APK to your phone. Android may ask you to allow installation from the browser/files app. This is not a Play Store release. Never install APKs from untrusted sources.

Build locally with JDK 17+, Android SDK platform 35, build-tools 35.0.0, `zip` and the Android SDK environment:

```sh
export ANDROID_HOME=/path/to/android-sdk
"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" 'platforms;android-35' 'build-tools;35.0.0'
bash android/scripts/build-apk.sh
# Output: android/build/sourcebook-debug.apk
```

The build uses Android SDK tools directly (aapt2, javac, d8, zipalign, apksigner), without downloading Gradle or third-party Android dependencies. It executes pure-Java URL-policy tests first and verifies the APK signature afterwards. CI caches a personal debug keystore so later builds can normally update the same app. If that cache is deleted, a new key is generated and Android will require uninstalling the old APK before installing. Production distribution requires your own private release signing process; no release key is committed.

## Connect the app

1. Start your server with its AI configuration (see main README):
   ```sh
   export SOURCEBOOK_TOKEN='a-long-random-secret'
   export AI_BASE_URL='https://your-provider.example/v1'
   export AI_MODEL='your-model'
   export AI_API_KEY='your-private-key'
   cargo run --release -- serve --bind 0.0.0.0:3000
   ```
2. Prefer a stable **HTTPS** reverse-proxy address, e.g. `https://research.example.com`. TLS certificates must be valid. The server must be mounted at the address root, not `/sourcebook/`.
3. In the APK, enter that address and tap **Connect workspace**.
4. Enter `SOURCEBOOK_TOKEN` in the web interface. Your provider key stays on the Rust server.

For trusted LAN development only, use your computer's LAN IP, e.g. `http://192.168.1.20:3000`, and explicitly check **Allow unencrypted HTTP**. The phone must be on a network that can reach that computer and its firewall must allow the port. `127.0.0.1`/`localhost` on the phone points at the phone, not your computer. HTTP exposes your access token and research data to the network; don't use it publicly.

The app remembers only the server address/insecure-HTTP choice. The token stays in WebView session storage, not native preferences. Switching servers clears the current browser session. Rotating the device preserves the live WebView; app process death can require signing in again. Changing servers does not delete server data.

## Existing features on mobile

- Notebooks, source import/restore, edit/delete, chat/citations and history, notes and exports.
- Native file picker for PDF, DOCX, text/Markdown/CSV/JSON, and audio/video uploads; existing server limits apply (10 MB uploads, 16 MB restore).
- **Sources / Chat / Studio** mobile tabs; phone-sized controls and safe-area support; wide tables scroll horizontally.
- Interactive flashcards/quizzes, mind maps, slide decks, source guides, tables and other text materials.
- MP3 playback and native MP3 save, with speech/transcription models configured server-side.
- JSON/Markdown/CSV/source exports using Android's document-save picker, rather than unsupported WebView blob downloads. Native save bridge has a 24 MB limit.
- Print / PDF invokes the Android print service; choose **Save as PDF** if available on the device. Printing is based on the displayed generated document, not a native PPTX exporter.
- Read-only share links can be copied from the app; recipients can open them in a normal browser without installing the APK. Opening external sites requires confirmation and uses the external browser.

Background media playback, push notifications, offline synchronization, direct microphone recording and native share-intent ingestion are not provided. Android may pause playback when the app is backgrounded. The CLI remains a computer/server tool, not an Android terminal screen.

## Security

Only connect to your own/trusted server: the server supplies the app UI. Native bridge functions can request a user-confirmed file save or print. Top-level navigation/subresources are restricted to the chosen origin; external sites aren't loaded with the native bridge. File-system access and mixed content are disabled. Content-provider access is used for user-selected uploads; no general storage permission is requested. TLS errors are never bypassed, third-party cookies are disabled, backup is disabled, and production WebView debugging is off.

A debug-signed APK is suitable for personal testing, not a hardened enterprise release. Test on a physical phone before relying on document import, audio playback or printing. Browser mocks verify interface behavior but are not substitutes for Android device/emulator tests.

Build verification has passed, including signature verification. Ten browser behavior tests pass, including mobile tab switching, native save payloads and safe native print HTML. The APK has not been installed/tested on a physical Android device in this workspace. The sandbox blocks GitHub's artifact-storage host, so use the GitHub download link above rather than expecting a local APK attachment here.
