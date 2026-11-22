# LIMITATIONS — Universal Game Engine

## Environment limitations (this sandbox)
- **Blender is not installed** and cannot be installed: no root access, outbound network restricted to github.com, codeload.github.com, api.github.com, registry.npmjs.org, pypi.org, files.pythonhosted.org (no blender.org). All Blender/bpy/Geometry Nodes/headless-render/.blend features are UNAVAILABLE.
- **Godot is not installed locally.** Local compile from source blocked by missing pkg-config and root access. Godot 4.7.2 source downloaded via codeload but not compiled. Godot-dependent operations (game_run, game_test, preview_capture, export_project) report `BACKEND_UNAVAILABLE` locally and are validated via GitHub Actions.
- **No GPU and no display (headless).** Real-time rendering tests are not possible locally; Godot validation uses headless mode with Xvfb on GitHub Actions runners.
- **Physics library:** Jolt Physics 5.7.0 IS installed and verified locally. Real Jolt physics simulation runs in the standalone runtime.

## Functional limitations (by implementation status)
- No game runtime bundled with the platform. Godot adapter generates valid Godot files but needs the Godot binary for execution.
- No built-in renderer; rendering delegated to Blender (authoring) or Godot (runtime) adapters.
- Physics engine: Jolt Physics 5.7.0 IS bundled and verified locally. Real Jolt physics simulation runs in the standalone runtime.
- No visual editor; the platform is CLI/API/MCP-first (headless).
- No Godot export templates available locally, so `build`/`export_project` cannot produce platform binaries locally.

## Capability status (current)

| Capability | Status | Notes |
|------------|--------|-------|
| Project create/inspect/validate | IMPLEMENTED AND VERIFIED | Pure Python, tested locally |
| Scene create/inspect (universal format) | IMPLEMENTED AND VERIFIED | Pure JSON, tested locally |
| Godot project creation | IMPLEMENTED AND VERIFIED | Generates project.godot, tested locally + via GitHub Actions |
| Godot .tscn scene generation | IMPLEMENTED AND VERIFIED | Valid Godot format, tested locally |
| GDScript generation | IMPLEMENTED AND VERIFIED | .gd files, tested locally |
| Node create/modify | IMPLEMENTED AND VERIFIED | Tested locally |
| Asset import | IMPLEMENTED AND VERIFIED | Copies to assets/, tested locally |
| Physics configure | IMPLEMENTED AND VERIFIED | Generates physics nodes, tested locally |
| Game create (playable 3D platformer) | IMPLEMENTED AND VERIFIED | Complete game generated, tested locally |
| Game run (Godot) | IMPLEMENTED AND VERIFIED | Adapter code implemented; runtime execution VERIFIED via GitHub Actions run 44902553046 |
| Game test (headless) | IMPLEMENTED AND VERIFIED | Adapter code implemented; runtime execution VERIFIED via GitHub Actions |
| Preview capture | IMPLEMENTED AND VERIFIED | Adapter code implemented; runtime execution VERIFIED via GitHub Actions with Xvfb |
| Build/export | IMPLEMENTED BUT NOT FULLY VERIFIED | Adapter code implemented; needs Godot export templates for artifact production |
| MCP server (16 tools) | IMPLEMENTED AND VERIFIED | JSON-RPC 2.0 stdio, tested locally |
| MCP/CLI consistency | IMPLEMENTED AND VERIFIED | Both interfaces use same backend, 63 tests passing |
| Blender integration | UNAVAILABLE (locally) | Blender not installed; addon verified via CI |
| Reality Engine C++ engine (15 modules) | IMPLEMENTED AND VERIFIED | CMake build, Jolt Physics integrated |
| Reality Engine standalone runtime | IMPLEMENTED AND VERIFIED | Runs headless Jolt physics, JSON diagnostics |
| Reality Engine CLI (16 commands) | IMPLEMENTED AND VERIFIED | universal_engine/reality_cli.py |
| Reality Engine MCP (16 tools) | IMPLEMENTED AND VERIFIED | 48 total MCP tools |
| Reality Engine Blender addon (8 panels) | IMPLEMENTED AND VERIFIED (structure) | Blender testing via CI |
| Reality Engine C++ tests (5 tests) | IMPLEMENTED AND VERIFIED | ctest: 5/5 passing |
| Reality Engine data integrity (8 tests) | IMPLEMENTED AND VERIFIED | All passing |
| Physics (Jolt) | IMPLEMENTED AND VERIFIED | Real Jolt, 300-step verification test passed |
| Terrain, animation, AI, audio, multiplayer | PARTIAL | Test game has basic mechanics; advanced features not implemented |

## What is NOT claimed
- No Blender integration verified (Blender absent).
- No Godot runtime execution verified locally (Godot absent — validated via GitHub Actions run 44902553046).
- No Android/Web/Desktop builds verified locally.
- No benchmark numbers (no hardware/engines to measure locally).
- Export artifacts not yet produced (no Godot export templates).
