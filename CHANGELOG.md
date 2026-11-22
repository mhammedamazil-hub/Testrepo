# CHANGELOG — Universal Game Engine

## 0.1.0 — Milestone 1 (committed)

### Implemented
- **Platform core**: Python 3 CLI + MCP server, adapter-based architecture, project/scene/asset data models.
- **CLI**: `universal-engine` entry point and `python -m universal_engine`. Commands: version, project (create/inspect/validate), scene (create/inspect), godot (project create, adapters), scene godot (create/inspect), node (create/modify), script (create), asset (import/inspect), physics (configure), game (create/run/stop/test), preview (capture), build, adapters, mcp (serve).
- **JSON mode**: `--json` flag on all commands for machine-readable output.
- **Exit codes**: 0 success, 1 general error, 2 validation error, 3 not implemented/unavailable, 4 backend missing.
- **Godot adapter**: Real Godot 4 integration — project.godot generation, .tscn scene generation (ext_resource/sub_resource/node format), .gd script generation, node create/modify, asset import, physics configure, game run/stop/test, preview capture, export. Honestly reports BACKEND_UNAVAILABLE when Godot binary is missing. Godot runtime execution VERIFIED via GitHub Actions.
- **Blender source code**: CLONED at `blender-source/` (446MB shallow clone from github.com). Build blocked: missing dev headers, no root, insufficient RAM. cmake installed via pip.
- **Blender adapter**: Interface ready in `universal_engine/adapters/blender.py` — reports UNAVAILABLE until Blender binary is built/installed.
- **Blender CLI commands**: 13 subcommands implemented and verified: `blender project create`, `blender scene create/inspect`, `blender object create/modify`, `blender mesh generate`, `blender material create`, `blender render`, `blender export`, `blender prefab create/instance`, `blender addressable register/resolve`, `blender light create`, `blender camera create`, `blender preview`. All support `--json`. bpy-dependent operations report BACKEND_UNAVAILABLE; universal JSON operations work without Blender.
- **Blender MCP tools**: 16 tools added to MCP server (blender_project_create, blender_scene_create, blender_scene_inspect, blender_object_create, blender_object_modify, blender_mesh_generate, blender_material_create, blender_render, blender_export, blender_prefab_create, blender_prefab_instance, blender_addressable_register, blender_addressable_resolve, blender_light_create, blender_camera_create, blender_preview_capture). Total MCP tools: 32.
- **MCP server**: Real JSON-RPC 2.0 server over stdio with Content-Length framing. 32 tools total (16 original + 16 Blender). All handlers call the same backend services as the CLI.
- **Playable test game**: `game create` generates a complete 3D platformer/collector game — ground plane, player character (movement/jumping/gravity), follow camera, 5 rotating collectibles, score UI, restart button, game manager. All generated via GDScript and .tscn files.
- **GitHub Actions**: ci.yml (CI testing), godot.yml (Godot validation with Xvfb), release.yml (game artifact generation). All workflows have push + workflow_dispatch triggers.
- **Godot Validation workflow run 44902553046: SUCCESS** — all 11 steps passed. Godot 4.7.2 launched, project loaded, main scene loaded, scripts compiled, game ran, smoke tests passed, preview capture executed.

### Tests
63 tests, all passing:
- tests/test_core.py (12): core unit tests including find_object_by_name
- tests/test_godot_adapter.py (25): Godot adapter file generation
- tests/test_cli_integration.py (12): CLI command integration
- tests/test_mcp_server.py (10): MCP server JSON-RPC communication
- tests/test_mcp_cli_consistency.py (4): MCP/CLI consistency and equivalence

### Documentation
MASTER_PLAN.md, PROJECT_STATUS.md, ARCHITECTURE.md, DECISIONS.md, TASKS.md, TEST_RESULTS.md, LIMITATIONS.md, CHANGELOG.md, RESEARCH_STATUS.md.
Docs: VISION.md, ROADMAP.md, CAPABILITIES.md, CLI_REFERENCE.md, MCP_REFERENCE.md, BLENDER_INTEGRATION.md.

### Research database
research/engines/{godot,bevy,blender,upbge,panda3d}.md, research/physics/{godot_physics,jolt,bullet,box2d,rapier}.md, research/coverage_matrix.md.

### License/audit
THIRD_PARTY_NOTICES.md, LICENSES/, DEPENDENCIES.md, INTEGRATION_AUDIT.md.

### Decisions recorded
- D-01: Godot 4 runtime (MIT)
- D-02: glTF/GLB asset exchange

## 0.1.1 — Reality Engine Phase 1 (committed)

### Implemented
- **Native C++ engine**: 15 modules with CMake build system — core, ecs, world, scene, assets, physics, rendering, platform, input, animation, audio, navigation, scripting, gameplay, diagnostics
- **Jolt Physics 5.7.0**: Real physics integration (NOT stubbed). Built from source, linked into engine. REALITY_HAS_JOLT compile definition gates real vs stub code paths.
- **Standalone runtime**: Reality Engine Runtime v0.1.0-phase1
Usage: reality_runtime <project_path> [options]
Options:
  --scene <name>     Scene to load (default: first scene)
  --frames <N>       Number of frames to simulate (default: 120)
  --headless         Run in headless mode (default)
  --diagnostics      Output diagnostics JSON on exit
  --help             Show this help — runs headless Jolt physics simulation, outputs entity states and JSON diagnostics. Operates without Blender.
- **Reality Engine CLI**: 16  commands — project-create, scene-create, scene-load, scene-export, entity-create, entity-inspect, entity-modify, component-add, component-remove, physics-configure, physics-simulate, runtime-launch, runtime-status, runtime-inspect, runtime-stop, asset-list, engine-diagnostics
- **Reality Engine MCP**: 16  tools (48 total MCP tools) with proper JSON-RPC 2.0 handling and error responses
- **Reality Engine Studio Blender addon**: 8 panels (Project, Scene, Entity, Component, Physics, Runtime, Export, Diagnostics) + 16 operators. Works with or without bpy.
- **Jolt physics verification**: 300+ step simulation test with ground + 6 dynamic objects, varying mass/restitution. Verified objects fall under gravity, collisions detected, ground stays stationary.
- **Data integrity tests**: 8 tests — save/reload, stable UUIDs, component persistence, schema versioning, invalid data handling, coordinate conversion, unit consistency, scene export. All passing.

### Tests
- 5 C++ unit tests (tests/reality/): test_ecs, test_transform, test_entity_id, test_scene, test_jolt_physics — ALL PASSING via ctest
- 8 data integrity tests (tests/reality/test_data_integrity.py) — ALL PASSING
- 16 CLI reality_* commands — ALL VERIFIED
- 16 MCP reality_* tools — ALL VERIFIED

### GitHub Actions workflows added
- engine-linux.yml — Linux build and test
- engine-windows.yml — Windows build and test
- engine-macos.yml — macOS build and test
- blender-addon.yml — Blender addon testing
- physics-validation.yml — Jolt physics validation
- mcp-integration.yml — MCP integration testing


- D-03: Python 3 platform language
- D-04: Godot Physics primary, Jolt candidate
- D-05: GDScript gameplay + Python tooling
- D-06: Blender as authoring foundation (not runtime)

### Bug fixes
- Fixed `game_test --quit-after 0` → `--quit-after 2` (Godot quits immediately with 0, preventing scene load)
- Fixed MCP `node_create`/`node_modify` to work with universal JSON scenes (not just Godot .tscn)
- Fixed `Scene.find_object` to add `find_object_by_name` (name-based lookup for node operations)
- Fixed CLI `run_cli` test helper to use `argv` instead of `list(args)`
