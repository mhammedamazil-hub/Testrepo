# Alpine Mirror game — playable prototype status

## Verdict

**Playable prototype: PASS WITH NOTES. Native 1080p rendering: VERIFIED. Requested 60 FPS: NOT MET in the available software-rendering test.**

This is not a production-ready 1080p60 game, not a finished GTA-scale world, and not a photorealism approval. A configured 60 FPS cap or 60 Hz physics does not satisfy the rendering requirement.

## Delivered

- Real **Godot 4.4.1 Web release**, running in the Arena live preview.
- The original Alpine mountain/valley heightfields adapted to a new roughly **965 m lakeside road loop**.
- Third-person walking/running/jumping; a follow camera with collision, orbit and rear view.
- A Blender-authored car with steering/wheel animation, acceleration, braking, collision and stopped-car enter/exit checks.
- Four scenic checkpoints, lap timer, locally saved best lap, pause, recovery and mute controls.
- Original scene spruce placements, 1,551 filtered billboard impostors, CPU-baked terrain materials, original animated hiker and procedural ambience/motor sounds.
- Balanced lighting by default; F2 toggles enhanced real-time shadows without lowering the native render resolution.
- Source project under `game/`, asset-generation/build/test tools under `tools/game/`, specialist usage trace in `docs/GAME_SKILL_USAGE.md`.
- Downloadable Web package: `.exports/Alpine_Mirror_Web.zip` (generated outside Git). It includes actual WASM/PCK runtime files, licenses and credits. Serve it over HTTP(S), not `file://`.

## Verified evidence

| Gate | Result | Evidence |
|---|---|---|
| Real engine/toolchain | PASS | Official pinned Godot executable, matching Web templates, original upstream checksums and local transport hashes; `docs/GODOT_TOOLCHAIN_PROVENANCE.json` |
| Original cinematic preserved | PASS | `.blend` SHA-256 still `ef72c7f780af86dd6b89a07ae13aab9970d485ed782e835c19061c57b343dfc3`; no production script/workflow modified |
| Blender -> Godot asset import | PASS | Native heightfields resampled to 61,400 terrain triangles; CPU-baked original materials; GLB assets imported by actual Godot |
| Actual engine physics/state | **14/14 PASS** | `headless-validation.json`: grounding, animation import, walking, entering, driving, braking, blocked moving exit, stationary exit, pause, checkpoints and recovery |
| Rendered browser gameplay | **PASS** | `browser-validation.json`: real Chromium WebGL 2 / SwiftShader, actual keyboard input, 4.23 m recorded drive displacement, braking and subsequent exit, no console errors |
| Native 1080p | **VERIFIED** | Both Godot viewport and actual browser canvas are 1920 x 1080; render scale is 1.0; actual PNG captures below |
| GitHub Pages hosting | **LIVE** | [Play online](https://mhammedamazil-hub.github.io/Testrepo/). [Deployment run](https://github.com/mhammedamazil-hub/Testrepo/actions/runs/42484554999) passed, including public HTTPS HTML/JS/audio-worklet checks, WASM/PCK binary headers and WASM MIME type. Pages source is Actions; the `github-pages` environment allows the active branch. Hosting checks do not certify rendered performance. |
| Source/evidence regression suite | **23/23 PASS locally and in CI** | Six new game integrity tests plus the existing 17 audit/production/recovery checks |
| Clean public-runner import/test/export | **PASS** | [First independent CI run](https://github.com/mhammedamazil-hub/Testrepo/actions/runs/42478054008): verified engine restore, clean asset import, 14 engine checks, 23 regression tests, actual Web export and downloadable artifact. Standard public-repository CPU runner; not a rendered FPS benchmark. |
| 60 FPS rendering | **NOT MET** | Final software-rendering sample reported 1 FPS and 1,814.5 ms P95 wall-clock frame interval across 9 samples. This is a short diagnostic, not a broad hardware benchmark. Hardware-GPU performance remains untested. |
| Photoreal / full open-world completion | NOT APPROVED | Simplified character/car, static tree impostors, no traffic/NPC/combat/mission systems |

Headless tests are deliberately labeled `rendered: false` / `fps_benchmarked: false`. They prove game logic and physics behavior, not graphics speed.

### Actual engine images

- [Menu — native 1080p](menu-1080p.png)
- [On foot — native 1080p](walking-1080p.png)
- [Driving — native 1080p](driving-1080p.png)

![Actual rendered driving view](driving-1080p.png)

These are captures of the actual Godot Web canvas, not image-generated mockups or offline Blender stills.

## Optimization and failures retained

The first version used expensive per-glyph label shadows and enhanced world shadows. Approximately 598 menu / 661–707 gameplay draw calls were observed. The current balanced profile uses gradient UI backplates instead of text shadows and cheap contact blobs instead of global shadow maps. The observed counts fell to **54 menu / roughly 69–75 gameplay draw calls**, with roughly 73k–77k total rendered primitives in sampled views. This is an optimization result, **not** proof of 60 FPS.

The initial browser harness used fixed short sleeps and simulation-time telemetry; under extremely slow software graphics it sampled stale state. That failed result remains in `browser-validation-initial.json`. The corrected harness uses wall-clock telemetry and waits for actual motion/state transitions while keys remain held. Its successful result is separately retained in `browser-validation.json`.

Earlier empty tree-impostor and wheel-tangent issues were fixed before this build: update source transforms before bounds/camera placement, bypass inherited cinematic compositing for the asset capture, assert nonempty alpha, and triangulate n-gon caps before tangent export.

The optional embedded-bpy authoring cleanup workaround remains disclosed in `game/README.md` and the asset manifest. It is not part of the Godot gameplay runtime. Headless tests skip audio-device creation; graphical browser builds load audio normally. Audible playback was not subjectively reviewed in the sandbox.

## Remaining acceptance work

1. Measure sustained native-1080p gameplay on an accessible real graphics device. The sandbox's CPU SwiftShader result cannot be advertised as 60 FPS or extrapolated into a hardware guarantee.
2. Continue CPU/GPU profiling with explicit frame-time and loading-stall budgets; keep native resolution visible and do not silently upscale a smaller render.
3. Improve close-up terrain detail, character deformation/animation, vehicle suspension/contact and environment art. The current car is arcade/kinematic, not a full wheel/suspension simulation.
4. Broaden browser/device testing and longer route/edge-case playtesting before production approval.

The game is now a concrete, editable, playable starting point using the recommended pipeline. The 60 FPS requirement remains explicitly unfinished.
