# Sourcebook standalone Android · hybrid AI

**New direction:** the standalone APK retains its embedded Rust core, but now
supports direct provider APIs and explicit website imports. It **requests INTERNET
permission**. It is no longer an exclusively network-disabled build. Previous
0.4 offline-only artifact links are not the new hybrid release.

## Install and start

Download the latest successful **Build standalone Rust Android APK** workflow
artifact, extract `sourcebook-offline-arm64.apk`, and sideload it. The legacy
filename/package `app.sourcebook.offline` is retained for compatibility. It is
an experimental, debug-signed ARM64 build for Android 9+ / API 28, targeting 35.
A current System WebView is required. GitHub may require sign-in to download an
Actions artifact. Do not use the older **Build Sourcebook Android APK** artifact:
that is a separate, server-connected client.

1. Open the app. No server URL, server token, Termux, or localhost server is needed.
2. Open **Settings**, choose a provider preset, and **Add an AI provider**.
3. Enter your API key, select **Load models**, choose a returned model, and use
   **Test connection**. Testing sends a small billable request but does not save settings.
   Choose a **default** under **Task routing**, then **Save changes**. APIs do **not** require importing a GGUF model.
4. Add more providers/models if desired: assign flashcards to one, quizzes to
   another, chat/slides to others. Unassigned text tasks inherit the default.
5. Create a notebook, add sources, then use Sources / Chat / Studio.
6. Choose System / Light / Dark. System follows device appearance changes;
   explicit selection persists across sessions.

Supported wire protocols: OpenAI-compatible chat completions, native Gemini
`generateContent`, and native Anthropic `messages`. Presets include OpenAI,
Gemini, Anthropic, OpenRouter, Groq, DeepSeek, Mistral, xAI, Ollama and LM Studio.
They are editable endpoint templates, **not guarantees** that every service/model
supports every task. You must supply valid credentials/model IDs and check costs.
For speech/transcription assign dedicated OpenAI-compatible audio models; Gemini
and Anthropic text protocols do not implement their separate speech APIs here.

## Architecture and data

Java invokes `libsourcebook.so` through JNI. Rust dispatches Axum requests
**in memory**, without binding a TCP port. HTML/CSS/JS are packaged assets under
an intercepted `https://sourcebook.offline` origin; the UI never loads from a
remote server. Browser fetch is restricted to local API paths. Rust makes
explicit provider/website network requests, not the browser. No telemetry SDK,
automatic model download or Google login is included.

Notebooks and keys live in Android app-private storage. Keys are not stored in
browser local/session storage, returned by provider settings GET, or included in
notebook JSON exports. Configuration files have restricted permissions, **not
application-level key encryption or Android Keystore wrapping**. Source text or
frames leave the device when you run a cloud task or import a network source;
your chosen provider's privacy terms and charges apply. Localhost URLs refer to
the phone itself, not your computer. Back up notebooks before uninstalling or
clearing app data. Exports include source text, history and retained video frames;
treat them as sensitive. Download MP3 files separately from JSON exports.

Public sharing is disabled in this standalone build: without a reachable server,
a local share URL would not work on another device. Use notebook export/restore.

## Optional offline models — not required for API use

Manual storage, notes and existing study views work without Internet or models.
The packaged optional local engine is llama.cpp CPU inference. It currently
supports compatible **GGUF** decoder-only instruct weights with supported chat
templates, not `.task`, `.litertlm`, arbitrary `.bin` or another app's private
models. No non-GGUF engine has been implemented. If you do not want GGUF, use API
models; do not expect a different local format to work in this APK.

Use **Settings → App & device → Manage local AI → Choose GGUF** only if you want this optional engine. Start with
a small licensed 0.5B–1.5B Q4 model you have downloaded separately. The app copies
it into private storage (second-copy space required; max 8 GB and free-space
limit). Add a native provider and assign it as desired. No weights are bundled.

Four CPU threads, 4096 context, bounded prompts and 1024 output tokens;
cancellation and a five-minute inference limit. Larger models can exceed RAM.
The local text runtime cannot see images, transcribe audio or synthesize speech.
Reliable citation/structured JSON quality depends on the model. Invalid study
structures are rejected. Keep the app open; Android may kill background work.

## Video and motion graphics: precise scope

### Android: two supported paths (0.6 experimental)

1. **Public YouTube URL → Gemini.** Assign a Gemini model with video/YouTube
   support to **vision** in Settings. Enter a watch/short/youtu.be link, then a
   start/end segment (max 600 seconds, ending within 24 hours). Rust normalizes
   the video URL and sends Gemini `fileData` with requested `videoMetadata`
   offsets. The provider fetches this explicitly authorized source; this is not
   chat browsing. No yt-dlp, local download or external workspace server is used.
   Account/model support, private/age/region restrictions, provider token limits
   and billing apply. This yields labelled **generated video observations**, not
   a certified transcript; verify them in the original. No frames are retained
   for this direct-URL route. Real provider execution was not tested here.
2. **Choose video from device → native frame sampling.** Android's document
   picker gives temporary access to your file. MediaMetadataRetriever decodes up
   to eight scaled JPEGs (longest edge about 640px) from the first ten minutes.
   Rust sends those frames to the assigned vision API, keeps the sampled frames
   with the generated observations, and clearly labels approximate timestamps.
   **No audio is analyzed**, and sparse frames may miss events. Use a supported
   codec such as MP4/H.264; corrupt/unsupported files return errors. Keep the app
   open. Physical-device codec decoding and provider analysis remain untested.

