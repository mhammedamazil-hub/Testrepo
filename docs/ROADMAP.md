# ROADMAP — Universal Game Engine

Phases with measurable exit criteria (from MASTER_PLAN.md).

| Phase | Goal | Exit criteria | Status |
|-------|------|---------------|--------|
| 0 — Environment & Baseline | Inspect env/hardware/software; confirm Blender; reproducible baseline | Environment doc + baseline created; Blender absence documented | DONE |
| 1 — Ecosystem Research | Research engines/components; license audit; research database | research/ files complete; coverage matrix; decisions documented | IN PROGRESS |
| 2 — Architecture | Document runtime/physics/rendering/scripting/adapter/CLI/MCP decisions | ARCHITECTURE.md + decision docs complete | PLANNED |
| 3 — Core Platform | Project management, config, core API, logging, diagnostics, asset/scene model, adapter system | CLI can create/inspect/validate a project (pure Python, no Blender/Godot) | PLANNED |
| 4 — Blender Integration | Blender automation (bpy), headless, scene/object/mesh/material, import/export, render previews | Blender operations actually executed and tested | BLOCKED (no Blender) |
| 5 — Runtime Integration | Godot adapter, scene conversion, launching, input, gameplay, physics, scripting, asset loading | Game launched and controlled headlessly | BLOCKED (no Godot) |
| 6 — Physics & Simulation | Rigid bodies, collision, constraints, characters, simulation, testing, benchmarks | Physics benchmarks run with numbers | PLANNED |
| 7 — AI Automation | CLI, API, MCP, structured tools, previews, diagnostics | CLI + MCP server functional with JSON mode | IN PROGRESS (scaffold) |
| 8 — Visual Feedback | Screenshot capture, Blender/runtime previews, scene inspection, artifact management | Actual images produced and inspectable | BLOCKED (no Blender/Godot/display) |
| 9 — Game Dev Capabilities | Terrain, animation, AI, audio, multiplayer, procedural gen, streaming, LOD | Integrated and tested features | PLANNED |
| 10 — Packaging & Distribution | Linux/Android/Web/Desktop builds, platform validation | At least one verified build per claimed platform | PLANNED |
| 11 — Final Validation | Full tests, integration, runtime, Blender, CLI, MCP, headless, performance, license/security/docs audits | Verified capability report | PLANNED |

## No platform claimed until an actual build has been verified.
