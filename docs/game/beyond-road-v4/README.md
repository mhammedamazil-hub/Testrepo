# Beyond the Road — v0.4 release evidence

Actual local Chromium/WebGL2 screenshots, not AI concepts. QA explicitly selects the existing Performance preset under software rendering to complete deterministic tests; default Full quality/budgets are unchanged. This is not physical-tablet FPS evidence.

## Added

- Original sports-game-inspired, car-first startup lobby; working Drive / Flight selection, Garage, Settings and on-foot launch. Flight concept selected before implementation; garage concepts were not approved. No copied Rocket League assets.
- Matching touch flight HUD, finite boost ring, independent lift/down/boost/pedal inputs; six ordered air gates.
- Optional **fictional** force/torque Roadster flight, assisted landing, airborne exit guard and ground-circuit shortcut protection. Normal wheel-based driving and walking remain available.
- 10,845 additional original instanced grass plants, deterministic terrain placement, road/lake exclusions and GPU wind. Existing photographic grass retained.
- Unchanged-preset optimizations: exact cheaper road query, fewer temporary allocations, reduced diagnostic DOM updates, static-menu on-demand rendering, shader warmup, default drawing buffer lifecycle, night-only invisible-shaft bypass, and native exact-material vehicle multi-draw with unsupported-device fallback.

## Validation

- **52 Python tests** pass, including source/provenance, physical parameters, meadow corridor/terrain and preset/flight guards.
- **27 Node tests** pass: driving/circuit, flight forces/boost/landing, route equivalence, grass geometry and batching fallback/material preservation.
- **12 DOM/touch cases** pass across wheel/arrows, portrait/landscape and flight modes (`ui-input-validation.json`).
- **31 actual Chromium/WebGL checks** pass with no runtime errors (`browser-validation.json`): real scene launch, touch controls, separate gas/brake/steering and flight input sources, flight lift, boost, safe exit, landing to wheel solver, walking, pause/focus, settings and actual A/B readback.
- Full Rapier circuit endurance rechecked: one lap in **120.8667 simulated seconds**, maximum centerline error **0.72199 m**, minimum **4** wheel contacts. Test-only input pursuit, no runtime autopilot or scripted body movement.
- Production build and whitespace checks pass. Large Rapier chunk warning remains.

## Measured optimization scope

- `route-query-benchmark.json`: 5,000 exact nearest-road queries, five runs, median **261.543 → 27.391 ms (~9.55×)**. Only this CPU query, not game FPS.
- `vehicle-batch-comparison.json`: same scene/camera/materials/triangles, **238 → 175 recorded draw submissions (~26.5%)**; both 983,118 triangles. Mean channel error **0.0000173/255**, maximum 13 at an edge; one pixel differs by more than four levels. Not strictly pixel-identical and not a GPU/FPS claim. Native support is required; original rendering remains the fallback.
- `night-pass-comparison.json`: with batching active, invisible-shaft bypass separately reduces **181 → 175 submissions**, **zero pixel difference**, at 994×522. No silent texture/shadow/reflection or resolution reduction.

## Captures

`launcher-ui.png` is the actual 1200×630 startup screen used for the v4 JPEG share preview (`social-preview.json`). `landscape-wheel.png`, `landscape-arrows.png`, `portrait-wheel.png`, `flight-landscape.png` and `flight-portrait.png` show the running game and touch interface. Actual visuals remain stylized browser graphics; no universal photorealism, physical-tablet FPS, AAA-engine parity or real Tesla flight claim.

[Research and implementation limits](../../research/tablet-rendering-and-flight.md) · [Asset/source credits](../../../game/CREDITS.md)
