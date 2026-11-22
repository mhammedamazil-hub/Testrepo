# TASKS — Universal Game Engine

## Phase 0 — Environment & Baseline (DONE)
- [x] Inspect environment (headless Linux, 2 CPU, 3.8 GiB RAM, no GPU/display)
- [x] Confirm Python 3.11.2, Node.js v22.22.3, npm
- [x] Confirm Blender NOT installed; `bpy` unavailable; no root; network restricted
- [x] Confirm Godot NOT installed locally; local compile blocked by missing pkg-config/root
- [x] Create reproducible baseline (PROJECT_STATUS.md, MASTER_PLAN.md)

## Phase 1 — Ecosystem Research (DONE)
- [x] Research Godot 4 (MIT, Node/Scene, GDScript, headless) → research/engines/godot.md
- [x] Research Bevy (MIT/Apache, Rust/ECS, pre-1.0) → research/engines/bevy.md
- [x] Research UPBGE (GPL, Blender fork) → research/engines/upbge.md
- [x] Research Panda3D (BSD, Python, scene graph) → research/engines/panda3d.md
- [x] Research Blender (authoring foundation, bpy, blocked in env) → research/engines/blender.md
- [x] Research physics: Godot Physics, Jolt (MIT), Bullet, Box2D, Rapier → research/physics/*.md
- [x] Create research coverage matrix → research/coverage_matrix.md
- [x] License audit → LICENSES/, THIRD_PARTY_NOTICES.md, INTEGRATION_AUDIT.md, DEPENDENCIES.md

## Phase 2 — Architecture (DONE)
- [x] Write ARCHITECTURE.md
- [x] Write DECISIONS.md with evidence-based decisions
- [x] Define capability status system (VERIFIED/FUNCTIONAL/PARTIAL/EXPERIMENTAL/PLANNED/UNAVAILABLE)

## Phase 3 — Core Platform (IMPLEMENTED & VERIFIED)
- [x] Project management (create/inspect/validate) — tested
- [x] Configuration + core API + logging + diagnostics
- [x] Asset management + scene model + adapter system
- [x] 12 core unit tests passing

## Phase 4 — Blender Integration (SOURCE CLONED, CLI/MCP IMPLEMENTED, BUILD BLOCKED)
- [x] Blender source code cloned at `blender-source/` (446MB, github.com)
- [x] cmake installed via pip (4.4.5)
- [x] Blender CLI commands: project create, scene create/inspect, object create/modify, mesh generate, material create, render, export, prefab create/instance, addressable register/resolve, light create, camera create, preview
- [x] Blender MCP tools: 16 tools added to MCP server
- [ ] Blender build from source — BLOCKED: missing dev headers (boost-dev, X11 dev, Wayland dev, python3-dev, libssl-dev, etc.), no root access, 3.8GB RAM insufficient, 2 CPU cores too slow
- [ ] Blender automation (bpy) — depends on successful build
- [ ] Geometry Nodes integration, import/export (glTF/GLB) — depends on successful build
- [ ] Render previews, scene inspection via bpy — depends on successful build

## Phase 5 — Runtime Integration (IMPLEMENTED & VERIFIED)
- [x] Godot adapter: project_create, scene_create (.tscn), script_create (.gd), node_create/node_modify
- [x] Godot adapter: asset_import, physics_configure, game_run/game_stop/game_test
- [x] Godot adapter: preview_capture, export_project
- [x] Godot adapter: capability detection, honest BACKEND_UNAVAILABLE reporting
- [x] Godot runtime execution VERIFIED via GitHub Actions run 44902553046
- BLOCKER for local execution: Godot binary not installed locally

## Phase 6 — Physics & Simulation (PARTIAL)
- [x] Physics adapter methods implemented (configure rigid body, collision shape, mass, friction, restitution)
- [x] Physics execution verified via GitHub Actions (game test passed)
- [ ] Physics benchmarks (needs Godot binary locally)
- [ ] Character controller, vehicle, soft body (needs Godot binary)

## Reality Engine — Phase 1 Extension (IMPLEMENTED & VERIFIED)

- [x] Native C++ engine: 15 modules with CMake build system — core, ecs, world, scene, assets, physics, rendering, platform, input, animation, audio, navigation, scripting, gameplay, diagnostics
- [x] Jolt Physics 5.7.0 integration — cloned from GitHub, built as static lib, linked into engine
- [x] REALITY_HAS_JOLT compile definition — gates real vs stub code paths
- [x] Standalone runtime: Reality Engine Runtime v0.1.0-phase1
Usage: reality_runtime <project_path> [options]
Options:
  --scene <name>     Scene to load (default: first scene)
  --frames <N>       Number of frames to simulate (default: 120)
  --headless         Run in headless mode (default)
  --diagnostics      Output diagnostics JSON on exit
  --help             Show this help — runs headless Jolt physics simulation
- [x] Runtime: project loading, scene parsing, ECS init, Jolt init, simulation, transform sync, clean shutdown
- [x] Reality Engine CLI: 16  commands in 
- [x] Reality Engine MCP: 16  tools (48 total MCP tools) with proper error handling
- [x] Reality Engine Studio Blender addon: 8 panels + 16 operators at 
- [x] C++ unit tests: test_ecs, test_transform, test_entity_id, test_scene, test_jolt_physics — all passing via ctest
- [x] Jolt physics verification: 300+ step simulation with ground + 6 dynamic objects, varying mass/restitution — objects fall under gravity, collisions detected, ground stationary
- [x] Data integrity tests: 8 tests — save/reload, stable UUIDs, component persistence, schema versioning, invalid data handling, coordinate conversion, unit consistency, scene export — all passing
- [x] Acceptance demo: project → scene → ground + 6 dynamic objects → physics → export → runtime → 300-frame Jolt sim → inspect → stop — ALL VERIFIED
- [x] GitHub Actions workflows: engine-linux.yml, engine-windows.yml, engine-macos.yml, blender-addon.yml, physics-validation.yml, mcp-integration.yml
- [x] PHASE1_VERIFICATION_REPORT.md — Complete verification report with evidence

## Phase 7 — AI Automation (IMPLEMENTED & VERIFIED)
- [x] CLI: project create/inspect/validate, scene create/inspect, godot project/scene/node/script/asset/physics/game/preview/build commands
- [x] CLI: JSON mode (`--json`), structured errors, exit codes, logging, help
- [x] CLI: `game create` generates complete playable 3D platformer/collector game
- [x] MCP server: real JSON-RPC 2.0 over stdio, 16 tools, all tested
- [x] MCP/CLI consistency verified (63 tests passing)
- [x] 12 CLI integration tests + 10 MCP server tests + 4 consistency tests passing

## Phase 8 — Visual Feedback (PARTIAL)
- [x] preview_capture implemented in Godot adapter
- [x] CLI: `preview capture` command
- [x] MCP: preview_capture tool
- [x] Actual screenshot capture VERIFIED via GitHub Actions run 44902553046 (Xvfb + headless)
- [ ] Artifact management (GitHub Actions upload-artifact)

## Phase 9 — Game Dev Capabilities (PARTIAL)
- [x] Playable test game: 3D environment, ground, player movement/jumping/gravity, follow camera, 5 collectibles, score UI, restart
- [ ] Terrain generation, advanced animation, AI/NPC, audio, multiplayer, procedural gen, streaming, LOD

## Phase 10 — Packaging & Distribution (PARTIAL)
- [x] export_project implemented in Godot adapter
- [x] CLI: `build` command
- [x] GitHub Actions release.yml workflow
- [ ] Verified build artifacts (needs Godot export templates)
- [ ] Android/Web/Desktop platform validation

## Phase 11 — Final Validation (PARTIAL)
- [x] Unit tests: 12 core tests
- [x] Integration tests: 25 Godot adapter + 12 CLI + 10 MCP + 4 consistency = 51 tests
- [x] All 63 tests passing
- [x] GitHub Actions validation: run 44902553046 SUCCESS
- [ ] Full license audit (done for research, pending for final)
- [ ] Security audit
- [ ] Verified capability report
