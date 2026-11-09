> **Current primary edition:** [Alpine: After Dark](../../engine/README.md) — custom Roadster/night runtime; root and `/alpine/` now target that edition. This document preserves historical release evidence, not current vehicle/deployment claims.

# Licensed vegetation / live-water / custom-runtime release

## Play both published editions

- **Alpine custom framework:** https://mhammedamazil-hub.github.io/Testrepo/alpine/
- **Improved Godot edition:** https://mhammedamazil-hub.github.io/Testrepo/

Source release: `4487760bc9d0855f3f2ea2e54a86ff2032ec5726` on `arena/f0bb5c2d-testrepo`.
Clean build, both exports, Pages deployment and public HTTPS file checks: **[42507599886 — SUCCESS](https://github.com/mhammedamazil-hub/Testrepo/actions/runs/42507599886)**.
No paid services or GPU provisioning were used.

## Actually implemented

- Original small **Alpine 0.1 framework** around Blender/bpy asset compilation, Three.js rendering and actual Rapier WASM collision/gameplay. One custom framework was created; Alpine is playable in it, alongside retained Godot. This does not mean every surveyed engine was implemented or ported.
- Actual CC0 Poly Haven grass geometry (79-triangle tiny-a), photographic pine needle island and bark on an adapted 412-triangle branch-card scaffold, plus photographic ground PBR maps. The 17M-triangle/949MB pine source geometry was deliberately rejected.
- Current-frame mirrored-camera water in **both** editions: 512-square Three Water target; 512×288 shared-world Godot SubViewport. Animated normals/Fresnel. Godot's previous panorama is only an out-of-frustum fallback.
- Depth-occluded screen-space sun shafts in both editions. These are **not** true volumetric ray marching, GI, Lumen or ray tracing.
- Walking/run/jump, vehicle enter/drive/steer/brake/exit, actual collision, follow camera, mobile multi-pointer controls, cancellation/focus safety, pause, recovery and checkpoint/lap state in the custom edition.
- Fixed two visual QA failures before release: isolate the correct photographic needle island rather than stretching opaque cone/wood atlas regions; explicitly restore depth writing when converting GLTF BLEND foliage to alpha-tested opaque materials, preventing distant trees drawing over near branches.

## Evidence

| Check | Result |
|---|---|
| Python source/asset/provenance safeguards | **33 passed** |
| Actual native Godot physics/input suite | **26 passed** |
| Actual Rapier WASM physics tests | **5 passed** (multiple assertions each) |
| Actual Chromium mobile touch + WebGL2 custom game | **15 passed, no runtime errors** |
| Actual Godot WebGL2 enhanced-scene render + touch Start | **Passed, no browser runtime errors** |
| Main view | **1920×1080**, actual canvas and render captures |
| Original cinematic | SHA256 **unchanged**: `ef72c7f780af86dd6b89a07ae13aab9970d485ed782e835c19061c57b343dfc3` |
| Physical phones / verified 60 FPS | **Not tested / not verified** |

Raw actual browser records: [custom](alpine-browser-validation.json), [Godot](godot-library-browser-validation.json). Screenshots: [custom native 1080p](alpine-library-water-shafts-1080p.png), [mobile browser UI](alpine-mobile-browser.png), [Godot native 1080p](godot-library-water-shafts-1080p.png). These are rendered game captures, not generated-image substitutes. Native Godot runtime evidence in the JSON is CPU software rendering; low recorded software FPS is **not** a phone benchmark or 60 FPS proof.

## Explicit remaining boundaries

This is **not photorealistic, AAA, GTA-scale or an Unreal-level engine**. Characters, terrain and vehicle art remain simplified. Trees use cards/distant impostors; scatter objects are cosmetic rather than a fully collidable forest. Vehicle handling is kinematic/arcade, not a complete suspension/tire simulator. Screen-space shafts and planar water have the normal limitations of those techniques. 60 Hz simulation and a 60 FPS cap/target do not establish 60 FPS rendering on hardware.

Research is a bounded relevant **32-repository survey**, not an exhaustive review of every open-source library. See [survey and asset decisions](../research/open-source-runtime-and-assets.md), [framework architecture/build](../../engine/README.md), [compiled CC0-source provenance](../../game/assets/library/manifest.json), and [full third-party notices](../../engine/THIRD_PARTY_NOTICES.txt). Three is MIT, Rapier Apache-2.0, postprocessing **Zlib**; Poly Haven asset CC0 is distinct from its API server software license. Original Alpine scaffold/game code retains repository terms. Legacy CC-BY-3.0 grass attribution is preserved.
