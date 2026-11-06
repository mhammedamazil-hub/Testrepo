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
