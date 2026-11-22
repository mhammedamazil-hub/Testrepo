# MASTER_PLAN — Universal Game Engine

## Purpose
A unified, AI-native game development ecosystem built around Blender as the primary 3D content creation / scene authoring foundation, with Godot 4 as the primary game runtime, glTF/GLB as the asset exchange format, and a Python-based CLI + MCP server for AI/CLI/headless control.

This document is the single source of truth for the project's scope, phases, and status. It is maintained alongside `PROJECT_STATUS.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TASKS.md`, `TEST_RESULTS.md`, `LIMITATIONS.md`, and `CHANGELOG.md`.

## Environment (verified at project start)
- Host: Linux x86_64, 2 CPU cores, ~3.8 GiB RAM, no GPU, no display (headless)
- Python 3.11.2 + pip 23.0.1 (no `bpy` / Blender installed)
- Node.js v22.22.3 + npm 10.9.8
- No root access (cannot apt-install Blender)
- Outbound network restricted to: github.com, codeload.github.com, api.github.com, registry.npmjs.org, pypi.org, files.pythonhosted.org
- Godot 4.7.2 NOT installed locally; local compile blocked by missing pkg-config/root. Godot runtime validated via GitHub Actions (run 44902553046).

## Core decisions (see DECISIONS.md)
- Runtime: Godot 4 (MIT) — selected over Bevy (Rust/ECS, pre-1.0 churn, code-first) and UPBGE (GPL copyleft).
- Asset exchange: glTF / GLB between Blender (authoring) and Godot (runtime).
- Physics: Godot Physics (built-in) as primary backend tied to the runtime; Jolt Physics (MIT) noted as a dedicated-server/headless physics candidate.
- Scripting: GDScript (Python-like, AI-friendly) for gameplay; Python for the platform CLI/MCP core.
- Platform language: Python 3 (CLI + MCP server), no compiled engine code bundled.

## Phases
| Phase | Goal | Status |
|-------|------|--------|
| 0 — Environment & Baseline | Inspect env/hardware/software; confirm Blender (absent); create reproducible baseline | DONE |
| 1 — Ecosystem Research | Research engines/components; audit licenses; create research database | DONE |
| 2 — Architecture | Document runtime/physics/rendering/scripting/adapter/CLI/MCP decisions | DONE |
| 3 — Core Platform | Project management, config, core API, logging, diagnostics, asset/scene model, adapter system | IMPLEMENTED AND VERIFIED |
| 4 — Blender Integration | Blender automation (bpy), headless, scene/object/mesh/material, import/export, render previews | SOURCE CLONED, CLI/MCP INTERFACE IMPLEMENTED, BUILD BLOCKED |
| 5 — Runtime Integration | Godot adapter, scene conversion, launching, input, gameplay, physics, scripting, asset loading | IMPLEMENTED AND VERIFIED (adapter code + GitHub Actions runtime validation) |
| 6 — Physics & Simulation | Rigid bodies, collision, constraints, characters, simulation, testing, benchmarks | PARTIAL (adapter methods implemented; execution verified via GitHub Actions) |
| 7 — AI Automation | CLI, API, MCP, structured tools, previews, diagnostics | IMPLEMENTED AND VERIFIED (CLI + MCP server + consistency tests) |
| 8 — Visual Feedback | Screenshot capture, Blender/runtime previews, scene inspection, artifact management | PARTIAL (preview_capture implemented; VERIFIED via GitHub Actions with Xvfb) |
| 9 — Game Dev Capabilities | Terrain, animation, AI, audio, multiplayer, procedural gen, streaming, LOD | PARTIAL (playable test game implemented) |
| 10 — Packaging & Distribution | Linux/Android/Web/Desktop builds, platform validation | PARTIAL (export_project implemented; needs export templates) |
| 11 — Final Validation | Full tests, integration, runtime, Blender, CLI, MCP, headless, performance, license/security/docs audits | PARTIAL (63 tests passing; GitHub Actions validation successful) |

## Anti-fake rules (enforced)
- Every capability carries one of: VERIFIED, FUNCTIONAL, PARTIAL, EXPERIMENTAL, PLANNED, UNAVAILABLE.
- Blender-dependent items are UNAVAILABLE in this environment until Blender is installed and tested.
- No placeholder/mock implementations disguised as completed features.
- Tests verify actual behavior, not just success return values.

## Reality Engine (Phase 1 extension)

The Reality Engine extends the Universal Game Engine with a native C++ engine, standalone runtime, and Jolt Physics integration.

### Reality Engine components
- **Native C++ engine**: 15 modules with CMake build system
- **Jolt Physics 5.7.0**: Real physics integration, verified with 300-step simulation test
- **Standalone runtime**: Reality Engine Runtime v0.1.0-phase1
Usage: reality_runtime <project_path> [options]
Options:
  --scene <name>     Scene to load (default: first scene)
  --frames <N>       Number of frames to simulate (default: 120)
  --headless         Run in headless mode (default)
  --diagnostics      Output diagnostics JSON on exit
  --help             Show this help — runs without Blender
- **CLI**: 16  commands
- **MCP**: 16  tools (48 total)
- **Blender addon**: Reality Engine Studio — 8 panels, 16 operators
- **Tests**: 5 C++ tests + 8 data integrity tests — all passing

### Reality Engine GitHub Actions workflows
-  — Linux build and test
-  — Windows build and test
-  — macOS build and test
-  — Blender addon testing
-  — Jolt physics validation
-  — MCP integration testing

## GitHub Actions
- `.github/workflows/ci.yml` — CI testing (unit tests, CLI smoke tests, MCP smoke tests)
- `.github/workflows/godot.yml` — Godot runtime validation (download Godot, run generated project, headless test, preview capture) — RUN 44902553046: SUCCESS
- `.github/workflows/release.yml` — Game artifact generation (export builds with Godot export templates)
