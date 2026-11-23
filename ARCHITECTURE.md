# ARCHITECTURE — Universal Game Engine

## Conceptual layout

```
AI AGENTS
    |
CLI / API / MCP  (Python 3, same core API for both)
    |
CORE PLATFORM
 ______________________________
|          |         |        |
Projects  Scenes    Assets   Testing
|          |         |        |
|          |         |        |
Blender  Runtime   Physics  AI Tools
|          |         |        |
||________|___________|________|
|
BUILD / DEPLOYMENT
```

This is conceptual, not a fixed implementation.

## Layers

### 1. Interface layer
- **CLI** (`universal-engine` / `python -m universal_engine`): every major operation, JSON mode (`--json`), structured errors, exit codes, logging, help.
- **MCP server** (`mcp` subcommand, stdio): exposes the same core API as the CLI via typed tool schemas. No dangerous unrestricted system execution by default.
- **Python API** (`universal_engine.core`): importable library used by both CLI and MCP.

### 2. Core platform (language: Python 3)
- Project management: create/configure/inspect/validate projects, templates, dependency management, asset/scene tracking, build configs.
- Scene model: creation, inspection, object hierarchy, transforms, serialization, validation, runtime conversion.
- Object system: creation, meshes, transforms, materials, components, physics, animation, scripts, metadata.
- Asset system: import, conversion (glTF/GLB canonical), optimization, inspection, search, dependency analysis, validation.
- Adapter system: pluggable backends with clear interfaces, capability declarations, version info, compatibility/dependency checks, error handling, tests.

### 3. Adapters (pluggable, not all required)
| Adapter | Backend | Status in this env |
|---------|---------|--------------------|
| Blender adapter | Blender (bpy), headless | BLOCKED/UNAVAILABLE (no Blender installed) |
| Runtime adapter | Godot 4 | SPEC ONLY (Godot not installed) |
| Physics adapter | Godot Physics (primary), Jolt (candidate) | SPEC ONLY |
| Asset adapter | glTF/GLB via Blender/Godot | PLANNED |
| Scripting adapter | GDScript (runtime), Python (platform) | PLANNED |
| Rendering adapter | Blender EEVEE/Cycles / Godot Vulkan | PLANNED (blocked without Blender/Godot binaries) |

### 4. Build / deployment
- Build configuration, packaging, platform validation (Linux/Android/Web/Desktop), artifact management.
- No platform claimed until an actual build is verified.

## Data model (canonical)
- Project: `universal-engine.json` + `scenes/`, `assets/`, `scripts/`, `builds/` directories.
- Scene: serialized as JSON; convertible to Godot `.tscn/.scn` and Blender `.blend` via adapters.
- Assets: canonical glTF/GLB; source assets kept alongside.

## AI-contract
- Every AI operation grounded in an actual capability.
- Never claim an object was modified when the underlying operation failed.
- Structured, machine-readable responses; errors carry codes and messages.
- Visual feedback requires actual images (screenshots/renders), not metadata-only inspection.

## Honesty about this environment
- Blender is not installed and cannot be installed here → Blender adapter, headless Blender rendering, Geometry Nodes, and .blend I/O are UNAVAILABLE until Blender is present.
- Godot is not installed → runtime adapter cannot be executed; only the interface/spec exists.
- These are marked UNAVAILABLE/PLANNED, never VERIFIED or FUNCTIONAL.
