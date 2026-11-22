# Research: UPBGE (Uchronia Project Blender Game Engine)

## Identity
- Name: UPBGE
- Repository: https://github.com/UPBGE/upbge
- License: GNU GPL-3.0 (as a whole; individual files may differ but compatible)
- Language: C++, Python
- Architecture: fork of Blender focused on the old Blender Game Engine; fully integrated with Blender (modeling, animation, game dev in one environment); uses Blender EEVEE for real-time rendering; Bullet Physics for simulation; OpenAL/Audaspace audio; logic bricks + logic nodes + Python scripting
- Core technologies: Blender fork, EEVEE renderer, Bullet physics, OpenAL/Audaspace, logic bricks/nodes, Python (bge/bpy), glTF/FBX/Collada/OBJ/STL import/export
- Major features: real-time PBR rendering, SSR, GTAO, bloom, soft shadows, volumetrics, rigid-body physics, obstacle simulation, pathfinding, 3D audio, logic bricks/nodes, Python scripting, no export step needed (blend-native)
- Unique strengths: superb Blender integration (authoring + runtime in one), no asset export step, Python scripting
- Weaknesses: GPL copyleft (blenderplayer and scripts referencing UPBGE/Blender API bound by GPL), project described as under-developed/inactive, performance concerns (UPBGE 0.3+ noted as poor performance), desktop-only exports
- Reusable components: Bullet physics integration, EEVEE rendering, Python game logic
- Integration possibilities: Blender-native runtime; rejected for this platform due to GPL and maturity
- Compatibility: GPL-3.0 — copyleft, incompatible with a permissive commercially-friendly platform as a core runtime
- Maintenance status: described as under-developed/inactive; syncs with Blender but slowly
- Research depth: DOCUMENTATION_REVIEWED
- Source references: [GitHub UPBGE](https://github.com/UPBGE/upbge) [dlab.ninja](https://www.dlab.ninja/2025/06/blender-game-engines.html) [Blender Artists](https://blenderartists.org/t/will-game-engine-get-back-to-blender-upgraded/1206773/58)
- Adoption decision: REJECTED as runtime. GPL copyleft + inactivity/performance concerns conflict with project goals.
