# Research: Panda3D

## Identity
- Name: Panda3D
- Repository: https://github.com/panda3d/panda3d
- Official documentation: https://docs.panda3d.org/
- License: Revised BSD (Panda3D License; versions before 2008-05-28 non-free)
- Language: C++, C, Python
- Architecture: scene graph engine; C++ core with automatic Python wrapper-generator exposing full functionality; integrated with Python's garbage collector
- Core technologies: scene graph, rendering, audio (FMOD/OpenAL/Miles), collision detection, physics (ODE and Bullet integration), FSM, networking, AI
- Major features: graphics, audio, I/O, collision, physics, performance analysis tools, scene graph exploration, debugging, art export/import pipeline, cross-platform (Windows/Linux/macOS/FreeBSD)
- Unique strengths: mature (since 2002, Disney/CMU), Python-first, liberal BSD license, performance/debugging tools
- Weaknesses: scene-graph (older model vs ECS/Node-Scene), smaller community than Godot, weaker headless/server story, less active development
- Reusable components: scene graph, Python bindings, collision/physics integration, asset pipeline
- Integration possibilities: alternative Python-friendly runtime; candidate but not selected
- Compatibility: Revised BSD — permissive
- Maintenance status: maintained; stable releases (1.10.x)
- Research depth: DOCUMENTATION_REVIEWED
- Source references: [Wikipedia](https://en.wikipedia.org/wiki/Panda3D) [GitHub](https://github.com/panda3d/panda3d)
- Adoption decision: NOT selected as primary (Godot chosen). Documented as a viable BSD-licensed Python runtime candidate.
