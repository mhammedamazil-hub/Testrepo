# BLENDER WORKSPACE ARCHITECTURE — Blender-Integrated 3D Workspace for MCP & CLI

## Overview
Blender is the central 3D authoring foundation. The Universal Game Engine platform builds on top of Blender's source code, integrating the best features from every major game engine (Godot, Bevy, Unity, Unreal) into a single 3D workspace maximized for MCP and CLI control.

## Source Status
- Blender source cloned: `blender-source/` (446MB, shallow clone from github.com)
- cmake installed via pip (4.4.5)
- **Build blocked**: Missing development headers (boost-dev, X11 dev, Wayland dev, python3-dev, libssl-dev, etc.), no root access to install them, 3.8GB RAM insufficient for full compilation, 2 CPU cores too slow.
- **Blender adapter**: Interface ready in `universal_engine/adapters/blender.py` — reports `UNAVAILABLE` until Blender binary is built/installed.

## Feature Integration Matrix — Best of Every Engine

| Feature | Source Engine | Implementation in Blender Workspace |
|---------|--------------|-----------------------------------|
| Node/Scene tree | Godot | Blender collections/objects mapped to scene graph; .blend as native scene format |
| GDScript-like scripting | Godot | Python (bpy) as native scripting language; GDScript-compatible API wrapper |
| Headless server mode | Godot | `blender --background --python` for headless operations |
| Signals | Godot | Blender animation drivers + custom event bus via Python |
| Text-based scene files | Godot | .blend (binary) + JSON export/import for MCP/CLI manipulation |
| ECS architecture | Bevy | Blender objects + custom property groups as components; Python systems |
| Modular plugins | Bevy | Blender add-on system + Python module plugins |
| Change detection | Bevy | Blender dependency graph (depsgraph) + change listeners |
| Parallel scheduler | Bevy | Python concurrent.futures + Blender job system |
| Prefabs | Unity | Blender collections as prefab templates; linked duplicates |
| Addressable assets | Unity | Blender asset catalogs + custom address system |
| Object pooling | Unity | Blender dupli instances + custom pool manager |
| Asset import pipeline | Unity | Blender import operators + post-process rules (glTF, FBX, OBJ) |
| Blueprints visual scripting | Unreal | Blender geometry nodes + node editor as visual scripting |
| Nanite virtualized geometry | Unreal | Blender multiresolution + decimate + LOD generation |
| Lumen global illumination | Unreal | Blender EEVEE Next + Cycles with path guiding |
| Niagara VFX | Unreal | Blender geometry nodes + particle systems + Mantaflow |
| Chaos Physics | Unreal | Blender Bullet physics + rigid body constraints |

## Architecture Layers

### Layer 1: Blender Core (C++)
- Blender source code (`blender-source/`)
- bpy Python API
- Dependency graph (depsgraph)
- Geometry nodes, EEVEE, Cycles renderers
- Bullet physics integration

### Layer 2: Universal Engine Core (Python)
- Project/Scene/Asset data models
- Adapter pattern (BlenderAdapter + GodotAdapter)
- JSON serialization for scenes and objects
- Result/error types with exit codes

### Layer 3: Blender Adapter (Python + bpy)
- `blender_adapter.py` — wraps bpy operations
- Headless execution: `blender --background --python <script>`
- Scene create/inspect, object create/modify, mesh generation
- Material creation, render, screenshot capture
- glTF/GLB export
- Prefab-like collection templates
- Addressable asset catalog

### Layer 4: CLI (`universal_engine.cli`)
- `blender <COMMAND>` subcommands: scene, object, mesh, material, render, export, inspect, prefab, addressable
- `--json` mode for all commands
- Structured errors and exit codes

### Layer 5: MCP Server (JSON-RPC 2.0 over stdio)
- 16+ Blender-specific tools: blender_scene_create, blender_object_create, blender_mesh_generate, blender_material_create, blender_render, blender_export_gltf, blender_scene_inspect, blender_preview_capture, blender_prefab_create, blender_addressable_register, blender_node_graph_edit, blender_physics_configure, blender_animation_create, blender_light_create, blender_camera_create
- All tools call the same BlenderAdapter backend as the CLI

## Blender Adapter Operations (MCP/CLI)

