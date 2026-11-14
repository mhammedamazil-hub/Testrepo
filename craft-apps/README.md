# craft-apps — x86_64 headless CLIs, fetched by CLI

The upstream release tarballs are **not reachable from the sandbox** (`release-assets.githubusercontent.com`
→ `SSL_ERROR_SYSCALL`). GitHub Actions runners can reach them, so the runners do the download and this repo
holds the result.

## What is in the repo (small, committed)

```
craft-apps/
  bin/gridcraft-0.19.1-linux-x86_64-cli.gz     7.3 MB   ← runnable, verified
  bin/soundcraft-0.20.1-linux-x86_64-cli.gz    4.1 MB   ← runnable, verified
  fetch.sh                                     pulls the rest from the release
  manifest.md                                  app, tag, gz size, sha256
  manifest-assets.txt                          every asset on the release
  *-cli.version.txt / *-cli.help.txt           version + first 40 help lines for all 13 apps
```

```bash
cd craft-apps/bin && gunzip -c gridcraft-0.19.1-linux-x86_64-cli.gz > gridcraft-cli && chmod +x gridcraft-cli
./gridcraft-cli --version      # gridcraft-cli 0.19.1
./gridcraft-cli eval '=SUM(1,2,3,4)'   # 10
```

## What is on the release (too big for git)

`gh release view craft-apps-x86_64` → 52 assets, one `-cli.gz` (~531 MB total) per app, each with
`.sha256`, `.version.txt`, `.help.txt`. Fetch them anywhere with:

```bash
./craft-apps/fetch.sh                 # all 13 → ~/.local/opt/craft-apps/bin
./craft-apps/fetch.sh photocraft      # one app
```

| app | tag | cli gz |
| --- | --- | --- |
| photocraft | v0.23.1 | 57.1 MB |
| vectorcraft | v0.24.1 | 63.3 MB |
| filmcraft | v0.20.1 | 47.6 MB |
| lightcraft | v0.21.1 | 55.9 MB |
| pdfcraft | v0.21.1 | 43.5 MB |
| effectcraft | v0.24.1 | 36.9 MB |
| designcraft | v0.20.1 | 51.7 MB |
| figcraft | v0.18.1 | 42.2 MB |
| wordcraft | v0.18.1 | 48.1 MB |
| soundcraft | v0.20.1 | 4.1 MB |
| deckcraft | v0.18.1 | 44.1 MB |
| cadcraft | v0.20.1 | 29.3 MB |
| gridcraft | v0.19.1 | 7.3 MB |

The GUI binaries in each tarball are 90–190 MB each and are deliberately not carried — only `bin/*-cli`.
Licence: the upstream repos are Apache-2.0; these are unmodified republished binaries.

## Workflows

| workflow | purpose |
| --- | --- |
| `craft-bundle.yml` | re-download all 13 releases, gzip `bin/*-cli`, compute sha256, attach to the `craft-apps-x86_64` release, regenerate `craft-apps/manifest.md` + `fetch.sh` |
| `craft-inrepo.yml` | copy the two smallest CLIs into `craft-apps/bin/` (git-friendly payload) |
| `craft-demo.yml`, `craft-suite.yml`, `craft-sound.yml`, `craft-pdf-final.yml` | the earlier real-output runs (see `../craft-suite/RESULTS.md`) |
| `craft-sizes.yml` | regenerate `../craft-sizes.md` (payload measurements) |

Run any of them with `gh workflow run <file> -R mhammedamazil-hub/Testrepo`.
`craft-bundle.yml` takes `release_tag` (default `craft-apps-x86_64`) and `upload_raw=true` to also attach the
uncompressed ~1.3 GB of CLIs.
