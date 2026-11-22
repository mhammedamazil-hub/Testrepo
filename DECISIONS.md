# DECISIONS — Universal Game Engine

Evidence-based architecture decisions with alternatives, tradeoffs, and sources.

---

## D-01: Primary game runtime = Godot 4

**Decision:** Use Godot 4 as the primary game runtime. Integrate via a Godot adapter (headless/server mode + CLI + GDScript).

**Evidence:**
- License: MIT (permissive, no royalties, no copyleft). [1](https://cosmiclearn.com/godot/) [2](https://generalistprogrammer.com/godot)
- Architecture: Node/Scene tree + SceneTree + server subsystems (RenderingServer, PhysicsServer3D, AudioServer, DisplayServer). [1](https://cosmiclearn.com/godot/)
- Scripting: GDScript (Python-like, AI-friendly, easy to generate/sandbox), C#, C++/GDExtension. [1](https://cosmiclearn.com/godot/)
- Rendering: Vulkan + OpenGL 4.3 (Godot 4), dedicated 2D and 3D pipelines. [1](https://cosmiclearn.com/godot/)
- Headless: `--headless` server mode supported; CLI-driven automation possible. [4](https://www.8ration.com/blogs/godot-game-engine-development-guide/)
- Cross-platform: desktop, mobile, web. [2](https://generalistprogrammer.com/godot/)
- Proven, stable, active community; ~100 MB editor. [5](https://makerstack.co/reviews/godot-review/)

**Alternatives considered:**
- **Bevy** (MIT/Apache-2.0, Rust/ECS): rejected. Code-first (no visual editor yet), pre-1.0 API churn every ~3 months, Rust is a poor fit for AI-generated/sandboxed gameplay scripting and long compile times hurt iteration. Strong runtime architecture but weak AI-controllability fit for this project. [bevy searches]
- **UPBGE** (GPL): rejected. GPL copyleft on blenderplayer and scripts that reference the UPBGE/Blender API; project described as under-developed/inactive with performance concerns. License incompatible with a permissive, commercially-friendly platform. [upbge searches]
- **Panda3D** (BSD): viable but rejected as primary. Smaller community, scene-graph (older model), weaker headless/server story than Godot, less active development. Kept as a documented candidate. [panda3d searches]
- **Unreal/Unity**: not selected as core. Licensing (royalties/subscription), source-access/automation constraints, and closed editor models conflict with the MIT-first, AI-controllable, headless philosophy.

**Tradeoffs:** Godot 3D is capable but not industry-leading vs Unreal; accepted because the goal is an open, automatable platform, not AAA visual fidelity out of the box.

**Status:** DECIDED (spec only — Godot binary not installed in this env; adapter cannot be executed yet).

---

## D-02: Asset exchange format = glTF / GLB

**Decision:** Canonical interchange format between Blender (authoring) and Godot (runtime) is glTF 2.0 / GLB.

**Reasoning:** glTF is the open, widely-supported "JPEG of 3D"; Blender exports glTF/GLB natively; Godot imports glTF/GLB natively. Keeps the Blender↔Godot pipeline lossy-but-practical and avoids custom file formats.

**Status:** DECIDED (not yet tested — no Blender/Godot binaries).

---

## D-03: Platform language = Python 3

**Decision:** The CLI, MCP server, and core platform are implemented in Python 3.

**Reasoning:** Python is installed (3.11.2), AI-friendly, excellent for automation/tooling, and is Blender's native scripting language (bpy), which creates a natural bridge to Blender integration when Blender becomes available.

**Status:** DECIDED (implemented — scaffold present).

---

## D-04: Physics = Godot Physics (primary), Jolt Physics (candidate)

**Decision:** Primary physics backend is Godot Physics (built into the selected runtime). Jolt Physics (MIT) is a documented candidate for a dedicated-server / headless physics adapter if Godot Physics proves insufficient.

**Evidence:**
- Jolt: MIT, multithreaded C++, continuous collision detection, character controller, vehicle support, used in Horizon Forbidden West / Death Stranding 2; no dependencies beyond STL. [physics searches]
- Bullet: mature, zlib per some sources (GPL confusion noted — treat with caution), PyBullet bindings exist. [physics searches]
- Box2D: MIT, 2D only. [physics searches]
- Rapier: Apache-2.0, Rust/WASM. [physics searches]

**Status:** DECIDED (spec only — no physics library installed).

---

## D-05: Scripting = GDScript (runtime gameplay), Python (platform/tooling)

**Decision:** Gameplay scripts authored in GDScript; platform CLI/MCP in Python.

**Reasoning:** GDScript is Python-like and tightly integrated with Godot nodes/signals; Python is the platform language and Blender's language, unifying tooling and (eventually) Blender automation.

**Status:** DECIDED (spec only).

---

## D-06: Blender = central 3D authoring foundation (NOT the runtime)

**Decision:** Blender is the primary 3D content creation / scene authoring / modeling / animation / procedural (Geometry Nodes) foundation. Blender is not forced to be the game runtime.

**Reasoning:** Matches the project philosophy; Blender is the strongest open-source authoring tool; Godot is a stronger, MIT-licensed runtime. Blender exports to glTF/GLB for Godot.

**Blocker in this env:** Blender is not installed and cannot be installed (no root, no blender.org network). All Blender/bpy features are UNAVAILABLE here.

**Status:** DECIDED (blocked in this environment).

---

## Decision log format
Each decision: ID, decision, evidence (with sources), alternatives considered, tradeoffs, status. Status values: PROPOSED, DECIDED, IMPLEMENTED, VERIFIED, REVISITED, REVERTED.
