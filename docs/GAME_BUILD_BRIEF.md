# Blender -> Godot game build brief

Status: authorized to build. User confirmed the existing Alpine terrain through the environment clarification. No playable game or achieved frame rate is claimed yet.

## Locked requirements

- Use the recommended Blender/bpy asset factory + Godot runtime architecture.
- Zero paid resources, paid assets or required paid services.
- Native 1920 x 1080 rendering target, 60 FPS target (16.67 ms/frame).
- Do not confuse a 60 FPS cap, 60 Hz physics, video frame rate or UI viewport size with measured 1080p gameplay performance.
- Preserve the completed Alpine production and all unrelated work.
- Do not base the architecture on the user's laptop or ask for its RAM/OS again.
- First implementation milestone: a bounded playable slice, not a claim of a complete GTA-scale game.

## Confirmed environment

The user selected **existing Alpine terrain**: adapt the mountain-and-lake Blender environment into an optimized playable area with a road. Preserve the cinematic source separately.

Proposed gameplay default, unless changed: third-person walking and a drivable vehicle, enter/exit interaction, collision, follow camera, restart and pause controls. A small environment must work before expanding the world.

## Skill inventory and usage plan

The existing upstream Blender library contains 94 skills, plus the local realistic-production guide. Added the MIT-licensed `godot-gdscript-patterns` skill from `wshobson/agents`, pinned in `.claude/GODOT_SKILLS_SOURCE.json`; license retained in `.claude/GODOT_SKILLS_LICENSE`. Total currently installed: 96. Relevant set: 31 skills. These are guidance, not substitutes for executable tests or governing instructions.

| Phase | Relevant skills | Required application / evidence |
|---|---|---|
| Direction and scope | blender-director, genre-open-world-sandbox, genre-racing-sports, realistic-blender-production | Locked environment, controllable slice and explicit acceptance gates |
| Environment | environment-artist, procedural-modeling, geometry-nodes, vegetation-artist, scene-assembly, set-dressing | Modular low-cost terrain/roads/props, deliberate composition and reusable instances |
| Modeling | blender-modeler, hard-surface, vehicle-artist, character-artist, retopology | Correct proportions and scale; separate moving car parts; economical meshes |
| Materials and appearance | materials, texture-workflow, uv-workflow, realistic-style, lighting, lookdev | Baked portable PBR maps, validated UVs/normal orientation, readable controlled lighting |
| Motion and camera | rigging, animation, camera-cinematography | Character/vehicle motion and an actual playable follow camera, not a prerecorded video |
| Runtime | godot-gdscript-patterns | Typed Godot 4 scripts, reusable scenes, state/input separation, physics-step motion and profiling |
| Optimization and interchange | asset-optimization, lod-pipeline, collision-proxy, export-pipeline, godot-export | Explicit budgets, LOD/culling, simplified colliders, GLB exports and real Godot import validation |
| Verification | qa-review | Playable build, input/collision checks, screenshots, native-resolution and frame-time evidence; limitations disclosed |

Skills are read and applied at their relevant build stage. Installation alone is not evidence that every checklist has passed. Godot runtime/import/export-template availability must be established in the current sandbox; the earlier Mesa proof does not prove those capabilities.

## Delivery gates

1. Engine/tooling bootstrap without paid infrastructure; pin executable/runtime version and preserve licensing.
2. An actual game project that imports and runs; no fabricated engine API or browser mock presented as Godot.
3. Interactive walking/driving and stable collision/camera behavior in the selected environment.
4. Visual QA on real engine output, with materials checked after import.
5. Explicit native-1080p settings and repeatable gameplay performance capture. Record renderer/test environment and frame-time percentiles. If 60 FPS is not measured, report the target as unmet rather than equating configuration with achievement.
6. Source project, reproducible asset generation, controls/readme and playable export/preview where the available tooling permits.

The earlier embedded-bpy bake shutdown issue remains disclosed in `VIRTUAL_GPU_BPY_GAME_ENGINE_AUDIT.md`; do not silently promote that workaround into proof of a stable long-lived bpy runtime. Prefer isolated authoring workers and a real Godot gameplay runtime.