Android still does not bundle Python, yt-dlp or FFmpeg, and **does not download
Instagram videos**. For Instagram, import a saved video you have permission to
use. No DRM/login bypass or hidden external processing server is included.

The desktop pipeline accepts public HTTPS YouTube/Instagram links, uses yt-dlp
without configuration/cookies/playlists, limits metadata duration to 10 minutes,
requests an 80 MB maximum file size, and verifies resulting size. Each command
has a 180-second timeout; download size checks are best-effort when metadata is
missing. FFmpeg extracts at most 8 JPEGs, about one per minute at width 640. An
assigned **vision-capable API model** receives these frames. Retained frames and
explicitly labelled model observations become a source. **No audio is analyzed,
not every frame is seen, and observations are not a transcript.** Sparse sampling
can miss important events. No login/DRM bypass is attempted; respect platform
terms and permissions. Temporary files are deleted on handled completion/error;
an abruptly killed desktop process may leave its private temporary directory.

Studio includes typed flashcards, quizzes, mind maps, slide decks/presentations,
data tables and written materials. **Motion graphic** creates a validated timed
scene storyboard with animated typography preview, not a rendered MP4, generative
video or a complete NotebookLM replacement. Structured JSON can be exported.

## Build and verification

Workflow `.github/workflows/android-offline.yml` cross-compiles the Rust library
and pinned llama.cpp with NDK 28.2 for ARM64, packages Java/assets/native libraries,
signs and verifies the APK, checks INTERNET permission and emits SHA-256.
The old `android-offline` feature/workflow filename identifies the standalone
architecture, not a promise of no networking. No listening server is added.

Browser tests cover appearance, provider editing, per-task assignments, safe
study rendering, mobile tabs, native export/print and ordered JNI chunking.
Rust tests exercise owner authorization, secret redaction/persistence, task
routing, study validation and offline boundaries. CI compilation/tests do not
prove that live provider credentials, platform downloads or physical-device
inference work. No physical phone or real model/API credentials were exercised
in this sandbox; those remain device acceptance tests.

References: [official Android runtime guide](https://github.com/ggml-org/llama.cpp/blob/7d7f0287530bc8981690f361d8c1627dbae1c99a/docs/android.md),
[pinned runtime C API](https://github.com/ggml-org/llama.cpp/blob/7d7f0287530bc8981690f361d8c1627dbae1c99a/include/llama.h),
[Rust JNI](https://github.com/jni-rs/jni-rs).


## 0.5.1 mobile refinement and provider troubleshooting

The old native top toolbar is removed. Reload, local-model management and local
cancellation are under **Settings → App & device**. AI connections, task routing
and device preferences are separate settings tabs with a pinned Save action.
The first new connection automatically becomes the default until you change it.
Endpoint/protocol/key removal live in an advanced disclosure, not the main form.

The UI uses quieter flat surfaces and document icons instead of a decorative AI
orb/gradients. Sources can be searched by title or extracted content without
changing selections. Answers have Copy; text inputs grow with your question.
Request errors remain inline, with Retry and a shortcut to connection settings.

If Gemini returns HTTP 400, the earlier generic message cannot identify the
account-specific cause. This revision shows a bounded structured provider message
with the configured credential/token-like strings redacted, plus appropriate
model/auth/quota guidance. Raw response bodies and headers are never shown.
**Load models** uses your provider's real list (Gemini filters for generateContent)
instead of guessing current model IDs. **Test connection** validates the native
wire protocol and selected model using a minimal request. Manual IDs remain
supported; model discovery is limited to the first page on some services.
Neither successful compilation nor mock-provider tests verify your real key,
project billing, region eligibility, or an individual provider's model access.


## 0.6 NIE, discovery and spatial UI

`src/nie-system.txt` contains the thirteen-section Notebook Intelligence Engine
policy with a mandatory **strict source-only override**. Chat, source guides and
study generation get the notebook title, inventory and current retrieved excerpts.
The optional constrained local engine uses a shorter equivalent policy to stay
within its token budget. The engine is instructed to explain and connect ideas
rather than paste paragraphs, distinguish inference from fact, cite real current
excerpts and admit insufficient evidence. It has no browsing/tool declarations.
The policy forbids external-memory facts and general-knowledge fallbacks, but a
prompt cannot erase pretrained weights or guarantee factual compliance. Check
citations. Retrieval is bounded; no claim of full-notebook processing is made.

**Discover sources** is a separate, explicitly user-triggered Wikipedia title
search implemented in Rust, not a model generating unverified URLs. Results are
search suggestions, not evidence or quality endorsements. Only **Add source**
fetches and imports a selected page. There is no automatic external search when
creating a notebook or answering questions. The empty conversation offers this
opt-in discovery action. This allows finding material without giving NIE browsing
tools. Availability of the live search service remains network dependent.

The library defaults to an experimental CSS 3D shelf with touch swipes, arrows,
keyboard navigation and an immediate persistent **List** fallback. Transitions
cover tabs, workspace entry, dialogs, messages, interactive surfaces and shelf
selection; system reduced-motion preference disables animation. Local PDF,
YouTube, Instagram, web, document, text, audio and video source badges do not make
favicon requests to trackers. The design uses no remote assets or canvas engine.

Validation includes mocked Gemini video/fileData schema and segment bounds,
invalid frame rejection, NIE policy tests, browser shelf fallback/native-picker
contracts and mobile/desktop Chromium layout checks. These are not proof of live
Gemini video support, decoder behavior on a physical phone, or search availability.
Reference: [Google Gemini video cookbook](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Video_understanding.ipynb).
