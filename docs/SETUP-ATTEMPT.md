# Note on "npx ecc-universal@2.2.3 setup"

This command **was** downloaded and run. It fails in this environment by design, and the
equivalent install path was used instead. Full transcript is in `docs/ECC-USAGE.md`.

## What happens when you run it

```text
$ npx ecc-universal@2.2.3 setup
Error: Interactive setup requires a terminal. Pass --mode claude-plugin and the required flags.

$ npx ecc-universal@2.2.3 setup --mode claude-plugin --scope project --hooks standard --yes --json
{"error":{"code":"CLAUDE_NOT_FOUND",
  "message":"Claude Code is not installed or `claude` is not on PATH.",
  "phase":"inventory"}}
```

`setup` installs the `ecc@ecc` **Claude Code plugin**. It needs two things this sandbox does not
have: a TTY, and a `claude` binary on `PATH`. Neither is fixable from inside the repo.

## What was used instead

`ecc-universal` exposes a second, non-interactive installer that writes the same agents, skills,
rules, and commands into a target directory and records them in an install-state file:

```bash
npm i ecc-universal@2.2.3
npx ecc install --profile full --target claude-project --no-hooks
```

This is the project-scoped install (`.claude/` inside the repo) rather than the user-scoped
plugin install. It does not need Claude Code, does not need a TTY, and does not install a hook
runtime into an unattended sandbox.

## Result

```text
$ npx ecc doctor
- claude-project
  Status: OK
  Issues: none
Summary: checked=1, ok=1, warnings=0, errors=0
```

68 agents · 293 skills · 94 commands · 979 files · 8.7 MB at `.claude/`
