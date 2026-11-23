# PHASE1_IMPLEMENTATION_PLAN — Reality Engine Phase 1 Implementation Plan

## Plan Overview

Implement Phase 1 in 12 steps. Each step produces a working, testable increment. Do not proceed to the next step until the current step's tests pass.

| Step | Area | Deliverable | Tests |
|------|------|-------------|-------|
| 1 | Build system | engine/CMakeLists.txt + module CMakeLists.txt | cmake configures, no errors |
| 2 | Core | engine init/shutdown, lifecycle, logging, config, error | Unit: engine start/stop, log output |
| 3 | ECS | Entity creation/destruction, component registration, system scheduling | Unit: create entity, add/remove component, query |
| 4 | Entity IDs | Stable UUID IDs, serialization roundtrip | Unit: ID persists across save/load |
| 5 | Transforms | Transform component, parent-child hierarchy | Unit: transform update, hierarchy transform |
| 6 | World | World state, entity lifecycle management | Unit: world create/destroy, entity add/remove |
| 7 | Scene | Scene management, JSON serialization/deserialization | Unit: scene save/load, validation |
| 8 | Physics | Jolt integration, world creation, gravity, bodies, colliders | Unit: objects fall, collide, settle |
| 9 | Assets | Asset manager, glTF interface, resource loading | Unit: asset load, missing asset detection |
| 10 | Rendering | Renderer interface, headless implementation | Unit: renderer init, draw call logging |
| 11 | Runtime | Standalone executable, project load, simulation, diagnostics | Integration: load scene, run physics, inspect |
| 12 | Blender + MCP/CLI | Blender addon, reality_* CLI commands, reality_* MCP tools | Integration: export → load → run → inspect |

## Detailed Step Plans

### Step 1: Build System
- Create `engine/CMakeLists.txt` (top-level)
- Create `engine/<module>/CMakeLists.txt` for each of 13 modules
- Configure C++20 (or best available with g++ 12.2)
- Output: static libraries, headless build
- Build directory: `engine/build/`
- Install prefix: `engine/install/` (local, no root)

### Step 2: Engine Core
- `engine/core/engine.h/cpp`: `Engine::Init()`, `Engine::Shutdown()`, `Engine::IsRunning()`
- `engine/core/application.h/cpp`: `Application::Run()`, `Application::Quit()`
- `engine/core/game_loop.h/cpp`: Fixed timestep simulation (60 Hz), variable timestep rendering
- `engine/core/logging.h/cpp`: Structured logging with levels (DEBUG, INFO, WARN, ERROR)
- `engine/core/config.h/cpp`: JSON configuration load/save
- `engine/core/error.h/cpp`: Result<T, Error> type, error codes
- Tests: engine start/stop, logging output, config load

### Step 3: ECS
- `engine/ecs/ecs.h/cpp`: `Registry`, `Entity`, `Component`, `System`
- Entity creation: `Registry::CreateEntity()`
- Component: `Registry::AddComponent<T>(entity, comp)`, `GetComponent<T>()`, `RemoveComponent<T>()`
- Query: `Registry::View<T>()`, `Registry::Each<T>()`
- System: `System::Update(Registry&, delta_time)`
- Tests: create entity, add component, query entities with component, remove component

### Step 4: Entity IDs
- `engine/ecs/entity_id.h/cpp`: `EntityId` (UUID-based), `EntityIdRegistry`
- UUID generation, persistence in scene JSON
- Tests: ID stability across serialization, ID uniqueness, ID lookup

### Step 5: Transforms
- Transform component: position, rotation (quaternion), scale
- Parent-child hierarchy with world transform computation
- Tests: local→world transform, hierarchy propagation, transform update

### Step 6: World
- `engine/world/world.h/cpp`: World container, entity lifecycle
- World creation, destruction, entity add/remove
- Tests: world create/destroy, entity lifecycle

### Step 7: Scene
- `engine/scene/scene.h/cpp`: Scene container, entities, components
- JSON serialization/deserialization matching shared format
- Schema validation, version checking
- Tests: scene save/load, validation, version check

### Step 8: Physics (Jolt)
- Build Jolt Physics static library from `jolt-physics/`
- `engine/physics/physics_world.h/cpp`: Jolt world wrapper
- Gravity configuration, body creation (static/dynamic/kinematic)
- Colliders: box, sphere, capsule
- Collision layers, contact events
- Fixed-step simulation
- Physics ↔ ECS transform synchronization
- Tests: objects fall, collide, settle on ground plane; reproducibility

### Step 9: Assets
- `engine/assets/asset_manager.h/cpp`: Resource loading, caching
- `engine/assets/gltf_loader.h/cpp`: glTF 2.0 loader interface (Phase 1: stub)
- Missing asset detection
- Tests: asset load, missing asset error

### Step 10: Rendering
- `engine/rendering/renderer.h/cpp`: Abstract renderer interface
- `engine/rendering/headless_renderer.h/cpp`: No-op renderer, draw call logging
- Tests: renderer init, draw call logging, shutdown

### Step 11: Runtime
- `runtime/main.cpp`: Standalone executable
- Load project JSON, initialize engine, create entities from scene
- Initialize physics, run simulation, expose diagnostics
- Clean shutdown
- Output: JSON diagnostics to stdout
- Integration test: load scene, run N frames, inspect entity positions/velocities

### Step 12: Blender Addon + MCP/CLI
- `blender_addon/reality_engine_studio/`: Blender addon (Python, bpy)
- 8 panels, operators for all Reality Engine operations
- Export: `project.reality` + `scenes/*.scene.reality`
- CLI: `reality project_create`, `reality scene_create`, `reality entity_create`, etc.
- MCP: 16 `reality_*` tools
- MCP↔runtime: structured JSON protocol, timeouts, lifecycle management
- Integration test: export from Blender format → load in runtime → run physics → inspect

## Acceptance Criteria (Phase 1)

1. [ ] `engine/build/` configures and builds without errors
2. [ ] ECS: entity create/destroy, component add/remove/query works
3. [ ] Entity IDs: stable UUIDs survive scene serialization roundtrip
4. [ ] Scene: JSON save/load, validation, version checking
5. [ ] Physics: 5+ dynamic objects fall, collide, settle on ground plane (reproducible)
6. [ ] Runtime: loads project, runs simulation, outputs JSON diagnostics
7. [ ] CLI: all `reality_*` commands work with `--json`
8. [ ] MCP: all 16 `reality_*` tools respond correctly via JSON-RPC 2.0
9. [ ] End-to-end: Blender export → runtime load → physics → inspect → save → reload
10. [ ] All unit and integration tests pass

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| No GPU/Vulkan | Headless renderer interface, Vulkan documented as Phase 2 |
| No SDL3 | Build headless, SDL3 from source if needed later |
| 3.8GB RAM | Release build, -j2, strip symbols, minimal debug info |
| No root | All deps to local prefix, no system installs |
| No bpy locally | Blender addon written to spec, documented UNTESTED LOCALLY |
| Jolt build fails | Documented fallback: custom simple physics for Phase 1 |
