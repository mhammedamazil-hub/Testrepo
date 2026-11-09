> Historical v0.4 implementation research. The continuous hover/airborne recharge described below is superseded by [v0.5 finite-thruster corrections](short-hop-and-time-attack.md). Prior optimization measurements remain scoped to v0.4.

# Tablet smoothness, grass and fictional Roadster flight

## Research: preserve the existing Full preset before lowering quality

The WebGL specification recommends leaving `preserveDrawingBuffer` false where possible because preserving it can significantly hurt performance on some platforms. Same-render synchronous readback is the documented capture alternative [1](https://registry.khronos.org/webgl/specs/latest/1.0/). We previously kept it true for screenshot convenience; that is now removed. The canvas is opaque with a fully rendered sky/background; screenshots use compositor capture or readPixels in the rendering call. This does not lower resolution, texture detail or lighting.

WebGL Insights recommends reusing render-loop objects, reducing transient allocations and updating uniforms only as needed [2](https://webglinsights.github.io/tips.html). Three.js documents `compileAsync` as shader precompilation using KHR_parallel_shader_compile where available, and documents renderer draw-call/triangle diagnostics [1](https://threejs.org/docs/pages/WebGLRenderer.html). Precompilation moves some first-use work into loading; it is not a guarantee against every driver/shadow/postprocess/light-variant hitch.

### Verified repository-specific waste

Installed `postprocessing` 6.39.6 `EffectPass.render()` calls every contained effect's update unconditionally. `GodRaysEffect.update()` runs depth copy, light-source rendering, optional blur and radial scattering even with blend opacity zero. Our night mode made the sun shafts invisible by setting opacity to zero, but retained that work. The new pipeline chooses the existing shaft+ACES pass for day/shafts-on, and an ACES-only pass when shafts are not visible. It does **not** lower daytime shaft settings. The actual same-scene render A/B report lives in `../game/beyond-road-v4/night-pass-comparison.json`; it compares the invisible-but-updating path against the bypass, with identical camera, grass, render dimensions and graphics settings. It is not a whole-version GPU benchmark.

Three.js Water already disables shadow-map auto-updates inside its mirror render. We inspected the installed source; that optimization is **not** claimed as new work or a new speedup. The current-frame 512² reflection is retained.

### Same-material car batching

Three.js documents BatchedMesh for geometries with shared materials and compatible attributes [1](https://threejs.org/docs/pages/BatchedMesh.html). The supplied compiled car has 49 primitives; 28 opaque wheel/caliper/source pieces can be grouped into seven exact-material batches. Original vertices, UVs, normals/tangents, texture/material objects and animated transforms are retained. Transparent glass keeps its original sorting path. We require native WEBGL_multi_draw; unsupported devices retain the unchanged mesh path. Matrix texture lookups/CPU storage have costs, so draw-call reduction is not a universal GPU-time guarantee.

In the saved actual same-scene A/B, recorded renderer submissions fell **238 → 175 (~26.5%)**, with **983,118 triangles in both paths**. Mean absolute RGB channel error was **0.0000173 / 255**, maximum 13 at an edge, with one pixel exceeding a four-level difference (~0.000193% of the image). This is not claimed bit-identical: tiny rasterization/rounding differences are explicitly recorded. `vehicle-batch-comparison.json` contains the measurements.

With batching active, the night-pass A/B separately fell **181 → 175 submissions**, with **zero pixel difference**. Tests selected the same Performance preset on both sides under software rendering; these are isolated workload/image checks, **not physical-tablet FPS measurements**.

### Implemented without changing the chosen preset

- Do not preserve the presented drawing buffer unnecessarily; opaque canvas.
- Bypass invisible shaft update/render work at night or with shafts toggled off. ACES remains active.
- Reuse world transform scratch vectors/quaternions, wheel state objects and the vehicle collision predicate.
- Exact nearest-route queries compare squared distances and reuse a result instead of allocating candidate objects/square-rooting every segment. All segments remain checked—no approximate shortcut that could break recovery.
- Cache DOM lookups; refresh HUD values at 20 Hz and diagnostic statistics at 4 Hz rather than sorting/frame-allocating diagnostics and rewriting the whole HUD every render. The 3D view still targets 60 Hz and the real solver stays at fixed 60 Hz. HUD number refresh is intentionally separated from 3D rendering.
- Render the already-static lobby/pause scene only when dirty. Its simulation/wind time was already frozen; no existing animation is removed. Continue rendering every gameplay frame. Stop invisible-tab render work.
- Precompile active scene material shaders during loading. No claim that every future daylight/shadow/postprocessing variant is prewarmed.
- Expose local FPS/draw-call information in Controls so device-specific bottlenecks can be observed, not guessed from screenshots.

**Unchanged:** default Full budget ~2.07 MP, all existing textures and supplied Roadster geometry, 1024² directional shadows / 512² car-light shadow, current-frame 512² water reflection, PBR/ACES, photographed day/night skies, original photographic grass and vegetation settings. Balanced/Performance remain explicit existing user choices; no new hidden auto-resolution reduction is introduced.

### CPU microbenchmark, not FPS

`node engine/tests/route-query-benchmark.js [output.json]` compares the historical v3 nearest-query implementation and the exact optimized version using the same 640-segment route and 5,000 deterministic queries. The saved local run measured median **261.54 ms → 27.39 ms (~9.55× faster for this query only)**. This cannot be converted into a 9.55× whole-game speedup or a physical-tablet FPS result. Geometry, recovery distances and segment selection are regression-tested separately.

## Grass, not just another painted texture

`tools/game/build_meadow.py` produces **10,845 deterministic ground-conforming plants**, sampled against the actual graded terrain. Lake/road corridor plants are excluded; source/output hashes and seed are shipped in `world/meadow/provenance.json`.

Each plant uses original, tapered, curved three-blade geometry (24 triangles), spatially instanced into shared-material cells. GPU vertex wind avoids per-blade CPU updates. The opaque blades avoid a new large alpha-blended overdraw carpet, receive existing lighting/shadows, and use root-to-tip vertex-color variation. Existing licensed photographic grass is retained. Cell bounds/frustum and distance culling prevent every plant being drawn from every view. Grass adds real geometry and shading cost; it is **not free** and instancing is not a promise of universal performance. This improves vegetation richness, not a certification of ultra-realism.

## Fictional flight mechanics and boundaries

The 2020-labelled model and disclosed estimated driving specification remain unchanged. Flight is **explicitly game fiction**, not a Tesla-certified capability, a validated aircraft or an implementation of a manufacturer's announced real thruster system.

- Opt-in from the lobby, Training, or J / FLY; normal driving remains unchanged by default.
- Actual dynamic Rapier chassis, Earth gravity, thrust forces, attitude stabilization torque and damping. No ordinary flight position/rotation/velocity assignment. Engagement does not teleport the vehicle.
- Hold Lift / Space to raise hover target, Descend / C / Ctrl to lower it, steering wheel/buttons/WASD to yaw/drive thrust, Gas for forward thrust, Brake/S for air-braking, Shift/Boost for extra force with a finite charge meter and regeneration.
- Land / L requests a controlled descent with horizontal damping and returns to wheel-driven ground mode when contact is established. Exit is blocked while flight is armed. Recovery disarms flight and restores a safe road spawn.
- Six 3D air gates with swept-volume crossing and altitude checks. UI reports altitude relative to the lake/world datum, not a certified altimeter or terrain-clearance guarantee.
- Small original emissive plumes indicate the fictional thrusters without adding expensive new dynamic lights. No propellant simulation, aerodynamic validation, damage, realistic jet exhaust, manufacturer ADAS or autonomous navigation.

## What remains unverified

We cannot honestly promise unchanged ultra-realistic graphics at 60 FPS on **every** low-end device. Available GPU, memory bandwidth, thermal throttling, browser/WebGL driver and sustained workload impose real limits. Software Chromium tests verify rendering, pixel equivalence for the isolated night-pass change, touch behavior and dynamics; they do not establish the user's tablet FPS. The game remains a stylized playable prototype, not photorealism/AAA/Rocket League parity. No Rocket League assets, branding, accounts, paid GPU or paid resources are used.
