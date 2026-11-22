# Research: Jolt Physics

## Identity
- Name: Jolt Physics
- Repository: https://github.com/jrouwe/JoltPhysics
- License: MIT License
- Language: C++
- Architecture: multi-core-friendly rigid-body physics and collision detection; no dependencies beyond the STL; GJK/EPA, continuous collision detection (full TOI + speculative), 6-DOF/hinge/slider/fixed/cone constraints, character controller, vehicle support, soft-body and ragdoll simulation
- Major features: rigid bodies of various shapes, CCD, constraints, character controller, vehicles, soft bodies/ragdolls, multithreaded, used in Horizon Forbidden West and Death Stranding 2
- Unique strengths: modern, multithreaded, AAA-proven, MIT, minimal dependencies
- Compatibility: MIT — permissive
- Maintenance status: actively maintained (recent commits within days)
- Research depth: DOCUMENTATION_REVIEWED
- Source references: [guideflow.com](https://www.guideflow.com/blog/physics-engine-software/) [pistack.xyz](https://www.pistack.xyz/posts/2026-06-25-physics-simulation-engines-bullet3-box2d-jolt-physics/) [libhunt](https://www.libhunt.com/compare-bullet3-vs-JoltPhysics) [cpp.libhunt.com](https://cpp.libhunt.com/joltphysics-alternatives)
- Adoption decision: CANDIDATE for dedicated-server / headless physics adapter (D-04); not primary (Godot Physics is primary, tied to Godot runtime).
