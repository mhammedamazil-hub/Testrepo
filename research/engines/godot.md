# Research: Godot Engine

## Identity
- Name: Godot Engine
- Repository: https://github.com/godotengine/godot
- Official documentation: https://docs.godotengine.org/
- License: MIT License
- Language: C++ (engine), GDScript / C# / C++ (GDExtension) (scripting)
- Architecture: Node and Scene tree; SceneTree execution model; server subsystems (RenderingServer, PhysicsServer3D, AudioServer, DisplayServer); driver & platform layer (Vulkan, OpenGL, OS integration)
- Core technologies: Scene system, nodes, resources, signals, Vulkan/OpenGL renderers, Godot Physics, navigation, animation, audio, networking (ENet, WebRTC, WebSocket, high-level multiplayer RPC)
- Major features: 2D and 3D rendering, dedicated 2D renderer, Vulkan (Godot 4), GDScript, C#, visual scripting, one-click export desktop/mobile/web, headless server mode, CLI, XR support
- Unique strengths: MIT license (no royalties), small (~100 MB) portable editor, Node/Scene architecture easy to grasp, GDScript is Python-like (AI-friendly), headless/CLI automation, cross-platform export
- Weaknesses: 3D not industry-leading vs Unreal; smaller asset ecosystem than Unity/Unreal; Godot 4 3D still maturing
- Reusable components: entire engine as a library via headless/server mode; GDScript; GDExtension; scene files (.tscn/.scn); glTF/GLB import/export
- Integration possibilities: primary game runtime for this platform; scene conversion target from Blender via glTF/GLB; GDScript gameplay scripting; headless server for testing/simulation
- Compatibility: MIT — permissive, compatible with this project's goals
- Maintenance status: actively maintained by Godot Foundation + community; regular releases; Godot 4.x current
- Research depth: DOCUMENTATION_REVIEWED (web-sourced architecture/licensing; no source clone in this env)
- Source references: [1](https://cosmiclearn.com/godot/) [2](https://generalistprogrammer.com/godot/) [4](https://www.8ration.com/blogs/godot-game-engine-development-guide/) [5](https://makerstack.co/reviews/godot-review/)
- Adoption decision: SELECTED as primary game runtime (D-01). Spec/interface only in this env — Godot binary not installed; cannot execute end-to-end.
