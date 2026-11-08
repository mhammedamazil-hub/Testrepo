# Free runtime / rendering / vegetation survey

This is a **bounded relevant survey, not “every open-source library.”** Package installation and license research alone are not playable engines. GitHub license endpoint results, source URLs and exact license blob SHAs are retained in `runtime-license-survey.json`; `NOASSERTION` and errors mean unresolved metadata, not a verified license. Do not adopt those components on an assumed license.

## Decision

Keep the working Godot edition and build one original small Alpine framework using Three.js + Rapier + postprocessing, with real bpy authoring. These components run on free static GitHub Pages, require no paid GPU/server, and have inspected redistribution notices. This framework is **not an Unreal-level engine**: its shader, physics and renderer infrastructure comes from named upstream libraries. bpy does not replace a real-time renderer.

| Area | Relevant alternatives surveyed | Chosen / boundary |
|---|---|---|
| Full engines | Godot, UPBGE, Armory, O3DE, Panda3D, Urho3D/rbfx, Fyrox, Bevy, Stride, WickedEngine, Ursina, pygame | Preserve actual Godot build. Do not claim installed/tested ports to alternatives. |
| Browser rendering | Three.js, Babylon.js, PlayCanvas, regl, PixiJS | Three.js 0.187.0, MIT. Existing addon implements genuine planar reflected-camera water. Pixi is primarily 2D. |
| Native graphics abstraction | bgfx, wgpu, Filament, sokol | Relevant research, not integrated into a browser framework by merely listing them. |
| Physics | Rapier, Jolt, Bullet, cannon-es | Rapier compat 0.21.0, Apache-2.0; actual WASM/collision tests. |
| Effects / geometry acceleration | postprocessing, three-mesh-bvh, three-gpu-pathtracer | postprocessing 6.39.6 **Zlib**, actual GodRaysEffect. No path-tracing/AAA-performance claim. |
| Authoring | Blender / bpy | Real asset compilation, GLB export and protected-source hash. Not bundled into the browser. |
| Asset acquisition | Poly Haven API / CC0 library | Actual bounded source downloads, verified upstream MD5 and recorded SHA256. API repository software licensing is distinct from CC0 assets. |

## Assets actually used

