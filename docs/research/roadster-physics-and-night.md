# Roadster / After Dark research and implementation

## Identity and rights

The user supplied `roadster_lite.glb`. Its embedded `asset.extras` identifies **Tesla Roadster 2020**, author **metarex.4d**, [Sketchfab source](https://sketchfab.com/3d-models/tesla-roadster-2020-1fbf29e297bd4a17ac39a00a378441d8), **CC-BY-4.0**. Preserve the author, source, [license link](https://creativecommons.org/licenses/by/4.0/) and modification disclosure. This is not an official Tesla game or a manufacturer's model/telemetry endorsement.

Source SHA256: `e10253ef699ed774a4d9f749bd01d176931b8980a0e7af6a9b717bfd443a44d3`. The supplied binary is **not overwritten**. `tools/game/prepare_roadster.py` uses real Blender/bpy to normalize forward to -Z, ground the model, preserve UVs/materials, separate four rotating wheel and caliper pivots, merge draw groups, apply bounded decimation and cap delivery textures at 1024. Geometry remains an actual derivative of the supplied model, not a substitute primitive. Compiled hashes, measured dimensions and wheel pivots: `engine/roadster-model.json` and the shipped `world/roadster/model.json`.

## What can and cannot be researched

- [Tesla's current official Roadster page](https://www.tesla.com/roadster) now describes newer aero/thruster/fan variants. It is **not** a source of certified mass, spring/damper rates, tire curves or inertia for this older 2020-labelled art asset. Those newer systems are not simulated here.
- Contemporary reporting of the **2017 unveiling / expected 2020 concept** records the advertised 1.9-second 0–60 claim, AWD and 10,000 Nm wheel torque: [1](https://www.ign.com/articles/2017/11/17/elon-musk-reveals-tesla-semi-truck-roadster), [2](https://theweeklydriver.com/2017/11/telsa-announces-rocket-roadster-wicked-specs/), [3](https://techcrunch.com/2017/11/16/tesla-unveils-the-new-roadster/). These are **historical announced claims**, not independently verified production-car test data. Do not label them current certified specifications.
- Model-derived wheelbase is approximately 2.922 m; dimensions approximately 4.626 m long × 1.891 m wide × 1.180 m high. These are **measurements of this art asset in assumed metre units**, not factory engineering drawings.
- No lookalike `tesla-order` domain was used as an authoritative manufacturer source. No paid source/API or proprietary vehicle telemetry was acquired.

## The actual simulation

`engine/src/physics.js` replaces the prior kinematic car with a **dynamic Rapier rigid body** and its [DynamicRayCastVehicleController](https://github.com/dimforge/rapier.js/blob/master/src/control/ray_cast_vehicle_controller.ts). It uses four independent raycast wheel springs/dampers, body inertia/rotation, continuous collision detection, load-dependent tire forces, front Ackermann geometry and AWD. Ordinary driving does **not** assign chassis speed, yaw or translation. Direct resets are only for spawning/recovery.

| Parameter | Value / status |
|---|---|
| Gravity / fixed simulation | 9.81 m/s² / 60 Hz |
| Mass | **2,200 kg — estimate** |
| Peak power | **800 kW — estimate** |
| Wheel torque ceiling | 10,000 Nm — historical concept claim used as a game ceiling |
| Drive split | 40% front / 60% rear — estimate |
| Centre-of-mass height | 0.55 m — estimate |
| Principal inertia | 3,800 / 4,300 / 900 kg·m² — estimate |
| Spring rest / travel | 0.24 / 0.16 m — estimates |
| Spring rate | Rapier normalized stiffness 45 s⁻²; approximately 99 kN/m per wheel for this body mass — estimate |
| Compression / rebound | 5.5 / 7 normalized damping — estimates |
| Dry road / grass grip | 1.35 / 0.65 estimated force coefficients |
| Drag area / downforce area | 0.58 / 0.35 m² — estimates |
| Maximum service brake force | 30 kN, capped by available tire load/grip — estimate |

The raycast solver's `frictionSlip` is not a measured tire coefficient. An additional explicit load-based longitudinal force cap accounts for previous-step lateral impulse through a friction-circle approximation. Wheel forces disappear without ground contact; no airborne steering torque or forward thrust is applied. Aerodynamic drag scales with speed squared, power limits drive force at speed, rolling resistance requires contact, and reverse input brakes opposing motion before reversing. Parking brakes do not pin the body's transform: an external impulse can still move it.

The chassis uses compound collision proxies; nearby tree trunks and rocks now have fixed collision proxies. Those proxies are not exact scan geometry. Walking retains a capsule/character controller under Earth gravity, not a full ragdoll. This is a real force/impulse-driven **game simulation**, not a validated OEM multibody/tire/thermal simulator. Tire deformation/Pacejka curves, battery SOC/thermal management, full differential/ABS electronics, damage deformation, suspension link geometry and water buoyancy are not implemented. Rocket thrusters, suction fans and flight are not implemented.

## Reproducible measurements and checks

[Actual solver benchmark](../game/after-dark/vehicle-benchmark.json): approximately **2.433 s to 60 mph** and **29.092 m braking distance** from ~26.95 m/s to <0.1 m/s on the flat dry test plane. These are actual integration results under the documented estimates, **not** a reproduction of Tesla's 1.9-second marketing claim. No timed acceleration animation or speed assignment is used to manufacture a target result.

Reproduce the flat-road benchmark with `node engine/tests/vehicle-benchmark.js` (optional output JSON filename as the final argument). Tiny floating-point differences between test-plane tessellations are expected; the rounded figures are not factory claims.

`npm test --prefix engine` includes actual WASM tests for body mass/gravity, four load-bearing wheels, body response to an external impulse, airborne loss of traction, physical pitch on a slope, surface-dependent acceleration, coasting/braking, steering/Ackermann geometry, collisions, walking/jump, entry/exit and recovery.

## Night photography, lighting and UI

The night sky is **Satara Night**, actual photographic stars and Milky Way by **Greg Zaal / Poly Haven**, [CC0 source](https://polyhaven.com/a/satara_night). The bounded downloader verifies the upstream MD5, records source/output SHA256, resizes to 4096×2048 and feathers the lower hemisphere to dark navy so village/ground imagery is not a landscape backplate. Provenance is shipped at `world/night/provenance.json`. The Milky Way is not an AI-generated concept image. Its appearance is photographic/art-directed long exposure, not naked-eye brightness or a location/time-accurate star catalogue simulation.

Night uses cold directional/ambient fill, real spot-light headlights with distance falloff, lamp emission, brake-light response, and current-frame planar lake reflections. Lighting exposure is art-directed for readable driving, not photometric certification. Day/night and headlights are real user toggles.

The launcher is inspired by premium PC game/library presentation: launch directly in the Roadster, optional on-foot start, functional garage/specification and controls panels, pause/resume/recovery, restrained navigation and live vehicle HUD. No fake reviews, player counts, Steam integration or platform endorsement.

## Link previews

Open Graph + Twitter large-image metadata exists in **raw HTML**, with a public absolute HTTPS 1200×630 JPEG made from the **actual launch screen**, not unrelated artwork. The game name is “Alpine: After Dark — Roadster Expedition.” The custom game becomes the main `/Testrepo/` site; the prior `/Testrepo/alpine/` URL remains usable. Godot source is preserved but no longer rebuilt as the primary release.

Compatible unfurling clients such as Discord can display the title and image without running WebGL/JavaScript. Metadata cannot force every platform to unfurl, override user settings or instantly clear previously cached cards; a newly versioned image URL is used. No Discord/Steam account or API integration is necessary or claimed.

## Fidelity and performance boundary

Actual Roadster art, real photographed stars, PBR/reflections and force-driven physics improve the prototype. **This is not photorealism/AAA/Unreal parity**, and 60 Hz physics is not proof of 60 FPS rendering. Native 1920×1080 is retained; physical-phone frame rate is unverified. CPU SwiftShader tests are functional/render evidence only.
