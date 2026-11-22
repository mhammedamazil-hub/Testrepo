# PHASE1_AUDIT — Reality Engine Phase 1 Repository Audit

## Audit Date
2026-11-20

## Auditor
Principal Game-Engine Architect

## Repository State

### Branch
- Current: `arena/67bc2899-testrepo`
- Base: `a12b75d8d34ecd20063b4f4ec62966e6f8c0aba8` (origin/main)
- Status: Active, working directory clean except untracked files

### Existing Python Platform (Universal Game Engine v0.1.0)

| Component | Path | Status | Reusable? |
|-----------|------|--------|-----------|
| CLI | `universal_engine/cli.py` | IMPLEMENTED, 63 tests pass | YES — extend with `reality_*` commands |
| MCP Server | `universal_engine/mcp_server.py` | IMPLEMENTED, JSON-RPC 2.0 stdio | YES — extend with `reality_*` tools |
| Core Data Model | `universal_engine/core.py` | IMPLEMENTED (Project, Scene, ObjectDef, Transform) | YES — extend for Reality Engine format |
| Blender Adapter | `universal_engine/adapters/blender.py` | INTERFACE ONLY (UNAVAILABLE) | PARTIAL — replace with Reality Engine Blender addon |
| Godot Adapter | `universal_engine/adapters/godot.py` | IMPLEMENTED (.tscn/.gd generation) | YES — keep, do not remove |
| Tests | `tests/` | 63 tests, all passing | YES — extend with Reality Engine tests |
| pyproject.toml | `pyproject.toml` | Python package config | YES — extend for C++ build |
| Docs | `docs/` | VISION, ROADMAP, CAPABILITIES, etc. | YES — extend |

### Dependencies Already Available

| Dependency | Version | Source | Notes |
|------------|---------|--------|---------|
| g++ | 12.2.0 | System | C++20 support partial (no concepts, no modules) |
| cmake | 4.4.5 | pip install | Installed |
| Python 3 | 3.11.2 | System | bpy NOT available |
| git | system | System | Working |
| Blender source | cloned | `blender-source/` | 446MB, shallow clone |
| Jolt Physics | cloned | `jolt-physics/` | 55MB, shallow clone |

### Dependencies NOT Available (and cannot install without root)

| Dependency | Required For | Blocker |
|------------|--------------|---------|
| SDL3 | Windowing, input | No root, no .deb packages |
| Vulkan headers | Graphics backend | No root, no GPU, no dev headers |
| python3-dev | Blender Python C API | No root |
| libboost-dev | ECS library alternative | No root |
| Blender binary | bpy, headless rendering | Cannot build (3.8GB RAM, no root) |

### Workaround Strategy

- **SDL3**: Download source from GitHub, build from source with cmake (no root needed, install to local prefix)
- **Vulkan**: NOT available. Implement a clearly separated headless simulation path with a renderer interface. Document Vulkan as PLANNED for Phase 2.
- **ECS**: Implement a lightweight custom ECS in C++20 (no external dependency needed). Document EnTT/Flecs as evaluated alternatives.
- **Blender addon**: Write Python addon that works when Blender is installed. Cannot test locally (no bpy). Document as UNTESTED LOCALLY.

### What Can Be Reused

1. **CLI argument parser pattern** — extend `build_parser()` with `reality` subcommand
2. **MCP server JSON-RPC 2.0 framing** — extend `TOOL_SCHEMAS` and `HANDLERS` with `reality_*` tools
3. **Project/Scene data model** — extend `core.py` with Reality Engine structures
4. **Result/error pattern** — `ok_result()` / `error_result()` used consistently
5. **Exit code convention** — 0/1/2/3/4 already established
6. **Godot adapter** — KEEP. Do not remove. Documented technical reason: Godot remains a supported runtime target alongside Reality Engine.

### What Needs Modification

1. `universal_engine/core.py` — Add Reality Engine project/scene format structures alongside existing universal format
2. `universal_engine/cli.py` — Add `reality` subcommand group with all `reality_*` operations
3. `universal_engine/mcp_server.py` — Add 16 `reality_*` tool schemas and handlers
4. `universal_engine/adapters/blender.py` — Update to reference Reality Engine Blender addon

### What Needs Replacement (None — additive only)

- No existing functionality removed. Godot integration preserved.

### What Needs Creation

1. `engine/` — Native C++ engine source (13 modules)
2. `engine/CMakeLists.txt` — Build system
3. `blender_addon/` — Reality Engine Studio Blender addon
4. `runtime/` — Standalone runtime executable
5. `tests/reality/` — C++ unit and integration tests
6. Phase 1 documentation (4 files)

## Environment Constraints (Critical)

| Constraint | Value | Impact |
|------------|-------|--------|
| RAM | 3.8GB | Cannot build Blender from source. Cannot link large C++ projects with debug info. Use `-j1`, strip symbols. |
| CPU | 2 cores | Parallel builds limited. Use `-j2` max. |
| Disk | 19GB free | Sufficient for engine + dependencies + build artifacts. |
| Root | NO | Cannot apt-get install. All deps built from source to local prefix. |
| GPU | NONE | Vulkan renderer impossible locally. Headless simulation only. |
| Display | NONE | No windowing. SDL3 built headless or not at all. |
| Network | Restricted | Only github.com, codeload, npm, pypi accessible. |

## Reuse Decision Summary

| Decision | Rationale |
|----------|-----------|
| Keep Python CLI/MCP | Already working, tested, 63 tests pass. Extend rather than rewrite. |
| Keep Godot adapter | Working, validated via GitHub Actions. Reality Engine is an additional runtime, not a replacement. |
| Custom C++ ECS | EnTT/Flecs require external deps we cannot install. Lightweight custom ECS is sufficient for Phase 1. |
| Headless renderer | No GPU/Vulkan. Renderer interface defined, headless/no-op implementation for Phase 1. Vulkan planned Phase 2. |
| Jolt Physics from source | Cloned. Can build static lib. MIT license. |
| Blender addon (Python) | Cannot test without bpy. Write to Blender Python API spec. Document as untested locally. |