- [Grass medium 01](https://polyhaven.com/a/grass_medium_01): acquired glTF has 17 variants, 28–6422 triangles each, despite the much larger advertised cinematic collection. Import actual **tiny-a, 79 triangles**, normalize to 0.42m, preserve its UVs, combine real diffuse and alpha.
- [Pine tree 01](https://polyhaven.com/a/pine_tree_01): full three-tree source has **17,182,252 triangles / 948,849,556-byte geometry**. Deliberately reject that binary for mobile. Apply the actual photographic twig/opacity island to our optimized **412-triangle** 3D branch-card scaffold. This is an adaptation, not a full scan import.
- [Pine bark](https://polyhaven.com/a/pine_bark): actual photographic diffuse/GL-normal maps on the trunk.
- [Leafy grass](https://polyhaven.com/a/leafy_grass): actual photographic ground diffuse, GL-normal and ARM maps in the custom runtime; diffuse/normal in Godot.

Source authors, URLs, download hashes and bytes: `library-catalog.json`. Compiled geometry/map hashes and precise modifications: `game/assets/library/manifest.json`. **Powered by Poly Haven** appears in the game credits. Legacy OpenGameArt CC-BY-3.0 attribution is retained, not relabeled MIT or CC0.

## Water / god rays

- Custom runtime: Three Water's mirrored-camera planar render with clipping, current scene objects and animated normal distortion/Fresnel; lower-resolution reflection target, native 1080p main view. Real-time reflections, not static sky masquerading as reflection.
- Godot: shared-world mirrored SubViewport camera at 512×288, recursion excluded via layers, projective water sampling; previous panorama retained only for out-of-frustum fallback.
- Custom shafts: postprocessing's depth-occluded screen-space scattering source. Godot shafts: original bounded 32-tap screen-space sky-depth masking. Neither is a full volumetric/path-traced atmosphere.
- WebGPU-only FFT water and experimental BVH real-time ray tracing were not selected as the baseline: narrower compatibility and no validated mobile/SwiftShader path here.

## Skills applied

Existing downloaded Blender skills: vegetation-artist (instancing/budget), lighting (sun/occlusion), materials/texture/UV workflow (correct opacity and atlas islands/PBR), asset-optimization/LOD-pipeline (79/412 triangles; reject 17M-triangle pine), export-pipeline/godot-export (actual GLB/material/transform transfer), collision-proxy and QA-review (actual solver and screenshot evidence). These are guidance, not proof of runtime performance.

## Repository license metadata snapshot

Only the chosen runtime components have their exact installed license texts bundled. This broader list is not a claim that all projects were installed, audited or incorporated.

| Repository | GitHub license metadata | Evidence |
|---|---|---|
| blender/blender | NOASSERTION | [license source](https://github.com/blender/blender/blob/main/COPYING) |
| UPBGE/upbge | NOASSERTION | [license source](https://github.com/UPBGE/upbge/blob/master/COPYING) |
| godotengine/godot | MIT | [license source](https://github.com/godotengine/godot/blob/master/LICENSE.txt) |
| mrdoob/three.js | MIT | [license source](https://github.com/mrdoob/three.js/blob/dev/LICENSE) |
| BabylonJS/Babylon.js | Apache-2.0 | [license source](https://github.com/BabylonJS/Babylon.js/blob/master/license.md) |
| playcanvas/engine | MIT | [license source](https://github.com/playcanvas/engine/blob/main/LICENSE) |
| o3de/o3de | NOASSERTION | [license source](https://github.com/o3de/o3de/blob/development/LICENSE.txt) |
| panda3d/panda3d | NOASSERTION | [license source](https://github.com/panda3d/panda3d/blob/master/LICENSE) |
| urho3d/Urho3D | unresolved | [license source](https://github.com/urho3d/Urho3D) |
| rbfx/rbfx | MIT | [license source](https://github.com/rbfx/rbfx/blob/master/LICENSE) |
| FyroxEngine/Fyrox | MIT | [license source](https://github.com/FyroxEngine/Fyrox/blob/master/LICENSE.md) |
| bevyengine/bevy | Apache-2.0 | [license source](https://github.com/bevyengine/bevy/blob/main/LICENSE-APACHE) |
| stride3d/stride | MIT | [license source](https://github.com/stride3d/stride/blob/master/LICENSE.md) |
| turanszkij/WickedEngine | MIT | [license source](https://github.com/turanszkij/WickedEngine/blob/master/LICENSE.txt) |
| armory3d/armory | Zlib | [license source](https://github.com/armory3d/armory/blob/main/LICENSE.md) |
| pokepetter/ursina | MIT | [license source](https://github.com/pokepetter/ursina/blob/master/LICENSE) |
| pygame/pygame | unresolved | [license source](https://github.com/pygame/pygame) |
| bkaradzic/bgfx | BSD-2-Clause | [license source](https://github.com/bkaradzic/bgfx/blob/master/LICENSE) |
| gfx-rs/wgpu | Apache-2.0 | [license source](https://github.com/gfx-rs/wgpu/blob/trunk/LICENSE.APACHE) |
| google/filament | Apache-2.0 | [license source](https://github.com/google/filament/blob/main/LICENSE) |
| dimforge/rapier | Apache-2.0 | [license source](https://github.com/dimforge/rapier/blob/master/LICENSE) |
| jrouwe/JoltPhysics | MIT | [license source](https://github.com/jrouwe/JoltPhysics/blob/master/LICENSE) |
| bulletphysics/bullet3 | NOASSERTION | [license source](https://github.com/bulletphysics/bullet3/blob/master/LICENSE.txt) |
| pmndrs/cannon-es | MIT | [license source](https://github.com/pmndrs/cannon-es/blob/master/LICENSE) |
| gkjohnson/three-mesh-bvh | MIT | [license source](https://github.com/gkjohnson/three-mesh-bvh/blob/master/LICENSE) |
| pmndrs/postprocessing | Zlib | [license source](https://github.com/pmndrs/postprocessing/blob/main/LICENSE.md) |
| gkjohnson/three-gpu-pathtracer | MIT | [license source](https://github.com/gkjohnson/three-gpu-pathtracer/blob/main/LICENSE) |
| regl-project/regl | MIT | [license source](https://github.com/regl-project/regl/blob/main/LICENSE) |
| pixijs/pixijs | MIT | [license source](https://github.com/pixijs/pixijs/blob/dev/LICENSE) |
| floooh/sokol | Zlib | [license source](https://github.com/floooh/sokol/blob/master/LICENSE) |
| Poly-Haven/Public-API | AGPL-3.0 | [license source](https://github.com/Poly-Haven/Public-API/blob/master/LICENSE) |
| Gdquest/godot-demos | MIT | [license source](https://github.com/gdquest-demos/godot-3-demos/blob/master/LICENSE) |

## Validation and scope

See `engine/README.md`, `docs/game/alpine-browser-validation.json` when the full mobile test completes, and native headless validation. A screen at 1080p, a 60 Hz solver or a successful software render **does not verify 60 FPS**. Physical-phone testing is not available here. Full engine ports, photoreal terrain/characters, GI/Lumen, production vehicle suspension and Unreal parity remain outside this delivered prototype. No paid services were provisioned.
