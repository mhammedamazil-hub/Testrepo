# BLENDER_INTEGRATION — Universal Game Engine

## Role
Blender is the primary 3D content creation, scene authoring, modeling, animation, procedural generation (Geometry Nodes), and visual foundation. Blender is NOT the game runtime.

## Intended capabilities (via Blender adapter, bpy)
- Headless Blender (background mode)
- Scene creation, object creation, mesh creation/editing
- Materials, textures, UVs
- Cameras, lighting, render settings
- Geometry Nodes (procedural modeling/terrain)
- Animation, rigging
- Import/export (glTF/GLB, FBX, OBJ, USD)
- Scene inspection, error detection
- Screenshot capture, render previews
- Scene complexity measurement, asset optimization, report generation

## Status in this environment
**UNAVAILABLE / BLOCKED.** Blender is not installed and cannot be installed in this sandbox (no root access; outbound network restricted to github.com, registry.npmjs.org, pypi.org — blender.org is not reachable). `bpy` is not importable.

All Blender-dependent features are therefore PLANNED at best and UNAVAILABLE until Blender is installed and tested in an environment where it is available.

## Asset exchange
Blender → Godot via glTF/GLB. Blender authors the scene/assets; Godot runs the game. This avoids forcing Blender to be a runtime.

## When Blender becomes available
1. Verify `blender --version` and headless operation (`blender --background --python ...`).
2. Implement the Blender adapter (bpy) against real Blender operations.
3. Test: create scene, create object, modify mesh, create material, render preview, capture screenshot, export glTF/GLB.
4. Mark Blender-dependent capabilities as VERIFIED only after actual execution.
