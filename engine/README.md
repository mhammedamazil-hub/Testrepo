# Alpine: After Dark — Runtime 0.4

A free browser driving/exploration prototype with an original custom framework. Three.js renders the world; Rapier WASM simulates the dynamic vehicle and walking collisions. Blender/bpy is the offline asset compiler, not the browser runtime. No paid GPU, Steam integration or manufacturer endorsement.

## Play / build

- Main site after publication: https://mhammedamazil-hub.github.io/Testrepo/
- Compatibility URL: https://mhammedamazil-hub.github.io/Testrepo/alpine/
- `npm ci --prefix engine`
- `npm test --prefix engine` — actual Rapier suspension, inertia, acceleration/braking, wall collision, airborne behavior, slope gravity, grass grip, walk/jump, safe entry/exit and recovery tests.
- `npm run dev --prefix engine` — port 3001, binds 0.0.0.0 and accepts Arena preview hosts.
- `npm run build --prefix engine` — standalone static game in `.exports/alpine`.
- `node tools/game/beyond_browser_test.cjs` — real Chromium CDP multi-touch and WebGL2 QA using the separately downloaded test browser. Not a physical-phone benchmark.

Drive Roadster or Explore on Foot from the launcher. Touch driving supports both a drag-around-rim steering wheel and angular left/right buttons; switch below the steering control or in Controls. Actual ribbed gas/brake pedal shapes, a stopped-car D/R selector, independent camera touch and nearest-safe recovery replace the old joystick/pedal text buttons. Walking retains its own joystick. WASD/arrows move, mouse drag looks, Shift runs, Space jumps/brakes, E enters/exits, R recovers, N changes day/night, H toggles headlights, Escape pauses. Both driving modes support independent simultaneous steering, gas, brake and look inputs. Garage, controls and pause panels are functional.

## Roadster and real physics

The owner's repository-root `roadster_lite.glb` is preserved unchanged. `tools/game/prepare_roadster.py` uses bpy to compile its body, four independently spinning wheels/calipers, delivery textures and measured geometry into `public/world/roadster/`. Author: metarex.4d; CC-BY-4.0. `roadster-model.json` records source/output hashes, attribution and model-derived dimensions.

`src/physics.js` uses a **dynamic** 2200 kg rigid chassis and Rapier's four-wheel raycast vehicle controller: suspension load, tire forces, actual inertia/gravity/collisions, drag, wheel torque/power limits and load-limited longitudinal friction. Ordinary driving does not assign the body's position, speed or yaw. The walking character remains a kinematic collision controller, not a ragdoll. Mass, power, suspension, tire, inertia and aerodynamic parameters are disclosed estimates in `src/vehicle-spec.js`, not published Tesla measurements. Historical concept marketing is separated from simulation results in `../docs/research/roadster-physics-and-night.md`.

Measured flat/dry 60 Hz simulation: 0–60 mph **2.43 s**; stopping from 26.95 m/s takes **2.20 s / 29.09 m**. These are solver tests, not road tests or certified factory specifications. No Pacejka calibration, thermal/battery model, damage, tire deformation, buoyancy, rockets or suction fans.

## Beyond the Road: lobby, grass and fictional flight

The car-first sports-game-inspired lobby has real Play/Garage/Training/Settings actions and Drive/Flight selection. **Flight is opt-in game fiction, not a Tesla capability.** J / FLY arms it in the vehicle. Gas applies forward thrust, wheel/buttons steer, Space / Lift climbs, C/Ctrl / Down descends, Shift / Boost adds force using a finite charge, S / Brake air-brakes, and L / Land requests assisted landing. Exit is blocked while armed; recovery disarms. Six air gates use 3D swept crossings. Ground driving/walking remain the default.

