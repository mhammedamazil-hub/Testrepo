# Specialist skills applied to the Alpine game

The user's environment choice was **existing Alpine terrain**. The installed library contains the original 94 Blender skills, the local realistic-production guide and the newly pinned Godot patterns skill (96 total). These 31 relevant guides were routed to the implementation below; unrelated styles/genres were not mechanically mixed into the project.

| Guides | Concrete application / evidence |
|---|---|
| blender-director; realistic-blender-production | Resource audit, locked brief, isolated game output, original source hash protected, real-engine and visual tests; no fabricated 60 FPS claim. |
| genre-open-world-sandbox; genre-racing-sports | Traversable loop around a recognizable lake, distant massif landmark, four scenic markers, bounded playable slice before larger-world scope. |
| environment-artist; scene-assembly; set-dressing | Native valley/massif reuse, engineered lakeside road, guideposts, vegetation cells, playable foreground/midground/background in `main.gd`. |
| blender-modeler; procedural-modeling | Blender mesh generation, applied transforms, original heightfield retessellation and continuous Catmull-Rom road sampling in `build_assets.py`. |
| geometry-nodes | Reusable instancing/scatter guidance was reviewed; runtime instancing uses Godot MultiMesh. No claim that a Geometry Nodes graph is running in Godot. |
| hard-surface; vehicle-artist | Non-branded car with separate wheels, glass, lights and manufactured bevels; triangulated n-gon wheel caps before tangent export. |
| character-artist; rigging; animation | Original hiker, 11-bone skeleton, weighted mesh pieces, Idle/Walk NLA clips; actual Godot animation import asserted. Art is intentionally simplified, not photoreal approved. |
| materials; texture-workflow; uv-workflow | Projected terrain UVs, CPU-baked original albedo/tangent normal maps, proper non-color normals, repeatable asphalt map and embedded GLB textures. |
| realistic-style; lookdev; lighting | Meter-scale assets, outdoor directional/ambient lighting, existing CC0 photographic sky, water PBR/ripple shader, actual engine captures. The realism guide supplies criteria, not an automatic realism PASS. |
| camera-cinematography | Follow camera with smoothing, pitch limits, wheel zoom, rear view and spring-arm world collision; excludes controlled bodies. |
| vegetation-artist | CPU-rendered native spruce cutout, original placements filtered off road, spatially grouped instancing and distance limits. Billboards are disclosed. |
| retopology; asset-optimization; lod-pipeline | Original 2,224,092 unique cinematic polygons replaced with 61,400 terrain triangles plus economical gameplay assets; Godot generated mesh LOD import is enabled. No unverified hand-authored LOD chain is claimed. |
| collision-proxy | Primitive character capsule and vehicle box; static terrain/road triangle collision; stopped-car exit checks both door spaces. No cinematic forest meshes used for dynamic collision. |
| export-pipeline; godot-export | Actual GLB export, actual Godot import, real Web release export with matching templates; native coordinate/scale checked through gameplay physics. |
| godot-gdscript-patterns | Typed controllers, input actions, signals, reusable scripts, physics-step movement, checkpoint state, local config save and explicit profiling. Version pinned in `.claude/GODOT_SKILLS_SOURCE.json`. |
| qa-review | Fourteen actual-engine physics/state/import checks; separate rendered browser tests and frame-time evidence. Failed/intermediate tests are not silently promoted into success. |

## Performance decisions

- Keep native 1920 x 1080; no hidden render-scale reduction.
- CPU-bake authored material detail rather than transferring Blender procedural graphs.
- MultiMesh vegetation/guideposts and automatically generated mesh LODs.
- Remove per-glyph text shadows after high draw-call counts were observed; use inexpensive UI gradient backplates instead.
- Balanced outdoor lighting and contact blobs by default; optional enhanced real-time shadows through F2.
- Record wall-clock intervals, not clamped simulation delta; F8 starts a fresh measurement window. Headless physics checks never count as rendering benchmarks.
- The 60 FPS target remains an acceptance gate until measured in rendered gameplay on a declared test environment.

## Provenance

- `arjun988/blender-skills@8f778d2405a214b508d4c7d80742be8e43acdd52`, MIT, retained in `.claude/BLENDER_SKILLS_LICENSE`.
- `wshobson/agents@4bde3168b43c0655c4d00ea2726e631719908a6d`, Godot patterns, MIT, retained in `.claude/GODOT_SKILLS_LICENSE`.
- Local skill files are guidance only; actual installed Godot APIs, imports, source code, rendered pixels and runtime tests are the verification authority.
