# Research: Bevy Engine

## Identity
- Name: Bevy
- Repository: https://github.com/bevyengine/bevy
- Official documentation: https://bevyengine.org/
- License: MIT OR Apache-2.0 (dual)
- Language: Rust, WGSL (shaders)
- Architecture: Entity-Component-System (ECS) for everything (renderer, UI, engine features are systems/components); systems are plain Rust functions scheduled in parallel; app model = plugins + resources + events; renderer built on wgpu (Vulkan/Metal/DX12/WebGPU)
- Core technologies: Bevy ECS, wgpu renderer, WGSL shaders, plugin system, scene serialization (RON/JSON), hot reload
- Major features: 2D and 3D rendering, ECS, automatic multithreading, hot reloading, modular plugin design, cross-platform (Linux/macOS/Windows/Web/iOS/Android)
- Unique strengths: data-oriented design, automatic parallelism, compile-time safety, modular/replaceable features, permissive license, most-starred Rust game engine
- Weaknesses: code-first (no visual editor yet — in development), pre-1.0 (breaking API changes every ~3 months with migration guides), Rust is a poor fit for AI-generated/sandboxed gameplay scripting, long compile times hurt iteration, weaker headless/server story than Godot
- Reusable components: ECS scheduler, wgpu render graph, scene system, UI framework
- Integration possibilities: could serve as a specialized high-performance runtime backend; rejected as primary for this project
- Compatibility: MIT/Apache-2.0 — permissive
- Maintenance status: actively developed, Bevy Foundation; regular releases; pre-1.0
- Research depth: DOCUMENTATION_REVIEWED
- Source references: [opensource.fyi](https://opensource.fyi/projects/bevy/) [rustify.rs](https://rustify.rs/articles/rust-for-game-development-bevy-2026/) [engineranked.com](https://engineranked.com/article/bevy-engine-review-2026/)
- Adoption decision: REJECTED as primary runtime. Strong architecture but weak AI-controllability fit (Rust scripting, code-first, pre-1.0 churn).
