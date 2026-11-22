# VISION — Universal Game Engine

## Mission
Build a completely new, unified, AI-native game development ecosystem that leverages the best existing open-source technologies instead of reinventing them. Blender is the primary 3D content creation, scene authoring, modeling, animation, and procedural-generation foundation. Godot is the primary game runtime. glTF/GLB is the asset exchange format. A Python-based CLI and MCP server make the entire platform controllable by AI agents, through natural language, CLI, APIs, and MCP — with headless operation as a first-class capability.

## What this is NOT
- Not simply a Blender plugin.
- Not simply a game made in Blender.
- Not a wrapper around a single existing game engine.
- Not a from-scratch engine rewrite.
- Not a collection of disconnected tools.

## Core principles
- Reuse proven open-source technology; research before implementing.
- Blender is the primary 3D foundation, not necessarily the entire runtime.
- Every major operation has a CLI equivalent.
- MCP exposes capabilities to AI agents when appropriate.
- Headless operation is first-class.
- Previews, screenshots, logs, test results, and structured outputs are AI-accessible.
- Modularity over tight coupling; performance and stability over unnecessary visual effects.
- No fake functionality, simulated integrations, or placeholder implementations disguised as completed features.
- Every integration must have a reason to exist.

## End-goal workflows (made progressively real)
1. Create a new third-person game project. Generate a terrain environment using Blender. Create a vehicle using procedural geometry. Import into the runtime. Set up rigid-body physics. Create a controller. Add lighting, cameras, materials, environment. Run the game. Capture screenshots. Inspect. Detect problems. Fix them. Test physics. Optimize assets. Build the game.
2. Create a realistic open-world environment: terrain, roads, buildings, vegetation, props. Optimize assets. Streaming and LOD. Lighting. Test performance. Capture previews. Iterate until criteria met.
3. Inspect a game project. Find physics problems, broken assets, incorrect materials, inefficient meshes, missing dependencies, scripting errors, runtime issues. Produce a report, fix issues safely, verify every fix.

## Capability truthfulness
Every capability is labeled VERIFIED, FUNCTIONAL, PARTIAL, EXPERIMENTAL, PLANNED, or UNAVAILABLE. Labels are accurate; nothing is overclaimed.
