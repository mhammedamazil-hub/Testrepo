# Sourcebook

An independent, local-first research notebook with a **Rust server and CLI**, a responsive browser UI, and **bring-your-own AI**. Inspired by the source-grounded notebook workflow—not affiliated with Google, and not a complete NotebookLM clone.

## What is implemented

- Create, search, rename, delete and export notebooks.
- Add/select/remove pasted text, UTF-8 text/Markdown/CSV/JSON files, text-based PDFs, and public static web pages.
- Ask questions grounded in selected sources, with persistent conversations and clickable retrieved source excerpts.
- Save answers to notes, create notes, download source text and generated Markdown, export a full notebook as JSON.
- Studio: summaries, study guides, FAQs, briefings, timelines, flashcards, quizzes, mind-map outlines, data tables, **podcast scripts**, and **slide outlines**.
- Configurable OpenAI-compatible `/chat/completions` endpoint/model: hosted providers, OpenRouter-style gateways, Ollama or other local servers. No Gemini requirement. Native Anthropic/Gemini protocols need an OpenAI-compatible gateway.
- CLI commands for notebooks, source files/URLs, questions, generation, notes, export and deletion.
- Server-side API keys, token-protected API, URL-import SSRF controls, bounded uploads/responses, atomic JSON persistence, two-job AI concurrency limit.

Generated text is shown as plain, safe text (Markdown syntax is preserved in downloads). Flashcards and quizzes are generated documents, not interactive spaced-repetition/test engines. Citations are model-generated references to retrieved excerpts, **not automatically fact-checked claims**.

## Run

Requires a current stable Rust toolchain and network access to crates.io for the initial build. No Node/npm is needed for Sourcebook itself. The browser assets are embedded in the Rust executable.

```sh
# Set these in your shell; .env files are NOT automatically loaded.
export SOURCEBOOK_TOKEN='replace-with-a-random-secret-at-least-16-characters'
export AI_BASE_URL='https://api.openai.com/v1'
export AI_MODEL='your-model-name'
export AI_API_KEY='your-key'  # never commit this
cargo run -- serve
```

Open `http://127.0.0.1:3000`, enter `SOURCEBOOK_TOKEN`, create a notebook and add sources. Storage operations work without an AI provider; asking/generating requires a configured model. The token is stored only in browser session storage, not local storage. Disconnect clears it and the visible workspace.

Local Ollama example (install/run Ollama separately and pull your chosen model):

```sh
export AI_BASE_URL='http://127.0.0.1:11434/v1'
export AI_MODEL='llama3.2'
unset AI_API_KEY
cargo run -- serve
```

### Arena / remote deployment

```sh
cargo run -- serve --bind 0.0.0.0:3000
```

Frontend calls use same-origin relative URLs and accept the preview hostname without a host allowlist. **The access token is required even on localhost.** Use HTTPS through a reverse proxy for remote access. This is a trusted-owner, single-user server; the token grants access to all notebooks. Do not deploy as a public multi-user service. The service is not currently running in Arena: the sandbox has no Rust toolchain and blocks Rust distribution/crate download hosts. A GitHub Actions workflow builds/tests on an unrestricted runner and uploads a Linux executable when successful.

### CLI

Run these while the server is running, with the same `SOURCEBOOK_TOKEN` environment variable:

```sh
cargo run -- list
cargo run -- create 'Biology research'
# Use the notebook UUID from create/list:
cargo run -- source NOTEBOOK_ID --file paper.pdf
cargo run -- source NOTEBOOK_ID --link https://example.org/article --title 'Article'
cargo run -- ask NOTEBOOK_ID 'What are the key findings?'
cargo run -- generate NOTEBOOK_ID study-guide --instructions 'Write for beginners'
cargo run -- note NOTEBOOK_ID 'My thought' 'Compare the two methods.'
cargo run -- export NOTEBOOK_ID --output notebook.json
cargo run -- delete NOTEBOOK_ID --yes
```

Repeat `--source SOURCE_ID` on `ask` or `generate` to limit retrieval. CLI defaults to all sources if no `--source` is supplied. Browser requires at least one explicitly selected source. For another server, set `SOURCEBOOK_URL` or pass `--url`. Errors return nonzero exit codes; successful CLI output is JSON.

