# Sourcebook Offline: embedded Rust + on-device GGUF

This is a separate APK (`app.sourcebook.offline`) from the server-connected client.
Its Rust core is compiled into `libsourcebook.so` and called through JNI **in the
same process**. It never binds a TCP port and does not require Termux, Ollama,
an external computer or a local HTTP server. The APK deliberately has **no
INTERNET permission**. Its UI is packaged as Android assets, not fetched from a
website. The apparent `https://sourcebook.offline` origin is intercepted locally.

## Model import

Install the ARM64 APK on Android 9 or newer, open it, and tap **Model → Choose GGUF**.
Select a model you previously downloaded and have permission to use. It is copied
to private app storage (so allow storage for a second copy). Single-file,
decoder-only, text-instruct GGUF models with a supported embedded chat template
are required. Start with a small 0.5B–1.5B Q4 model. Large models may not fit RAM;
the APK does not include model weights. Import is limited to 8 GB and available
storage. The app retains one model; replacing it unloads the previous one.

Model loading/inference uses the pinned MIT-licensed llama.cpp CPU runtime,
called by Rust—not an API pretending to be local inference. It uses four CPU
threads, a 4096-token context, at most 3000 prompt tokens and 1024 generated tokens.
Cancel AI requests cancellation; generation is limited to five minutes. Small
models can produce incorrect citations or invalid study JSON; invalid structured
results are rejected instead of saved. There is no guarantee every GGUF
architecture/template is supported, or that every phone has sufficient memory.

## Fully on-device features

Notebook/source/note management; text/Markdown/CSV/JSON/PDF/DOCX ingestion;
source selection and retrieval; chat, evidence and saved answers; text studio
materials, quizzes and flashcards/review state; mind maps, slide decks and tables;
JSON restore and JSON/Markdown/CSV exports; Android document picker/save and
Android print/PDF. Storage/manual notes/existing study materials work before a
model is imported. AI text operations require a compatible model loaded.

Network webpage import and public share links cannot work with no network and
are disabled. Import an article's saved text instead; use notebook JSON export
for transfers. Offline speech synthesis, speech recognition and video generation
are **not included**; the desktop/cloud speech endpoints have not been relabeled
as offline features. Import an existing transcript as text. No offline sync,
background inference service or microphone recording is included. Keep the app
open while importing or generating; Android can kill a background process.

All app data and the model live in Android private storage. There is no browser
server token to enter and no API key. Uninstalling/clearing app data deletes the
local database and model. Export/back up notebooks before uninstalling. Export
does not contain model weights. Shared JSON exports contain full source text and
history and should be treated as sensitive. No device encryption layer is added
beyond Android app-private storage and device encryption.

## Research and implementation references

- [Official llama.cpp Android guide](https://github.com/ggml-org/llama.cpp/blob/7d7f0287530bc8981690f361d8c1627dbae1c99a/docs/android.md): NDK cross compilation, ARM64 baseline, context-size/memory caveats.
- [Pinned llama.cpp C API](https://github.com/ggml-org/llama.cpp/blob/7d7f0287530bc8981690f361d8c1627dbae1c99a/include/llama.h): GGUF loading, chat templates, tokenization, CPU decoding, cancellation callbacks.
- [Rust JNI library](https://github.com/jni-rs/jni-rs): Android calls into Rust without an HTTP boundary.

Build workflow: `android-offline.yml`. Cross-compiles llama.cpp with Android NDK
28.2, then Rust for aarch64-linux-android, packages both Rust and C++ runtimes,
assets, Java UI, signs the APK and verifies its signature/no-INTERNET manifest.
The build is debug-signed for personal sideloading, not a Play Store release.

Do not infer runtime/model quality from compilation alone: real-model device
inference and airplane-mode testing require a compatible phone and GGUF file.