| Operation | CLI Command | MCP Tool | Description |
|-----------|------------|----------|-------------|
| scene_create | `blender scene create <name>` | blender_scene_create | Create new Blender scene |
| scene_inspect | `blender scene inspect <name>` | blender_scene_inspect | Inspect scene objects and hierarchy |
| object_create | `blender object create <type> <name>` | blender_object_create | Create mesh/empty/camera/light object |
| object_modify | `blender object modify <name>` | blender_object_modify | Modify object transform/properties |
| mesh_generate | `blender mesh generate <type> <name>` | blender_mesh_generate | Generate cube/sphere/ico/cylinder mesh |
| material_create | `blender material create <name>` | blender_material_create | Create Principled BSDF material |
| render | `blender render <scene> <output>` | blender_render | Render scene to image |
| export_gltf | `blender export <scene> <output>` | blender_export_gltf | Export scene as glTF/GLB |
| prefab_create | `blender prefab create <name>` | blender_prefab_create | Create collection as prefab template |
| prefab_instance | `blender prefab instance <name>` | blender_prefab_instance | Instance a prefab in scene |
| addressable_register | `blender addressable register <path>` | blender_addressable_register | Register asset as addressable |
| addressable_resolve | `blender addressable resolve <addr>` | blender_addressable_resolve | Resolve addressable to asset path |
| node_graph_edit | `blender nodes edit <graph>` | blender_node_graph_edit | Edit geometry nodes / shader nodes |
| physics_configure | `blender physics configure <obj>` | blender_physics_configure | Configure rigid body / collision |
| animation_create | `blender animation create <obj>` | blender_animation_create | Create keyframe animation |
| light_create | `blender light create <type> <name>` | blender_light_create | Create sun/point/spot/area light |
| camera_create | `blender camera create <name>` | blender_camera_create | Create camera object |
| preview_capture | `blender preview <scene> <output>` | blender_preview_capture | Capture viewport screenshot |

## Blender Source Directory Structure (for reference)

```
blender-source/
  blender/           # Blender application (blender.exe/blender binary)
  bpy/               # Python API module
  intern/            # Internal C++ source
  source/            # Source code (C/C++)
  scripts/           # Python scripts (addons, startup, UI modules)
  release/           # Release scripts and configs
  CMakeLists.txt     # Main CMake build file
```

## Build Plan (for proper environment)

When a build environment with root access and sufficient RAM is available:

```bash
# Install dependencies
apt-get install build-essential cmake python3-dev libboost-dev \
  libxi-dev libxxf86vm-dev libxrandr-dev libxcursor-dev \
  libxinerama-dev libwayland-dev libxkbcommon-dev libssl-dev \
  libffi-dev libbz2-dev liblzma-dev libglew-dev libopenal-dev \
  libfreetype6-dev libjpeg-dev libpng-dev libtiff-dev \
  libopenexr-dev libopenimageio-dev libopensubdiv-dev \
  libalembic-dev libembree-dev libblosc-dev libspnav-dev

# Build Blender (headless)
cd blender-source
make full  # or: make -j2 (limited by 2 CPU)
```

## MCP/CLI Maximization Principles

1. **Headless-first**: All operations work via `blender --background --python` without a display
2. **JSON everywhere**: All CLI commands support `--json`; all MCP tools return structured JSON
3. **Structured errors**: Machine-readable error codes (INVALID_INPUT, SCENE_NOT_FOUND, OBJECT_NOT_FOUND, BACKEND_UNAVAILABLE, etc.)
4. **Exit codes**: 0 success, 1 general error, 2 validation error, 3 not implemented, 4 backend missing
5. **No bpy dependency at import time**: Adapter gracefully degrades when Blender is unavailable
6. **Universal scene format**: JSON scenes can be created and inspected without Blender; converted to .blend when Blender is available

## Current Status

| Component | Status |
|-----------|--------|
| Blender source code | CLONED (blender-source/) |
| cmake | INSTALLED (pip) |
| Build dependencies | BLOCKED (no root, missing dev headers) |
| Blender binary | NOT BUILT |
| bpy module | NOT IMPORTABLE |
| Blender adapter | INTERFACE READY (reports UNAVAILABLE) |
| Blender CLI commands | DESIGNED (not yet implemented) |
| Blender MCP tools | DESIGNED (not yet implemented) |

## Next Steps

1. Implement Blender CLI commands (`blender scene/object/mesh/material/render/export/inspect` subcommands)
2. Implement Blender MCP tools (16+ tools in mcp_server.py)
3. Add Blender adapter methods that call bpy when available
4. Write Blender integration tests (run when Blender is available)
5. Create build scripts for Blender from source
6. Test end-to-end: CLI → MCP → Blender → rendered output
