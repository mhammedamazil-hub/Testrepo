# Alpine Runtime 0.1

An **original small browser game framework**, not a from-scratch renderer or an Unreal replacement. Blender/bpy compiles licensed geometry, textures and a hashed level contract; Three.js handles WebGL2 rendering, postprocessing provides occluded sun shafts, and the actual Rapier WASM solver handles collision/character movement. `bpy` is an offline authoring API, not the browser's real-time runtime.

## Play / build (no paid service)

- Godot edition: https://mhammedamazil-hub.github.io/Testrepo/
- Alpine framework edition after deployment: https://mhammedamazil-hub.github.io/Testrepo/alpine/
- `npm ci --prefix engine`
- `npm test --prefix engine` — actual Rapier floor, walk/run/jump, enter/drive/brake/exit, wall collision and recovery tests.
- `npm run dev --prefix engine` — port 3001, binds 0.0.0.0 and accepts Arena preview hosts.
- `npm run build --prefix engine` — standalone static game in `.exports/alpine`; asset plugin copies only allowlisted Blender resources, not the repository.
- `node tools/game/alpine_browser_test.cjs` — real Chromium CDP touch input and WebGL2 rendering, using the existing downloaded test browser. This is emulation, not a physical phone benchmark.

## Authoring pipeline

`tools/game/prepare_library_assets.py` uses real bpy 4.2.23 to import the verified Poly Haven grass glTF, select its 79-triangle tiny-a mesh, normalize its transform, combine independent photographic opacity maps, and export actual GLBs. It adapts the photographic pine needle island and bark onto our 412-triangle branch-card LOD. The mixed source atlas's opaque cone/wood islands are explicitly excluded; applying the whole atlas to foliage would produce opaque rectangles. Compiled files have SHA256 hashes in `game/assets/library/manifest.json`.

The original cinematic `.blend` is not edited. Its SHA256 is carried in the bpy-produced `level.json`. Scene terrain, road, character, vehicle and placements are shared with Godot, not a disconnected sample scene. To rebuild library inputs, the free public `library-assets.yml` workflow acquires bounded verified sources; raw downloads stay in ignored `.cache`, not the final distributable.

## Framework boundaries

- `src/physics.js`: fixed 60 Hz kinematic controllers over actual Rapier trimesh collision; gravity, snap-to-ground, walking/running/jump, bicycle steering, acceleration/braking, blocked-door checks and recovery. This is not a full rigid-body suspension/tire simulator.
- `src/input.js`: keyboard plus independently owned touch pointers; source-counted held actions, look/joystick/pedals, cancellation and focus-loss release.
- `src/world.js`: shared GLB/PBR loader, cell-based vegetation instancing, real current-frame mirrored-camera water (512-square target), animated normals/Fresnel, sun/shadows and occlusion source.
- `src/main.js`: scene lifecycle, pause, collision-aware follow camera, checkpoints/laps/local best, HUD, telemetry and optional synthesized sound.
- Shafts: depth-occluded screen-space radial scattering; **not** true volumetric clouds, voxel GI or path tracing. Water: planar reflection; **not** ray tracing, fluid simulation or underwater refraction.
- Main view: native 1920×1080, 60 FPS **target**, 60 Hz physics. Shadows/reflections/shaft intermediate buffers are lower resolution. Physical-phone testing and verified 60 FPS are **not** claimed; CPU SwiftShader tests are functional/visual evidence only.
- Trees still use optimized cards and distant impostors; terrain, car and character are simplified. This is an improved playable prototype, **not photorealism or Unreal/GTA parity**.

Both engines remain separate, usable editions. Only **one** custom framework was created, and Alpine is playable in it; this does not pretend to implement or port the game to every surveyed engine.

## Licenses

See `THIRD_PARTY_NOTICES.txt` (Three MIT, Rapier Apache-2.0, postprocessing **Zlib**), shared `game/CREDITS.md`, and `docs/research/library-catalog.json`. The shipped `world/credits.txt` includes full dependency notices and “Powered by Poly Haven.” CC0 asset licensing is distinct from the API server repository's AGPL license. Existing CC-BY-3.0 legacy grass credit is preserved in the shared repository.
