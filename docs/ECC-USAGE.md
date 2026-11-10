# ECC usage log

Version: `ecc-universal@2.2.3`
Install date: 2026-11-10
Target: `claude-project` (repo-local `.claude/`)

## What was run

```bash
npm i ecc-universal@2.2.3
npx ecc install --profile full --target claude-project --no-hooks
npx ecc list-installed
npx ecc doctor
npx ecc status
npx ecc memory init --scope project
npx ecc memory save ...   # three memos
npx ecc memory search "lot gate"
```

### `npx ecc setup` — why it did not run here

The requested command was `npx ecc-universal@2.2.3 setup`. It was downloaded and executed, and
it refuses in this environment for two reasons, both by design:

```text
$ npx ecc-universal@2.2.3 setup --yes
Error: Interactive setup requires a terminal. Pass --mode claude-plugin and the required flags.

$ npx ecc-universal@2.2.3 setup --mode claude-plugin --scope project --hooks standard --yes --json
{"error":{"code":"CLAUDE_NOT_FOUND","message":"Claude Code is not installed or `claude` is not on PATH."}}
```

`setup` is a Claude Code **plugin** installer: it wants a TTY and a `claude` binary on PATH.
This sandbox has neither. The package supports a second path for exactly this case — the
selective-install executor — which writes the same agents, skills, rules, and commands into the
repo without needing Claude Code present. That is what was used, and it is the equivalent
install for the purposes of *using* ECC's content.

The package tarball was inspected before running it: sponsorships are passive links, the Itô
compute CLI is opt-in and not invoked, and hooks were declined with `--no-hooks` because an
unattended sandbox should not install a hook runtime.

## Verification output

```text
$ npx ecc list-installed
- claude-project
  Root: /home/user/Testrepo/.claude
  Profile: full
  Modules: 26
  Source version: 2.2.3

$ npx ecc doctor
- claude-project
  Status: OK
  Issues: none
Summary: checked=1, ok=1, warnings=0, errors=0
```

## Inventory actually on disk

| Item | Count |
|---|---:|
| Agents | 68 |
| Skills | 293 |
| Commands | 94 |
| Files under `.claude/` | 979 |
| Size | 8.7 MB |

## What was used for the company

| Component | Where it shows up |
|---|---|
| `customs-trade-compliance` | GRI 1 classification of 0904 11; Incoterms; the India export stack; penalty/prior-disclosure logic |
| `logistics-exception-management` | Three-axis severity model, eat-the-cost thresholds, claims windows |
| `quality-nonconformance` | NCR disposition sequence, RCA method selection, CAPA effectiveness rule (90 days / 3 lots / zero recurrence) |
| `inventory-demand-planning` | Croston/SBA for lumpy B2B demand, safety-stock service levels, slow-mover kill rule |
| `market-research` | Tier ladder, sourced market facts, explicit assumptions |
| `investor-materials` | One-source-of-truth rule, deck flow, bear case |
| `brand-voice` | The "name the grade, the lot, the test result" voice rules |
| `finance-billing-ops` | Evidence-first pricing, channel margin truth |
| `seo` | Page structure, structured data, Core Web Vitals |

## Memory vault

Three durable entries under `.ecc/memory/project/`:

- `decisions/` — why this company, and which alternatives were rejected
- `lessons/` — the driver-based model lesson (hard-coded numbers contradicted each other)
- `runbooks/` — the lot gate

They are labelled `[unreviewed]` by design: ECC treats tool-written memory as context, never as
policy.
