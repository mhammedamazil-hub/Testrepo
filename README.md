# Sourcebook · Rust research notebooks

An independent, local-first NotebookLM-style research app. **The server, provider calls, ingestion, persistence, CLI, study validation, grading and media handling are written in Rust.** The embedded browser client uses HTML/CSS/JavaScript. Not affiliated with Google; this is a substantial alternative, not a claim of complete proprietary-feature parity.

## Standalone Android APK — embedded Rust, your choice of AI

The standalone APK embeds **Rust + optional llama.cpp** in the same Android
process: **no external workspace server, localhost listener or server token**.
It now supports **direct API keys, multiple providers and per-task assignments**,
plus a redesigned library/workspace with persistent System / Light / Dark themes.
**API use does not require GGUF.** Optional bundled local inference currently
supports compatible GGUF weights only; other offline model runtimes are not implemented.

This hybrid revision **requests INTERNET permission** for selected APIs and website
imports. It supersedes the previous strictly offline-only design. ARM64 Android 9+;
model weights are not bundled. [Installation, privacy, current limits and build details](docs/OFFLINE-ANDROID.md).
The separate older server-connected Android client remains available.

## Features

- **Notebooks:** create, search, rename, delete, full JSON export and restore into a new notebook.
- **Sources:** paste text; upload text/Markdown/CSV/JSON, text-based PDFs and DOCX; import public static webpages. Select sources, preview/download extracted text, edit or delete them, generate a source guide with key topics and suggested questions.
- **Chat:** source-grounded questions and follow-ups, persistent history, clickable retrieved evidence, save answers to notes.
- **Notes:** create/edit/delete notes, download Markdown, browser print/save as PDF.
- **Studio:** summaries, study guides, FAQs, briefings, timelines and podcast scripts; **interactive flashcards with persisted known/review state**, **multiple-choice quizzes graded in Rust with explanations**, expandable **mind maps**, navigable **slide decks** with speaker notes and print layouts, **data tables with CSV export**.
- **Audio:** actual MP3 audio overviews (single narrator) using your provider's speech endpoint; playback/download in the UI. Audio/video uploads can be transcribed into sources using a configured transcription endpoint.
- **Sharing:** revocable, unguessable read-only links. Explicitly enabling sharing exposes **all** sources, notes, history, materials and audio in that notebook to anyone with the link. Shared users cannot mutate owner data; quiz practice in shared views is local and unsaved.
- **CLI:** manage notebooks, add sources, ask, generate, save notes, restore/export, review quizzes/cards, generate source guides, download structured files/MP3, enable/revoke sharing.
- **Bring your own AI:** multiple OpenAI-compatible, Gemini and Anthropic providers, with separate assignments per task. Optional local/native providers; no required GGUF or Google login for API use. Owner-only Settings saves redacted configuration and keys with restricted file permissions (not custom encryption).
- **Video research:** Android can send public YouTube segments directly to a compatible Gemini vision model, or sample up to eight frames from a chosen device video using Android’s decoder. No audio is analyzed in the local-frame route. Desktop yt-dlp/FFmpeg remains an optional separate path; Instagram downloading is not bundled.
- **NIE source-only intelligence:** notebook-aware explanations, evidence and synthesis under a strict no-external-knowledge/no-browsing policy. Models still use learned language abilities; prompts cannot erase training or guarantee compliance.
- **Source discovery:** explicit notebook-title Wikipedia search with add-to-notebook actions; search results are not evidence until imported.
- **Experimental 3D shelf:** keyboard/touch notebook selection, persistent List fallback and reduced-motion-respecting transitions. Source badges use local assets, not third-party favicons.
- **Motion graphics:** validated timed scenes with an animated typography storyboard preview and JSON export, not rendered MP4.

Studio JSON is parsed into typed Rust structures and validated before saving. The client builds study views using safe DOM text nodes, not provider-generated HTML. Older Markdown-only materials remain readable.

## Start

Requires a current stable Rust toolchain and network access to crates.io for the initial build. Browser assets are embedded in the executable; Node/npm is **not** required to run Sourcebook.

```sh
# .env files are NOT loaded automatically. Set variables in your shell.
export SOURCEBOOK_TOKEN='replace-with-a-long-random-secret-at-least-16-characters'
export AI_BASE_URL='https://api.openai.com/v1'
export AI_MODEL='your-model-name'
export AI_API_KEY='your-key' # never commit it or paste it into chat
cargo run -- serve
```

Open **http://127.0.0.1:3000** and enter `SOURCEBOOK_TOKEN`. Data is stored in `data/notebooks.json`, or set `SOURCEBOOK_DATA`. No provider is included. API fees depend on your provider. Storage and manual notes work without an AI model; AI actions return honest configuration errors rather than fabricated output.

For Arena or a remote server:

```sh
cargo run -- serve --bind 0.0.0.0:3000
```

