# ArtCraft suite — what actually works headless

Everything below was produced by GitHub Actions runners (`ubuntu-latest`, no GUI, no `DISPLAY`,
no X11/Wayland), downloading the **official open-source (Apache-2.0) releases** of the ArtCraft
"crafting apps" from `github.com/storytold/*` and running their own `*-cli` binaries.

Reproduce with: `Actions → craft-demo / craft-suite / craft-sound / craft-pdf-final → Run workflow`.

## Why the sandbox itself cannot do this

| Blocker | Evidence |
| --- | --- |
| `release-assets.githubusercontent.com` / `objects.githubusercontent.com` are unreachable from the sandbox | `curl` → `SSL_ERROR_SYSCALL`; `gh release download` → `EOF` |
| crates.io is blocked, and no Rust toolchain + no GTK/WebKit | `cargo` missing, `ldconfig -p \| grep webkit2gtk` → 0 |
| No display server | app binaries die with `neither WAYLAND_DISPLAY nor WAYLAND_SOCKET nor DISPLAY is set` |
| Node fetch in the sandbox does not trust the TLS chain | `UNABLE_TO_VERIFY_LEAF_SIGNATURE` (fixable with `NODE_EXTRA_CA_CERTS`) |

So: the sandbox orchestrates (`gh` + REST API), the runner executes. Artifacts come back
committed into `craft-demo/` and `craft-suite/`.

## Verified working headless CLIs

| App | Version | Headless entry point | Proof produced here |
| --- | --- | --- | --- |
| PhotoCraft | 0.23.1 | `photocraft-cli` (convert/info/run/batch/mcp/serve) | PPM → PNG → **PSD** → PNG round-trip, PNG → WebP, PNG → JPG (`photocraft-*.png/webp/jpg`) |
| VectorCraft | 0.24.1 | `vectorcraft-cli` (convert/run/mcp) | SVG → **PNG** + **PDF** (`vectorcraft-badge.*`) |
| GridCraft | 0.19.1 | `gridcraft-cli` (eval/convert/cat/check/run/mcp) | formula engine (`=SUM`, `=TEXT`), CSV → **XLSX** → **PDF**, round-trip check ok |
| FigCraft | 0.18.1 | `figcraft-cli` (info/export/convert/render/run/mcp) | SVG design → **PNG** + **PDF** (`figcraft-card.*`) |
| PdfCraft | 0.21.1 | `pdfcraft-cli` (info/render/text/edit/combine/extract/split/check/audit/mcp) | 2-doc **combine**, page **extract**, page **render** (640×400 @96dpi), **text** extraction (`FIGCRAFT`), faux-redaction audit → 0 findings |
| SoundCraft | 0.20.1 | `soundcraft-cli` (info/convert/run/script/commands) | WAV → **FLAC** + converted **WAV**, JSON audio metadata (`soundcraft-tone.*`) |
| FilmCraft, LightCraft, DeckCraft, DesignCraft, WordCraft, CADCraft, EffectCraft | releases 0.18–0.21 | `*-cli` present in the tarball (reports in `craft-demo/<app>/REPORT.md`) | CLI binaries + `--version`/`--help` verified on the runner |

GUI binaries (`photocraft`, `figcraft`, `pdfcraft`, `gridcraft`, …) confirm the headless claim by
**failing on the runner** with `WinitEventLoop … neither WAYLAND_DISPLAY nor …` — the `*-cli`
siblings do not need a display.

## The GUI route (option B), in principle

`packaging/` in `storytold/artcraft` + upstream CI already produce `.AppImage` / `.deb` / `.rpm` /
`.flatpak` per app; `xvfb-run` + a Tauri webview is the usual way to drive the desktop UI. That
needs `WEBKIT_DISABLE_COMPOSITING_MODE`-style flags and ~1.5 GB per app, and it is *not* what the
upstream automation surfaces expect. The supported route is the `*-cli` / MCP / `--control <PORT>`
JSON channel, which is what these runs prove out.

## Sibling tooling found on npm (unverified by us, no code executed)

`pi-craft` (`@blackbelt-technology/pi-dashboard-craft-apps`), `dsh-artcraft-plugin-*`,
`pi-artcraft-skills`, `@ninkch/dsh-artcraft` — wrappers that provision the same release binaries and
expose them over MCP. `pi-craft apps` lists all 13 apps offline; provisioning works wherever the
release CDN is reachable.
