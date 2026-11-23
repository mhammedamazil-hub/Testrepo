# Research: Blender

## Identity
- Name: Blender
- Repository: https://projects.blender.org/blender/blender (git on developer.blender.org mirrors to GitHub)
- Official documentation: https://docs.blender.org/
- License: GPL-2.0+
- Language: C, C++, Python (bpy API)
- Architecture: monolithic 3D creation suite; bpy Python API exposes modeling, animation, rigging, Geometry Nodes, shading, rendering (EEVEE/Cycles), compositing, video editing, asset management; headless/background mode available
- Core technologies: bpy, BMesh, Geometry Nodes, EEVEE, Cycles, Audaspace (audio), OpenCOLLADA, glTF/FBX/OBJ/USD import/export
- Major features: modeling, sculpting, animation, rigging, Geometry Nodes (procedural generation), materials/shaders, rendering, camera systems, scene management, Python automation, headless mode
- Unique strengths: industry-grade open-source authoring; unmatched modeling/procedural (Geometry Nodes); Python automation; headless background mode; free
- Weaknesses: GPL license (copyleft), not a game runtime, heavy GUI-centric design, large install, no headless GPU rendering without a display/offscreen setup
- Reusable components: bpy automation, Geometry Nodes, glTF/GLB exporter, headless rendering
- Integration possibilities: central 3D authoring foundation for this platform; creates scenes/assets exported to glTF/GLB for Godot
- Compatibility: GPL — copyleft; Blender is used as an external tool (authoring), not linked into platform code, so GPL does not viral-infect the platform; but any code linking against bpy/Blender binaries would be affected
- Maintenance status: actively maintained by Blender Foundation; frequent releases
- Research depth: DOCUMENTATION_REVIEWED (architecture/licensing); EXPERIMENTED not possible here (Blender not installed)
- Source references: Blender license https://www.blender.org/about/license/; [UPBGE licensing discussion](https://devtalk.blender.org/t/monetization-of-upbge-game/16060/2)
- Adoption decision: SELECTED as central 3D authoring foundation (D-06), NOT the runtime. BLOCKED/UNAVAILABLE in this environment — Blender not installed and cannot be installed (no root, no blender.org network access).
