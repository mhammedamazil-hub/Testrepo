# Research: Bullet Physics

## Identity
- Name: Bullet Physics SDK
- Repository: https://github.com/bulletphysics/bullet3
- License: zlib (permissive) per guideflow; note: some community discussions reference GPL confusion — treat license with caution and verify before use
- Language: C++
- Architecture: real-time collision detection and multi-physics simulation; rigid bodies, soft bodies, GPU-accelerated collision detection (OpenCL), 6-DOF/hinge/slider/cone constraints, speculative + time-of-impact CCD, GJK/EPA, convex decomposition, dynamic-tree broadphase
- Major features: rigid body dynamics, soft body simulation, GPU rigid-body pipeline, robotics/VR/ML use, PyBullet Python bindings
- Unique strengths: 15+ years as de facto open-source physics workhorse, broad feature set, GPU acceleration
- Weaknesses: license ambiguity in community sources (verify), older codebase
- Compatibility: zlib if confirmed — permissive; GPL concerns if applicable
- Maintenance status: maintained
- Research depth: DOCUMENTATION_REVIEWED
- Source references: [guideflow.com](https://www.guideflow.com/blog/physics-engine-software/) [pistack.xyz](https://www.pistack.xyz/posts/2026-06-25-physics-simulation-engines-bullet3-box2d-jolt-physics/)
- Adoption decision: NOT selected (Godot Physics primary, Jolt candidate). Documented as a mature alternative.
