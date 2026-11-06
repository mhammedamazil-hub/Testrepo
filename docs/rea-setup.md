# REA workspace tools

Official upstream: https://github.com/morluto/rea. The workspace pins `rea-agents` 6.8.0 and local Node 22.23.4 in package.json. These are independent of the Rust Sourcebook application.

```sh
npm ci --omit=optional --no-audit --no-fund
npm run rea -- --version
npm run rea -- --help
npm run rea:doctor
npm run rea -- analyze-javascript-application /absolute/path/to/app --json
```

REA static JavaScript analysis was verified in an earlier turn. Native/Android providers are NOT installed. The installer below targets Linux x64 and verifies official release checksums:

```sh
npm run rea:install-android
npm run rea -- doctor --provider jadx --provider ghidra --json
npm run rea -- inspect-apktool-client --json
```

It selects Temurin JDK 21.0.13+9, jadx-headless-mcp 0.7.1, Apktool 3.0.3, and Ghidra 12.1.4. GitHub releases redirect to release-assets.githubusercontent.com, which this workspace blocks, so the installation attempt failed. Rerun only when release access is available. Tools stay in ignored `.tools/`. No commercial tools/licenses are supplied. ADB, emulators, Android SDK and instrumentation are not installed.

`.mcp.json` is a project-local REA stdio registration. It does not attach tools to an already-running Arena session. The matching upstream skill is bundled at `node_modules/rea-agents/skills/reverse-engineer-anything/SKILL.md`. The launcher automatically selects locally installed analysis tools when present.