Browser API calls are same-origin relative URLs. Put remote deployments behind HTTPS and an access-controlled reverse proxy. Token authentication is mandatory even on localhost. The token is held in browser session storage and can be cleared with Disconnect. Saved provider keys are never returned to the browser. New keys entered in Settings are sent to the Rust core over the authenticated connection; use HTTPS remotely. `.env.example` lists all settings.

### Local AI

Install/run Ollama separately and pull your chosen model:

```sh
export AI_BASE_URL='http://127.0.0.1:11434/v1'
export AI_MODEL='llama3.2'
unset AI_API_KEY
cargo run -- serve
```

Models must support text chat completions; structured study generation requires reliable JSON output. Settings also supports native Anthropic/Gemini wire protocols without a gateway. A localhost endpoint is on the host/device running Rust. Some models are much better than others at citations and schemas.

### Real speech and transcription

In Settings assign dedicated OpenAI-compatible **speech** and **transcription** providers/models, or use these environment fallbacks. Set only models the chosen provider actually supports:

```sh
export AI_TTS_MODEL='your-speech-model'
export AI_TTS_VOICE='alloy' # or a voice supported by your provider
export AI_TRANSCRIPTION_MODEL='your-transcription-model'
```

`AI_BASE_URL` must expose OpenAI-compatible `/audio/speech` (MP3 response) and `/audio/transcriptions` (multipart upload, JSON `{text:...}` response). A chat-only provider such as standard Ollama will not automatically provide these services. Audio generation uses a grounded single-narrator script of at most 4,000 characters, not a two-host or real-time interactive podcast. Supported uploads: MP3, WAV, M4A, MP4, WebM, OGG, max 10 MB. This transcribes audio; it does **not** analyze video frames. Only the transcript is kept, not the uploaded audio/video. No OCR or downloader is bundled; the separate desktop video-link pipeline requires installed yt-dlp and FFmpeg and analyzes sampled frames, not this audio upload.

MP3 files live beside the database under `notebooks.media/`. Back up both the database and media directory. Database/media operations are not a cross-file transaction; an interrupted generation can leave an unused private MP3. JSON export/restore includes scripts/materials but **not MP3 bytes**; download audio separately. Deleting a notebook or audio artifact removes its media file during normal operation.

## CLI examples

With the server running and the same `SOURCEBOOK_TOKEN`:

```sh
cargo run -- create 'Biology research'
cargo run -- list
cargo run -- source NOTEBOOK_ID --file paper.pdf
cargo run -- source NOTEBOOK_ID --file lecture.mp3
cargo run -- source NOTEBOOK_ID --file notes.docx
cargo run -- source NOTEBOOK_ID --link https://example.org/article --title Article
cargo run -- ask NOTEBOOK_ID 'What are the key findings?'
cargo run -- generate NOTEBOOK_ID quiz --instructions 'Beginner level'
cargo run -- generate NOTEBOOK_ID audio-overview --instructions 'Brief and clear'
cargo run -- guide NOTEBOOK_ID SOURCE_ID
cargo run -- review NOTEBOOK_ID QUIZ_ARTIFACT_ID --answers 0,1,2,0
cargo run -- card NOTEBOOK_ID CARDS_ARTIFACT_ID 0 --known
cargo run -- download NOTEBOOK_ID ARTIFACT_ID --audio --output overview.mp3
cargo run -- download NOTEBOOK_ID ARTIFACT_ID --output material.json
cargo run -- share NOTEBOOK_ID
cargo run -- share NOTEBOOK_ID --revoke
cargo run -- export NOTEBOOK_ID --output notebook.json
cargo run -- import notebook.json
cargo run -- delete NOTEBOOK_ID --yes
```

Repeat `--source SOURCE_ID` on ask/generate to restrict retrieval. Omitted/empty IDs mean all sources in the API/CLI. The UI requires at least one selected source. Set `SOURCEBOOK_URL` or `--url` for another server. Quiz answers/card indexes are zero-based. Successful CLI output is JSON except binary downloads; failures return nonzero exit codes. `--known` marks a flashcard known; omit it to mark study-again.

## Grounding and safety boundaries