**10,845 additional ground-conforming instanced grass plants** use original tapered blades and GPU wind, retaining the existing photographic grass. No replacement car/sky or hidden resolution reduction. Full's ~2.07 MP budget and existing texture/shadow/reflection settings remain unchanged. Native same-material multi-draw car batching (with unchanged fallback), invisible-shaft bypass, active-material prewarming, object reuse, exact cheaper route queries, throttled diagnostics and on-demand static lobby rendering reduce avoidable work. They do not guarantee every tablet's FPS or ultra-realism. [Research, actual A/B pixel/workload results and limits](../docs/research/tablet-rendering-and-flight.md).

`node tools/game/beyond_ui_test.cjs` validates real touch/layout for driving and flight. `node engine/tests/route-query-benchmark.js` is only a CPU query microbenchmark, not a whole-game speedup. Build additional grass with `python tools/game/build_meadow.py` after the graded terrain (NumPy required). [Release evidence](../docs/game/beyond-road-v4/README.md).

## Corrected circuit and mobile HUD

The custom road is a smooth 640-point, 10 m wide loop over a separately graded terrain derivative. The previous terrain intersected the road at 45/160 sampled center points (up to 0.67 m). Render/collision road vertices now match, all 960 lane samples pass clearance/ray tests, and an actual input-driven Rapier endurance test completes a lap with four contacts throughout. Physical guardrails, road-corridor decoration exclusion, forward swept gates/finish and nearest-safe recovery preserve useful progress. Optional road assist eases/caps force requests and requests braking before bends; it never scripts the body or steers automatically.

Compact progress/timer, live route map, suggested bend speed, wrong-way/off-road prompts and a smaller speed/gear HUD replace the oversized telemetry card. [Evidence, reproduction and limits](../docs/game/circuit-v3/README.md). AI-generated images in `../docs/design/` are user-selected concepts, not game screenshots.

## Night, presentation and social cards

Default night uses **real Milky Way photography**, Satara Night by Greg Zaal / Poly Haven (CC0), plus art-directed moon/fill lighting and car head/brake lights. It is not an astronomically accurate local sky. Daytime, planar water reflections and occluded daytime sun shafts remain available. Shadows, reflections and shafts are optimized intermediate buffers, not ray tracing or volumetric GI.

The responsive launcher is premium-PC-game-inspired, without fabricated reviews, player counts or storefront badges. Static HTML includes Open Graph/Twitter title, description and an absolute 1200×630 JPEG of the actual launcher. Crawlers need no JavaScript to read metadata. Platform card support and cache refresh are outside the game's control. The custom game is deployed to both root and `/alpine/`; Godot sources are retained as legacy, not built by this publication workflow.

## Authoring and boundaries

`tools/game/prepare_library_assets.py` compiles licensed Poly Haven foliage, terrain textures and a level contract. It preserves the Roadster/corrected terrain selection. Rebuild the custom circuit with `node tools/game/build_track.mjs` then `python tools/game/grade_track_terrain.py` (NumPy required); source terrain and cinematic remain unchanged. The original cinematic `output/Alpine_Mirror.blend` is not edited; its SHA256 stays in `level.json`. Tree cards use an isolated photographic needle island, not opaque cone/wood atlas regions. Provenance is in `game/assets/library/manifest.json` and `public/world/night/provenance.json`.

The view fills the actual portrait/landscape aspect without letterboxing or stretching. Full defaults to a ~1920×1080 pixel budget; explicit Balanced (~1280×720 budget) and Performance (~960×540 budget) modes can be selected in Controls. Actual dimensions adapt to viewport shape. **60 FPS is a target, not a verified physical-phone result.** CPU SwiftShader captures are functional evidence only. This remains a playable prototype with simplified terrain, vegetation and rendering, not Unreal/GTA parity or certified photorealism.

See `THIRD_PARTY_NOTICES.txt`, `../game/CREDITS.md`, and `../docs/research/roadster-physics-and-night.md`. The deployed `world/credits.txt` includes dependency notices and asset attribution, including “Powered by Poly Haven.”
