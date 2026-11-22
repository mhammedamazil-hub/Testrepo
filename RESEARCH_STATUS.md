# RESEARCH_STATUS — Universal Game Engine

## Status system
NOT_RESEARCHED | METADATA_REVIEWED | DOCUMENTATION_REVIEWED | SOURCE_REVIEWED | EXPERIMENTED | BENCHMARKED | INTEGRATED | REJECTED | BLOCKED

Note: per project rules, no project is marked fully researched after reading only a README. Entries marked SOURCE_REVIEWED and above include web-sourced architectural/licensing detail. No engine has been EXPERIMENTED, BENCHMARKED, or INTEGRATED in this environment (binaries not installable).

## Engines
| Engine | Repo | License | Language | Status | Notes |
|--------|------|---------|----------|--------|-------|
| Godot 4 | github.com/godotengine/godot | MIT | C++, GDScript, C# | DOCUMENTATION_REVIEWED | Selected primary runtime (D-01). Node/Scene, headless server mode, Vulkan/OpenGL. Not installed here. |
| Bevy | github.com/bevyengine/bevy | MIT OR Apache-2.0 | Rust | DOCUMENTATION_REVIEWED | Rejected as primary (code-first, pre-1.0 churn, weak AI scripting fit). |
| Blender | blender.org | GPL-2.0+ | C, C++, Python | BLOCKED | Central authoring foundation. Not installed; cannot install in this env. |
| UPBGE | github.com/UPBGE/upbge | GPL-3.0 | C++, Python | REJECTED | GPL copyleft; under-developed/inactive; performance concerns. |
| Panda3D | github.com/panda3d/panda3d | Revised BSD | C++, Python | DOCUMENTATION_REVIEWED | Viable but weaker headless story/smaller community than Godot. Candidate. |

## Physics
| Component | Repo | License | Language | Status | Notes |
|-----------|------|---------|----------|--------|-------|
| Godot Physics | bundled with Godot | MIT | C++ | DOCUMENTATION_REVIEWED | Primary physics backend (tied to Godot runtime). |
| Jolt Physics | github.com/jrouwe/JoltPhysics | MIT | C++ | DOCUMENTATION_REVIEWED | Candidate for dedicated-server/headless physics adapter. |
| Bullet | github.com/bulletphysics/bullet3 | zlib | C++ | DOCUMENTATION_REVIEWED | Mature; license ambiguity noted — treat with caution. |
| Box2D | github.com/erincatto/box2d | MIT | C++ | DOCUMENTATION_REVIEWED | 2D rigid-body physics. |
| Rapier | github.com/dimforge/rapier | Apache-2.0 | Rust | DOCUMENTATION_REVIEWED | 2D/3D, Rust/WASM. |

## Research depth
- Tier 1 (deep, directly relevant): Godot, Bevy, Blender, UPBGE, Godot Physics, Jolt.
- Tier 2 (documentation + selective source): Panda3D, Bullet, Box2D, Rapier.
- Tier 3 (catalog only): remaining engines/components from the project list (O3DE, Flax, Stride, OGRE, Raylib, SDL, Pygame, etc.) — not individually researched unless a decision requires it.

## Gaps (to fill when binaries are available)
- Source-level code review of Godot/Bevy/Blender (no clones possible under current network/root constraints? github clones are possible — note for later).
- Hands-on experimentation with bpy, Godot headless, Jolt.
- Benchmarks (100/1000 rigid bodies, rendering, asset processing).
