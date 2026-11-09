> Historical After Dark 0.2 evidence. Current controls, responsive rendering and corrected circuit are documented in [Circuit v3](../circuit-v3/README.md). Fixed-size 1080p checks below apply to the older build, not the new responsive pixel-budget settings.

# Alpine: After Dark — release validation

## Scope

Custom Alpine runtime only. The original cinematic and uploaded `roadster_lite.glb` retain their original SHA256 values. Godot sources remain as legacy; the publication workflow builds the custom edition at root and `/alpine/`.

## Executed checks

- **41 Python tests passed:** source protection, original model hash, compiled model/wheel nodes/hash, sky attribution/hash, raw crawler metadata, real screenshot/JPEG provenance, existing cinematic/recovery and library regressions.
- **12 actual Rapier WASM tests passed:** walking/jump, safe entry/exit, collisions/recovery plus dynamic mass, suspension loads, external impulses, airborne loss of traction, slope pitch, grass grip, coasting/braking and steering.
- **20 actual Chromium mobile-emulation gameplay checks passed; browser errors `[]`.** See `browser-validation.json`: actual WebGL2 render, default photographic night, dynamic 2200kg chassis/four contacts, launch, real multi-touch driving/braking/walking/look, exit, cancellation, garage/controls, day/night/headlights, pause/blur, portrait and live reflections.
- **Touch/desktop contrast regression passed.** Reviewing the actual gameplay screenshot exposed a sticky-hover contrast issue on the recovery button. Corrected after capture; `ui-contrast-validation.json` checks the real HTML/CSS with touch and desktop pointer modes. This is explicitly DOM-only, not additional gameplay evidence.
- Production Vite build passed. The ~5 MB JavaScript bundle includes Rapier WASM and triggers the existing large-chunk warning; this is not hidden as a performance success.

## Captures and link preview

- `launcher-1080p.png`: actual native game canvas.
- `launcher-ui.png`: actual 1200×630 first-screen UI captured from Chromium.
- `night-gameplay-1080p.png` / `night-gameplay-ui.png`: actual gameplay after touch driving, exit and recovery.
- `social-preview.json`: capture and JPEG hashes, conversion, credits. The published `social/after-dark-v2.jpg` is a 125,756-byte JPEG of `launcher-ui.png`, not generated concept art.

Roadster model: metarex.4d, CC-BY-4.0. Night photograph: Satara Night by Greg Zaal / Poly Haven, CC0-1.0. Full source URLs and modification disclosures ship in `world/credits.txt`, `world/roadster/model.json`, and `world/night/provenance.json`.

## Physics measurements and limits

`vehicle-benchmark.json` records actual flat/dry 60 Hz solver results: **2.433 s 0–60 mph**, **2.200 s / 29.092 m** braking from ~26.951 m/s to <0.1 m/s. Reproduce with `node engine/tests/vehicle-benchmark.js`. These are simulation results under explicitly estimated mass/power/tire/suspension/aero parameters, **not manufacturer-certified telemetry**. [Research and assumptions](../../research/roadster-physics-and-night.md).

The browser uses CPU SwiftShader in this environment. Very low software-rendering FPS is present in telemetry; this is functional evidence only. **Physical-phone performance and 60 FPS remain unverified.** Native 1920×1080 and 60 Hz physics do not establish rendering speed. The result is a playable prototype, not photorealism/Unreal/GTA parity.

## Publication

`.github/workflows/game-build.yml` validates and exports, publishes root plus `/alpine/`, then requests public raw HTML and image as a crawler, checks static Open Graph/Twitter tags, retrieves the real Roadster GLB and JavaScript bundle, and verifies the compatibility URL. A successful workflow is the public-host verification record; local test success alone does not establish deployment. Platform card support/cache refresh cannot be forced by metadata.
