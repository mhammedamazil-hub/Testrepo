# Short Hop / Time Attack — v0.5 evidence

## What changed

The v0.4 indefinite hover/airborne recharge controller was replaced with **short, finite cold-gas-inspired hops**. Lift, forward/boost thrust, braking and stabilization share one supply. No airborne re-arm/refill; empty or powered-time ceiling means gravity with no free landing force. Touchdown returns normal driving without restoring charge. The 6s powered ceiling, 2.8s automatic descent and 20s ground refill are **game-balance settings, not official Tesla specifications**. Normal driving/walking remain.

The track now has original red/ivory kerbs, aggregate/rubber asphalt detail retaining the original base texture, checker start paint, branded gantry, reflectors and corner chevrons. No new dynamic lights/shadow maps; compatible static art is merged and repeated pieces instanced. Existing road geometry/colliders are unchanged. Kerbs are cosmetic trackside art, not a new tire-rumble solver.

Time Attack adds launch countdown, three ordered sector splits, same-assist benchmark deltas, saved clean personal best and Gold/Silver/Bronze. Recovery/hops/changed assist invalidate the current attempt, not the following lap. Solo time trials, not multiplayer or AI opponents.

## Validation

- **57 Python tests:** source, provenance, preserved graphics/collision settings, finite-thruster guards, race invalidation, actual social-capture hashes.
- **35 Node tests:** ground physics/circuit, finite gas/launch/exhaustion/gravity/ground refill, race state/storage/comparison, static matrix equivalence, no-op DOM updates and existing optimizations.
- **12 real Chromium DOM/touch cases:** wheel/arrows, portrait/landscape, driving/hop controls. New PB/sector readouts, race header and route hint included in non-overlap checks.
- **39 actual WebGL/runtime checks:** no browser runtime errors; real terrain/model/grass and new track art; unchanged HUD node identity; A/B render readback; independent multi-touch steering/pedals/lift/boost; countdown; bounded hop and no airborne refill; landing/exit safety; walking, pause/focus and full race/PB persistence.
- **Full runtime lap:** actual `AlpineGame.tick` + Rapier + route + countdown + TimeTrial, driven only with test pursuit **input**, no transform/speed assignments after reset. **121.60 simulated seconds**, Gold, three splits **31.77 / 61.83 / 92.13s**, maximum centerline distance **0.71658 m**; clean result and local-storage PB verified. `runtime-time-trial.json`.
- Production build and whitespace checks pass. Large Rapier chunk warning remains.

## Measured scope (not physical-device FPS)

`static-forest-comparison.json`: 141 static scene nodes. Same camera/settings/scene before/after static matrix freezing: **192 submissions / 997,012 triangles in both**, **zero pixel difference** at 994×522. Median five runs of 200 `scene.updateMatrixWorld()` calls: **7.4 → 4.1 ms** locally. This measures matrix work, not whole-frame speed or tablet FPS. Camera vectors are reused and HUD text/gear DOM is only replaced on changes.

`vehicle-batch-comparison.json`: existing capability-gated exact-material car batching in the new scene **255 → 192 submissions**, identical triangle count; mean channel error ~0.0000173/255, one edge pixel exceeds four levels. Transparent glass unchanged; unsupported native multi-draw keeps the original path.

`night-pass-comparison.json`: existing night invisible-shaft bypass is separately measured with zero image difference. Do not add isolated numbers into a claimed universal whole-version speedup.

A 39-cell forest split was tested and **rejected**: additional draw submissions outweighed its small triangle reduction. The final forest retains one original instanced draw and every tree. New track art adds real cost (the earlier v0.4 scene had fewer objects); no whole-version FPS improvement is established just by adding detail.

Full's original ~2.07MP budget, texture/car assets, shadows, current-frame water reflections, ACES and vegetation remain. These actual screenshots/readbacks explicitly select the existing Performance preset under software Chromium for practical QA; **that is not the default or a hidden runtime downgrade**. No physical tablet/sustained thermal FPS test, universal 60 FPS, photorealism or validated real-vehicle stunt claim.

## Actual captures

- `launcher-ui.png`: actual 1200×630 lobby; source of the updated crawler JPEG (`social-preview.json`).
- `circuit-day.png`: actual finished lap, Gold/PB feedback and daylight circuit art.
- `landscape-wheel.png`, `landscape-arrows.png`, `portrait-wheel.png`: actual night circuit/control layouts.
- `hop-landscape.png`, `hop-portrait.png`: actual short-hop state and shared gas/time readout, not sustained-flight concepts.

[Official-source research and limitations](../../research/short-hop-and-time-attack.md) · [Asset/source credits](../../../game/CREDITS.md)