## Retrieval and data handling

Documents are split into Unicode-safe, overlapping 1,200-character excerpts. Chat ranks excerpts using normalized lexical term overlap and sends at most 12 to the model, plus the last eight conversation messages. Studio tries to cover one excerpt per source (up to 12) before filling with ranked excerpts. This is a lightweight lexical RAG baseline, **not semantic embeddings or exhaustive whole-library analysis**. Selected sources restrict the new retrieval; historical conversation text is still included in follow-up chats. Clear history when you need strict separation from past source selections.

Your configured provider receives retrieved excerpts, titles, recent chat and the request. Original sources, notes and results persist in `data/notebooks.json` (`SOURCEBOOK_DATA` overrides it). The provider key is read from the environment, never persisted or returned by the configuration API. Use only one server process per data file; there is no cross-process locking. Keep backups. Notebook exports contain all source text and history and should be treated as sensitive. Sources are untrusted input: instruction isolation reduces but does not eliminate prompt injection. This app cannot execute AI tool calls.

Limits: 100 sources/notebook, 2 MB extracted text/source, 10 MB PDF, 16 MB request body, 12 retrieved excerpts/request, 4,096 requested output tokens. Providers may impose additional limits. PDF extraction is CPU-bound and requires selectable text; complex PDFs may fail. This initial local-owner build has no per-user quotas or hardened parser subprocess isolation. Do not expose it to untrusted uploaders.

URL imports reject private/local/reserved destinations, pin validated DNS addresses, disable proxies and redirects, allow only HTTP(S) on ports 80/443, and limit response size/time. Paste a redirect's final URL directly. Website imports do not run JavaScript, sign in, bypass paywalls, or fetch external assets. Workspace network restrictions still apply.

## Feature boundary / next work

| Area | Status |
| --- | --- |
| Notebook/source CRUD, notes, export, text/PDF/public URL ingestion | Implemented; verify build/test results before use |
| Cited chat with your own model | Implemented; provider integration must be tested with your endpoint |
| Eleven text studio formats | Implemented through real provider calls, no fake generated results |
| Actual audio/video, slides/PDF/PNG exports and infographics | Not implemented; scripts/outlines are not media files |
| OCR, YouTube transcription, Drive sync, web research/search | Not implemented |
| Sharing, accounts, collaboration, mobile APK/desktop installers | Not implemented |
| Embedding search, interactive quizzes/cards, streaming, jobs/cancellation | Not implemented |
| Notebook import/restore | Not implemented; JSON export and file backups only |

This is a first working implementation scope, not “every feature.” No proprietary APK/EXE/DEB was downloaded or decompiled. Feature research used the accessible [notebooklm-py README](https://github.com/teng-lin/notebooklm-py), an unofficial feature reference. No Google login, hidden Google endpoints, or undocumented Google backend is used.

## Tests and builds

```sh
cargo fmt --all
cargo test --all-targets
cargo clippy --all-targets
cargo build --release
node --check web/app.js  # optional static JS syntax check
```

Tests cover Unicode chunking, source ranking/filtering, private network rejection, authentication, notebook/source/note persistence, export, invalid source inputs, and chat/studio with an in-process mock OpenAI-compatible provider. No real API key is needed for tests. `.github/workflows/rust.yml` runs these checks and uploads `sourcebook-linux-x64`. Only the Linux target is packaged at present.

## Existing REA tools

The original REA workspace setup remains alongside Sourcebook. See [REA setup](docs/rea-setup.md). REA is useful for authorized analysis but is **not a runtime dependency** of this application. `npm run rea -- --help` uses that separate setup. Optional decompiler installation is still blocked by release-asset network restrictions here.

The HTTP endpoint reference is in [docs/API.md](docs/API.md). Browser behavior tests use `jsdom` with a mock API (they do not verify a running Rust server):

```sh
npm ci --ignore-scripts --omit=optional --no-audit --no-fund
npm run test:web
```

The three browser tests cover authentication headers/library navigation, source upload and selected-source chat, safe rendering of hostile model/citation text, and disconnect cleanup. `.github/workflows/web.yml` runs these independently of the Rust build.
