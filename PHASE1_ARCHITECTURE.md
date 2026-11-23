# PHASE1_ARCHITECTURE — Reality Engine Phase 1 Architecture

## Overview

BLENDER RAGE — REALITY ENGINE is a modular, AAA-oriented game engine with Blender as the primary development environment and a standalone native C++ runtime. Phase 1 delivers the native engine core, ECS, Jolt Physics integration, shared project format, Blender addon, standalone runtime, and MCP/CLI control.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Blender (Authoring)                      │
│  Reality Engine Studio Addon (Python)                       │
│  └─ Project / Entities / Physics / Materials / Runtime      │
└─────────────────────────────┬───────────────────────────────┘
                              │ exports .reality.json
┌─────────────────────────────▼───────────────────────────────┐
│              Shared Reality Project Format (JSON)           │
│  project.reality | scenes/*.scene.reality | assets/         │
└─────────────────────────────┬───────────────────────────────┘
                              │ loads
┌─────────────────────────────▼───────────────────────────────┐
│              Standalone Runtime (C++20)                     │
│  engine/core | engine/ecs | engine/world | engine/scene     │
│  engine/physics (Jolt) | engine/rendering (headless)        │
│  engine/platform | engine/input | engine/assets | ...       │
└─────────────────────────────┬───────────────────────────────┘
                              │ MCP / CLI
┌─────────────────────────────▼───────────────────────────────┐
│         Python Platform (CLI + MCP Server)                  │
│  reality_project_*, reality_scene_*, reality_entity_*,      │
│  reality_component_*, reality_physics_*, reality_runtime_*  │
└─────────────────────────────────────────────────────────────┘
```

## Module Directory Layout

```
engine/
  CMakeLists.txt
  core/
    CMakeLists.txt
    engine.h          # Engine init/shutdown/lifecycle
    engine.cpp
    application.h     # Application lifecycle
    application.cpp
    game_loop.h       # Fixed timestep sim + variable timestep render
    game_loop.cpp
    logging.h         # Structured logging (spdlog-style, header-only)
    logging.cpp
    config.h          # Configuration management (JSON)
    config.cpp
    error.h           # Error reporting (result types)
    error.cpp
  ecs/
    CMakeLists.txt
    ecs.h             # Entity, Component, System, Registry
    ecs.cpp
    entity_id.h       # Stable persistent entity IDs
    entity_id.cpp
  world/
    CMakeLists.txt
    world.h           # World state, entity lifecycle
    world.cpp
  scene/
    CMakeLists.txt
    scene.h           # Scene management
    scene.cpp
    scene_format.h    # Reality Engine scene format (JSON)
    scene_format.cpp
  assets/
    CMakeLists.txt
    asset_manager.h   # Resource management
    asset_manager.cpp
    gltf_loader.h     # glTF 2.0 loader (Phase 1: stub/interface)
    gltf_loader.cpp
  physics/
    CMakeLists.txt
    physics_world.h   # Jolt Physics wrapper
    physics_world.cpp
    physics_body.h    # RigidBody/Collider components
    physics_body.cpp
  rendering/
    CMakeLists.txt
    renderer.h        # Renderer interface (abstract)
    renderer.cpp
    headless_renderer.h  # Headless/no-op renderer (Phase 1)
    headless_renderer.cpp
  platform/
    CMakeLists.txt
    platform.h        # Platform abstraction
    platform.cpp
  input/
    CMakeLists.txt
    input.h           # Input handling
    input.cpp
  animation/
    CMakeLists.txt
    animation.h       # Animation interface
    animation.cpp
  audio/
    CMakeLists.txt
    audio.h           # Audio interface
    audio.cpp
  navigation/
    CMakeLists.txt
    navigation.h      # Navigation interface
    navigation.cpp
  scripting/
    CMakeLists.txt
    scripting.h       # Scripting interface (Python)
    scripting.cpp
  gameplay/
    CMakeLists.txt
    gameplay.h        # Gameplay systems
    gameplay.cpp
  diagnostics/
    CMakeLists.txt
    diagnostics.h     # Diagnostics and profiling
    diagnostics.cpp
```

## Data Flow

1. **Authoring**: User creates project/scene in Blender via Reality Engine Studio addon
2. **Export**: Addon writes `project.reality` + `scenes/*.scene.reality` (JSON)
3. **Runtime**: Standalone runtime loads project JSON, initializes engine, creates entities, runs physics simulation
4. **Control**: MCP/CLI sends commands to runtime via stdio or subprocess
5. **Diagnostics**: Runtime exposes entity positions, velocities, physics stats via JSON

## Component Design (Phase 1 Required)

| Component | Fields | Purpose |
|-----------|--------|---------|
| Transform | position(3), rotation(3/4 quat), scale(3) | Entity transform, parent-child hierarchy |
| Name | string | Human-readable name (NOT permanent ID) |
| MeshRef | mesh_id (string) | Reference to mesh asset |
| MaterialRef | material_id (string) | Reference to material asset |
| RigidBody | type (static/dynamic/kinematic), mass, friction, restitution | Physics body type |
| Collider | shape (box/sphere/capsule), size(3), radius | Collision shape |
| Velocity | linear(3), angular(3) | Physics velocity |
| Camera | fov, near, far, aspect | Camera component |
| Light | type, color, intensity | Light component |
| Metadata | uuid, created_at, version | Stable persistent entity metadata |

## Entity ID Design

- Entity IDs are UUIDs (128-bit), generated at creation time
- Stored in Metadata component
- Persistent across scene serialization and reload
- Blender object names are NOT used as entity IDs
- ID lookup via ECS registry: ID → entity index

## Physics Design (Jolt)

- Jolt Physics integrated as static library
- Physics world runs at fixed timestep (60 Hz)
- Bodies: static, dynamic, kinematic
- Colliders: box, sphere, capsule
- Collision layers: configurable bitmask
- Contact events: callback-based
- Transform sync: physics → ECS Transform each frame

## Rendering Design (Phase 1)

- `Renderer` abstract interface class
- `HeadlessRenderer` implementation: no-op, logs draw calls, no actual rendering
- Vulkan renderer: PLANNED for Phase 2 (no GPU/dev headers locally)
- Runtime starts in headless mode by default

## MCP / CLI Protocol

- MCP: JSON-RPC 2.0 over stdio (existing, extended)
- CLI: `reality <SUBCOMMAND> [ARGS]` with `--json` flag (existing pattern, extended)
- Runtime communication: subprocess spawn, stdout JSON lines, stdin commands
- Timeouts: 30s default for all operations
- Error codes: INVALID_INPUT, SCENE_NOT_FOUND, ENTITY_NOT_FOUND, BACKEND_UNAVAILABLE, RUNTIME_NOT_RUNNING, etc.

## Blender Addon (Reality Engine Studio)

- Language: Python (bpy)
- Panels: Project, World, Entities, Physics, Materials, Runtime, Diagnostics, AI
- Operators: Create project, create entity, assign components, configure physics, export scene, validate scene, launch runtime, inspect runtime
- Export format: JSON (shared Reality Engine format)
- Cannot test locally (no bpy) — documented as UNTESTED LOCALLY

## Build System

- CMake, out-of-source build
- Static libraries for engine modules
- Static link Jolt Physics
- Headless build (no SDL3/Vulkan locally)
- Build type: Release (minimal RAM usage)
- Parallel jobs: -j2 (2 CPU cores)
- Strip symbols: -s flag to reduce binary size

## License Compliance

| Dependency | License | Compliant? |
|------------|---------|------------|
| Jolt Physics | MIT | YES |
| Custom engine code | Proprietary (see LICENSE) | YES |
| Blender addon | GPL (Blender addon requirement) | YES (separate from engine) |
| Python platform | Proprietary | YES |
