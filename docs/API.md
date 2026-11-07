# Sourcebook HTTP API

All `/api/*` endpoints require `Authorization: Bearer $SOURCEBOOK_TOKEN`.
JSON bodies/responses; errors use `{ "error": "human-readable message" }`.
The UI `/`, static assets, and `/health` are public. No CORS policy is added;
use same-origin browser requests or the CLI. Every token holder has owner access.

| Method | Route | Body / behavior |
| --- | --- | --- |
| GET | `/health` | Version and liveness, no secrets |
| GET | `/api/config` | Model identifier and availability booleans, never the API key |
| GET | `/api/notebooks` | Notebook metadata list |
| POST | `/api/notebooks` | `{ "title": "Research", "description": "optional" }` |
| GET | `/api/notebooks/:id` | Full notebook |
| PATCH | `/api/notebooks/:id` | `{ "title": "New title", "description": "optional" }` |
| DELETE | `/api/notebooks/:id` | Permanent deletion |
| GET | `/api/notebooks/:id/export` | Full JSON download |
| POST | `/api/notebooks/:id/sources` | See source formats below |
| DELETE | `/api/notebooks/:id/sources/:source` | Remove source; historical excerpts remain in saved answers |
| POST | `/api/notebooks/:id/chat` | `{ "question": "Key ideas?", "source_ids": ["uuid"] }` |
| DELETE | `/api/notebooks/:id/chat` | Clear conversation |
| POST | `/api/notebooks/:id/notes` | `{ "title": "Thought", "content": "Text" }` |
| DELETE | `/api/notebooks/:id/notes/:note` | Remove note |
| POST | `/api/notebooks/:id/generate` | `{ "kind": "summary", "instructions": "optional preferences", "source_ids": [] }` |
| DELETE | `/api/notebooks/:id/artifacts/:artifact` | Remove generated artifact |

Source bodies:

```json
{"title":"Notes","kind":"text","content":"Your text"}
```

```json
{"title":"Website","kind":"url","url":"https://example.org/final-page"}
```

```json
{"title":"Paper","kind":"pdf","content":"BASE64_ENCODED_PDF_BYTES"}
```

`kind: "markdown"` accepts a UTF-8 Markdown string. Text is extracted but no
original binary PDF is retained. PDF base64 content has the request-size limit
in addition to the 10 MB decoded-file limit. Source text must be nonempty and
at most 2 MB UTF-8. Scanned PDFs require external OCR first.

`source_ids` omitted or empty means all current sources. Unknown source IDs
are rejected. Chat returns a persisted assistant message with `content` and
`evidence`: `{number, source_id, title, excerpt}` entries correspond to the
model's context. They are retrieved evidence candidates, not proof that each
was cited or that generated factual claims are verified. The same structure is
saved on artifacts. Conversation updates detect concurrent chat/source changes
and return 409 instead of appending stale results. Retrying a generation after
a conflict may incur another provider charge.

Generations run synchronously, max two requests in flight, 120-second provider
timeout, no automatic retries. A client disconnect does not guarantee provider
cancellation. Use `summary`, `study-guide`, `faq`, `briefing`, `timeline`,
`flashcards`, `quiz`, `mind-map`, `data-table`, `podcast-script`, or `slide-outline`.
No generation has fake/demo output; an unconfigured/unavailable provider returns
an error and does not save a fabricated result.

## Rust v0.2 additions

All endpoints below require the owner bearer token **except `/api/share/*`**:

| Method | Route | Behavior |
| --- | --- | --- |
| POST | `/api/notebooks/import` | Notebook JSON export; creates new IDs, clears share links/review state/media references |
| PATCH | `/api/notebooks/:id/sources/:source` | `{title, content}` replaces extracted source text/title |
| POST | `/api/notebooks/:id/sources/:source/guide` | Generate source summary, topics and suggested questions |
| PATCH | `/api/notebooks/:id/notes/:note` | `{title, content}` edits note |
| POST | `/api/notebooks/:id/transcribe` | `{title, filename, content}` where content is base64 audio/video |
| POST | `/api/notebooks/:id/artifacts/:artifact/review` | Quiz: `{answers:[0,1,...]}`; flashcard: `{card:0, known:true}` |
| GET | `/api/notebooks/:id/artifacts/:artifact/media` | Authenticated MP3 bytes |
| GET | `/api/notebooks/:id/artifacts/:artifact/download` | CSV for data tables, JSON for typed study data, Markdown otherwise |
| POST | `/api/notebooks/:id/share` | Enable/get revocable read-only link; exposes all notebook data to token holders |
| DELETE | `/api/notebooks/:id/share` | Revoke link immediately for future requests |
| GET | `/api/share/:share_token` | Read-only full notebook; owner token not needed, share token required |
| GET | `/api/share/:share_token/media/:artifact` | Shared audio bytes with valid share token |

Source kind `docx` accepts base64 bytes, max 10 MB, bounded main-document XML extraction.
`transcribe` allows mp3/wav/m4a/mp4/webm/ogg filenames and requires `AI_TRANSCRIPTION_MODEL`.
`generate` additionally accepts `slides` and `audio-overview`. `audio-overview` requires
`AI_TTS_MODEL` and writes actual provider-returned MP3 bytes. Existing `slide-outline`
and `podcast-script` remain text-only formats.

Artifacts now have optional `data`, `progress` and `media` fields. `data.type` is one
of `flashcards`, `quiz`, `mind-map`, `slides`, `data-table`, and its schema is validated
in Rust. Study review validates indices and calculates quiz scores server-side. Owner
notebook reads include quiz answers, so this is a study tool, not a secure exam platform.
Shared-view practice does not write owner progress.

Notebook exports contain share tokens, so treat exports as private; restore deliberately
clears them and creates fresh IDs. Binary MP3s are not bundled into JSON. A restored audio
artifact retains its script but no longer claims an associated audio file. Historical
citations whose source was removed retain their excerpt but have no current source ID.
All responses use no-store/no-referrer/nosniff headers. Share URLs should still be treated
as bearer secrets and must not be placed in public logs or forwarded accidentally.