- Sources are chunked into Unicode-safe, overlapping 1,200-character excerpts. Chat uses lexical relevance and a maximum of 12 excerpts. Studio covers up to one excerpt per source before relevance fill (max 12). This is **not** exhaustive whole-document analysis or semantic-embedding retrieval.
- Recent conversation text (last eight messages) is also sent to the provider. Clear history to avoid context from older source selections. Newly retrieved context uses the selected sources only.
- Citation markers are model-generated; retrieved excerpts are evidence candidates, **not automatically verified claims**. Always inspect them. Models can hallucinate even with grounding instructions.
- Your provider receives relevant source excerpts, titles, recent chat and your request. For transcription it also receives the uploaded media. For speech it receives the generated script.
- Source instructions are treated as untrusted data; this reduces but does not eliminate prompt injection. The app cannot execute AI tool calls.
- Private/local URL imports, non-HTTP schemes, credentialed URLs, proxies, redirects and non-80/443 ports are blocked. Validated DNS results are pinned to prevent rebinding. No JavaScript execution, paywall bypass, Google login or hidden Google backend endpoints.
- Owner token grants full access to every notebook. This remains a **trusted-owner, single-user** server, not a multi-tenant service. Shared links intentionally grant broad read access to the selected notebook; use them carefully and revoke when finished.
- One server process per data file, atomic JSON replacement with restrictive permissions. No cross-process database locking or full multi-file crash recovery. Keep backups.
- Limits: 100 sources/notebook, 2 MB extracted source text, 10 MB PDF/DOCX/audio/video, 16 MB request body/restore, 12 context excerpts, 4,096 requested generation tokens, two concurrent AI/media requests, 120-second provider timeout, 20 MB MP3 output. Complex/scanned/encrypted PDFs may fail. DOCX extracts main-document text, not drawings/comments/embedded files.

## Feature parity: what is still not implemented

Do **not** mistake the current implementation for a complete clone:

- Google Drive OAuth/sync, Google Docs/Sheets integration, YouTube transcript fetching, web search/deep research.
- OCR/image understanding, embedding/vector retrieval, streamed responses and persistent background job queues.
- Generated videos, rendered infographics, native PPTX export, two-host/interactive audio. PDF export currently uses the browser's print system, not a Rust PDF renderer.
- Multi-user accounts, edit collaboration, enterprise administration, native desktop installers. Separate offline and server-connected Android APKs are available.

Full private-service parity requires separate integrations, infrastructure and provider capabilities; simply installing REA cannot recover Google's backend. Feature research used the accessible [notebooklm-py feature reference](https://github.com/teng-lin/notebooklm-py). No proprietary APK/EXE/DEB was downloaded or decompiled.

## Tests / build status

```sh
cargo fmt --all
cargo test --all-targets
cargo clippy --all-targets
cargo build --release
# Optional browser behavior tests:
npm ci --ignore-scripts --omit=optional --no-audit --no-fund
npm run test:web
```

The v0.2 expansion passed GitHub Rust build/tests, and the mobile update has ten passing browser behavior tests. Rust tests cover typed study validation, quiz/card grading, editing, restore with ID remapping, share revocation, DOCX extraction, real speech/transcription HTTP protocol handling with mock providers, media authorization and cleanup, plus the original CRUD/auth/retrieval tests. Check the latest GitHub Actions run for the exact tested revision. Real hosted AI/media generation has not been tested with your credentials.

This workspace has no Rust toolchain and blocks the Rust download hosts, so no live Rust server is running here. GitHub Actions builds on an unrestricted runner and uploads a Linux executable after a successful run. Workflows: `.github/workflows/rust.yml` and `web.yml`.

See [HTTP API reference](docs/API.md). Existing independent REA setup is documented in [docs/rea-setup.md](docs/rea-setup.md); REA is not a Sourcebook runtime dependency.

## Android APK / mobile

The Android client now lives in [`android/`](android/) with a dedicated [APK build workflow](.github/workflows/android.yml). It connects to your running Rust server and exposes the existing app features through mobile **Sources / Chat / Studio** tabs, native document picking/saving, audio playback/download, and Android print/PDF. That older client is **not** the offline APK; choose the separate Rust+GGUF build above for no-server use. See [Android setup and download instructions](docs/ANDROID.md) for requirements, signing, LAN/HTTPS connection and limitations.

The v0.2 Rust expansion subsequently passed GitHub build/tests. The mobile update has **10 passing local browser tests**, including tab switching and native save/print bridge contracts. APK compilation, pure-Java URL-policy tests, signing and signature verification also passed [the Android build](https://github.com/mhammedamazil-hub/Testrepo/actions/runs/42487957011). Physical-device testing is still required.

### Astryx interface (0.7)

The app now bundles **Meta Astryx** React 19 components, with a local Sourcebook
 theme derived from Astryx Matcha: provider settings, per-task routing, device and
 appearance controls, library actions, view selector, and Studio actions. The
 notebook workspace and study viewers retain their existing interface; this is
 an incremental integration, not a claim that every screen has been migrated.
 Light, dark and system modes use the same theme. Fonts and UI assets are local;
 no CDN or font download is needed by the APK.

After editing `ui/` or `src/themes/sourcebook/`, run `npm ci --ignore-scripts`,
 `npm run build:web`, `npm run check:design` and `npm run test:web`. Commit the
 generated `web/astryx.js`, `web/astryx.css`, theme outputs and license notices.
 Rust and Android consume those prebuilt assets without requiring Node at runtime.
 The Astryx source doctor may flag bridge classes and CSS imports: these connect
 the incremental React islands to the existing native dialog and legacy layout.
 API providers still receive selected source content when invoked; local UI assets
 do not make remote model calls offline.
